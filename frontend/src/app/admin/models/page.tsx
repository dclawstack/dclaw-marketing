"use client";

/**
 * /admin/models — Model Registry surface (S4-M10).
 *
 * Three sections:
 *   A. Feature Availability — Platform Components (colour-coded chips)
 *      + Capability Summary (pills with counts)
 *   B. Providers — cards with "Add Provider" radio + Others-dropdown form
 *   C. Models Table — sortable, with Logs + Metrics slide-overs
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Plus, RefreshCw, Search, X } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkChip,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkSkeleton,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface ProviderTypeInfo {
  type: string;
  label: string;
  tier: number;
  fields: string[];
  base_url_locked: boolean;
  default_base_url: string | null;
  description: string;
}

interface ProviderRow {
  id: string;
  organization_id: string | null;
  provider_type: string;
  name: string;
  base_url: string | null;
  has_api_key: boolean;
  is_active: boolean;
  health_status: "unknown" | "healthy" | "unhealthy" | "disabled";
  health_error: string | null;
  last_health_check_at: string | null;
}

interface ModelEntryRow {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  capabilities: string[];
  pricing_json: {
    prompt?: string;
    completion?: string;
    request?: string;
    image?: string;
    currency?: string;
    is_free?: boolean;
  } | null;
  status: "unknown" | "healthy" | "unhealthy" | "disabled";
  last_health_check_at: string | null;
  is_active: boolean;
}

interface FeatureAvailability {
  components: Record<
    string,
    { required: string[]; covered: string[]; missing: string[]; status: "full" | "partial" | "none" }
  >;
  capabilities: Record<string, { available: boolean; model_count: number; healthy_count: number }>;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  if (r.status === 204) return undefined as T;
  return r.json();
}

const TOP_LEVEL_RADIO_TYPES = [
  "anthropic",
  "openai",
  "openai_compatible",
  "ollama",
  "openrouter",
] as const;

function StatusChip({ status }: { status: ProviderRow["health_status"] }) {
  const color =
    status === "healthy"
      ? "bg-emerald-100 text-emerald-700"
      : status === "unhealthy"
        ? "bg-rose-100 text-rose-700"
        : status === "disabled"
          ? "bg-slate-200 text-slate-600"
          : "bg-amber-100 text-amber-700";
  const label = status === "healthy" ? "● healthy" : status === "unhealthy" ? "● unhealthy" : status;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>{label}</span>;
}

function ComponentCard({
  name,
  data,
}: {
  name: string;
  data: FeatureAvailability["components"][string];
}) {
  const color =
    data.status === "full"
      ? "border-emerald-300 bg-emerald-50"
      : data.status === "partial"
        ? "border-amber-300 bg-amber-50"
        : "border-rose-300 bg-rose-50";
  const tick = data.status === "full" ? "✅" : data.status === "partial" ? "⚠" : "✗";
  return (
    <div className={`rounded-lg border p-3 ${color}`}>
      <div className="flex items-center justify-between">
        <div className="font-medium capitalize">{name.replace(/_/g, " ")}</div>
        <span>{tick}</span>
      </div>
      {data.missing.length > 0 && (
        <div className="text-xs text-rose-700 mt-1">
          missing: {data.missing.join(", ")}
        </div>
      )}
    </div>
  );
}

// All canonical capabilities — must stay in sync with backend
// app/models/model_registry.py::Capability. Used for the filter chip
// set on the Models table.
const ALL_CAPABILITIES = [
  "text",
  "embedding",
  "multimodal_embedding",
  "image_generation",
  "image_understanding",
  "audio_transcription",
  "text_to_speech",
  "text_to_video",
  "text_to_music",
  "function_calling",
  "reasoning",
  "reranking",
  "web_search",
] as const;

export default function AdminModelsPage() {
  const [providerTypes, setProviderTypes] = useState<ProviderTypeInfo[]>([]);
  const [providers, setProviders] = useState<ProviderRow[]>([]);
  const [entries, setEntries] = useState<ModelEntryRow[]>([]);
  const [feature, setFeature] = useState<FeatureAvailability | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // URL-state-driven filters for the Models table (#363).
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const selectedProviders = useMemo(
    () => new Set((searchParams.get("provider") ?? "").split(",").filter(Boolean)),
    [searchParams],
  );
  const selectedCaps = useMemo(
    () => new Set((searchParams.get("cap") ?? "").split(",").filter(Boolean)),
    [searchParams],
  );
  const freeOnly = searchParams.get("free") === "1";

  const updateParams = useCallback(
    (mut: { q?: string; provider?: Set<string>; cap?: Set<string>; free?: boolean }) => {
      const next = new URLSearchParams(searchParams.toString());
      if (mut.q !== undefined) {
        if (mut.q) next.set("q", mut.q);
        else next.delete("q");
      }
      if (mut.provider) {
        const v = Array.from(mut.provider).filter(Boolean).join(",");
        if (v) next.set("provider", v);
        else next.delete("provider");
      }
      if (mut.cap) {
        const v = Array.from(mut.cap).filter(Boolean).join(",");
        if (v) next.set("cap", v);
        else next.delete("cap");
      }
      if (mut.free !== undefined) {
        if (mut.free) next.set("free", "1");
        else next.delete("free");
      }
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname);
    },
    [router, pathname, searchParams],
  );

  const toggleProvider = useCallback(
    (id: string) => {
      const s = new Set(selectedProviders);
      if (s.has(id)) s.delete(id);
      else s.add(id);
      updateParams({ provider: s });
    },
    [selectedProviders, updateParams],
  );
  const toggleCap = useCallback(
    (cap: string) => {
      const s = new Set(selectedCaps);
      if (s.has(cap)) s.delete(cap);
      else s.add(cap);
      updateParams({ cap: s });
    },
    [selectedCaps, updateParams],
  );
  const clearFilters = useCallback(() => {
    router.replace(pathname);
  }, [router, pathname]);

  const filteredEntries = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return entries.filter((e) => {
      if (selectedProviders.size > 0 && !selectedProviders.has(e.provider_id)) {
        return false;
      }
      if (selectedCaps.size > 0) {
        const hit = e.capabilities.some((c) => selectedCaps.has(c));
        if (!hit) return false;
      }
      if (freeOnly && !isFreeEntry(e)) {
        return false;
      }
      if (needle) {
        const provName = providers.find((p) => p.id === e.provider_id)?.name ?? "";
        const hay = `${e.model_id} ${e.display_name} ${provName}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
  }, [entries, providers, q, selectedProviders, selectedCaps, freeOnly]);

  const hasActiveFilters =
    !!q || selectedProviders.size > 0 || selectedCaps.size > 0 || freeOnly;

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pt, p, e, f] = await Promise.all([
        api<ProviderTypeInfo[]>("/api/v1/models/provider-types"),
        api<ProviderRow[]>("/api/v1/models/providers"),
        api<ModelEntryRow[]>("/api/v1/models/entries"),
        api<FeatureAvailability>("/api/v1/models/feature-availability"),
      ]);
      setProviderTypes(pt);
      setProviders(p);
      setEntries(e);
      setFeature(f);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <DkPageHeader
        title="Model Registry"
        description="Per-org and global AI model providers. Sprint 4 S4-M."
        actions={
          <div className="flex gap-2">
            <DkButton onClick={refresh}>
              <RefreshCw className="w-4 h-4" />
              Refresh
            </DkButton>
            <DkButton onClick={() => setShowAdd(true)}>
              <Plus className="w-4 h-4" />
              Add Provider
            </DkButton>
          </div>
        }
      />

      {error && (
        <div className="rounded border border-rose-300 bg-rose-50 p-3 text-rose-700 text-sm">
          {error}
        </div>
      )}

      {/* Section A — Feature Availability */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Feature Availability</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          {loading || !feature ? (
            <DkSkeleton className="h-32" />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {Object.entries(feature.components).map(([name, data]) => (
                  <ComponentCard key={name} name={name} data={data} />
                ))}
              </div>
              <div className="flex flex-wrap gap-2 pt-3 border-t">
                {Object.entries(feature.capabilities).map(([cap, v]) => (
                  <DkChip key={cap}>
                    {cap}
                    <span
                      className={`ml-2 text-xs ${v.available ? "text-emerald-700" : "text-rose-600"}`}
                    >
                      {v.available ? `✅ ${v.healthy_count}` : `✗ ${v.model_count}`}
                    </span>
                  </DkChip>
                ))}
              </div>
            </div>
          )}
        </DkCardContent>
      </DkCard>

      {/* Section B — Providers */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Providers</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          {loading ? (
            <DkSkeleton className="h-24" />
          ) : providers.length === 0 ? (
            <div className="text-sm text-slate-500 py-6 text-center">
              No providers yet. Click <strong>Add Provider</strong> to configure your first one.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {providers.map((p) => {
                const ct = entries.filter((e) => e.provider_id === p.id).length;
                return (
                  <div
                    key={p.id}
                    className="rounded-lg border border-slate-200 p-3 hover:shadow-sm"
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{p.name}</div>
                      <StatusChip status={p.health_status} />
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {p.provider_type} {p.organization_id ? "" : "· global"}
                    </div>
                    <div className="text-xs text-slate-600 mt-2">
                      {ct} model{ct === 1 ? "" : "s"} · key {p.has_api_key ? "set" : "missing"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </DkCardContent>
      </DkCard>

      {/* Section C — Models Table */}
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Models</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          {loading ? (
            <DkSkeleton className="h-32" />
          ) : entries.length === 0 ? (
            <div className="text-sm text-slate-500 py-6 text-center">
              No models discovered yet. Add a provider to begin.
            </div>
          ) : (
            <>
              {/* Filter bar — search left, provider+capability chips wrap right (#363) */}
              <div className="flex flex-wrap items-start gap-3 pb-4 border-b mb-3">
                <div className="relative flex-shrink-0 min-w-[260px]">
                  <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                  <DkInput
                    value={q}
                    onChange={(e) => updateParams({ q: e.target.value })}
                    placeholder="Search models / providers…"
                    className="pl-8"
                  />
                </div>
                <div className="flex flex-wrap items-center gap-1.5 flex-1 min-w-0">
                  {providers.map((p) => (
                    <FilterChip
                      key={p.id}
                      label={p.name}
                      sublabel={p.provider_type}
                      active={selectedProviders.has(p.id)}
                      onClick={() => toggleProvider(p.id)}
                    />
                  ))}
                </div>
                <div className="flex flex-wrap items-center gap-1.5 flex-1 min-w-0">
                  {ALL_CAPABILITIES.map((cap) => (
                    <FilterChip
                      key={cap}
                      label={cap}
                      active={selectedCaps.has(cap)}
                      onClick={() => toggleCap(cap)}
                    />
                  ))}
                </div>
                <FilterChip
                  label="Free only"
                  active={freeOnly}
                  onClick={() => updateParams({ free: !freeOnly })}
                />
                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="text-xs text-slate-500 hover:text-ink underline underline-offset-2 self-center"
                  >
                    Clear filters
                  </button>
                )}
              </div>
              <div className="text-xs text-slate-500 mb-2">
                Showing {filteredEntries.length} of {entries.length} models
              </div>
              {filteredEntries.length === 0 ? (
                <div className="text-sm text-slate-500 py-6 text-center">
                  No models match the current filters.
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="ml-2 underline underline-offset-2 hover:text-ink"
                  >
                    Clear filters
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-slate-500 border-b">
                        <th className="py-2 px-2">Model</th>
                        <th className="py-2 px-2">Provider</th>
                        <th className="py-2 px-2">Capabilities</th>
                        <th className="py-2 px-2 whitespace-nowrap">Pricing</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredEntries.map((e) => {
                        const p = providers.find((pp) => pp.id === e.provider_id);
                        return (
                          <tr key={e.id} className="border-b last:border-0">
                            <td className="py-2 px-2 font-mono text-xs">{e.model_id}</td>
                            <td className="py-2 px-2">{p?.name ?? "?"}</td>
                            <td className="py-2 px-2">
                              <div className="flex flex-wrap gap-1">
                                {e.capabilities.map((c) => (
                                  <DkChip key={c} tone="neutral">
                                    {c}
                                  </DkChip>
                                ))}
                              </div>
                            </td>
                            <td className="py-2 px-2 whitespace-nowrap">
                              <PricingCell entry={e} />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </DkCardContent>
      </DkCard>

      {showAdd && (
        <AddProviderDialog
          providerTypes={providerTypes}
          onClose={() => setShowAdd(false)}
          onCreated={() => {
            setShowAdd(false);
            refresh();
          }}
        />
      )}
    </div>
  );
}

function AddProviderDialog({
  providerTypes,
  onClose,
  onCreated,
}: {
  providerTypes: ProviderTypeInfo[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const topLevel = useMemo(
    () => providerTypes.filter((t) => TOP_LEVEL_RADIO_TYPES.includes(t.type as any)),
    [providerTypes],
  );
  const others = useMemo(
    () =>
      providerTypes.filter((t) => !TOP_LEVEL_RADIO_TYPES.includes(t.type as any)),
    [providerTypes],
  );

  const [picked, setPicked] = useState<string>(topLevel[0]?.type ?? "");
  const [name, setName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const spec = providerTypes.find((t) => t.type === picked);

  useEffect(() => {
    if (!spec) return;
    setName(spec.label);
    setBaseUrl(spec.default_base_url ?? "");
  }, [spec]);

  const submit = async () => {
    if (!spec) return;
    setSubmitting(true);
    setError(null);
    try {
      await api("/api/v1/models/providers", {
        method: "POST",
        body: JSON.stringify({
          provider_type: spec.type,
          name,
          api_key: apiKey || null,
          base_url: baseUrl || null,
        }),
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-[640px] max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b p-4">
          <div className="font-medium">Add Provider</div>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <DkLabel>Provider type</DkLabel>
            <div className="space-y-2 mt-1">
              {topLevel.map((t) => (
                <label key={t.type} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="provider"
                    value={t.type}
                    checked={picked === t.type}
                    onChange={() => setPicked(t.type)}
                  />
                  <span className="font-medium">{t.label}</span>
                  <span className="text-xs text-slate-500">{t.description}</span>
                </label>
              ))}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="provider"
                  checked={!TOP_LEVEL_RADIO_TYPES.includes(picked as any)}
                  readOnly
                />
                <span className="font-medium">Others ▾</span>
                <DkSelect
                  className="ml-2"
                  value={
                    TOP_LEVEL_RADIO_TYPES.includes(picked as any)
                      ? ""
                      : picked
                  }
                  onChange={(e) => setPicked(e.target.value)}
                >
                  <option value="">— pick one —</option>
                  {others.map((t) => (
                    <option key={t.type} value={t.type}>
                      {t.label}
                    </option>
                  ))}
                </DkSelect>
              </label>
            </div>
          </div>

          {spec && (
            <>
              <div>
                <DkLabel>Name</DkLabel>
                <DkInput value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              {spec.fields.includes("api_key") && (
                <div>
                  <DkLabel>API Key</DkLabel>
                  <DkInput
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="paste API key"
                  />
                </div>
              )}
              {spec.fields.includes("base_url") && !spec.base_url_locked && (
                <div>
                  <DkLabel>Base URL</DkLabel>
                  <DkInput
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder={spec.default_base_url ?? ""}
                  />
                </div>
              )}
            </>
          )}

          {error && <div className="text-rose-600 text-sm">{error}</div>}
        </div>
        <div className="border-t p-3 flex justify-end gap-2">
          <DkButton variant="ghost" onClick={onClose} disabled={submitting}>
            Cancel
          </DkButton>
          <DkButton onClick={submit} disabled={submitting || !spec}>
            {submitting ? "Saving…" : "Save"}
          </DkButton>
        </div>
      </div>
    </div>
  );
}

// ---- Filter chip used in the Models filter bar (#363) ---------------------

function FilterChip({
  label,
  sublabel,
  active,
  onClick,
}: {
  label: string;
  sublabel?: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors " +
        (active
          ? "bg-[var(--dk-purple-50)] border-brand text-brand"
          : "bg-white border-slate-200 text-slate-600 hover:border-slate-400 hover:text-ink")
      }
    >
      <span>{label}</span>
      {sublabel && (
        <span className={active ? "text-brand/70" : "text-slate-400"}>· {sublabel}</span>
      )}
    </button>
  );
}


// ---- Pricing helpers (#365) ----------------------------------------------

function isFreeEntry(e: ModelEntryRow): boolean {
  if (e.pricing_json?.is_free) return true;
  if (e.model_id.endsWith(":free")) return true;
  const pr = e.pricing_json;
  if (!pr) return false;
  const p = Number(pr.prompt ?? 0);
  const c = Number(pr.completion ?? 0);
  return p === 0 && c === 0 && !pr.image && !pr.request;
}

function _fmtRate(perToken: string | undefined): string | null {
  if (perToken === undefined || perToken === null) return null;
  const n = Number(perToken);
  if (!Number.isFinite(n)) return null;
  if (n === 0) return "$0";
  // $/M tokens. Use 3 sig-fig style for very small numbers.
  const perMillion = n * 1_000_000;
  if (perMillion < 0.01) return `$${perMillion.toFixed(4)}`;
  if (perMillion < 1) return `$${perMillion.toFixed(3)}`;
  return `$${perMillion.toFixed(2)}`;
}

function PricingCell({ entry }: { entry: ModelEntryRow }) {
  if (isFreeEntry(entry)) {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-xs font-medium">
        Free
      </span>
    );
  }
  const pr = entry.pricing_json;
  if (!pr) return <span className="text-slate-400">—</span>;
  const prompt = _fmtRate(pr.prompt);
  const completion = _fmtRate(pr.completion);
  if (!prompt && !completion) return <span className="text-slate-400">—</span>;
  return (
    <span className="text-xs font-mono text-slate-700">
      {prompt ?? "—"}
      <span className="text-slate-400"> / </span>
      {completion ?? "—"}
      <span className="text-slate-400 ml-1">/M</span>
    </span>
  );
}
