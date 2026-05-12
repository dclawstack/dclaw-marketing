"use client";

import { useCallback, useEffect, useState } from "react";
import { Gauge, RefreshCw, Zap } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type Quota = {
  id: string;
  organization_id: string;
  channel: string;
  window_start: string;
  window_seconds: number;
  limit: number;
  count: number;
  last_used_at: string | null;
  pct_used: number;
  is_breaker: boolean;
};

async function authFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function fmtWindow(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

function pctTone(pct: number, breaker: boolean): "success" | "warning" | "danger" {
  if (breaker) return "danger";
  if (pct >= 90) return "danger";
  if (pct >= 70) return "warning";
  return "success";
}

export default function AdminQuotasPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<Quota[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!currentOrg) return;
    setLoading(true);
    setError(null);
    try {
      const data = await authFetch<Quota[]>(
        `/api/v1/quotas?organization_id=${currentOrg.id}`,
      );
      setRows(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load quotas.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // Live: poll every 8s while the page is open.
  useEffect(() => {
    if (!currentOrg) return;
    const id = window.setInterval(() => {
      void refresh();
    }, 8000);
    return () => window.clearInterval(id);
  }, [currentOrg, refresh]);

  const regular = rows.filter((r) => !r.is_breaker);
  const breakers = rows.filter((r) => r.is_breaker);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · Theme I1"
        title="Rate limits & quotas"
        description="Live sliding-window counters per channel + provider. Counters reset when the window closes. Circuit-breakers trip on sustained provider 5xx and auto-reset after cooldown."
        actions={
          <DkButton onClick={refresh} disabled={loading}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </DkButton>
        }
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      {!currentOrg ? (
        <DkEmptyState
          icon={<Gauge className="h-6 w-6" />}
          title="Pick an organization"
          description="Quotas are per-Org — use the workspace switcher."
        />
      ) : loading && rows.length === 0 ? (
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <DkSkeleton key={i} className="h-24" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<Gauge className="h-6 w-6" />}
          title="No quota counters yet"
          description="Counters appear here as soon as outbound publishing fires (calendar dispatcher + Celery tasks write through the QuotaGuard)."
        />
      ) : (
        <>
          {regular.length > 0 ? (
            <div className="flex flex-col gap-3">
              <h2 className="font-display text-lg font-semibold">
                Live counters ({regular.length})
              </h2>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {regular.map((r) => (
                  <DkCard key={r.id}>
                    <DkCardContent className="flex flex-col gap-2 py-3">
                      <div className="flex items-center gap-2">
                        <Gauge className="h-4 w-4 text-brand" />
                        <span className="font-medium">{r.channel}</span>
                        <DkBadge tone="neutral" className="ml-auto">
                          {fmtWindow(r.window_seconds)} window
                        </DkBadge>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm">
                          {r.count} / {r.limit}
                        </span>
                        <DkBadge tone={pctTone(r.pct_used, false)}>
                          {r.pct_used.toFixed(0)}%
                        </DkBadge>
                      </div>
                      <div className="h-2 rounded bg-[var(--dk-gray-100)] overflow-hidden">
                        <div
                          className="h-full bg-[var(--dk-purple-400)]"
                          style={{ width: `${Math.min(100, r.pct_used)}%` }}
                        />
                      </div>
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            </div>
          ) : null}

          {breakers.length > 0 ? (
            <div className="flex flex-col gap-3">
              <h2 className="font-display text-lg font-semibold">
                Circuit-breaker state ({breakers.length})
              </h2>
              <div className="grid gap-3 md:grid-cols-2">
                {breakers.map((r) => (
                  <DkCard key={r.id}>
                    <DkCardContent className="flex items-center gap-2 py-3">
                      <Zap className="h-4 w-4 text-[var(--dk-danger)]" />
                      <span className="font-medium">{r.channel}</span>
                      <span className="ml-auto font-mono text-sm">
                        {r.count} / {r.limit}
                      </span>
                      <DkBadge tone={pctTone(r.pct_used, true)}>
                        {r.pct_used.toFixed(0)}%
                      </DkBadge>
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
