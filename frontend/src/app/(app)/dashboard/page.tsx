"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Check,
  DollarSign,
  Palette,
  Sparkles,
  Target,
  Users,
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
  DkSkeleton,
} from "@/components/dk";
import {
  DashboardStats,
  getDashboard,
  getActiveBrandKit,
  kgStats,
  listBrandKits,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";

interface StatTile {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
}

interface QuickStartStep {
  label: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  done: boolean;
}

export default function DashboardPage() {
  const { currentOrg, orgs, loading: orgsLoading } = useOrg();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [hasBrandKit, setHasBrandKit] = useState(false);
  const [kgSourceCount, setKgSourceCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const promises: Promise<unknown>[] = [
        getDashboard()
          .then(setStats)
          .catch(() => setStats(null)),
      ];
      if (currentOrg) {
        promises.push(
          listBrandKits(currentOrg.id)
            .then((kits) => setHasBrandKit(kits.length > 0))
            .catch(() => setHasBrandKit(false)),
        );
        promises.push(
          kgStats(currentOrg.id)
            .then((s) => setKgSourceCount(s.source_count))
            .catch(() => setKgSourceCount(0)),
        );
      } else {
        setHasBrandKit(false);
        setKgSourceCount(0);
      }
      await Promise.all(promises);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

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

  const orgReady = currentOrg !== null;
  const allSetUp = orgReady && hasBrandKit && kgSourceCount > 0;

  const quickStart: QuickStartStep[] = currentOrg
    ? [
        {
          label: "Set up your brand kit",
          description: "Palette, voice, do-say / don't-say, personas. Agents read from this.",
          href: `/orgs/${currentOrg.id}/brand`,
          icon: Palette,
          done: hasBrandKit,
        },
        {
          label: "Ingest your context",
          description: "Drop in files, URLs, transcripts. Becomes searchable memory.",
          href: `/orgs/${currentOrg.id}/knowledge`,
          icon: BookOpen,
          done: kgSourceCount > 0,
        },
        {
          label: "Set goals & autonomy",
          description: "Objectives, ICPs, budgets, per-action trust modes.",
          href: `/orgs/${currentOrg.id}/goals`,
          icon: Target,
          done: false,
        },
        {
          label: "Run the Creatives Agent",
          description: "Hand it a brief; review variants in the Inbox.",
          href: `/agents/creatives`,
          icon: Sparkles,
          done: false,
        },
      ]
    : [];

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow={currentOrg ? `Workspace · ${currentOrg.name}` : "Workspace"}
        title="Dashboard"
        description={
          currentOrg
            ? "Snapshot of campaign activity, leads, and spend across your workspace."
            : "Create an organization to start using DClaw Marketing."
        }
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-4 py-3 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      {/* No org yet */}
      {!orgsLoading && orgs.length === 0 && (
        <DkEmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="Welcome to DClaw Marketing"
          description="Get started by creating your first organization. It's the top container for your brand kit, knowledge base, projects, and connected accounts."
          actions={
            <Link href="/orgs/new">
              <DkButton withArrow>Create Your First Organization</DkButton>
            </Link>
          }
        />
      )}

      {/* Stat tiles */}
      {currentOrg && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {loading || !stats
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
      )}

      {/* Quick-start guide */}
      {currentOrg && !allSetUp && (
        <DkCard>
          <DkCardHeader>
            <div className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <DkCardTitle className="text-lg">
                  Finish setting up {currentOrg.name}
                </DkCardTitle>
                <DkCardDescription>
                  A few one-time steps unlock the full agent workflow.
                </DkCardDescription>
              </div>
              <DkBadge tone="brand">
                {quickStart.filter((s) => s.done).length}/{quickStart.length}{" "}
                done
              </DkBadge>
            </div>
          </DkCardHeader>
          <DkCardContent className="grid gap-3 sm:grid-cols-2">
            {quickStart.map((step, i) => {
              const Icon = step.icon;
              return (
                <Link
                  key={step.href}
                  href={step.href}
                  className="group block"
                >
                  <div
                    className={`flex items-start gap-3 rounded-md border p-4 transition-colors duration-fast ${
                      step.done
                        ? "border-[var(--dk-success)] bg-[var(--dk-success-bg)]"
                        : "border-[var(--dk-border)] hover:border-brand hover:bg-[var(--dk-bg-tint)]"
                    }`}
                  >
                    <div
                      className={`flex h-9 w-9 items-center justify-center rounded-md shrink-0 ${
                        step.done
                          ? "bg-[var(--dk-success)] text-white"
                          : "bg-[var(--dk-purple-50)] text-brand"
                      }`}
                    >
                      {step.done ? (
                        <Check className="h-4 w-4" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="flex items-center gap-1.5 text-sm font-semibold text-ink">
                        <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                          {i + 1}.
                        </span>
                        {step.label}
                      </p>
                      <p className="mt-1 text-xs text-[var(--dk-fg-2)] leading-normal">
                        {step.description}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-[var(--dk-fg-2)] group-hover:text-brand group-hover:translate-x-0.5 transition-all duration-fast" />
                  </div>
                </Link>
              );
            })}
          </DkCardContent>
        </DkCard>
      )}
    </div>
  );
}
