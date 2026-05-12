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

// ============================================================
// Brand Kits (Theme Q1 / B1)
// ============================================================

export interface BrandPalette {
  primary?: string;
  secondary?: string;
  ink?: string;
  surface?: string;
  surface_muted?: string;
}

export interface BrandFonts {
  display?: string;
  body?: string;
}

export interface BrandVoice {
  formal_casual?: number; // 0–100
  technical_witty?: number; // 0–100
  calm_energetic?: number; // 0–100
  do_say?: string[];
  dont_say?: string[];
}

export interface BrandPositioning {
  what_we_do?: string;
  who_we_serve?: string;
  why_we_matter?: string;
}

export interface PersonaIn {
  name: string;
  description?: string;
  demographics?: Record<string, unknown>;
  jobs_to_be_done?: string[];
  fears?: string[];
  desires?: string[];
  traits?: string[];
}

export interface PersonaRead extends PersonaIn {
  id: string;
}

export interface BrandKit {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  version: number;
  is_active: boolean;
  logo_asset_id: string | null;
  logo_dark_asset_id: string | null;
  palette_json: BrandPalette | null;
  fonts_json: BrandFonts | null;
  voice_json: BrandVoice | null;
  positioning_json: BrandPositioning | null;
  personas: PersonaRead[];
}

export async function listBrandKits(orgId: string): Promise<BrandKit[]> {
  return fetchJson<BrandKit[]>(`/api/v1/orgs/${orgId}/brand-kits`);
}

export async function getActiveBrandKit(orgId: string): Promise<BrandKit> {
  return fetchJson<BrandKit>(`/api/v1/orgs/${orgId}/brand-kits/active`);
}

export async function getBrandKit(
  orgId: string,
  kitId: string,
): Promise<BrandKit> {
  return fetchJson<BrandKit>(`/api/v1/orgs/${orgId}/brand-kits/${kitId}`);
}

