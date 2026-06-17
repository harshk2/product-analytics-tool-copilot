-- PostgreSQL initialization script
-- Extensions required by the application

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- For text similarity search in memory layer

-- Create the analytics database if not exists (already done by docker env)
-- This script runs in the analytics_copilot database context

-- ── Core Tables ────────────────────────────────────────────────────────────────

-- Users table with full lifecycle tracking
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    external_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE,

    -- Demographics
    country VARCHAR(2),
    city VARCHAR(100),
    timezone VARCHAR(50),
    language VARCHAR(10),

    -- Acquisition
    acquisition_source VARCHAR(100),
    acquisition_campaign VARCHAR(255),
    acquisition_channel VARCHAR(50),

    -- Company info (B2B)
    company_id UUID,
    company_name VARCHAR(255),
    company_size VARCHAR(20),
    industry VARCHAR(100),

    -- User attributes
    plan VARCHAR(50) DEFAULT 'free',
    role VARCHAR(50),

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_plan CHECK (plan IN ('free', 'starter', 'pro', 'enterprise'))
);

-- Events table for behavioral tracking
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID,

    -- Event classification
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50),
    event_action VARCHAR(100),
    event_label VARCHAR(255),

    -- Context
    page_url TEXT,
    page_path VARCHAR(500),
    referrer TEXT,
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(255),

    -- Technical context
    platform VARCHAR(20),
    device_type VARCHAR(20),
    browser VARCHAR(50),
    os VARCHAR(50),
    ip_address INET,

    -- Properties
    properties JSONB DEFAULT '{}',

    -- Timing
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_device_type CHECK (device_type IN ('desktop', 'mobile', 'tablet', NULL))
);

-- Subscriptions for revenue tracking
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    company_id UUID,

    -- Plan info
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    billing_cycle VARCHAR(20) DEFAULT 'monthly',

    -- Pricing
    base_amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    discount_cents INTEGER DEFAULT 0,

    -- Dates
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    current_period_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,

    -- Cancellation
    cancellation_reason VARCHAR(100),
    will_renew BOOLEAN DEFAULT TRUE,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_sub_status CHECK (status IN ('active', 'trialing', 'past_due', 'canceled', 'paused', 'expired')),
    CONSTRAINT valid_billing_cycle CHECK (billing_cycle IN ('monthly', 'annual'))
);

-- Payments table for financial tracking
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subscription_id UUID REFERENCES subscriptions(id),
    user_id UUID NOT NULL REFERENCES users(id),

    -- Payment info
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,
    payment_method VARCHAR(20),

    -- External refs
    external_payment_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),

    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,

    -- Error tracking
    failure_code VARCHAR(50),
    failure_message TEXT,

    -- Risk scoring
    risk_score DECIMAL(5,2),
    is_flagged BOOLEAN DEFAULT FALSE,

    -- Metadata
    metadata JSONB DEFAULT '{}',

    CONSTRAINT valid_payment_status CHECK (status IN ('pending', 'succeeded', 'failed', 'refunded', 'disputed'))
);

-- Chargebacks for fraud/risk analysis
CREATE TABLE IF NOT EXISTS chargebacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID REFERENCES payments(id),
    user_id UUID NOT NULL REFERENCES users(id),

    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(20) NOT NULL,

    reason_code VARCHAR(20),
    reason_description TEXT,

    due_date DATE,
    resolved_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_chargeback_status CHECK (status IN ('pending', 'won', 'lost', 'closed'))
);

-- Feature flags for correlating changes with metrics
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,

    enabled_at TIMESTAMP WITH TIME ZONE,
    disabled_at TIMESTAMP WITH TIME ZONE,

    rollout_percentage INTEGER DEFAULT 100
        CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),

    targeting_rules JSONB DEFAULT '[]',

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Feature exposure events
CREATE TABLE IF NOT EXISTS feature_exposures (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    feature_flag_id UUID REFERENCES feature_flags(id),
    exposed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    variant VARCHAR(50),
    context JSONB DEFAULT '{}'
);

-- Cohorts for cohort analysis
CREATE TABLE IF NOT EXISTS cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,

    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    is_dynamic BOOLEAN DEFAULT TRUE,
    last_calculated_at TIMESTAMP WITH TIME ZONE
);

