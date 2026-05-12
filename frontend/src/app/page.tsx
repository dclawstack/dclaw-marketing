"use client";

import { useEffect, useState } from "react";
import { ArrowUpRight, Users, Target, BarChart3, DollarSign } from "lucide-react";

import {
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { getDashboard, DashboardStats } from "@/lib/api";

interface StatTile {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const tiles: StatTile[] = stats
    ? [
        { label: "Active Campaigns", value: stats.active_campaigns, icon: Target },
        { label: "Total Leads", value: stats.total_leads, icon: Users },
        {
          label: "Conversion Rate",
          value: `${stats.conversion_rate}%`,
          icon: BarChart3,
        },
        {
          label: "Total Spend",
          value: `$${stats.total_spend.toFixed(2)}`,
          icon: DollarSign,
        },
      ]
    : [];

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace"
        title="Dashboard"
        description="Snapshot of campaign activity, leads, and spend. Drill into any tile for the full view."
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-4 py-3 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <DkCard key={i}>
                <DkCardHeader className="pb-2">
                  <DkSkeleton className="h-4 w-24" />
                </DkCardHeader>
                <DkCardContent>
                  <DkSkeleton className="h-9 w-20" />
                </DkCardContent>
              </DkCard>
            ))
          : tiles.map((t) => {
              const Icon = t.icon;
              return (
                <DkCard key={t.label} hover>
                  <DkCardHeader className="pb-2 flex-row items-center justify-between">
                    <DkCardTitle className="text-sm font-medium text-[var(--dk-fg-2)]">
                      {t.label}
                    </DkCardTitle>
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand">
                      <Icon className="h-4 w-4" />
                    </div>
                  </DkCardHeader>
                  <DkCardContent className="pt-0">
                    <div className="font-display text-3xl font-bold tabular-nums text-ink">
                      {t.value}
                    </div>
                  </DkCardContent>
                </DkCard>
              );
            })}
      </div>
    </div>
  );
}
