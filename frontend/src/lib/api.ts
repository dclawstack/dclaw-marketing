const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error ${response.status}: ${error}`);
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
