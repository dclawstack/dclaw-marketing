"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Save, Target, X } from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkChip,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkRadio,
  DkRadioGroup,
  DkSkeleton,
} from "@/components/dk";
import {
  AutonomyPosture,
  Constraints,
  Goals,
  Organization,
  TrustMode,
  getGoals,
  getOrg,
  updateGoals,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const OBJECTIVE_PRESETS = [
  "leads",
  "revenue",
  "awareness",
  "engagement",
  "retention",
];

const CHANNEL_PRESETS = [
  "linkedin",
  "x",
  "instagram",
  "threads",
  "bluesky",
  "facebook",
  "youtube",
  "tiktok",
  "newsletter",
  "blog",
];

const ACTION_CLASSES: { value: string; label: string; description: string }[] =
  [
    {
      value: "social_post",
      label: "Social post (outbound)",
      description: "Publishing to a connected social account.",
    },
    {
      value: "draft_email",
      label: "Email draft",
      description: "Generating a draft email; doesn't send.",
    },
    {
      value: "send_email_bulk",
      label: "Bulk email send",
      description: "Sending to >1k recipients.",
    },
    {
      value: "ad_spend",
      label: "Ad spend change",
      description: "Increasing or moving paid-media budget.",
    },
    {
      value: "internal_research",
      label: "Internal research",
      description: "Crawling, summarizing, KG writes.",
    },
    {
      value: "brand_kit_edit",
      label: "Brand kit edit",
      description: "Changing palette / voice / personas.",
    },
  ];

const TRUST_MODES: { value: TrustMode; label: string; description: string }[] =
  [
    {
      value: "autopilot",
      label: "Autopilot",
      description: "Agent acts immediately; logged in audit trail.",
    },
    {
      value: "soft_gate",
      label: "Soft gate",
      description: "Auto-approves after timeout unless a reviewer objects.",
    },
    {
      value: "hard_gate",
      label: "Hard gate",
      description: "Human must explicitly approve before action fires.",
    },
  ];

export default function GoalsPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // form state
  const [objectives, setObjectives] = useState<string[]>([]);
  const [icps, setIcps] = useState<string[]>([]);
  const [icpDraft, setIcpDraft] = useState("");
  const [channels, setChannels] = useState<string[]>([]);
  const [northStar, setNorthStar] = useState("");
  const [targetValue, setTargetValue] = useState<string>("");
  const [brandSafety, setBrandSafety] = useState<string[]>([]);
  const [brandSafetyDraft, setBrandSafetyDraft] = useState("");
  const [monthlyBudget, setMonthlyBudget] = useState<string>("");
  const [maxDailyPosts, setMaxDailyPosts] = useState<string>("");
  const [autonomy, setAutonomy] = useState<AutonomyPosture>({});

  const refresh = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [o, g] = await Promise.all([getOrg(orgId), getGoals(orgId)]);
      setOrg(o);
      const goals = g.goals ?? {};
      const constraints = g.constraints ?? {};
      const posture = g.autonomy_posture ?? {};

      setObjectives(goals.objectives ?? []);
      setIcps(goals.icps ?? []);
      setChannels(goals.channels_of_interest ?? []);
      setNorthStar(goals.north_star_metric ?? "");
      setTargetValue(goals.target_quarterly_value?.toString() ?? "");
      setBrandSafety(constraints.brand_safety_lines ?? []);
      setMonthlyBudget(constraints.monthly_budget_usd?.toString() ?? "");
      setMaxDailyPosts(constraints.max_daily_posts?.toString() ?? "");
      setAutonomy(posture);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function toggle<T>(list: T[], v: T): T[] {
    return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
  }

  function addIcp() {
    const v = icpDraft.trim();
    if (v && !icps.includes(v)) setIcps([...icps, v]);
    setIcpDraft("");
  }

  function addBrandSafety() {
    const v = brandSafetyDraft.trim();
    if (v && !brandSafety.includes(v)) setBrandSafety([...brandSafety, v]);
    setBrandSafetyDraft("");
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const payloadGoals: Goals = {
        objectives,
        icps,
        channels_of_interest: channels,
        north_star_metric: northStar || undefined,
        target_quarterly_value: targetValue ? Number(targetValue) : null,
      };
      const payloadConstraints: Constraints = {
        brand_safety_lines: brandSafety,
        monthly_budget_usd: monthlyBudget ? Number(monthlyBudget) : null,
        max_daily_posts: maxDailyPosts ? Number(maxDailyPosts) : null,
      };
      await updateGoals(orgId, {
        goals: payloadGoals,
        constraints: payloadConstraints,
        autonomy_posture: autonomy,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          {
            label: org?.name ?? "…",
            href: orgId ? `/orgs/${orgId}` : "/orgs",
          },
          { label: "Goals & Autonomy" },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization · Theme Q5"
        title="Goals & Autonomy Posture"
        description="Tell the Conductor what success looks like, what's off-limits, and how much rope each agent has. These configure planning and approval defaults across every project."
        actions={
          <DkButton onClick={handleSave} loading={saving} disabled={loading}>
            <Save className="h-4 w-4" />
            Save Changes
          </DkButton>
        }
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}
      {saved && (
        <div
          role="status"
          className="rounded-md border border-[var(--dk-success)] bg-[var(--dk-success-bg)] px-3 py-2 text-sm text-[var(--dk-success)]"
        >
          Saved.
        </div>
      )}

      {loading ? (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <DkSkeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Objectives</DkCardTitle>
              <DkCardDescription>
                What is this organization trying to achieve? Pick all that apply.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="flex flex-wrap gap-2">
              {OBJECTIVE_PRESETS.map((o) => {
                const on = objectives.includes(o);
                return (
                  <button
                    key={o}
                    type="button"
                    onClick={() => setObjectives(toggle(objectives, o))}
                    className={cn(
                      "rounded-pill px-3 py-1.5 text-sm font-semibold transition-colors duration-fast",
                      on
                        ? "bg-brand text-white"
                        : "bg-[var(--dk-gray-100)] text-[var(--dk-fg-1)] hover:bg-[var(--dk-purple-100)] hover:text-brand",
                    )}
                  >
                    {o}
                  </button>
                );
              })}
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>North Star</DkCardTitle>
              <DkCardDescription>
                A single metric the team rallies around, with a quarterly target.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="ns">Metric name</DkLabel>
                <DkInput
                  id="ns"
                  placeholder="monthly_qualified_leads"
                  value={northStar}
                  onChange={(e) => setNorthStar(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="tv">Quarterly target</DkLabel>
                <DkInput
                  id="tv"
                  type="number"
                  placeholder="500"
                  value={targetValue}
                  onChange={(e) => setTargetValue(e.target.value)}
                />
              </div>
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Ideal Customer Profiles</DkCardTitle>
              <DkCardDescription>
                Who are we writing to? Used by Creatives Agent to pick voice + targeting.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="flex flex-col gap-3">
              <div className="flex gap-2">
                <DkInput
                  placeholder="b2b-saas-cmo"
                  value={icpDraft}
                  onChange={(e) => setIcpDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addIcp();
                    }
                  }}
                  className="flex-1"
                />
                <DkButton variant="secondary" onClick={addIcp}>
                  <Plus className="h-4 w-4" />
                  Add
                </DkButton>
              </div>
              <div className="flex flex-wrap gap-2">
                {icps.length === 0 && (
                  <p className="text-sm text-[var(--dk-fg-2)]">
                    No ICPs yet — add one above.
                  </p>
                )}
                {icps.map((i) => (
                  <DkChip key={i} tone="brand" className="pr-1.5">
                    {i}
                    <button
                      type="button"
                      onClick={() => setIcps(icps.filter((x) => x !== i))}
                      aria-label={`Remove ${i}`}
                      className="ml-1 hover:bg-[var(--dk-purple-200)] rounded-pill p-0.5"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </DkChip>
                ))}
              </div>
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Channels of Interest</DkCardTitle>
              <DkCardDescription>
                Where does the team operate? Used to scope agent suggestions.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="flex flex-wrap gap-2">
              {CHANNEL_PRESETS.map((c) => {
                const on = channels.includes(c);
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setChannels(toggle(channels, c))}
                    className={cn(
                      "rounded-pill px-3 py-1.5 text-sm font-semibold transition-colors duration-fast",
                      on
                        ? "bg-brand text-white"
                        : "bg-[var(--dk-gray-100)] text-[var(--dk-fg-1)] hover:bg-[var(--dk-purple-100)] hover:text-brand",
                    )}
                  >
                    {c}
                  </button>
                );
              })}
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Brand-safety Lines</DkCardTitle>
              <DkCardDescription>
                Things the agents must never do. Free-form rules; the Creatives Agent runs them as a post-generation lint pass.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="flex flex-col gap-3">
              <div className="flex gap-2">
                <DkInput
                  placeholder="No political content"
                  value={brandSafetyDraft}
                  onChange={(e) => setBrandSafetyDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addBrandSafety();
                    }
                  }}
                  className="flex-1"
                />
                <DkButton variant="secondary" onClick={addBrandSafety}>
                  <Plus className="h-4 w-4" />
                  Add
                </DkButton>
              </div>
              <div className="flex flex-col gap-2">
                {brandSafety.length === 0 && (
                  <p className="text-sm text-[var(--dk-fg-2)]">
                    No safety lines yet.
                  </p>
                )}
                {brandSafety.map((b) => (
                  <div
                    key={b}
                    className="flex items-center justify-between gap-3 rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] px-3 py-2"
                  >
                    <span className="text-sm text-[var(--dk-fg-1)]">{b}</span>
                    <button
                      type="button"
                      onClick={() =>
                        setBrandSafety(brandSafety.filter((x) => x !== b))
                      }
                      aria-label={`Remove ${b}`}
                      className="text-[var(--dk-fg-2)] hover:text-[var(--dk-danger)] transition-colors duration-fast"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Budget Caps</DkCardTitle>
              <DkCardDescription>
                Hard limits — agents must escalate before exceeding.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="mb">Monthly budget (USD)</DkLabel>
                <DkInput
                  id="mb"
                  type="number"
                  placeholder="5000"
                  value={monthlyBudget}
                  onChange={(e) => setMonthlyBudget(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="mdp">Max daily posts</DkLabel>
                <DkInput
                  id="mdp"
                  type="number"
                  placeholder="6"
                  value={maxDailyPosts}
                  onChange={(e) => setMaxDailyPosts(e.target.value)}
                />
              </div>
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Autonomy Posture</DkCardTitle>
              <DkCardDescription>
                Per action class — how much rope does the agent have before a human must approve? Default for outbound posting is hard-gate.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent className="flex flex-col divide-y divide-[var(--dk-border)]">
              {ACTION_CLASSES.map((a) => {
                const current = autonomy[a.value] ?? "hard_gate";
                return (
                  <div
                    key={a.value}
                    className="grid md:grid-cols-[1fr_auto] gap-4 py-4 items-start"
                  >
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-semibold text-ink">
                        {a.label}
                      </span>
                      <span className="text-xs text-[var(--dk-fg-2)]">
                        {a.description}
                      </span>
                    </div>
                    <DkRadioGroup orientation="horizontal" className="md:items-center">
                      {TRUST_MODES.map((m) => (
                        <label
                          key={m.value}
                          className={cn(
                            "flex items-center gap-1.5 cursor-pointer rounded-md px-2.5 py-1.5 transition-colors duration-fast",
                            current === m.value
                              ? "bg-[var(--dk-purple-50)] text-brand"
                              : "text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)]",
                          )}
                        >
                          <DkRadio
                            name={`autonomy-${a.value}`}
                            value={m.value}
                            checked={current === m.value}
                            onChange={() =>
                              setAutonomy({ ...autonomy, [a.value]: m.value })
                            }
                          />
                          <span className="text-sm font-medium">{m.label}</span>
                        </label>
                      ))}
                    </DkRadioGroup>
                  </div>
                );
              })}
              <div className="pt-4">
                <DkBadge tone="info">
                  Resolution order: Org default → Project override → Channel override → Action-level override
                </DkBadge>
              </div>
            </DkCardContent>
          </DkCard>
        </div>
      )}
    </div>
  );
}