-- Stored investigations for memory layer
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),

    question TEXT NOT NULL,
    intent JSONB,
    investigation_plan JSONB,

    status VARCHAR(20) DEFAULT 'in_progress',

    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    tokens_used INTEGER,
    cost_cents INTEGER,

    findings JSONB DEFAULT '[]',
    root_causes JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',

    summary TEXT,
    full_transcript JSONB,

    metadata JSONB DEFAULT '{}'
);

-- ── Indexes ────────────────────────────────────────────────────────────────────

-- Events indexes for high-frequency queries
CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type_occurred ON events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_user_occurred ON events(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);

-- Subscriptions indexes
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_current_period
    ON subscriptions(current_period_starts_at, current_period_ends_at);

-- Payments indexes
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payments_flagged ON payments(is_flagged) WHERE is_flagged = TRUE;

-- User segmentation indexes
CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan);
CREATE INDEX IF NOT EXISTS idx_users_created ON users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_country ON users(country);
CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id) WHERE company_id IS NOT NULL;

-- Composite indexes for common analytics queries
CREATE INDEX IF NOT EXISTS idx_users_segment ON users(plan, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_subscriptions_mrr ON subscriptions(status, current_period_ends_at);
CREATE INDEX IF NOT EXISTS idx_payments_revenue ON payments(status, created_at DESC)
    INCLUDE (amount_cents);

-- Investigations (memory layer) - text search using pg_trgm
CREATE INDEX IF NOT EXISTS idx_investigations_question_trgm
    ON investigations USING gin (question gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_investigations_status ON investigations(status);
CREATE INDEX IF NOT EXISTS idx_investigations_started ON investigations(started_at DESC);

-- ── Materialized Views ─────────────────────────────────────────────────────────

-- Monthly active users (refreshed by Celery)
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_active_users AS
SELECT
    date_trunc('month', occurred_at) AS month,
    COUNT(DISTINCT user_id) AS mau,
    COUNT(*) AS total_events
FROM events
WHERE occurred_at >= NOW() - INTERVAL '24 months'
GROUP BY date_trunc('month', occurred_at);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mau_month ON monthly_active_users(month);

-- Daily metrics aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_metrics AS
SELECT
    d::date AS date,
    COALESCE(u.new_users, 0) AS new_users,
    COALESCE(e.active_users, 0) AS active_users,
    COALESCE(s.new_subscriptions, 0) AS new_subscriptions,
    COALESCE(p.revenue_cents, 0) AS revenue_cents
FROM generate_series(NOW() - INTERVAL '365 days', NOW(), INTERVAL '1 day') d
LEFT JOIN (
    SELECT created_at::date AS day, COUNT(*) AS new_users
    FROM users WHERE deleted_at IS NULL
    GROUP BY created_at::date
) u ON u.day = d::date
LEFT JOIN (
    SELECT occurred_at::date AS day, COUNT(DISTINCT user_id) AS active_users
    FROM events
    GROUP BY occurred_at::date
) e ON e.day = d::date
LEFT JOIN (
    SELECT started_at::date AS day, COUNT(*) AS new_subscriptions
    FROM subscriptions
    WHERE status IN ('active', 'trialing')
    GROUP BY started_at::date
) s ON s.day = d::date
LEFT JOIN (
    SELECT created_at::date AS day, SUM(amount_cents) AS revenue_cents
    FROM payments WHERE status = 'succeeded'
    GROUP BY created_at::date
) p ON p.day = d::date;

CREATE UNIQUE INDEX IF NOT EXISTS idx_dm_date ON daily_metrics(date);

-- ── Seed Feature Flags ─────────────────────────────────────────────────────────

INSERT INTO feature_flags (name, description, enabled_at, rollout_percentage, created_by)
VALUES
    ('new_checkout_flow', 'Redesigned payment checkout flow', NOW() - INTERVAL '14 days', 100, 'system'),
    ('ai_recommendations', 'AI-powered product recommendations', NOW() - INTERVAL '30 days', 50, 'system'),
    ('dashboard_v2', 'New analytics dashboard', NOW() - INTERVAL '7 days', 25, 'system')
ON CONFLICT (name) DO NOTHING;
