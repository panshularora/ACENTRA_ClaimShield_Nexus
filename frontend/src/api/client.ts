import type {
  AuditEvent,
  AuditLog,
  BatchDetail,
  BatchSummary,
  CaseBrief,
  CaseDetail,
  ClaimsPack,
  DecisionResult,
  EvidenceItem,
  Lane,
  LoadBatchResponse,
  MetaResponse,
  NetworkPack,
  PipelineRun,
  QueueCase,
  SessionUser,
  TimelineEvent,
  WikiPage,
  WikiProposal,
} from "./types";

export class ApiError extends Error {
  status: number;
  problem: Record<string, unknown>;

  constructor(status: number, message: string, problem: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

function readCookie(name: string): string | null {
  const parts = document.cookie.split("; ");
  const hit = parts.find((row) => row.startsWith(`${name}=`));
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : null;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = readCookie("cs_csrf");
  const method = (init.method ?? "GET").toUpperCase();
  if (csrf && method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrf);
  }

  const send = () =>
    fetch(path, {
      ...init,
      headers,
      credentials: "include",
    });

  let res = await send();
  if (
    res.status === 401 &&
    path !== "/api/v1/auth/login" &&
    path !== "/api/v1/auth/refresh" &&
    path !== "/api/v1/auth/me"
  ) {
    const refresh = await fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
    });
    if (refresh.ok) {
      res = await send();
    }
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
    const detail =
      (typeof body.detail === "string" && body.detail) ||
      (typeof body.title === "string" && body.title) ||
      res.statusText;
    throw new ApiError(res.status, detail, body);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  meta: () => request<MetaResponse>("/api/v1/meta"),
  me: () => request<SessionUser>("/api/v1/auth/me"),
  login: (email: string, password: string) =>
    request<SessionUser>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () =>
    request<{ status: string }>("/api/v1/auth/logout", { method: "POST" }),
  listBatches: () => request<BatchSummary[]>("/api/v1/batches"),
  getBatch: (batchId: string) => request<BatchDetail>(`/api/v1/batches/${batchId}`),
  loadBatch: (body: {
    adapter?: string;
    profile: string;
    seed: number;
    horizon_days: number;
    capacity_hours: number;
    max_slots?: number;
    member_weight?: number;
    run_now: boolean;
  }) =>
    request<LoadBatchResponse>("/api/v1/batches", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getRun: (runId: string) => request<PipelineRun>(`/api/v1/runs/${runId}`),
  getCurrentRun: () => request<PipelineRun>("/api/v1/runs/current"),
  startRun: (body: {
    batch_id?: string;
    horizon_days: number;
    capacity_hours: number;
    max_slots?: number;
    member_weight?: number;
  }) =>
    request<PipelineRun>("/api/v1/runs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  overrideRank: (caseId: string, body: { action: "promote" | "defer" | "release"; reason: string }) =>
    request<{
      case_id: string;
      lane: Lane;
      status: string;
      recommendation: string;
      override: { action: string; reason: string; actor_id: string; prior_lane: string };
      note: string;
    }>(`/api/v1/cases/${caseId}/rank`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getQueue: (runId: string) => request<QueueCase[]>(`/api/v1/runs/${runId}/queue`),
  getCase: (caseId: string) => request<CaseDetail>(`/api/v1/cases/${caseId}`),
  getBrief: (caseId: string) => request<CaseBrief>(`/api/v1/cases/${caseId}/brief`),
  getClaims: (caseId: string, unmask = false) =>
    request<ClaimsPack>(`/api/v1/cases/${caseId}/claims${unmask ? "?unmask=true" : ""}`),
  getTimeline: (caseId: string, unmask = false) =>
    request<{ case_id: string; events: TimelineEvent[] }>(
      `/api/v1/cases/${caseId}/timeline${unmask ? "?unmask=true" : ""}`,
    ),
  getNetwork: (caseId: string, hops = 2, unmask = false) =>
    request<NetworkPack>(
      `/api/v1/cases/${caseId}/network?hops=${hops}${unmask ? "&unmask=true" : ""}`,
    ),
  getEvidence: (caseId: string, itemId: string) =>
    request<EvidenceItem>(`/api/v1/cases/${caseId}/evidence/${itemId}`),
  assignCase: (caseId: string, assigneeId?: string) =>
    request<CaseDetail>(`/api/v1/cases/${caseId}/assign`, {
      method: "POST",
      body: JSON.stringify(assigneeId ? { assignee_id: assigneeId } : {}),
    }),
  decide: (
    caseId: string,
    body: {
      action: "escalate" | "monitor" | "dismiss" | "needs_evidence";
      reason: string;
      ladder_step?: string | null;
      evidence_refs?: string[];
    },
  ) =>
    request<DecisionResult>(`/api/v1/cases/${caseId}/decisions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getAudit: (params?: { actor?: string; action?: string; from?: string; to?: string }) => {
    const q = new URLSearchParams();
    if (params?.actor) q.set("actor", params.actor);
    if (params?.action) q.set("action", params.action);
    if (params?.from) q.set("from", params.from);
    if (params?.to) q.set("to", params.to);
    const suffix = q.toString() ? `?${q.toString()}` : "";
    return request<AuditLog>(`/api/v1/audit${suffix}`);
  },
  verifyAudit: () => request<AuditLog["verification"]>("/api/v1/audit/verify"),
  getAuditEvent: (seq: number) => request<AuditEvent>(`/api/v1/audit/${seq}`),
  listProposals: (status?: string) =>
    request<{ proposals: WikiProposal[] }>(
      `/api/v1/wiki/proposals${status ? `?status=${encodeURIComponent(status)}` : ""}`,
    ),
  getProposal: (id: string) => request<WikiProposal>(`/api/v1/wiki/proposals/${id}`),
  approveProposal: (id: string, note = "") =>
    request<{ proposal: WikiProposal; page: WikiPage }>(`/api/v1/wiki/proposals/${id}:approve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  rejectProposal: (id: string, note: string) =>
    request<WikiProposal>(`/api/v1/wiki/proposals/${id}:reject`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  listPages: (type?: string) =>
    request<{ pages: WikiPage[] }>(`/api/v1/wiki/pages${type ? `?type=${encodeURIComponent(type)}` : ""}`),
  getPage: (slug: string) => request<WikiPage>(`/api/v1/wiki/pages/${slug}`),
  approveDecision: (decisionId: string, note = "") =>
    request<{ decision_id: string; proposal: WikiProposal; page: WikiPage }>(
      `/api/v1/decisions/${decisionId}:approve`,
      { method: "POST", body: JSON.stringify({ note }) },
    ),
};

export function can(user: SessionUser | null, permission: string): boolean {
  if (!user) return false;
  return user.permissions.includes(permission) || user.permissions.includes("admin:*");
}
