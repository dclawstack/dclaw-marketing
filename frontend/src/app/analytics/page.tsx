"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface Totals {
  current: { touchpoints: number; conversions: number; revenue_usd: number };
  previous: { touchpoints: number; conversions: number; revenue_usd: number };
  delta_pct: {
    touchpoints: number | null;
    conversions: number | null;
    revenue_usd: number | null;
  };
}

interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

interface SankeyData {
  nodes: { id: string; label: string }[];
  links: SankeyLink[];
}

function Delta({ value }: { value: number | null }) {
  if (value === null) return <DkBadge tone="neutral">—</DkBadge>;
  const up = value >= 0;
  return (
    <DkBadge tone={up ? "success" : "danger"}>
      {up ? "+" : ""}
      {value.toFixed(1)}%
    </DkBadge>
  );
}

export default function AnalyticsRootPage() {
  const { currentOrg } = useOrg();
  const [totals, setTotals] = useState<Totals | null>(null);
  const [sankey, setSankey] = useState<SankeyData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    Promise.all([
      fetch(
        `/api/v1/analytics/totals?organization_id=${currentOrg.id}&days=30`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      ).then((r) => (r.ok ? r.json() : null)),
      fetch(
        `/api/v1/analytics/sankey?organization_id=${currentOrg.id}&days=30&model=linear`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      ).then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([t, s]) => {
        setTotals(t);
        setSankey(s);
      })
      .finally(() => setLoading(false));
  }, [currentOrg]);

  const maxLink = sankey?.links?.length
    ? Math.max(...sankey.links.map((l) => l.value || 0))
    : 0;

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 8 — F1"
        title="Analytics"
        description="Top-of-funnel through conversion. Past 30 days vs the prior 30."
        actions={
          <Link href="/analytics/attribution">
            <DkButton variant="secondary">Attribution model detail</DkButton>
          </Link>
        }
      />

      {loading || !totals ? (
        <DkSkeleton className="h-40 w-full" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          <DkCard>
            <DkCardContent className="py-5 flex flex-col gap-2">
              <p className="text-sm text-[var(--dk-fg-2)]">Touchpoints</p>
              <p className="font-display text-2xl font-semibold">
                {totals.current.touchpoints.toLocaleString()}
              </p>
              <Delta value={totals.delta_pct.touchpoints} />
            </DkCardContent>
          </DkCard>
          <DkCard>
            <DkCardContent className="py-5 flex flex-col gap-2">
              <p className="text-sm text-[var(--dk-fg-2)]">Conversions</p>
              <p className="font-display text-2xl font-semibold">
                {totals.current.conversions.toLocaleString()}
              </p>
              <Delta value={totals.delta_pct.conversions} />
            </DkCardContent>
          </DkCard>
          <DkCard>
            <DkCardContent className="py-5 flex flex-col gap-2">
              <p className="text-sm text-[var(--dk-fg-2)]">Revenue (USD)</p>
              <p className="font-display text-2xl font-semibold">
                ${totals.current.revenue_usd.toFixed(2)}
              </p>
              <Delta value={totals.delta_pct.revenue_usd} />
            </DkCardContent>
          </DkCard>
        </div>
      )}

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Channel → conversion (linear model)</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          {!sankey || sankey.links.length === 0 ? (
            <p className="text-sm text-[var(--dk-fg-2)]">
              No attribution rows in the last 30 days yet.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {sankey.links
                .slice()
                .sort((a, b) => b.value - a.value)
                .map((l) => {
                  const pct = maxLink ? (l.value / maxLink) * 100 : 0;
                  const label = l.source.replace("channel:", "");
                  return (
                    <div key={l.source}>
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{label}</span>
                        <span className="font-mono">${l.value.toFixed(2)}</span>
                      </div>
                      <div className="h-2 rounded-full bg-[var(--dk-gray-100)]">
                        <div
                          className="h-2 rounded-full bg-brand"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
            </div>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
