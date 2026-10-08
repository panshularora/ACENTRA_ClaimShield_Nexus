export type Role = "investigator" | "manager" | "analyst" | "auditor" | "admin";

export type Lane = "harm_priority" | "selected" | "needs_evidence" | "overflow";

export interface SessionUser {
  id: string;
  email: string;
  role: Role;
  display_name: string;
  permissions: string[];
  csrf_token?: string | null;
}

export interface DemoUser {
  email: string;
  role: string;
  password: string;
}

export interface MetaResponse {
  name: string;
  version: string;
  demo_mode: boolean;
  data_profile: string;
  demo_users?: DemoUser[];
}

export interface Problem {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
}

export interface BatchSummary {
  batch_id: string;
  adapter: string;
  status: string;
  profile: string | null;
  seed: number | null;
  created_at: string | null;
}

export interface RunSummary {
  run_id: string;
  status: string;
  summary: {
    n_alerts?: number;
    n_cases?: number;
    n_selected?: number;
    graph_nodes?: number;
    graph_edges?: number;
    capacity_hours?: number;
    horizon_days?: number;
    max_slots?: number;
    member_weight?: number;
    ranking_policy?: RankingPolicy;
    lanes?: Partial<Record<Lane, number>>;
  };
}

export interface BatchDetail {
  batch_id: string;
  adapter: string;
  status: string;
  profile: string | null;
  seed: number | null;
  load_report: {
    tables?: { name: string; loaded: number; rejected: number }[];
    ground_truth_rows?: number;
    scheme_ids?: string[];
    data_card?: Record<string, unknown>;
  };
  runs: RunSummary[];
}

export interface LoadBatchResponse {
  batch_id: string;
  adapter: string;
  status: string;
  profile: string | null;
  seed: number | null;
  load_report: BatchDetail["load_report"];
  run: (RunSummary["summary"] & { run_id: string; status: string }) | null;
}

export interface RankFactors {
  severity: number;
  exposure: number;
  member: number;
  evidence: number;
  urgency: number;
  composite: number;
  weights?: Record<string, number>;
  member_weight?: number;
}

export interface RankingPolicy {
  method: string;
  factors: { key: string; label: string; weight: number }[];
  max_slots: number;
  member_weight: number;
  capacity_hours: number;
  human_in_the_loop: boolean;
  overflow_is_dismissal: boolean;
  note: string;
}

export interface QueueOverride {
  action: "promote" | "defer" | "release" | string;
  reason: string;
  actor_id: string;
  prior_lane?: string;
}

export interface PipelineRun {
  run_id: string;
  batch_id: string;
  status: string;
  summary: RunSummary["summary"];
  n_alerts: number;
  n_cases: number;
  horizon_days?: number;
  capacity_hours?: number;
  screening_days?: number;
  max_slots?: number;
  member_weight?: number;
  ranking_policy?: RankingPolicy;
}

export interface QueueCase {
  case_id: string;
  lane: Lane;
  status: string;
  primary_entity_id: string;
  entity_ids?: string[];
  harm: number;
  severity: number;
  members_affected: number;
  flagged_dollars: number;
  evidence_strength: number;
  estimated_hours: number;
  p_confirm: number;
  expected_value?: number;
  f30: number | null;
  f60: number | null;
  f90: number | null;
  sla_due?: string | null;
  screening_days_left?: number | null;
  why_rank?: { code: string; text: string; recommendation?: string };
  rank_factors?: RankFactors;
  queue_rank?: number | null;
  recommendation?: "today_queue" | "gather_evidence" | "tracked_backlog" | string;
  override?: QueueOverride | null;
  suspicion_only?: boolean;
  alert_group?: { n_entities: number; n_alerts?: number; urgent?: boolean; text: string };
}

export interface PeerGroup {
  n_peers: number;
  dimensions_used: string[];
  selection: string;
  specialty?: string;
  provider_type?: string;
  geography?: string;
  service_line?: string;
  relaxed?: boolean;
  confidence?: string;
  limitation?: string;
  rural?: boolean;
}

export interface CaseAlert {
  alert_id: string;
  detector: string;
  approach?: string;
  review_reason?: string;
  rule_id: string | null;
  rule_version?: number | null;
  rule_title?: string | null;
  policy_ref?: string | null;
  entity_id: string;
  entity_type?: string;
  score: number;
  evidence: Record<string, unknown>;
  line_ids: string[];
  kind?: string;
  label?: string;
  lineage?: AlertLineage;
}

