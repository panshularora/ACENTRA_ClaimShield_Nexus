from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from claimshield.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    previous_refresh_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


class AuditEvent(Base):
    __tablename__ = "audit_event"

    seq: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(64), index=True)
    object_type: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class Member(Base):
    __tablename__ = "member"

    member_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    dob: Mapped[datetime] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(8))
    county: Mapped[str] = mapped_column(String(64))
    location_id: Mapped[str] = mapped_column(String(32), index=True)
    risk_tier: Mapped[int] = mapped_column(Integer, default=2)
    date_of_death: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class EligibilitySpan(Base):
    __tablename__ = "eligibility_span"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("member.member_id"), index=True)
    start: Mapped[datetime] = mapped_column(Date)
    end: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    program: Mapped[str] = mapped_column(String(16), default="FFS")


class Location(Base):
    __tablename__ = "location"

    location_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    address_norm: Mapped[str] = mapped_column(String(255), index=True)
    zip: Mapped[str] = mapped_column(String(10), index=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(32))
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Provider(Base):
    __tablename__ = "provider"

    provider_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    npi_syn: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16))
    specialty: Mapped[str] = mapped_column(String(64), index=True)
    service_line: Mapped[str] = mapped_column(String(32), index=True)
    location_id: Mapped[str] = mapped_column(String(32), index=True)
    enroll_date: Mapped[datetime] = mapped_column(Date)
    term_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    tin_token: Mapped[str] = mapped_column(String(32), index=True)
    rural: Mapped[bool] = mapped_column(Boolean, default=False)
    sole_community: Mapped[bool] = mapped_column(Boolean, default=False)


class Facility(Base):
    __tablename__ = "facility"

    facility_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    location_id: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(32))
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Owner(Base):
    __tablename__ = "owner"

    owner_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(128), index=True)
    dob: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class OwnershipLink(Base):
    __tablename__ = "ownership_link"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("owner.owner_id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("provider.provider_id"), index=True)
    pct: Mapped[float] = mapped_column(Float)
    start: Mapped[datetime] = mapped_column(Date)
    end: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class ContactPoint(Base):
    __tablename__ = "contact_point"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    entity_type: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
    value_hash: Mapped[str] = mapped_column(String(64), index=True)


class Referral(Base):
    __tablename__ = "referral"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referring_id: Mapped[str] = mapped_column(String(32), index=True)
    receiving_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    date: Mapped[datetime] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(24), default="referral")


class Claim(Base):
    __tablename__ = "claim"

    claim_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claim_type: Mapped[str] = mapped_column(String(24), index=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    billing_provider_id: Mapped[str] = mapped_column(String(32), index=True)
    facility_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    admit: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    discharge: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[datetime] = mapped_column(Date)
    adjudicated_date: Mapped[datetime] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16), default="paid")
    source_system: Mapped[str] = mapped_column(String(32), default="generator")
    source_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)


class ClaimLine(Base):
    __tablename__ = "claim_line"

    line_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claim.claim_id"), index=True)
    rendering_provider_id: Mapped[str] = mapped_column(String(32), index=True)
    ordering_provider_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dos_from: Mapped[datetime] = mapped_column(Date, index=True)
    dos_to: Mapped[datetime] = mapped_column(Date)
    code_system: Mapped[str] = mapped_column(String(16), index=True)
    code: Mapped[str] = mapped_column(String(24), index=True)
    modifiers: Mapped[list[str]] = mapped_column(JSON, default=list)
    units: Mapped[float] = mapped_column(Float)
    minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mileage: Mapped[float | None] = mapped_column(Float, nullable=True)
    dx: Mapped[list[str]] = mapped_column(JSON, default=list)
    pos: Mapped[str] = mapped_column(String(8), default="11")
    charge: Mapped[float] = mapped_column(Float)
    allowed: Mapped[float] = mapped_column(Float)
    paid: Mapped[float] = mapped_column(Float)


class InpatientStay(Base):
    __tablename__ = "inpatient_stay"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    facility_id: Mapped[str] = mapped_column(String(32))
    admit: Mapped[datetime] = mapped_column(Date)
    discharge: Mapped[datetime] = mapped_column(Date)


class EvvVisit(Base):
    __tablename__ = "evv_visit"

    visit_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    aide_id: Mapped[str] = mapped_column(String(32), index=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    provider_id: Mapped[str] = mapped_column(String(32), index=True)
    start_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    service_type: Mapped[str] = mapped_column(String(32))


class RxFill(Base):
    __tablename__ = "rx_fill"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    prescriber_id: Mapped[str] = mapped_column(String(32), index=True)
    pharmacy_id: Mapped[str] = mapped_column(String(32), index=True)
    drug_class_syn: Mapped[str] = mapped_column(String(32))
    days_supply: Mapped[int] = mapped_column(Integer)
    qty: Mapped[float] = mapped_column(Float)
    mme: Mapped[float] = mapped_column(Float)
    fill_date: Mapped[datetime] = mapped_column(Date, index=True)


class ExclusionRecord(Base):
    __tablename__ = "exclusion_record"

    excl_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lastname: Mapped[str] = mapped_column(String(64), default="")
    firstname: Mapped[str] = mapped_column(String(64), default="")
    busname: Mapped[str] = mapped_column(String(128), default="")
    dob: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    address: Mapped[str] = mapped_column(String(255), default="")
    npi: Mapped[str | None] = mapped_column(String(10), nullable=True)
    excl_type: Mapped[str] = mapped_column(String(16), default="1128a1")
    excl_date: Mapped[datetime] = mapped_column(Date)
    rein_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)


