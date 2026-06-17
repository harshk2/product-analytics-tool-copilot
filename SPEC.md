# AI Product Analytics Copilot - Technical Specification

## 1. System Overview

### 1.1 Purpose
An autonomous AI system that behaves like a senior product analyst, investigating business questions through multi-agent orchestration. The system understands business intent, generates investigation plans, executes SQL queries, performs various analyses, and produces actionable insights.

### 1.2 Core Objectives

Users can ask natural business questions:
- "Why did retention drop last week?"
- "Why did revenue decrease despite user growth?"
- "Which customer segments are most likely to churn?"
- "Why are payment failures increasing?"
- "What changed after feature launch X?"

The system must:
1. Understand business intent
2. Generate investigation plans
3. Generate and execute SQL queries
4. Perform cohort analysis
5. Perform segmentation analysis
6. Detect anomalies
7. Identify likely root causes
8. Generate visualizations
9. Produce executive summaries
10. Recommend actions

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │  Chat Interface │  │ Dashboard View  │  │  Visualization Renderer     │  │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘  │
└───────────┼────────────────────┼─────────────────────────┼──────────────────┘
            │                    │                         │
            │ WebSocket/REST     │ REST                    │ SSE
            ▼                    ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY LAYER                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         FastAPI Application                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │ /api/v1/chat │  │ /api/v1/query│  │ /api/v1/vis  │  │ /api/v1/mem  │  │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            │ Message Queue / Task Queue
            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORCHESTRATION LAYER                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                          LangGraph StateGraph                            │ │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │ │
│  │  │ Intent  │───▶│Metrics  │───▶│   SQL   │───▶│Analysis │               │ │
│  │  │  Agent  │    │  Agent  │    │  Agent  │    │  Agents │               │ │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘               │ │
│  │       │                                           │                     │ │
│  │       ▼                                           ▼                     │ │
│  │  ┌─────────────┐                          ┌─────────────┐               │ │
│  │  │ Root Cause  │◀─────────────────────────│    Viz      │               │ │
│  │  │   Agent     │                          │   Agent     │               │ │
│  │  └─────────────┘                          └─────────────┘               │ │
│  │       │                                        │                        │ │
│  │       └────────────────┬───────────────────────┘                        │ │
│  │                        ▼                                                 │ │
│  │               ┌─────────────────┐                                        │ │
│  │               │ Executive Summary│                                       │ │
│  │               │     Agent       │                                        │ │
│  │               └─────────────────┘                                        │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
            │
            ├──┬──┬──┬──┬──┐
            ▼  ▼  ▼  ▼  ▼  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICE LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Query Engine │  │   Analyzer   │  │    Memory    │  │   Monitor    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
            │                    │              │
            ▼                    ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ PostgreSQL   │  │    Redis     │  │    MinIO     │  │    Celery    │     │
│  │  (Primary)   │  │   (Cache)    │  │  (Artifacts) │  │  (Workers)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User Question
     │
     ▼
┌─────────────┐
│ Intent Agent│  ──▶ Structured Investigation Plan
└─────────────┘
     │
     ▼
┌─────────────┐
│Metrics Agent│  ──▶ Relevant Metrics & Data Sources
└─────────────┘
     │
     ▼
┌─────────────┐
│  SQL Agent  │  ──▶ Validated SQL Queries
└─────────────┘
     │
     ├──┬──────────────────────────┐
     ▼  ▼                          ▼
┌─────────┐ ┌─────────────┐ ┌───────────────┐
│Cohort   │ │Segmentation │ │  Root Cause   │
│Analysis │ │  Analysis   │ │    Agent      │
└─────────┘ └─────────────┘ └───────────────┘
     │           │                │
     └───────────┴────────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ Visualization │
            │    Agent      │
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   Executive   │
            │   Summary     │
            └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │   Response    │
            │  to User      │
            └───────────────┘
