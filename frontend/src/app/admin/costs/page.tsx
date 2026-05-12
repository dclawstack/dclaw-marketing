"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Minus,
  RefreshCw,
  Wallet,
} from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkPageHeader,
  DkSelect,
  DkSkeleton,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type Totals = {
  organization_id: string;
  days: number;
  current: {
    total_usd: number;
    by_kind: Record<string, number>;
    by_provider: Record<string, number>;
  };
  previous: {
    total_usd: number;
    by_kind: Record<string, number>;
    by_provider: Record<string, number>;
  };
  delta_pct: { total_usd: number | null };
};

type RecentResponse = {
  organization_id: string;
  items: Array<{
    id: string;
    provider: string;
    provider_resource: string | null;
    kind: string;
    amount_usd: number;
    units: number | null;
    units_kind: string | null;
    occurred_at: string;
  }>;
};

async function authFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function usd(n: number) {
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function AdminCostsPage() {
  const { currentOrg } = useOrg();
  const [days, setDays] = useState(30);
  const [totals, setTotals] = useState<Totals | null>(null);
  const [recent, setRecent] = useState<RecentResponse["items"]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!currentOrg) return;
    setLoading(true);
    setError(null);
    try {
      const [t, r] = await Promise.all([
        authFetch<Totals>(
          `/api/v1/costs/totals?organization_id=${currentOrg.id}&days=${days}`,
        ),
        authFetch<RecentResponse>(
          `/api/v1/costs/recent?organization_id=${currentOrg.id}&limit=50`,
        ),
      ]);
      setTotals(t);
      setRecent(r.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg, days]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function trendIcon(pct: number | null) {
    if (pct == null) return <Minus className="h-4 w-4 opacity-50" />;
    if (pct > 0) return <ArrowUpRight className="h-4 w-4 text-[var(--dk-danger)]" />;
    if (pct < 0) return <ArrowDownRight className="h-4 w-4 text-[var(--dk-success)]" />;
    return <Minus className="h-4 w-4 opacity-50" />;
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · Theme I3"
        title="Cost ledger"
        description="Per-Org LLM / image / video / ads spend with current-vs-previous-window delta. Cost-cap evaluator (hourly) reads from the same ledger."
        actions={
          <div className="flex items-center gap-2">
            <DkSelect
              value={String(days)}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-32"
            >
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
            </DkSelect>
            <DkButton onClick={refresh} disabled={loading}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </DkButton>
          </div>
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
          icon={<Wallet className="h-6 w-6" />}
          title="Pick an organization"
          description="Cost ledgers are per-Org — use the workspace switcher."
        />
      ) : loading && !totals ? (
        <div className="grid gap-3 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <DkSkeleton key={i} className="h-32" />
          ))}
        </div>
      ) : totals ? (
        <>
          <div className="grid gap-3 md:grid-cols-3">
            <DkCard>
              <DkCardHeader>
                <DkCardTitle className="text-base">
                  Total ({totals.days}d)
                </DkCardTitle>
                <DkCardDescription>
                  vs previous {totals.days}d
                </DkCardDescription>
              </DkCardHeader>
              <DkCardContent className="flex items-center gap-2">
                <span className="text-2xl font-display font-semibold">
                  {usd(totals.current.total_usd)}
                </span>
                {trendIcon(totals.delta_pct.total_usd)}
                {totals.delta_pct.total_usd != null ? (
                  <span className="text-sm opacity-70">
                    {totals.delta_pct.total_usd >= 0 ? "+" : ""}
                    {totals.delta_pct.total_usd}%
                  </span>
                ) : null}
              </DkCardContent>
            </DkCard>
            <DkCard>
              <DkCardHeader>
                <DkCardTitle className="text-base">By kind</DkCardTitle>
              </DkCardHeader>
              <DkCardContent className="flex flex-col gap-1 text-sm">
                {Object.entries(totals.current.by_kind).length === 0 ? (
                  <span className="opacity-50">No spend in window.</span>
                ) : (
                  Object.entries(totals.current.by_kind).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span>{k}</span>
                      <span className="font-mono">{usd(v)}</span>
                    </div>
                  ))
                )}
              </DkCardContent>
            </DkCard>
            <DkCard>
              <DkCardHeader>
                <DkCardTitle className="text-base">By provider</DkCardTitle>
              </DkCardHeader>
              <DkCardContent className="flex flex-col gap-1 text-sm">
                {Object.entries(totals.current.by_provider).length === 0 ? (
                  <span className="opacity-50">No spend in window.</span>
                ) : (
                  Object.entries(totals.current.by_provider).map(([p, v]) => (
                    <div key={p} className="flex justify-between">
                      <span>{p}</span>
                      <span className="font-mono">{usd(v)}</span>
                    </div>
                  ))
                )}
              </DkCardContent>
            </DkCard>
          </div>

          <div className="flex flex-col gap-3">
            <h2 className="font-display text-lg font-semibold">
              Recent charges ({recent.length})
            </h2>
            {recent.length === 0 ? (
              <DkEmptyState
                icon={<Wallet className="h-6 w-6" />}
                title="No charges yet"
                description="Every LLM / image / video / ads call writes a CostLedger row. Drive an agent run to populate."
              />
            ) : (
              <DkCard>
                <DkTable>
                  <DkTableHeader>
                    <DkTableRow>
                      <DkTableHead>When</DkTableHead>
                      <DkTableHead>Provider</DkTableHead>
                      <DkTableHead>Kind</DkTableHead>
                      <DkTableHead>Resource</DkTableHead>
                      <DkTableHead className="text-right">Amount</DkTableHead>
                    </DkTableRow>
                  </DkTableHeader>
                  <DkTableBody>
                    {recent.map((r) => (
                      <DkTableRow key={r.id}>
                        <DkTableCell className="font-mono text-xs">
                          {new Date(r.occurred_at).toLocaleString()}
                        </DkTableCell>
                        <DkTableCell>
                          <DkBadge tone="neutral">{r.provider}</DkBadge>
                        </DkTableCell>
                        <DkTableCell className="font-mono text-xs">
                          {r.kind}
                        </DkTableCell>
                        <DkTableCell className="font-mono text-xs">
                          {r.provider_resource ?? "—"}
                        </DkTableCell>
                        <DkTableCell className="text-right font-mono">
                          {usd(r.amount_usd)}
                        </DkTableCell>
                      </DkTableRow>
                    ))}
                  </DkTableBody>
                </DkTable>
              </DkCard>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