export interface DataSource {
  table: string;
  role: string;
}

export interface AlertLineage {
  detector: string;
  approach?: string;
  method: string;
  kind: string;
  how?: string | null;
  tables: DataSource[];
  fields_used?: string[];
  line_ids?: string[];
  comparison_peers_held_out?: string[];
}

export interface CaseGrouping {
  rule: string;
  text: string;
  entity_ids: string[];
  alert_count: number;
  comparison_peers_held_out?: string[];
}

export interface ProvenanceStep {
  step: number;
  name: string;
  detail: string;
}

export interface CaseProvenance {
  extract: string;
  steps: ProvenanceStep[];
  data_sources: DataSource[];
  grouping: CaseGrouping;
  urgent: { alert_id: string; rule_id: string | null; kind: string; label: string; entity_id: string; line_ids: string[] }[];
  suspicion_only?: boolean;
}

export interface ProviderCard {
  provider_id: string;
  name: string;
  npi_syn?: string | null;
  specialty?: string | null;
  kind?: string | null;
  service_line?: string | null;
  location_id?: string;
  tin_token?: string;
}

export interface MemberView {
  member_id: string;
  name: string | null;
  display: string;
  masked: boolean;
}

export interface Cite {
  id: string;
  kind: string;
  label: string;
}

export interface BriefSentence {
  text: string;
  cites: Cite[];
}

export interface BriefSection {
  title: string;
  sentences: BriefSentence[];
}

export interface MatchedPrecedent {
  page_id: string;
  slug: string;
  title: string;
  source_case: string | null;
  decision: string | null;
  why_it_matches: string;
  matching_facts: string[];
  citation: string;
}

export interface CaseBrief {
  case_id: string;
  generator: "template" | "llm";
  confidence: number;
  limitations: string[];
  action: string;
  evidence_gaps: string[];
  sections: BriefSection[];
  precedents?: MatchedPrecedent[];
  validator: { checked: number; dropped: number; cited: number };
}

export interface ClaimSignal {
  alert_id: string;
  rule_id: string | null;
  label: string;
}

export interface ClaimRow {
  line_id: string;
  claim_id: string;
  dos_from: string | null;
  dos_to: string | null;
  code: string;
  code_system: string;
  modifiers: string[];
  units: number;
  minutes: number | null;
  pos: string;
  charge: number;
  allowed: number;
  paid: number;
  rendering_provider_id: string;
  ordering_provider_id: string | null;
  billing_provider_id: string | null;
  facility_id: string | null;
  claim_type: string | null;
  claim_status: string | null;
  received_date: string | null;
  adjudicated_date: string | null;
  member: MemberView;
  signals: ClaimSignal[];
  source_system?: string | null;
  source_ref?: string | null;
}

export interface ClaimsPack {
  case_id: string;
  masked: boolean;
  rows: ClaimRow[];
}

export interface TimelineEvent {
  ts: string;
  kind: string;
  flag: boolean;
  ref: string;
  title: string;
  detail: string;
  entity_id: string;
}

/**
 * Network node from GET /cases/{id}/network. Fields marked "newer API" are being added on the
 * backend branch fix/backend-p0; they are optional so the UI works with both shapes
 * (components/network/graphModel.ts normalises them).
 */
export interface NetworkNode {
  id: string;
  type: string;
  label: string;
  primary?: boolean;
  masked?: boolean;
  /** Case p_confirm, on the primary node only. */
  risk?: number;
  specialty?: string;
  facility_type?: string;
  owner_kind?: string;
  /** Newer API: true for the case subject. */
  is_subject?: boolean;
  /** Newer API: true when the entity belongs to the case (vs surrounding context). */
  in_case?: boolean;
  /** Newer API: alerts on this case that involve the entity. */
  alert_ids?: string[];
  /** Newer API: flagged paid dollars on this case attributable to the entity. */
  flagged_dollars?: number;
  flagged_paid?: number;
  /** Newer API: flagged claim lines on this case attributable to the entity. */
  n_flagged_lines?: number;
  /** Newer API: hop distance from the subject (capped at 2). */
  hop?: number;
  /** Newer API: patient-harm level for the entity. */
  harm?: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  kind: string;
  /** Newer API: stable edge id. */
  id?: string;
  /** Newer API: "out" (source → target), "in", or "none". */
  direction?: "out" | "in" | "none";
  /** Newer API: number of underlying records (referrals, shared claims). */
  count?: number;
  /** Newer API: evidence ids (alerts, contact hashes, ownership links) behind the edge. */
  evidence_ids?: string[];
  /** Newer API: inferred / weak link. */
  inferred?: boolean;
}

