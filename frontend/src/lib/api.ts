import { getToken, clearToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options?.headers as Record<string, string> | undefined),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in.");
  }

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error ${response.status}: ${error}`);
  }
  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export async function getHealth() {
  return fetchJson<{ status: string }>("/health/");
}

export type CampaignType = "email" | "social" | "ppc" | "content";
export type CampaignStatus = "draft" | "scheduled" | "active" | "paused" | "completed";
export type LeadStatus = "new" | "contacted" | "qualified" | "converted" | "lost";
export type EventType = "impression" | "click" | "conversion" | "bounce";

export interface Campaign {
  id: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  start_date: string | null;
  end_date: string | null;
  budget: number | null;
  description: string | null;
}

export interface CampaignDetail extends Campaign {
  lead_count: number;
  total_spend: number;
  conversion_count: number;
}

export interface Lead {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  company: string | null;
  source: string | null;
  status: LeadStatus;
  campaign_id: string | null;
}

export interface AnalyticsEvent {
  id: string;
  campaign_id: string;
  event_type: EventType;
  value: number;
  recorded_at: string;
}

export interface DashboardStats {
  active_campaigns: number;
  total_leads: number;
  conversion_rate: number;
  total_spend: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export async function getDashboard(): Promise<DashboardStats> {
  return fetchJson<DashboardStats>("/api/v1/dashboard");
}

export async function getCampaigns(
  status?: CampaignStatus,
  type?: CampaignType
): Promise<PaginatedResponse<Campaign>> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (type) params.append("type", type);
  return fetchJson<PaginatedResponse<Campaign>>(`/api/v1/campaigns/?${params.toString()}`);
}

export async function getCampaign(id: string): Promise<CampaignDetail> {
  return fetchJson<CampaignDetail>(`/api/v1/campaigns/${id}`);
}

export async function createCampaign(data: Omit<Campaign, "id">): Promise<Campaign> {
  return fetchJson<Campaign>("/api/v1/campaigns/", { method: "POST", body: JSON.stringify(data) });
}

export async function updateCampaign(id: string, data: Partial<Campaign>): Promise<Campaign> {
  return fetchJson<Campaign>(`/api/v1/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteCampaign(id: string): Promise<void> {
  await fetchJson<void>(`/api/v1/campaigns/${id}`, { method: "DELETE" });
}

export async function getLeads(
  search?: string,
  source?: string,
  status?: LeadStatus,
  campaign_id?: string
): Promise<PaginatedResponse<Lead>> {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (source) params.append("source", source);
  if (status) params.append("status", status);
  if (campaign_id) params.append("campaign_id", campaign_id);
  return fetchJson<PaginatedResponse<Lead>>(`/api/v1/leads/?${params.toString()}`);
}

export async function getLead(id: string): Promise<Lead> {
  return fetchJson<Lead>(`/api/v1/leads/${id}`);
}

export async function createLead(data: Omit<Lead, "id">): Promise<Lead> {
  return fetchJson<Lead>("/api/v1/leads/", { method: "POST", body: JSON.stringify(data) });
}

