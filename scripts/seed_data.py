"""Data seeding script for realistic test data."""
import asyncio
import random
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

PLANS = ["free", "starter", "pro", "enterprise"]
PLAN_WEIGHTS = [0.50, 0.25, 0.20, 0.05]

COUNTRIES = ["US", "GB", "CA", "DE", "FR", "AU", "IN", "BR", "JP", "MX"]
COUNTRY_WEIGHTS = [0.35, 0.12, 0.08, 0.07, 0.06, 0.05, 0.08, 0.05, 0.04, 0.10]

ACQ_SOURCES = ["organic", "paid_search", "social", "referral", "email", "direct", "content"]
ACQ_WEIGHTS = [0.30, 0.25, 0.15, 0.12, 0.08, 0.07, 0.03]

EVENT_TYPES = [
    ("page_view", 0.40),
    ("feature_used", 0.20),
    ("button_clicked", 0.15),
    ("login", 0.10),
    ("search_performed", 0.05),
    ("dashboard_viewed", 0.04),
    ("export_created", 0.03),
    ("api_called", 0.03),
]

PAYMENT_METHODS = ["card", "paypal", "bank_transfer", "crypto"]
FAILURE_CODES = [
    ("insufficient_funds", 0.35),
    ("card_declined", 0.25),
    ("expired_card", 0.15),
    ("fraud_suspected", 0.10),
    ("3d_secure_required", 0.10),
    ("invalid_card_number", 0.05),
]


def weighted_choice(choices, weights):
    """Select a weighted random choice."""
    return random.choices(choices, weights=weights, k=1)[0]


def random_date(start: datetime, end: datetime) -> datetime:
    """Random datetime between start and end."""
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


async def seed_data(
    db: AsyncSession,
    user_count: int = 10000,
    days_back: int = 180,
) -> None:
    """Seed the database with realistic test data.

    Simulates a real SaaS product with:
    - Users signing up over time
    - Product events
    - Subscriptions with varying plans
    - Payment success/failure patterns
    - A retention "drop" around 6 weeks ago (to investigate)
    """
    from app.models import User, Event, Subscription, Payment

    print(f"Seeding {user_count} users with {days_back} days of history...")

    now = datetime.utcnow()
    start_date = now - timedelta(days=days_back)

    # ── Create Users ──────────────────────────────────────────────────────────
    users = []
    for i in range(user_count):
        signup_date = random_date(start_date, now - timedelta(days=1))
        plan = weighted_choice(PLANS, PLAN_WEIGHTS)

        user = User(
            id=str(uuid4()),
            email=f"user_{i}@example.com",
            created_at=signup_date,
            updated_at=signup_date,
            country=weighted_choice(COUNTRIES, COUNTRY_WEIGHTS),
            plan=plan,
            acquisition_source=weighted_choice(ACQ_SOURCES, ACQ_WEIGHTS),
            acquisition_channel=random.choice(["web", "mobile", "api"]),
        )
        users.append(user)

        if i % 1000 == 0:
            print(f"  Creating users: {i}/{user_count}")

    db.add_all(users)
    await db.flush()

    # ── Create Events ─────────────────────────────────────────────────────────
    # Simulate a retention drop ~6 weeks ago by reducing events in that period
    retention_drop_start = now - timedelta(weeks=7)
    retention_drop_end = now - timedelta(weeks=5)

    all_events = []
    for user in users:
        user_signup = user.created_at
        active_days = (now - user_signup).days

        # Generate activity for each day the user could have been active
        for day_offset in range(min(active_days, days_back)):
            event_date = user_signup + timedelta(days=day_offset)

            # Base daily event probability depends on plan
            base_prob = {
                "free": 0.25,
                "starter": 0.45,
                "pro": 0.65,
                "enterprise": 0.80,
            }.get(user.plan, 0.25)

            # Simulate retention drop
            if retention_drop_start <= event_date <= retention_drop_end:
                base_prob *= 0.65  # 35% drop during this period

            if random.random() > base_prob:
                continue

            # Number of events this day
            n_events = random.randint(1, 8)
            for _ in range(n_events):
                event_time = event_date + timedelta(
                    hours=random.randint(8, 22),
                    minutes=random.randint(0, 59),
                )

                etype, _ = weighted_choice(EVENT_TYPES, [w for _, w in EVENT_TYPES])

                event = Event(
                    user_id=user.id,
                    session_id=str(uuid4()),
                    event_type=etype,
                    event_category="product",
                    device_type=random.choice(["desktop", "mobile", "tablet"]),
                    platform=random.choice(["web", "ios", "android"]),
                    occurred_at=event_time,
                    properties={"version": "1.0.0"},
                )
                all_events.append(event)

        if len(all_events) > 50000:
            db.add_all(all_events)
            await db.flush()
            all_events = []
            print(f"  Flushed events batch...")

    if all_events:
        db.add_all(all_events)
        await db.flush()

    print(f"Events created")

    # ── Create Subscriptions ──────────────────────────────────────────────────
    subscriptions = []
    for user in users:
        if user.plan == "free":
            continue  # Free users don't have subscriptions

        plan_prices = {
            "starter": 2900,   # $29/mo
            "pro": 9900,        # $99/mo
            "enterprise": 49900, # $499/mo
        }
        price = plan_prices.get(user.plan, 2900)

        started = user.created_at + timedelta(days=random.randint(1, 14))
        sub = Subscription(
            id=str(uuid4()),
            user_id=user.id,
            plan=user.plan,
            status=random.choices(
                ["active", "canceled", "trialing"],
                weights=[0.75, 0.15, 0.10]
            )[0],
            billing_cycle=random.choices(["monthly", "annual"], weights=[0.7, 0.3])[0],
            base_amount_cents=price,
            started_at=started,
            current_period_starts_at=started,
            current_period_ends_at=started + timedelta(days=30),
        )
        subscriptions.append(sub)

    db.add_all(subscriptions)
    await db.flush()
    print(f"Subscriptions created: {len(subscriptions)}")

    # ── Create Payments ───────────────────────────────────────────────────────
    payments = []
    for sub in subscriptions:
        # Generate monthly payments for the subscription lifetime
        payment_date = sub.started_at
        while payment_date < now:
            # 8% failure rate, 92% success
            status = random.choices(["succeeded", "failed"], weights=[0.92, 0.08])[0]

            payment = Payment(
                id=str(uuid4()),
                subscription_id=sub.id,
                user_id=sub.user_id,
                amount_cents=sub.base_amount_cents,
                currency="USD",
                status=status,
                payment_method=random.choice(PAYMENT_METHODS),
                created_at=payment_date,
                processed_at=payment_date + timedelta(seconds=random.randint(1, 60)),
                failure_code=weighted_choice(
                    [fc for fc, _ in FAILURE_CODES],
                    [w for _, w in FAILURE_CODES]
                ) if status == "failed" else None,
                risk_score=random.uniform(0, 0.3),
            )
            payments.append(payment)
            payment_date += timedelta(days=30)

    db.add_all(payments)
    await db.commit()
    print(f"Payments created: {len(payments)}")
    print("✅ Database seeded successfully!")


async def main():
    """Run seeding."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await seed_data(db, user_count=5000, days_back=180)


if __name__ == "__main__":
    asyncio.run(main())