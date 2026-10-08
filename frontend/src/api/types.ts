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

/** GET /auth/session always returns 200, including before login. */
export interface AuthSession {
  authenticated: boolean;
  user: SessionUser | null;
  refresh_available: boolean;
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
    risk_model?: RiskModelInfo;
    /** Hours actually packed against capacity (override hours count). */
    capacity?: CapacitySummary;
  };
}

/** `run.summary.capacity`: investigator hours vs the desk budget. */
export interface CapacitySummary {
  capacity_hours: number;
  priority_override_hours: number;
  selected_hours: number;
  capacity_used_hours: number;
  over_capacity_hours: number;
  override_share: number | null;
  override_share_warning: boolean;
  needs_evidence_hours: number;
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
  capacity?: CapacitySummary;
}

/** Which scorer produced p_confirm and f30/f60/f90 for a run. */
export interface RiskModelInfo {
  score_kind: ScoreKind;
  model_version: string;
  calibrated: boolean;
  as_of?: string;
  note?: string;
  [key: string]: unknown;
}

export type ScoreKind = "trained_model" | "uncalibrated_heuristic";

/** One per-case driver of a model score (contribution to the logit). */
export interface RiskFactor {
  feature: string;
  label: string;
  value: number;
  contribution: number;
  direction: "raises" | "lowers";
}

/**
 * Risk-model fields on queue rows and case detail. p_confirm and f30/f60/f90 stay as before;
 * risk_30/60/90 are aliases of f30/f60/f90. See docs/MODEL_CARD.md.
 */
export interface RiskScoreFields {
  risk_30?: number | null;
  risk_60?: number | null;
  risk_90?: number | null;
  score_kind?: ScoreKind;
  model_version?: string;
  calibrated?: boolean;
  risk_as_of?: string | null;
  /** Provider whose 30/60/90 curve the case shows (riskiest subject). */
  risk_subject?: string | null;
  /** Monthly hazards h1..h3 behind the cumulative curve. */
  monthly_hazards?: number[] | null;
  risk_factors?: RiskFactor[];
  p_confirm_factors?: RiskFactor[];
}

export interface QueueCase extends RiskScoreFields {
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
  lane_label?: string;
  priority_override?: boolean;
  override_kinds?: string[];
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

/** Node from GET /cases/{id}/network (schema v2). */
export interface NetworkNode {
  id: string;
  type: string;
  label: string;
  primary?: boolean;
  masked?: boolean;
  /** Case priority score, primary node only. */
  risk?: number;
  specialty?: string;
  facility_type?: string;
  owner_kind?: string;
  is_subject?: boolean;
  in_case?: boolean;
  alert_ids?: string[];
  rule_ids?: string[];
  /** Paid $ on this case's flagged lines touching the node. Queue rows still use flagged_dollars. */
  flagged_paid?: number;
  n_flagged_lines?: number;
  hop?: number;
  harm?: number;
  /** Case severity 1–4, subject nodes only. */
  severity?: number;
  detail_path?: string;
}

export interface SharedAttribute {
  kind: string;
  value_masked: string;
}

export interface EdgeEvidence {
  alert_ids: string[];
  rule_ids: string[];
  claim_ids: string[];
  line_ids: string[];
  referral_ids: number[];
  attribute?: SharedAttribute | null;
  ownership_pct?: number | null;
  first_date?: string | null;
  last_date?: string | null;
  paid?: number | null;
}

export interface NetworkEdge {
  source: string;
  target: string;
  kind: string;
  id?: string;
  directed?: boolean;
  /** "out" (source → target) or "none". Schema v2 never sends "in". */
  direction?: "out" | "in" | "none";
  count?: number;
  weight?: number;
  label?: string;
  in_case?: boolean;
  evidence_ids?: string[];
  inferred?: boolean;
  evidence?: EdgeEvidence;
}

export interface NetworkLimits {
  hops: number;
  referral_top_n: number;
  max_providers: number;
  max_members: number;
  providers_shown: number;
  providers_dropped: number;
  members_total: number;
  members_shown: number;
}

export interface NetworkPack {
  schema_version?: number;
  case_id: string;
  hops: number;
  primary_entity_id: string;
  subject_ids?: string[];
  masked?: boolean;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  limits?: NetworkLimits;
}

export interface ClaimVolume {
  n_lines: number;
  paid: number;
  first_dos: string | null;
  last_dos: string | null;
  sample: ClaimRow[];
}

export interface RelatedCase {
  case_id: string;
  status: string;
  lane: string;
  primary_entity_id: string;
  is_primary: boolean;
}

export interface NodeDetail {
  case_id: string;
  node: NetworkNode;
  profile: Record<string, unknown>;
  alerts: CaseAlert[];
  claim_lines: ClaimRow[];
  connections: NetworkEdge[];
}

export interface EntitySummary {
  entity_id: string;
  case_id: string;
  node: NetworkNode;
  profile: Record<string, unknown>;
  claims: ClaimVolume;
  alerts: CaseAlert[];
  cases: RelatedCase[];
  case_claim_lines: ClaimRow[];
  connections: NetworkEdge[];
}

export interface DecisionRecord {
  decision_id: string;
  case_id: string;
  actor_id: string;
  action: string;
  status?: string;
  ladder_step: string | null;
  ladder_label?: string | null;
  reason: string;
  evidence_refs: string[];
  requires_approval?: boolean;
  approved_by?: string | null;
  approved_at?: string | null;
  review_note?: string | null;
  created_at: string | null;
}

export type DecisionAction = "escalate" | "monitor" | "dismiss" | "needs_evidence";

export interface LadderStepOption {
  step: string;
  label: string;
  default: boolean;
  requires_basis_on_approval: boolean;
}

export interface DecisionOption {
  id: DecisionAction;
  label: string;
  hint: string;
  requires_approval: boolean;
  closes_case: boolean;
  resulting_status: string;
  default_step: string | null;
  ladder: LadderStepOption[];
  enabled: boolean;
}

export interface DecisionOptions {
  case_id: string;
  status: string;
  role: string;
  can_decide: boolean;
  blocked_reason: string | null;
  allowed_actions: string[];
  can_approve: boolean;
  can_reopen: boolean;
  pending_decision: DecisionRecord | null;
  min_reason_chars: number;
  max_reason_chars: number;
  options: DecisionOption[];
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
    observed_pattern?: string[];
    pattern_status?: string;
    decision_context?: string;
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

export interface DecisionResult {
  decision_id: string;
  case_id: string;
  action: string;
  status: string;
  decision_status?: string;
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

/** POST /decisions/{id}:approve and :reject. */
export interface DecisionReviewResult {
  decision: DecisionRecord;
  case_id: string;
  status: string;
  audit: AuditReceipt;
  proposal?: WikiProposal;
  label?: LabelRecord;
  note?: string;
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

export interface CaseDetail extends RiskScoreFields {
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
  pending_decision?: DecisionRecord | null;
  allowed_actions?: string[];
  can_decide?: boolean;
  decision_blocked_reason?: string | null;
  decision_options?: DecisionOption[];
  latest_proposal?: WikiProposal | null;
  latest_label?: LabelRecord | null;
  member_unmask_permitted?: boolean;
  can_assign?: boolean;
  suspicion_only?: boolean;
  grouping?: CaseGrouping;
  provenance?: CaseProvenance;
  lane_label?: string;
  priority_override?: boolean;
  override_kinds?: string[];
}