class Investigation(Base):
    __tablename__ = "investigation"

    investigation_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    opened: Mapped[datetime] = mapped_column(Date)
    closed: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    lead_source: Mapped[str] = mapped_column(String(64), default="data_analysis")
    scheme_tag: Mapped[str | None] = mapped_column(String(16), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount_identified: Mapped[float] = mapped_column(Float, default=0.0)
    amount_recovered: Mapped[float] = mapped_column(Float, default=0.0)
    closed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class InvestigationSubject(Base):
    __tablename__ = "investigation_subject"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(
        ForeignKey("investigation.investigation_id"), index=True
    )
    provider_id: Mapped[str] = mapped_column(String(32), index=True)


class Rule(Base):
    __tablename__ = "rule"

    rule_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))


class RuleVersion(Base):
    __tablename__ = "rule_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey("rule.rule_id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    severity: Mapped[int] = mapped_column(Integer, default=2)
    service_lines: Mapped[list[str]] = mapped_column(JSON, default=list)
    policy_ref: Mapped[str] = mapped_column(String(32))
    effective_from: Mapped[datetime] = mapped_column(Date)
    effective_to: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    author: Mapped[str] = mapped_column(String(32), default="seed")
    approved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (UniqueConstraint("rule_id", "version"),)


class Alert(Base):
    __tablename__ = "alert"

    alert_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    detector: Mapped[str] = mapped_column(String(32), index=True)
    rule_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rule_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_id: Mapped[str] = mapped_column(String(32), index=True)
    entity_type: Mapped[str] = mapped_column(String(16))
    line_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    score: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    case_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)


class Case(Base):
    __tablename__ = "case"

    case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="open")
    lane: Mapped[str] = mapped_column(String(32), default="selected")
    assignee_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sla_due: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    primary_entity_id: Mapped[str] = mapped_column(String(32), index=True)
    primary_entity_type: Mapped[str] = mapped_column(String(16), default="provider")
    entity_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    harm: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    members_affected: Mapped[int] = mapped_column(Integer, default=0)
    flagged_dollars: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_hours: Mapped[float] = mapped_column(Float, default=8.0)
    p_confirm: Mapped[float] = mapped_column(Float, default=0.0)
    expected_value: Mapped[float] = mapped_column(Float, default=0.0)
    f30: Mapped[float | None] = mapped_column(Float, nullable=True)
    f60: Mapped[float | None] = mapped_column(Float, nullable=True)
    f90: Mapped[float | None] = mapped_column(Float, nullable=True)


class CaseRisk(Base):
    """Which model scored a case, whether it was calibrated, and its top contributing factors.

    A separate table so existing databases gain it through ``create_all`` without a migration.
    """

    __tablename__ = "case_risk"

    case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    score_kind: Mapped[str] = mapped_column(String(32))
    model_version: Mapped[str] = mapped_column(String(64))
    calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class QueueOverride(Base):
    __tablename__ = "queue_override"

    override_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), index=True)
    run_id: Mapped[str] = mapped_column(String(32), index=True)
    actor_id: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    prior_lane: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Decision(Base):
    __tablename__ = "decision"

    decision_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), index=True)
    actor_id: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    # recorded | pending_approval | approved | rejected
    status: Mapped[str] = mapped_column(String(24), default="recorded", index=True)
    prior_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    ladder_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    approved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Batch(Base):
    __tablename__ = "batch"

    batch_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    adapter: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="loaded")
    profile: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    load_report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(32))


class PipelineRun(Base):
    __tablename__ = "pipeline_run"

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(16), default="queued")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(32))


class Label(Base):
    __tablename__ = "label"

    label_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), index=True)
    decision_id: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    scheme_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WikiProposal(Base):
    __tablename__ = "wiki_proposal"

    proposal_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), default="precedent", index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_case_id: Mapped[str] = mapped_column(String(32), index=True)
    decision_id: Mapped[str] = mapped_column(String(32), index=True)
    body: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_by: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class IngestReceipt(Base):
    """Idempotency record for S3/Lambda ingest events. No claim/member payload."""

    __tablename__ = "ingest_receipt"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    batch_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bucket: Mapped[str] = mapped_column(String(128))
    object_prefix: Mapped[str] = mapped_column(String(255))
    trigger_key: Mapped[str] = mapped_column(String(512))
    event_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WikiPage(Base):
    __tablename__ = "wiki_page"

    page_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16), default="published")
    body: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_proposal_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str] = mapped_column(String(32))
