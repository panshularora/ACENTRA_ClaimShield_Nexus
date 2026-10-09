import type {
  AuditEvent,
  AuditLog,
  AuthSession,
  AwsStatus,
  BatchDetail,
  BatchSummary,
  CaseBrief,
  CaseDetail,
  ClaimsPack,
  DecisionAction,
  DecisionOptions,
  DecisionResult,
  DecisionReviewResult,
  EntitySummary,
  EvidenceItem,
  HistoryResponse,
  Lane,
  LoadBatchResponse,
  MetaResponse,
  NetworkPack,
  NodeDetail,
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

let csrfMemory: string | null = null;

function rememberCsrf(token: string | null | undefined): void {
  if (token) csrfMemory = token;
}

function csrfToken(): string | null {
  return readCookie("cs_csrf") || csrfMemory;
}

function captureCsrf(payload: unknown): void {
  if (!payload || typeof payload !== "object") return;
  const body = payload as { csrf_token?: unknown; user?: { csrf_token?: unknown } };
  if (typeof body.csrf_token === "string") rememberCsrf(body.csrf_token);
  if (typeof body.user?.csrf_token === "string") rememberCsrf(body.user.csrf_token);
}

const PROD_API = "https://claimshield-nexus-api.vercel.app";

/** Local Vite uses the /api proxy. Production talks to the public FastAPI origin. */
function apiUrl(path: string): string {
  if (import.meta.env.DEV) return path;
  const raw = (import.meta.env.VITE_API_BASE as string | undefined) || PROD_API;
  return `${raw.replace(/\/$/, "")}${path}`;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = csrfToken();
  const method = (init.method ?? "GET").toUpperCase();
  if (csrf && method !== "GET" && method !== "HEAD") {
    headers.set("X-CSRF-Token", csrf);
  }

  const send = () =>
    fetch(apiUrl(path), {
      ...init,
      headers,
      credentials: "include",
    });

  let res = await send();
  if (
    res.status === 401 &&
    path !== "/api/v1/auth/login" &&
    path !== "/api/v1/auth/refresh" &&
    path !== "/api/v1/auth/session"
  ) {
    const refreshHeaders = new Headers();
    const refreshCsrf = csrfToken();
    if (refreshCsrf) refreshHeaders.set("X-CSRF-Token", refreshCsrf);
    const refresh = await fetch(apiUrl("/api/v1/auth/refresh"), {
      method: "POST",
      credentials: "include",
      headers: refreshHeaders,
    });
    if (refresh.ok) {
      const refreshed = (await refresh.json().catch(() => null)) as unknown;
      captureCsrf(refreshed);
      const nextCsrf = csrfToken();
      if (nextCsrf) headers.set("X-CSRF-Token", nextCsrf);
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
  const data = (await res.json()) as T;
  captureCsrf(data);
  return data;
}

export const api = {
  meta: () => request<MetaResponse>("/api/v1/meta"),
  me: () => request<SessionUser>("/api/v1/auth/me"),
  session: () => request<AuthSession>("/api/v1/auth/session"),
  refresh: () => request<SessionUser>("/api/v1/auth/refresh", { method: "POST" }),
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
  getCaseHistory: () => request<HistoryResponse>("/api/v1/cases/history"),
  getAwsStatus: () => request<AwsStatus>("/api/v1/aws/status"),
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
  getNetworkNode: (caseId: string, nodeId: string, unmask = false) =>
    request<NodeDetail>(
      `/api/v1/cases/${caseId}/network/nodes/${encodeURIComponent(nodeId)}${unmask ? "?unmask=true" : ""}`,
    ),
  getEntitySummary: (entityId: string, caseId: string, unmask = false) =>
    request<EntitySummary>(
      `/api/v1/entities/${encodeURIComponent(entityId)}/summary?case_id=${encodeURIComponent(caseId)}${unmask ? "&unmask=true" : ""}`,
    ),
  getDecisionOptions: (caseId: string) =>
    request<DecisionOptions>(`/api/v1/cases/${caseId}/decision-options`),
  getEvidence: (caseId: string, itemId: string) =>
    request<EvidenceItem>(`/api/v1/cases/${caseId}/evidence/${encodeURIComponent(itemId)}`),
  assignCase: (caseId: string, assigneeId?: string) =>
    request<CaseDetail>(`/api/v1/cases/${caseId}/assign`, {
      method: "POST",
      body: JSON.stringify(assigneeId ? { assignee_id: assigneeId } : {}),
    }),
  unassignCase: (caseId: string) =>
    request<CaseDetail>(`/api/v1/cases/${caseId}/unassign`, {
      method: "POST",
      body: "{}",
    }),
  decide: (
    caseId: string,
    body: {
      action: DecisionAction;
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
    request<DecisionReviewResult>(`/api/v1/decisions/${decisionId}:approve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  rejectDecision: (decisionId: string, note: string) =>
    request<DecisionReviewResult>(`/api/v1/decisions/${decisionId}:reject`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  reopenCase: (caseId: string, reason: string) =>
    request<{ case_id: string; status: string; audit: AuditEvent }>(`/api/v1/cases/${caseId}/reopen`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
};

export function can(user: SessionUser | null, permission: string): boolean {
  if (!user) return false;
  return user.permissions.includes(permission) || user.permissions.includes("admin:*");
}