```

---

## 3. Database Schema

### 3.1 Core Tables

```sql
-- Users table with full lifecycle tracking
CREATE TABLE users (
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
    
    CONSTRAINT valid_country CHECK (country ~ '^[A-Z]{2}$'),
    CONSTRAINT valid_plan CHECK (plan IN ('free', 'starter', 'pro', 'enterprise'))
);

-- Events table for behavioral tracking
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
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
    
    -- Indexes for common queries
    CONSTRAINT valid_device_type CHECK (device_type IN ('desktop', 'mobile', 'tablet'))
);

-- Subscriptions for revenue tracking
CREATE TABLE subscriptions (
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
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'trialing', 'past_due', 'canceled', 'paused', 'expired')),
    CONSTRAINT valid_billing_cycle CHECK (billing_cycle IN ('monthly', 'annual'))
);

-- Payments table for financial tracking
CREATE TABLE payments (
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
CREATE TABLE chargebacks (
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
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    
    enabled_at TIMESTAMP WITH TIME ZONE,
    disabled_at TIMESTAMP WITH TIME ZONE,
    
    rollout_percentage INTEGER DEFAULT 100 CHECK (rollout_percentage >= 0 AND rollout_percentage <= 100),
    
    targeting_rules JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);

-- Feature exposure events
CREATE TABLE feature_exposures (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    feature_flag_id UUID REFERENCES feature_flags(id),
    exposed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    variant VARCHAR(50),
    context JSONB DEFAULT '{}'
);

-- Cohorts for cohort analysis
CREATE TABLE cohorts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL,  -- Stores the cohort definition
    
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    is_dynamic BOOLEAN DEFAULT TRUE,  -- Dynamic = recalculated on each query
    last_calculated_at TIMESTAMP WITH TIME ZONE
);

-- Stored investigations for memory layer
CREATE TABLE investigations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    
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
```

### 3.2 Key Indexes

```sql
-- Events indexes for high-frequency queries
CREATE INDEX idx_events_user_id ON events(user_id);
CREATE INDEX idx_events_occurred_at ON events(occurred_at DESC);
CREATE INDEX idx_events_type_occurred ON events(event_type, occurred_at DESC);
CREATE INDEX idx_events_user_occurred ON events(user_id, occurred_at DESC);
CREATE INDEX idx_events_session ON events(session_id);

-- Subscriptions indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_current_period ON subscriptions(current_period_starts_at, current_period_ends_at);

-- Payments indexes
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_created_at ON payments(created_at DESC);
CREATE INDEX idx_payments_flagged ON payments(is_flagged) WHERE is_flagged = TRUE;

-- User segmentation indexes
CREATE INDEX idx_users_plan ON users(plan);
CREATE INDEX idx_users_created ON users(created_at DESC);
CREATE INDEX idx_users_country ON users(country);
CREATE INDEX idx_users_company ON users(company_id) WHERE company_id IS NOT NULL;

-- Composite indexes for common analytics queries
CREATE INDEX idx_users_segment ON users(plan, created_at DESC);
CREATE INDEX idx_subscriptions_mrr ON subscriptions(status, current_period_ends_at);
CREATE INDEX idx_payments_revenue ON payments(status, created_at DESC) INCLUDE (amount_cents);
```

### 3.3 Materialized Views

```sql
-- Monthly active users
CREATE MATERIALIZED VIEW monthly_active_users AS
SELECT 
    date_trunc('month', occurred_at) AS month,
    COUNT(DISTINCT user_id) AS mau,
    COUNT(*) AS total_events
FROM events
WHERE occurred_at >= NOW() - INTERVAL '24 months'
GROUP BY date_trunc('month', occurred_at);

CREATE UNIQUE INDEX idx_mau_month ON monthly_active_users(month);

-- Daily metrics aggregation
CREATE MATERIALIZED VIEW daily_metrics AS
SELECT 
    d::date AS date,
    COALESCE(u.new_users, 0) AS new_users,
    COALESCE(e.active_users, 0) AS active_users,
    COALESCE(s.new_subscriptions, 0) AS new_subscriptions,
    COALESCE(p.mrr_cents, 0) AS mrr_cents
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
    SELECT created_at::date AS day, SUM(amount_cents) AS mrr_cents
    FROM payments WHERE status = 'succeeded'
    GROUP BY created_at::date
) p ON p.day = d::date;

