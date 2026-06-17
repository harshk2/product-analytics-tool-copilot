"""SQLAlchemy ORM models for all database tables."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4

from app.db.base import Base


class User(Base):
    """User model with full lifecycle tracking."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Demographics
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Acquisition
    acquisition_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    acquisition_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acquisition_channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Company info (B2B)
    company_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # User attributes
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    events: Mapped[list["Event"]] = relationship("Event", back_populates="user", lazy="dynamic")
    subscriptions: Mapped[list["Subscription"]] = relationship("Subscription", back_populates="user")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")

    __table_args__ = (
        CheckConstraint(
            "country ~ '^[A-Z]{2}$'",
            name="ck_users_valid_country",
        ),
        CheckConstraint(
            "plan IN ('free', 'starter', 'pro', 'enterprise')",
            name="ck_users_valid_plan",
        ),
        Index("idx_users_plan", "plan"),
        Index("idx_users_created", "created_at"),
        Index("idx_users_country", "country"),
        Index("idx_users_company", "company_id"),
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class Event(Base):
    """Event model for behavioral tracking."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    event_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Context
    page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    page_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    utm_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Technical context
    platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    os: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Properties
    properties: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Timing
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="events")

    __table_args__ = (
        Index("idx_events_user_id", "user_id"),
        Index("idx_events_occurred_at", "occurred_at"),
        Index("idx_events_type_occurred", "event_type", "occurred_at"),
        Index("idx_events_user_occurred", "user_id", "occurred_at"),
        Index("idx_events_session", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<Event {self.event_type} at {self.occurred_at}>"


class Subscription(Base):
    """Subscription model for revenue tracking."""

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    company_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    # Plan info
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)

    # Pricing
    base_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Dates
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cancellation
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    will_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="subscription")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'trialing', 'past_due', 'canceled', 'paused', 'expired')",
            name="ck_subscriptions_valid_status",
        ),
        CheckConstraint(
            "billing_cycle IN ('monthly', 'annual')",
            name="ck_subscriptions_valid_billing_cycle",
        ),
        Index("idx_subscriptions_user_id", "user_id"),
        Index("idx_subscriptions_status", "status"),
        Index("idx_subscriptions_current_period", "current_period_starts_at", "current_period_ends_at"),
    )

    @property
    def effective_amount_cents(self) -> int:
        """Calculate effective amount after discount."""
        return max(0, self.base_amount_cents - self.discount_cents)

    def __repr__(self) -> str:
        return f"<Subscription {self.plan} {self.status}>"


class Payment(Base):
    """Payment model for financial tracking."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    subscription_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("subscriptions.id"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )

    # Payment info
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # External refs
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Timing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error tracking
    failure_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Risk scoring
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payments")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription", back_populates="payments")

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded', 'disputed')",
            name="ck_payments_valid_status",
        ),
        Index("idx_payments_user_id", "user_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_created_at", "created_at"),
        Index("idx_payments_flagged", "is_flagged"),
    )

    @property
    def amount_dollars(self) -> float:
        """Convert cents to dollars."""
        return self.amount_cents / 100

    def __repr__(self) -> str:
        return f"<Payment {self.status} ${self.amount_dollars:.2f}>"


class Investigation(Base):
    """Investigation model for memory layer."""

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # The question asked
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Agent analysis results
    intent: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    investigation_plan: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Cost tracking
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Results
    findings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    root_causes: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    recommendations: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    # Summary
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    full_transcript: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Metadata
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed', 'cancelled')",
            name="ck_investigations_valid_status",
        ),
        Index("idx_investigations_user_id", "user_id"),
        Index("idx_investigations_status", "status"),
        Index("idx_investigations_started_at", "started_at"),
        Index("idx_investigations_session_id", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<Investigation '{self.question[:50]}...' {self.status}>"


class FeatureFlag(Base):
    """Feature flag model for correlating changes with metrics."""

    __tablename__ = "feature_flags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    enabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    targeting_rules: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "rollout_percentage >= 0 AND rollout_percentage <= 100",
            name="ck_feature_flags_valid_rollout",
        ),
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag {self.name}>"