export async function updateLead(id: string, data: Partial<Lead>): Promise<Lead> {
  return fetchJson<Lead>(`/api/v1/leads/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteLead(id: string): Promise<void> {
  await fetchJson<void>(`/api/v1/leads/${id}`, { method: "DELETE" });
}

export async function getAnalyticsByCampaign(
  campaignId: string,
  event_type?: EventType
): Promise<PaginatedResponse<AnalyticsEvent>> {
  const params = new URLSearchParams();
  if (event_type) params.append("event_type", event_type);
  return fetchJson<PaginatedResponse<AnalyticsEvent>>(
    `/api/v1/analytics/campaign/${campaignId}?${params.toString()}`
  );
}

export async function getAnalyticsSummary(campaignId: string): Promise<Record<string, { count: number; total_value: number }>> {
  return fetchJson<Record<string, { count: number; total_value: number }>>(
    `/api/v1/analytics/campaign/${campaignId}/summary`
  );
}

/* ============================================================
   Organizations & Projects (A1)
   ============================================================ */

export type OrgRole =
  | "admin"
  | "manager"
  | "creatives"
  | "social_media_manager"
  | "seo_specialist"
  | "paid_media_specialist"
  | "reviewer"
  | "analyst"
  | "viewer"
  | "client";

export type ProjectStatus = "active" | "paused" | "archived";

export interface Organization {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  is_external: boolean;
}

export interface Project {
  id: string;
  organization_id: string;
  slug: string;
  name: string;
  description: string | null;
  goals_json: Record<string, unknown> | null;
  status: ProjectStatus;
}

export interface OrgMembership {
  id: string;
  user_id: string;
  organization_id: string;
  role: OrgRole;
}

export interface ProjectMembership {
  id: string;
  user_id: string;
  project_id: string;
  role: OrgRole;
}

export async function listOrgs(): Promise<Organization[]> {
  return fetchJson<Organization[]>("/api/v1/orgs");
}

export async function createOrg(data: {
  slug: string;
  name: string;
  description?: string;
  is_external?: boolean;
}): Promise<Organization> {
  return fetchJson<Organization>("/api/v1/orgs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getOrg(orgId: string): Promise<Organization> {
  return fetchJson<Organization>(`/api/v1/orgs/${orgId}`);
}

export async function updateOrg(
  orgId: string,
  data: { name?: string; description?: string; is_external?: boolean },
): Promise<Organization> {
  return fetchJson<Organization>(`/api/v1/orgs/${orgId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteOrg(orgId: string): Promise<void> {
  await fetchJson<void>(`/api/v1/orgs/${orgId}`, { method: "DELETE" });
}

export async function listOrgMembers(orgId: string): Promise<OrgMembership[]> {
  return fetchJson<OrgMembership[]>(`/api/v1/orgs/${orgId}/memberships`);
}

export async function addOrgMember(
  orgId: string,
  data: { user_id: string; role: OrgRole },
): Promise<OrgMembership> {
  return fetchJson<OrgMembership>(`/api/v1/orgs/${orgId}/memberships`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateOrgMemberRole(
  orgId: string,
  membershipId: string,
  role: OrgRole,
): Promise<OrgMembership> {
  return fetchJson<OrgMembership>(
    `/api/v1/orgs/${orgId}/memberships/${membershipId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    },
  );
}

export async function removeOrgMember(
  orgId: string,
  membershipId: string,
): Promise<void> {
  await fetchJson<void>(
    `/api/v1/orgs/${orgId}/memberships/${membershipId}`,
    { method: "DELETE" },
  );
}

// ============================================================
// Goals / Constraints / Autonomy Posture (Theme Q5)
// ============================================================

export interface Goals {
  objectives?: string[];
  north_star_metric?: string;
  target_quarterly_value?: number | null;
  icps?: string[];
  channels_of_interest?: string[];
}

export interface Constraints {
  brand_safety_lines?: string[];
  monthly_budget_usd?: number | null;
  max_daily_posts?: number | null;
}

export type TrustMode = "autopilot" | "soft_gate" | "hard_gate";

export type AutonomyPosture = Partial<Record<string, TrustMode>>;

export interface GoalsRead {
  organization_id: string;
  goals: Goals | null;
  constraints: Constraints | null;
  autonomy_posture: AutonomyPosture | null;
}

export async function getGoals(orgId: string): Promise<GoalsRead> {
  return fetchJson<GoalsRead>(`/api/v1/orgs/${orgId}/goals`);
}

export async function updateGoals(
  orgId: string,
  data: {
    goals?: Goals | null;
    constraints?: Constraints | null;
    autonomy_posture?: AutonomyPosture | null;
  },
): Promise<GoalsRead> {
  return fetchJson<GoalsRead>(`/api/v1/orgs/${orgId}/goals`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

// ============================================================
// Ingestion + Knowledge Graph (Theme Q2 / Q3)
// ============================================================

export type IngestionSourceType = "file" | "url" | "git" | "zip";
export type IngestionStatus =
  | "queued"
  | "fetching"
  | "parsing"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

export interface IngestionSource {
  id: string;
  organization_id: string;
  source_type: IngestionSourceType;
  source_reference: string;
  name: string | null;
  status: IngestionStatus;
  document_chunks_created: number;
  error_message: string | null;
  metadata_json: Record<string, unknown> | null;
  job_id: string | null;
}

export interface DocumentChunk {
  id: string;
  source_id: string;
  position: number;
  text: string;
  estimated_tokens: number | null;
  metadata_json: Record<string, unknown> | null;
}

export interface IngestResponse {
  source_id: string;
  job_id: string;
  status: IngestionStatus;
}

export async function listIngestions(
  orgId: string,
  limit = 50,
): Promise<IngestionSource[]> {
  return fetchJson<IngestionSource[]>(
    `/api/v1/ingest?organization_id=${orgId}&limit=${limit}`,
  );
}

export async function getIngestion(sourceId: string): Promise<IngestionSource> {
  return fetchJson<IngestionSource>(`/api/v1/ingest/${sourceId}`);
}

export async function getIngestionChunks(
  sourceId: string,
): Promise<DocumentChunk[]> {
  return fetchJson<DocumentChunk[]>(`/api/v1/ingest/${sourceId}/chunks`);
}

export async function ingestFile(data: {
  organization_id: string;
  asset_id: string;
  name?: string;
}): Promise<IngestResponse> {
  return fetchJson<IngestResponse>(`/api/v1/ingest/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export interface KGSearchResultChunk {
  chunk_id: string;
  source_id: string;
  position: number;
  text: string;
  score: number;
  estimated_tokens: number | null;
  source_name: string | null;
  source_type: IngestionSourceType;
  source_reference: string;
}

export interface KGSearchResponse {
  query: string;
  top_k: number;
  organization_id: string;
  results: KGSearchResultChunk[];
}

export async function kgSearch(
  orgId: string,
  query: string,
  topK = 10,
): Promise<KGSearchResponse> {
  return fetchJson<KGSearchResponse>(`/api/v1/kg/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ organization_id: orgId, query, top_k: topK }),
  });
}

export interface KGStats {
  organization_id: string;
  chunk_count: number;
  embedded_count: number;
  source_count: number;
}

export async function kgStats(orgId: string): Promise<KGStats> {
  return fetchJson<KGStats>(`/api/v1/kg/stats?organization_id=${orgId}`);
}

export async function listProjects(orgId: string): Promise<Project[]> {
  return fetchJson<Project[]>(`/api/v1/orgs/${orgId}/projects`);
}

export async function createProject(
  orgId: string,
  data: { slug: string; name: string; description?: string; goals_json?: Record<string, unknown> },
): Promise<Project> {
  return fetchJson<Project>(`/api/v1/orgs/${orgId}/projects`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/* ============================================================
   Admin user management
   ============================================================ */

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
  password_reset_required: boolean;
}

export interface AdminUserCreateResponse {
  user: AdminUser;
  temp_password: string;
}

export async function adminListUsers(): Promise<AdminUser[]> {
  return fetchJson<AdminUser[]>("/api/v1/admin/users");
}

export async function adminCreateUser(data: {
  email: string;
  full_name?: string;
  is_superuser?: boolean;
}): Promise<AdminUserCreateResponse> {
  return fetchJson<AdminUserCreateResponse>("/api/v1/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function adminResetUserPassword(
  userId: string,
): Promise<{ user_id: string; temp_password: string }> {
  return fetchJson<{ user_id: string; temp_password: string }>(
    `/api/v1/admin/users/${userId}/reset-password`,
    { method: "POST" },
  );
}

export async function adminRevokeUser(userId: string): Promise<void> {
  return fetchJson<void>(`/api/v1/admin/users/${userId}`, { method: "DELETE" });
}

/* ============================================================
   Agents (Phase 2)
   ============================================================ */

export interface GenerateRequest {
  organization_id: string;
  project_id?: string;
  brief: string;
  n_variants?: number;
  channel?: string;
}

export interface GenerateResultItem {
  variant: string;
  approval_request_id: string;
}

export interface GenerateResponse {
  organization_id: string;
  project_id: string | null;
  channel: string;
  n_variants: number;
  results: GenerateResultItem[];
}

export async function generateCreatives(req: GenerateRequest): Promise<GenerateResponse> {
  return fetchJson<GenerateResponse>("/api/v1/agents/creatives/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

/* ============================================================
   Approvals (A4)
   ============================================================ */

export type ApprovalStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "auto_approved"
  | "canceled";

export interface ApprovalRequestItem {
  id: string;
  organization_id: string | null;
  project_id: string | null;
  requested_by_user_id: string | null;
  requested_by_agent: string | null;
  action_type: string;
  target_type: string | null;
  target_id: string | null;
  payload_json: Record<string, unknown> | null;
  summary: string | null;
  status: ApprovalStatus;
  decided_by_user_id: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  expires_at: string | null;
}

export async function listApprovals(opts?: {
  organizationId?: string;
  status?: ApprovalStatus;
}): Promise<ApprovalRequestItem[]> {
  const params = new URLSearchParams();
  if (opts?.organizationId) params.set("organization_id", opts.organizationId);
  if (opts?.status) params.set("approval_status", opts.status);
  const qs = params.toString();
  return fetchJson<ApprovalRequestItem[]>(`/api/v1/approvals${qs ? `?${qs}` : ""}`);
}

export async function approveRequest(
  approvalId: string,
  reason?: string,
): Promise<ApprovalRequestItem> {
  return fetchJson<ApprovalRequestItem>(`/api/v1/approvals/${approvalId}/approve`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function rejectRequest(
  approvalId: string,
  reason?: string,
): Promise<ApprovalRequestItem> {
  return fetchJson<ApprovalRequestItem>(`/api/v1/approvals/${approvalId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function cancelRequest(approvalId: string): Promise<ApprovalRequestItem> {
  return fetchJson<ApprovalRequestItem>(`/api/v1/approvals/${approvalId}/cancel`, {
    method: "POST",
  });
}
