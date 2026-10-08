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

export interface PipelineRun {
  run_id: string;
  batch_id: string;
  status: string;
  summary: RunSummary["summary"];
  n_alerts: number;
  n_cases: number;
}

export interface QueueCase {
  case_id: string;
  lane: Lane;
  status: string;
  primary_entity_id: string;
  harm: number;
  severity: number;
  members_affected: number;
  flagged_dollars: number;
  evidence_strength: number;
  estimated_hours: number;
  p_confirm: number;
  f30: number | null;
  f60: number | null;
  f90: number | null;
}

export interface CaseAlert {
  alert_id: string;
  detector: string;
  rule_id: string | null;
  rule_version?: number | null;
  rule_title?: string | null;
  entity_id: string;
  entity_type?: string;
  score: number;
  evidence: Record<string, unknown>;
  line_ids: string[];
  kind?: string;
  label?: string;
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

export interface CaseBrief {
  case_id: string;
  generator: "template" | "llm";
  confidence: number;
  limitations: string[];
  action: string;
  evidence_gaps: string[];
  sections: BriefSection[];
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

export interface NetworkNode {
  id: string;
  type: string;
  label: string;
  primary?: boolean;
  masked?: boolean;
  risk?: number;
  specialty?: string;
}

export interface NetworkEdge {
  source: string;
  target: string;
  kind: string;
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
  reason: string;
  evidence_refs: string[];
  created_at: string | null;
}

export interface DecisionResult {
  decision_id: string;
  case_id: string;
  action: string;
  status: string;
  reason: string;
  ladder_step: string | null;
  evidence_refs: string[];
  created_at: string | null;
  audit: {
    seq: number;
    hash: string;
    prev_hash: string;
    ts: string | null;
    action: string;
  };
  note: string;
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
  primary_entity?: ProviderCard;
  harm: number;
  severity: number;
  members_affected: number;
  flagged_dollars: number;
  evidence_strength: number;
  estimated_hours: number;
  p_confirm: number;
  f30: number | null;
  f60: number | null;
  f90: number | null;
  alerts: CaseAlert[];
  evidence_gaps?: string[];
  latest_decision?: DecisionRecord | null;
  member_unmask_permitted?: boolean;
}
