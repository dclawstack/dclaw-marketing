"use client";

import { useEffect, useState } from "react";

import {
  DkBadge,
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

export default function ClientAnalyticsPage() {
  const { currentOrg } = useOrg();
  const [totals, setTotals] = useState<Totals | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(
      `/api/v1/analytics/totals?organization_id=${currentOrg.id}&days=30`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    )
      .then((r) => (r.ok ? r.json() : null))
      .then(setTotals)
      .finally(() => setLoading(false));
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Client Portal"
        title="Analytics"
        description="A white-label summary of the past 30 days, compared to the prior 30."
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
          <DkCardTitle>How we measure</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="text-sm text-[var(--dk-fg-1)]">
          Touchpoints are unique impressions across your connected channels.
          Conversions are tracked via UTM parameters and inbound form fills.
          Revenue is attributed via a linear model (each touchpoint in the
          journey gets an equal share of the conversion value).
        </DkCardContent>
      </DkCard>
    </div>
  );
}