CREATE UNIQUE INDEX idx_dm_date ON daily_metrics(date);
```

---

## 4. Agent Specifications

### 4.1 Intent Agent

**Purpose**: Parse natural language business questions into structured investigation plans.

**Input**: User question (e.g., "Why did retention drop last week?")

**Output**:
```json
{
  "intent_type": "retention_investigation",
  "primary_metrics": ["retention_rate", "cohort_retention"],
  "time_range": {
    "focus": "last_week",
    "comparison": "previous_week"
  },
  "dimensions": ["plan", "acquisition_source"],
  "hypotheses": [
    "Feature change affecting engagement",
    "Payment issue causing churn",
    "Competitor activity"
  ],
  "required_analyses": ["cohort_retention", "segment_comparison"],
  "priority": "high"
}
```

**System Prompt Outline**:
- Extract temporal references
- Identify metric categories (retention, revenue, engagement, conversion)
- Determine comparison periods
- Identify relevant user segments
- Generate initial hypotheses

### 4.2 Metrics Agent

**Purpose**: Identify relevant metrics and data sources for the investigation.

**Responsibilities**:
- Map business questions to measurable metrics
- Identify data sources (tables, columns)
- Determine calculation methods
- Define baseline and comparison values

**Output**:
```json
{
  "metrics": [
    {
      "name": "weekly_retention_rate",
      "definition": "Users active in week N who return in week N+1",
      "calculation": "COUNT(DISTINCT active_week_N) / COUNT(DISTINCT active_week_N-1)",
      "table": "events",
      "time_granularity": "week"
    }
  ],
  "data_sources": [
    {
      "table": "events",
      "required_columns": ["user_id", "occurred_at", "event_type"],
      "filters": ["occurred_at >= start_date", "occurred_at <= end_date"]
    }
  ],
  "baseline_value": 0.42,
  "comparison_value": 0.38
}
```

### 4.3 SQL Agent

**Purpose**: Generate, validate, and execute SQL queries safely.

**Responsibilities**:
- Generate SQL from natural language requests
- Validate queries for safety (no DELETE, DROP, etc.)
- Optimize query performance
- Handle query errors gracefully

**Safety Rules**:
- Blocked: DELETE, DROP, TRUNCATE, ALTER, CREATE, INSERT, UPDATE
- Allowed: SELECT only
- Required: WHERE clause for large tables
- Rate limit: Max 10 queries per investigation

**Output**:
```json
{
  "query": "SELECT date_trunc('week', occurred_at) AS week, COUNT(DISTINCT user_id) AS active_users FROM events WHERE occurred_at >= '2024-01-01' AND occurred_at < '2024-02-01' GROUP BY 1 ORDER BY 1",
  "estimated_rows": 50000,
  "execution_time_ms": 234,
  "results": [...],
  "errors": []
}
```

### 4.4 Segmentation Agent

**Purpose**: Segment users/customers by behavior patterns.

**Analysis Types**:
- Behavioral segmentation (engagement levels)
- Demographic segmentation (cohorts, geography)
- Value-based segmentation (LTV, revenue)
- Risk-based segmentation (churn probability)

**Output**:
```json
{
  "segments": [
    {
      "name": "power_users",
      "definition": "Active 20+ days/month, 3+ feature adoptions",
      "user_count": 4521,
      "percentage": 15.2,
      "characteristics": {
        "avg_session_duration": 1800,
        "feature_adoption_rate": 0.85,
        "retention_rate": 0.92
      }
    }
  ],
  "recommendations": [
    {
      "segment": "power_users",
      "action": "Protect with loyalty rewards",
      "priority": "high"
    }
  ]
}
```

### 4.5 Cohort Analysis Agent

**Purpose**: Perform cohort-based retention and revenue analysis.

**Analysis Types**:
- Retention cohorts (by acquisition date)
- Revenue cohorts (by first payment)
- Engagement cohorts (by first action)
- Custom cohorts based on feature usage

**Output**:
```json
{
  "cohort_type": "weekly_retention",
  "cohorts": [
    {
      "period": "2024-W01",
      "size": 1250,
      "retention": [1.0, 0.65, 0.52, 0.44, 0.38, 0.35, 0.32, 0.30]
    }
  ],
  "insights": [
    {
      "metric": "Week 3 Retention",
      "value": 0.44,
      "trend": "declining",
      "change": -0.08
    }
  ]
}
```

### 4.6 Root Cause Agent

**Purpose**: Generate and test hypotheses for metric changes.

**Process**:
1. Generate hypotheses based on metric type
2. Rank hypotheses by prior probability
3. Test each hypothesis with data
4. Calculate confidence scores
5. Report ranked findings

**Hypothesis Categories**:
- Internal changes (features, pricing, UX)
- External factors (seasonality, competition)
- Data issues (tracking, processing)
- Segment-specific (certain user groups)

**Output**:
```json
{
  "hypotheses": [
    {
      "id": "h1",
      "description": "Payment page changes increased friction",
      "confidence": 0.85,
      "evidence": [
        {"type": "correlation", "metric": "payment_page_drop", "value": "+23%"},
        {"type": "timing", "feature_flag": "new_checkout", "enabled_at": "2024-01-10"}
      ],
      "ruled_out": false,
      "next_steps": ["A/B test revert", "User interviews"]
    }
  ],
  "root_cause": "h1",
  "confidence": 0.85
}
```

### 4.7 Visualization Agent

**Purpose**: Create appropriate visualizations for findings.

**Chart Types**:
- Line charts (trends over time)
- Bar charts (comparisons)
- Heatmaps (cohort analysis)
- Scatter plots (correlations)
- Funnel charts (conversion)
- Sankey diagrams (user flows)

**Output**:
```json
{
  "visualizations": [
    {
      "type": "retention_curve",
      "title": "Weekly Retention by Cohort",
      "data": [...],
      "config": {
        "x_axis": "Weeks Since Signup",
        "y_axis": "Retention Rate",
        "show_trend": true
      }
    }
  ],
  "format": "vega_lite"
}
```

### 4.8 Executive Summary Agent

**Purpose**: Synthesize all findings into actionable executive summaries.

**Output**:
```json
{
  "summary": "Retention dropped 8% last week primarily due to increased payment friction from the new checkout flow.",
  "key_findings": [
    "New checkout flow increased payment page abandonment by 23%",
    "Enterprise segment most affected (35% increase in support tickets)",
    "Mobile users 2.3x more likely to abandon"
  ],
  "recommendations": [
    {
      "action": "Roll back checkout change for mobile users",
      "impact": "Restore ~15% of lost retention",
      "effort": "low",
      "urgency": "high"
    }
  ],
  "metrics_impact": {
    "metric": "Weekly Retention",
    "current": 0.32,
    "projected": 0.38,
    "change": "+0.06"
  }
}
```

---

## 5. API Specifications

### 5.1 Chat API

**Endpoint**: `POST /api/v1/chat`

**Request**:
```json
{
  "message": "Why did retention drop last week?",
  "session_id": "uuid",
  "context": {
    "user_id": "uuid",
    "filters": {"plan": "pro", "country": "US"}
  }
}
```

**Response** (Server-Sent Events):
```
event: investigation_start
data: {"status": "analyzing", "agent": "intent"}