export interface NetworkPack {
  case_id: string;
  hops: number;
  primary_entity_id: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface DecisionRecord {
  decision_id: string;
  case_id: string;
  actor_id: string;
  action: string;
  ladder_step: string | null;
  ladder_label?: string | null;
  reason: string;
  evidence_refs: string[];
  approved_by?: string | null;
  created_at: string | null;
}

export interface AuditReceipt {
  seq: number;
  hash: string;
  prev_hash: string;
  ts: string | null;
  action: string;
  actor?: string;
  actor_id?: string | null;
  case_id?: string;
  reason?: string;
  chain_intact?: boolean;
  last_seq?: number;
}

export interface WikiProposal {
  proposal_id: string;
  kind: string;
  status: string;
  title: string;
  source_case_id: string;
  decision_id: string;
  body: {
    source_case?: string;
    decision?: string;
    outcome?: string;
    confirmed_pattern?: string[];
    scheme_tags?: string[];
    rules?: { rule_id: string; title: string }[];
    key_evidence?: { alert_id: string; rule_id: string | null; label: string; line_count: number }[];
    supporting_line_ids?: string[];
    rationale?: string;
    limitations?: string[];
    changes?: string[];
    sources?: { kind: string; id: string }[];
    [key: string]: unknown;
  };
  banner: string | null;
  created_by: string;
  created_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_note: string | null;
  page_id: string | null;
}

export interface WikiPage {
  page_id: string;
  slug: string;
  type: string;
  title: string;
  status: string;
  body: WikiProposal["body"];
  source_proposal_id: string;
  created_at: string | null;
  approved_by: string;
}

export interface LabelRecord {
  label_id: string;
  case_id: string;
  decision_id: string;
  action: string;
  status: string;
  scheme_tags: string[];
  rule_ids: string[];
  created_at: string | null;
  approved_by: string | null;
  approved_at: string | null;
}

/** Actions POST /cases/{id}/decisions accepts today (being revised on the backend). */
export type DecisionAction = "escalate" | "monitor" | "dismiss" | "needs_evidence";

export interface DecisionResult {
  decision_id: string;
  case_id: string;
  action: string;
  status: string;
  reason: string;
  ladder_step: string | null;
  ladder_label?: string | null;
  evidence_refs: string[];
  created_at: string | null;
  audit: AuditReceipt;
  proposal?: WikiProposal;
  label?: LabelRecord;
  note: string;
}

export interface AuditEvent {
  seq: number;
  ts: string;
  actor_id: string | null;
  actor: string;
  role: string;
  action: string;
  object_type: string;
  object_id: string;
  payload: Record<string, unknown>;
  chain_ok: boolean;
  hash?: string;
  prev_hash?: string;
}

export interface AuditLog {
  events: AuditEvent[];
  verification: {
    intact: boolean;
    last_seq: number;
    last_hash: string | null;
    n_events: number;
  };
}

export interface EvidenceItem {
  item_id: string;
  kind: string;
  payload: Record<string, unknown>;
}

export interface CaseDetail {
  case_id: string;
  run_id: string;
  status: string;
  lane: Lane;
  assignee_id: string | null;
  primary_entity_id: string;
  primary_entity_type: string;
  entity_ids?: string[];
  primary_entity?: ProviderCard;
  harm: number;
  severity: number;
  members_affected: number;
  flagged_dollars: number;
  evidence_strength: number;
  estimated_hours: number;
  p_confirm: number;
  expected_value?: number;
  f30: number | null;
  f60: number | null;
  f90: number | null;
  sla_due?: string | null;
  screening_days_left?: number | null;
  why_rank?: { code: string; text: string; recommendation?: string };
  rank_factors?: RankFactors;
  recommendation?: string;
  override?: QueueOverride | null;
  alerts: CaseAlert[];
  evidence_gaps?: string[];
  latest_decision?: DecisionRecord | null;
  latest_proposal?: WikiProposal | null;
  latest_label?: LabelRecord | null;
  member_unmask_permitted?: boolean;
  can_assign?: boolean;
  suspicion_only?: boolean;
  grouping?: CaseGrouping;
  provenance?: CaseProvenance;
}
