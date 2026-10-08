"""Response schema for the case network endpoint (schema version 2).

Version 2 keeps every version 1 field (`id`, `type`, `label`, `primary`, `risk`,
`specialty`, `masked`, `owner_kind`, `facility_type` on nodes; `source`, `target`,
`kind` on edges) so older clients keep rendering, and adds linkage evidence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NodeType = Literal["provider", "member", "facility", "owner", "address"]
EdgeKind = Literal[
    "prescribed",
    "dispensed",
    "rendered",
    "billed",
    "at_facility",
    "owns",
    "referral",
    "located_at",
    "shared_tin",
    "shared_contact",
]


class SharedAttribute(BaseModel):
    """The identifier two entities share, masked so the raw value never leaves the API."""

    kind: str = Field(description="phone, email, bank_token, tin or address")
    value_masked: str = Field(description="Masked value, e.g. 'phone ••••3F2A'")


class EdgeEvidence(BaseModel):
    """Why the edge exists: the alerts that rely on it and the records behind it."""

    alert_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    line_ids: list[str] = Field(default_factory=list)
    referral_ids: list[int] = Field(default_factory=list)
    attribute: SharedAttribute | None = None
    ownership_pct: float | None = None
    first_date: str | None = None
    last_date: str | None = None
    paid: float | None = None


class NetworkEdge(BaseModel):
    id: str = Field(description="Stable edge id: '<kind>:<source>:<target>'")
    source: str
    target: str
    kind: EdgeKind
    directed: bool = Field(description="True when source → target has meaning (referral, owns, billed).")
    direction: Literal["out", "none"] = Field(
        description="'out' = source → target (same as directed=true); 'none' = undirected. Never 'in'."
    )
    inferred: bool = Field(
        description="True when the link is inferred from a shared identifier (TIN, phone, email, bank token) "
        "rather than a recorded relationship (claim, referral, ownership, practice address)."
    )
    count: int = Field(description="Records behind the edge: referrals, claim lines, or 1 for a shared identifier.")
    weight: float = Field(description="count / max count of the same kind in this graph (0-1], for line width.")
    label: str
    in_case: bool = Field(description="True when an alert in this case relies on the edge or it joins case parties.")
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="Ids resolvable at GET /cases/{id}/evidence/{evidence_id}: alert:…, claim:…, line:… (capped).",
    )
    evidence: EdgeEvidence


class NetworkNode(BaseModel):
    id: str
    type: NodeType
    label: str
    primary: bool = False
    is_subject: bool = Field(default=False, description="A party to the case (case.entity_ids).")
    in_case: bool = Field(default=False, description="Subject, or appears on the case's flagged claim lines.")
    hop: int = Field(description="0 = subject; 1-2 = relationship hops from a subject.")
    alert_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    n_flagged_lines: int = 0
    flagged_paid: float = Field(default=0.0, description="Paid dollars on the case's flagged lines touching the node.")
    detail_path: str = Field(description="GET this path for the node's claims and findings.")
    risk: float | None = Field(default=None, description="Case priority score, primary node only.")
    harm: int | None = Field(default=None, description="Case beneficiary-harm level (0-4), subject nodes only.")
    severity: int | None = Field(default=None, description="Case severity (1-4), subject nodes only.")
    specialty: str | None = None
    masked: bool | None = None
    owner_kind: str | None = None
    facility_type: str | None = None


class NetworkLimits(BaseModel):
    hops: int
    referral_top_n: int
    max_providers: int
    max_members: int
    providers_shown: int
    providers_dropped: int
    members_total: int
    members_shown: int


class NetworkPack(BaseModel):
    schema_version: Literal[2] = 2
    case_id: str
    hops: int
    primary_entity_id: str
    subject_ids: list[str]
    masked: bool
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    limits: NetworkLimits


class NodeDetail(BaseModel):
    """Click-through payload for one node: its findings and the flagged lines it touches."""

    case_id: str
    node: NetworkNode
    profile: dict[str, object] = Field(description="Provider card, owner, address or masked member summary.")
    alerts: list[dict[str, object]] = Field(description="Serialized case alerts that reference the node.")
    claim_lines: list[dict[str, object]] = Field(description="Flagged claim lines of this case that involve the node.")
    connections: list[NetworkEdge] = Field(description="Edges in the case network that touch the node.")


class ClaimVolume(BaseModel):
    """All claim lines on file for the entity (not only the case's flagged lines)."""

    n_lines: int
    paid: float
    first_dos: str | None
    last_dos: str | None
    sample: list[dict[str, object]] = Field(description="Most recent lines (ClaimRow shape), members masked.")


class RelatedCase(BaseModel):
    case_id: str
    status: str
    lane: str
    primary_entity_id: str
    is_primary: bool


class EntitySummary(BaseModel):
    """Click-through for any node in a case network: total claims, findings and cases in the run."""

    entity_id: str
    case_id: str
    node: NetworkNode
    profile: dict[str, object]
    claims: ClaimVolume
    alerts: list[dict[str, object]] = Field(description="Alerts in this run that name the entity (any case).")
    cases: list[RelatedCase] = Field(description="Cases in this run that include the entity.")
    case_claim_lines: list[dict[str, object]] = Field(description="This case's flagged lines involving the entity.")
    connections: list[NetworkEdge]