event: finding
data: {"type": "metric", "data": {"retention_rate": 0.32, "change": -0.08}}

event: finding
data: {"type": "visualization", "chart_id": "retention_chart"}

event: recommendation
data: {"action": "Roll back checkout change", "impact": "high"}

event: complete
data: {"summary": "...", "investigation_id": "uuid"}
```

### 5.2 Query API

**Endpoint**: `POST /api/v1/query`

**Request**:
```json
{
  "question": "Show me DAU for the past 30 days",
  "response_format": "chart"
}
```

**Response**:
```json
{
  "query": "SELECT ... (generated SQL)",
  "results": [...],
  "visualization": {
    "type": "line",
    "data": [...]
  }
}
```

### 5.3 Memory API

**Endpoints**:
- `GET /api/v1/memory/investigations` - List past investigations
- `GET /api/v1/memory/investigations/{id}` - Get specific investigation
- `POST /api/v1/memory/learn` - Store new finding
- `GET /api/v1/memory/similar?question=...` - Find similar past issues

### 5.4 Dashboard API

**Endpoint**: `GET /api/v1/dashboard`

**Response**:
```json
{
  "kpis": {
    "dau": {"value": 15234, "change": 0.12},
    "mau": {"value": 89012, "change": 0.08},
    "retention_d7": {"value": 0.42, "change": -0.03},
    "mrr": {"value": 234000, "change": 0.15}
  },
  "alerts": [
    {"metric": "payment_failures", "severity": "warning", "message": "..."}
  ]
}
```

---

## 6. Folder Structure

```
ai-product-analytics-copilot/
├── README.md
├── SPEC.md
├── Makefile
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── pyproject.toml
├── poetry.lock
│
├── docs/
│   ├── architecture.md
│   ├── agents.md
│   ├── api.md
│   └── deployment.md
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application
│   │   ├── config.py               # Configuration management
│   │   ├── dependencies.py         # Dependency injection
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py         # Chat endpoints
│   │   │   │   ├── query.py        # Query endpoints
│   │   │   │   ├── memory.py       # Memory endpoints
│   │   │   │   └── dashboard.py    # Dashboard endpoints
│   │   │   └── router.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py         # Security utilities
│   │   │   ├── exceptions.py       # Custom exceptions
│   │   │   └── middleware.py       # Middleware
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py          # Database sessions
│   │   │   ├── base.py             # Base models
│   │   │   └── repositories.py     # Data access
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── event.py
│   │   │   ├── subscription.py
│   │   │   ├── payment.py
│   │   │   └── investigation.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py
│   │   │   ├── query.py
│   │   │   └── common.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── query_engine.py     # SQL execution
│   │   │   ├── analyzer.py         # Analytics engine
│   │   │   ├── memory.py           # Memory service
│   │   │   └── monitor.py          # Health monitoring
│   │   │
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base agent class
│   │   │   ├── intent.py           # Intent parsing
│   │   │   ├── metrics.py          # Metrics identification
│   │   │   ├── sql.py              # SQL generation
│   │   │   ├── segmentation.py     # User segmentation
│   │   │   ├── cohort.py           # Cohort analysis
│   │   │   ├── root_cause.py       # Root cause analysis
│   │   │   ├── visualization.py    # Chart generation
│   │   │   └── summary.py          # Executive summary
│   │   │
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── state.py            # Graph state
│   │   │   ├── nodes.py            # Graph nodes
│   │   │   ├── edges.py            # Graph edges
│   │   │   └── compiler.py         # Graph compilation
│   │   │
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── celery_app.py       # Celery configuration
│   │       └── tasks.py            # Background tasks
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── unit/
│       │   ├── __init__.py
│       │   ├── test_agents/
│       │   └── test_services/
│       └── integration/
│           ├── __init__.py
│           ├── test_api/
│           └── test_agents/
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── .env.local
│   │
│   ├── src/
│   │   ├── __init__.py
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── globals.css
│   │   │   └── api/
│   │   │       └── [...route]/route.ts
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn/ui components
│   │   │   ├── chat/
│   │   │   │   ├── chat-interface.tsx
│   │   │   │   ├── message.tsx
│   │   │   │   └── typing-indicator.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── kpi-cards.tsx
│   │   │   │   ├── chart.tsx
│   │   │   │   └── alerts.tsx
│   │   │   └── visualizations/
│   │   │       ├── retention-curve.tsx
│   │   │       ├── cohort-heatmap.tsx
│   │   │       └── funnel.tsx
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── sse.ts
│   │   │   └── utils.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── use-chat.ts
│   │   │   └── use-dashboard.ts
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   └── stores/
│   │       └── chat-store.ts
│   │
│   └── public/
│       └── ...
│
├── scripts/
│   ├── seed_data.py
│   └── load_test.py
│
├── infra/
│   ├── k8s/
│   │   ├── backend-deployment.yaml
│   │   ├── backend-service.yaml
│   │   ├── frontend-deployment.yaml
│   │   ├── postgres-statefulset.yaml
│   │   ├── redis-deployment.yaml
│   │   └── ingress.yaml
│   │
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── docker/
│       └── nginx.conf
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── cd.yml
│   │   └── linter.yml
│   └── ISSUE_TEMPLATE/
│
└── docker-compose.yml
```

---

## 7. Implementation Roadmap

### Phase 1: MVP (2-3 weeks)
- [x] Project scaffolding
- [ ] Basic LangGraph setup
- [ ] Intent Agent (basic)
- [ ] SQL Agent (basic)
- [ ] Simple chat interface
- [ ] Mock data for testing

### Phase 2: Core Analytics (2-3 weeks)
- [ ] Cohort Analysis Agent
- [ ] Segmentation Agent
- [ ] Query execution engine
- [ ] Basic visualizations
- [ ] PostgreSQL integration

### Phase 3: Root Cause (2 weeks)
- [ ] Root Cause Agent
- [ ] Hypothesis generation
- [ ] Statistical testing
- [ ] Confidence scoring

### Phase 4: Polish (2 weeks)
- [ ] Executive Summary Agent
- [ ] Memory layer
- [ ] Dashboard view
- [ ] Error handling
- [ ] Performance optimization

### Phase 5: Production (2 weeks)
- [ ] Celery workers
- [ ] Redis caching
- [ ] Kubernetes deployment
- [ ] Monitoring & alerting
- [ ] Load testing

---

## 8. Advanced Features

### 8.1 Predictive Analytics
- Churn prediction using ML models
- LTV forecasting
- Revenue projection

### 8.2 Anomaly Detection
- Automated metric monitoring
- Alert generation
- Root cause isolation

### 8.3 Natural Language to SQL
- LLM-powered query generation
- Query explanation
- Automatic optimization

### 8.4 Collaboration Features
- Investigation sharing
- Team annotations
- Export capabilities

---

## 9. Interview Talking Points

### Architecture Decisions

1. **LangGraph for Orchestration**
   - Why: Provides deterministic workflow with state management
   - Benefits: Replayability, debugging, checkpointing
   - Trade-offs: Learning curve vs. reliability

2. **PostgreSQL for Primary Data**
   - Why: Columnar indexes for analytics, JSONB for flexibility
   - Benefits: ACID compliance, powerful window functions
   - Trade-offs: Scaling requires partitioning

3. **Redis for Caching**
   - Why: Sub-millisecond response for repeated queries
   - Benefits: Reduces database load, improves UX
   - Trade-offs: Consistency vs. freshness

4. **Celery for Background Tasks**
   - Why: Async analysis, rate limiting
   - Benefits: Non-blocking UX, worker scaling
   - Trade-offs: Complexity, monitoring needs

5. **Modular Agent Design**
   - Why: Each agent is independently testable
   - Benefits: Easier debugging, parallel development
   - Trade-offs: Potential latency from agent chaining

### Scalability Considerations
- Query result caching with TTL
- Agent response caching
- Connection pooling
- Worker autoscaling
- Database read replicas

### Security Measures
- SQL injection prevention through parameterization
- Query validation before execution
- Rate limiting per user
- Audit logging for all queries
- Data access controls

### Observability
- Structured logging with correlation IDs
- Distributed tracing through LangGraph
- Custom metrics for agent performance
- Alerting on error rates