export async function createBrandKit(
  orgId: string,
  data: {
    name: string;
    description?: string;
    palette?: BrandPalette;
    fonts?: BrandFonts;
    voice?: BrandVoice;
    positioning?: BrandPositioning;
    personas?: PersonaIn[];
  },
): Promise<BrandKit> {
  return fetchJson<BrandKit>(`/api/v1/orgs/${orgId}/brand-kits`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateBrandKit(
  orgId: string,
  kitId: string,
  data: {
    name?: string;
    description?: string;
    palette?: BrandPalette;
    fonts?: BrandFonts;
    voice?: BrandVoice;
    positioning?: BrandPositioning;
  },
): Promise<BrandKit> {
  return fetchJson<BrandKit>(`/api/v1/orgs/${orgId}/brand-kits/${kitId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function activateBrandKit(
  orgId: string,
  kitId: string,
): Promise<BrandKit> {
  return fetchJson<BrandKit>(
    `/api/v1/orgs/${orgId}/brand-kits/${kitId}/activate`,
    { method: "POST" },
  );
}

// ============================================================
// Assets (Theme A3) — presigned PUT upload flow
// ============================================================

export type AssetKind =
  | "image"
  | "video"
  | "audio"
  | "document"
  | "data"
  | "archive"
  | "other";

export interface Asset {
  id: string;
  organization_id: string | null;
  created_by_user_id: string | null;
  kind: AssetKind;
  mime_type: string;
  original_filename: string | null;
  size_bytes: number | null;
  bucket: string;
  storage_key: string;
}

export interface AssetUploadResponse {
  asset: Asset;
  presigned_put_url: string;
  expires_in: number;
}

export async function startAssetUpload(data: {
  filename: string;
  mime_type: string;
  kind: AssetKind;
  organization_id?: string;
}): Promise<AssetUploadResponse> {
  return fetchJson<AssetUploadResponse>(`/api/v1/assets/upload`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function confirmAssetUpload(assetId: string): Promise<Asset> {
  return fetchJson<Asset>(`/api/v1/assets/${assetId}/confirm`, {
    method: "POST",
  });
}

export async function listAssets(
  orgId: string,
  kind?: AssetKind,
): Promise<Asset[]> {
  const q = new URLSearchParams({ organization_id: orgId });
  if (kind) q.set("kind", kind);
  return fetchJson<Asset[]>(`/api/v1/assets?${q.toString()}`);
}

export async function getAssetDownloadUrl(
  assetId: string,
): Promise<{ presigned_get_url: string; expires_in: number }> {
  return fetchJson(`/api/v1/assets/${assetId}/download`);
}

export async function deleteAsset(assetId: string): Promise<void> {
  await fetchJson<void>(`/api/v1/assets/${assetId}`, { method: "DELETE" });
}

export function inferAssetKind(mimeType: string, filename: string): AssetKind {
  const m = mimeType.toLowerCase();
  if (m.startsWith("image/")) return "image";
  if (m.startsWith("video/")) return "video";
  if (m.startsWith("audio/")) return "audio";
  if (
    m === "application/pdf" ||
    m === "application/msword" ||
    m === "text/plain" ||
    m === "text/markdown" ||
    m.includes("officedocument") ||
    /\.(md|txt|pdf|docx?|pptx?)$/i.test(filename)
  )
    return "document";
  if (m === "application/zip" || /\.(zip|tar|gz)$/i.test(filename))
    return "archive";
  if (m === "text/csv" || m === "application/json" || m === "image/svg+xml")
    return "data";
  return "other";
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


// ============================================================
// Social accounts (Theme C2 / Phase 5)
// ============================================================

export type SocialPlatform =
  | "linkedin"
  | "x"
  | "instagram"
  | "threads"
  | "bluesky"
  | "facebook"
  | "youtube"
  | "tiktok"
  | "newsletter"
  | "blog"
  | "reddit"
  | "pinterest"
  | "mastodon"
  | "snapchat"
  | "telegram"
  | "whatsapp"
  | "discord"
  | "quora"
  | "medium"
  | "substack"
  | "beehiiv"
  | "ghost"
  | "wordpress"
  | "webflow"
  | "spotify_podcasters";

export type SocialAccountStatus = "active" | "reauth_required" | "revoked";

export interface SocialAccount {
  id: string;
  organization_id: string;
  platform: SocialPlatform;
  handle: string;
  display_name: string | null;
  avatar_url: string | null;
  is_default_for_platform: boolean;
  status: SocialAccountStatus;
  scopes: string[] | null;
  last_health_at: string | null;
  last_publish_at: string | null;
  last_error_message: string | null;
  has_token: boolean;
  created_at: string;
  updated_at: string;
}

export async function listSocialAccounts(
  orgId: string,
): Promise<SocialAccount[]> {
  return fetchJson<SocialAccount[]>(`/api/v1/orgs/${orgId}/social-accounts`);
}

export async function createSocialAccount(
  orgId: string,
  data: {
    platform: SocialPlatform;
    handle: string;
    display_name?: string;
    avatar_url?: string;
    interim_access_token?: string;
    auth_metadata_json?: Record<string, unknown>;
    scopes?: string[];
    is_default_for_platform?: boolean;
  },
): Promise<SocialAccount> {
  return fetchJson<SocialAccount>(
    `/api/v1/orgs/${orgId}/social-accounts`,
    { method: "POST", body: JSON.stringify(data) },
  );
}

export async function setSocialAccountDefault(
  orgId: string,
  accountId: string,
): Promise<SocialAccount> {
  return fetchJson<SocialAccount>(
    `/api/v1/orgs/${orgId}/social-accounts/${accountId}/set-default`,
    { method: "POST" },
  );
}

export async function healthCheckSocialAccount(
  orgId: string,
  accountId: string,
): Promise<SocialAccount> {
  return fetchJson<SocialAccount>(
    `/api/v1/orgs/${orgId}/social-accounts/${accountId}/health-check`,
    { method: "POST" },
  );
}

export async function revokeSocialAccount(
  orgId: string,
  accountId: string,
): Promise<SocialAccount> {
  return fetchJson<SocialAccount>(
    `/api/v1/orgs/${orgId}/social-accounts/${accountId}`,
    { method: "DELETE" },
  );
}

// ============================================================

// ============================================================
// Scheduled posts (Theme C1, Phase 4)
// ============================================================

export type ScheduledPostChannel =
  | "linkedin"
  | "x"
  | "instagram"
  | "threads"
  | "bluesky"
  | "facebook"
  | "youtube"
  | "tiktok"
  | "newsletter"
  | "blog";

export type ScheduledPostStatus =
  | "queued"
  | "publishing"
  | "published"
  | "failed"
  | "cancelled"
  | "would_publish";

export interface ScheduledPost {
  id: string;
  organization_id: string;
  project_id: string | null;
  parent_campaign_id: string | null;
  channel: ScheduledPostChannel;
  asset_ids: string[] | null;
  copy: string | null;
  tags: string[] | null;
  scheduled_at: string;
  published_at: string | null;
  error_message: string | null;
  publisher_response: Record<string, unknown> | null;
  status: ScheduledPostStatus;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export async function listScheduledPosts(
  orgId: string,
  opts: {
    from?: string;
    to?: string;
    channel?: ScheduledPostChannel;
    status?: ScheduledPostStatus;
    project_id?: string;
  } = {},
): Promise<ScheduledPost[]> {
  const q = new URLSearchParams();
  if (opts.from) q.set("from", opts.from);
  if (opts.to) q.set("to", opts.to);
  if (opts.channel) q.set("channel", opts.channel);
  if (opts.status) q.set("status", opts.status);
  if (opts.project_id) q.set("project_id", opts.project_id);
  const qs = q.toString();
  return fetchJson<ScheduledPost[]>(`/api/v1/orgs/${orgId}/scheduled-posts${qs ? `?${qs}` : ""}`);
}

export async function createScheduledPost(
  orgId: string,
  data: {
    channel: ScheduledPostChannel;
    scheduled_at: string;
    copy?: string;
    asset_ids?: string[];
    tags?: string[];
    project_id?: string;
    parent_campaign_id?: string;
  },
): Promise<ScheduledPost> {
  return fetchJson<ScheduledPost>(`/api/v1/orgs/${orgId}/scheduled-posts`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateScheduledPost(
  orgId: string,
  postId: string,
  data: { channel?: ScheduledPostChannel; scheduled_at?: string; copy?: string; asset_ids?: string[]; tags?: string[] },
): Promise<ScheduledPost> {
  return fetchJson<ScheduledPost>(`/api/v1/orgs/${orgId}/scheduled-posts/${postId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function cancelScheduledPost(orgId: string, postId: string): Promise<ScheduledPost> {
  return fetchJson<ScheduledPost>(`/api/v1/orgs/${orgId}/scheduled-posts/${postId}`, { method: "DELETE" });
}

export async function publishScheduledPostNow(orgId: string, postId: string): Promise<ScheduledPost> {
  return fetchJson<ScheduledPost>(`/api/v1/orgs/${orgId}/scheduled-posts/${postId}/publish-now`, { method: "POST" });
}

// ============================================================
// Agent threads (Conductor + role-agents — Phase 9)
// ============================================================

export type AgentKind =
  | "conductor"
  | "creatives"
  | "smm"
  | "seo"
  | "paid_media"
  | "analyst"
  | "inbox";

export type AgentMessageRole = "user" | "agent" | "system" | "tool";

export interface AgentThread {
  id: string;
  organization_id: string;
  project_id: string | null;
  parent_thread_id: string | null;
  kind: AgentKind;
  title: string | null;
  started_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentMessage {
  id: string;
  thread_id: string;
  role: AgentMessageRole;
  agent_kind: AgentKind | null;
  content: string;
  tool_name: string | null;
  tool_arguments: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  metadata_json: Record<string, unknown> | null;
  approval_request_id: string | null;
  created_at: string;
}

export async function listAgentThreads(orgId: string): Promise<AgentThread[]> {
  return fetchJson<AgentThread[]>(`/api/v1/orgs/${orgId}/agent-threads`);
}

export async function createAgentThread(
  orgId: string,
  data: { kind?: AgentKind; title?: string; project_id?: string },
): Promise<AgentThread> {
  return fetchJson<AgentThread>(`/api/v1/orgs/${orgId}/agent-threads`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listAgentMessages(orgId: string, threadId: string): Promise<AgentMessage[]> {
  return fetchJson<AgentMessage[]>(`/api/v1/orgs/${orgId}/agent-threads/${threadId}/messages`);
}

export async function postAgentMessage(orgId: string, threadId: string, content: string): Promise<AgentMessage[]> {
  return fetchJson<AgentMessage[]>(`/api/v1/orgs/${orgId}/agent-threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}
