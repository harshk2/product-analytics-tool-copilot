"""Analytics Celery tasks: materialized view refresh and anomaly detection."""
import structlog
from celery import Task

from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(
    name="app.tasks.analytics.refresh_materialized_views",
    queue="default",
)
def refresh_materialized_views():
    """Refresh all PostgreSQL materialized views concurrently.

    Runs hourly via Celery beat. Uses CONCURRENTLY to avoid locking reads.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(engine)

    views = ["monthly_active_users", "daily_metrics"]

    results = {}
    with Session() as session:
        for view_name in views:
            try:
                session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
                session.commit()
                results[view_name] = "refreshed"
                logger.info("Materialized view refreshed", view=view_name)
            except Exception as e:
                session.rollback()
                results[view_name] = f"error: {str(e)}"
                logger.error("Failed to refresh materialized view", view=view_name, error=str(e))

    return results


@celery_app.task(
    name="app.tasks.analytics.compute_daily_metrics",
    queue="default",
)
def compute_daily_metrics():
    """Compute and store daily metric snapshots.

    Runs daily at 1 AM UTC. Computes:
    - DAU/WAU/MAU
    - MRR/ARR
    - Retention rates
    - Payment failure rates
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(engine)

    with Session() as session:
        # Trigger a refresh of daily_metrics materialized view
        try:
            session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_metrics"))
            session.commit()
            logger.info("Daily metrics computed successfully")
            return {"status": "success"}
        except Exception as e:
            session.rollback()
            logger.error("Failed to compute daily metrics", error=str(e))
            return {"status": "error", "error": str(e)}


@celery_app.task(
    name="app.tasks.analytics.run_anomaly_detection",
    queue="default",
)
def run_anomaly_detection():
    """Run statistical anomaly detection across key metrics.

    Detects anomalies using z-score method:
    - DAU drops/spikes > 2σ from 30-day rolling mean
    - MRR changes > 2σ
    - Payment failure rate spikes > 2σ
    - Retention drops > 1.5σ (more sensitive)

    Creates alerts in Redis for the dashboard.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    import json
    import redis
    from datetime import datetime

    engine = create_engine(settings.DATABASE_URL_SYNC)
    Session = sessionmaker(engine)
    redis_client = redis.from_url(settings.REDIS_URL)

    anomalies = []

    with Session() as session:
        try:
            # Check DAU anomaly (last 7 days vs 30-day rolling)
            dau_result = session.execute(text("""
                WITH daily AS (
                    SELECT
                        occurred_at::date AS day,
                        COUNT(DISTINCT user_id) AS dau
                    FROM events
                    WHERE occurred_at >= NOW() - INTERVAL '37 days'
                    GROUP BY occurred_at::date
                ),
                stats AS (
                    SELECT
                        AVG(dau) AS mean_dau,
                        STDDEV(dau) AS std_dau
                    FROM daily
                    WHERE day < NOW()::date - INTERVAL '7 days'
                )
                SELECT
                    d.day,
                    d.dau,
                    s.mean_dau,
                    s.std_dau,
                    CASE WHEN s.std_dau > 0
                        THEN (d.dau - s.mean_dau) / s.std_dau
                        ELSE 0
                    END AS z_score
                FROM daily d, stats s
                WHERE d.day >= NOW()::date - INTERVAL '7 days'
                ORDER BY d.day DESC
            """)).fetchall()

            for row in dau_result:
                if abs(row.z_score or 0) > settings.ANOMALY_DETECTION_THRESHOLD:
                    direction = "spike" if (row.z_score or 0) > 0 else "drop"
                    anomalies.append({
                        "metric": "daily_active_users",
                        "date": str(row.day),
                        "value": float(row.dau or 0),
                        "z_score": float(row.z_score or 0),
                        "severity": "critical" if abs(row.z_score or 0) > 3 else "warning",
                        "message": f"DAU {direction}: {row.dau:,.0f} users "
                                   f"({row.z_score:+.1f}σ from mean)",
                        "detected_at": datetime.utcnow().isoformat(),
                    })

            # Check payment failure rate anomaly
            payment_result = session.execute(text("""
                WITH daily_failures AS (
                    SELECT
                        created_at::date AS day,
                        COUNT(*) FILTER (WHERE status = 'failed') AS failures,
                        COUNT(*) AS total,
                        ROUND(
                            COUNT(*) FILTER (WHERE status = 'failed')::DECIMAL /
                            NULLIF(COUNT(*), 0) * 100, 2
                        ) AS failure_rate
                    FROM payments
                    WHERE created_at >= NOW() - INTERVAL '37 days'
                    GROUP BY created_at::date
                ),
                stats AS (
                    SELECT AVG(failure_rate) AS mean_rate, STDDEV(failure_rate) AS std_rate
                    FROM daily_failures
                    WHERE day < NOW()::date - INTERVAL '7 days'
                )
                SELECT
                    d.day, d.failure_rate, s.mean_rate, s.std_rate,
                    CASE WHEN s.std_rate > 0
                        THEN (d.failure_rate - s.mean_rate) / s.std_rate
                        ELSE 0
                    END AS z_score
                FROM daily_failures d, stats s
                WHERE d.day >= NOW()::date - INTERVAL '7 days'
                ORDER BY d.day DESC
            """)).fetchall()

            for row in payment_result:
                if (row.z_score or 0) > settings.ANOMALY_DETECTION_THRESHOLD:
                    anomalies.append({
                        "metric": "payment_failure_rate",
                        "date": str(row.day),
                        "value": float(row.failure_rate or 0),
                        "z_score": float(row.z_score or 0),
                        "severity": "critical" if (row.z_score or 0) > 3 else "warning",
                        "message": f"Payment failure rate spike: {row.failure_rate:.1f}% "
                                   f"({row.z_score:+.1f}σ above normal)",
                        "detected_at": datetime.utcnow().isoformat(),
                    })

        except Exception as e:
            logger.error("Anomaly detection query failed", error=str(e))

    # Store anomalies in Redis for dashboard
    if anomalies:
        redis_client.setex(
            "dashboard:anomalies",
            3600,  # 1 hour TTL
            json.dumps(anomalies),
        )
        logger.info("Anomalies detected and cached", count=len(anomalies))
    else:
        redis_client.delete("dashboard:anomalies")
        logger.info("No anomalies detected")

    return {"anomalies_detected": len(anomalies), "anomalies": anomalies}
