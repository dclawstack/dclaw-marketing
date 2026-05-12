"use client";

import { useEffect, useState } from "react";
import { Archive, Brain, Plus, RefreshCw, Trash2 } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTextarea,
} from "@/components/dk";
import {
  createBrandInsight,
  deleteBrandInsight,
  getActiveBrandKit,
  listBrandInsights,
  listOrgs,
  updateBrandInsight,
  type BrandInsight,
  type BrandInsightKind,
  type Organization,
} from "@/lib/api";

const KIND_OPTIONS: BrandInsightKind[] = [
  "performance",
  "voice",
  "audience",
  "hashtag",
  "timing",
  "other",
];

export default function BrandInsightsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState<string>("");
  const [kitId, setKitId] = useState<string | null>(null);
  const [insights, setInsights] = useState<BrandInsight[]>([]);
  const [includeArchived, setIncludeArchived] = useState(false);

  const [newKind, setNewKind] = useState<BrandInsightKind>("performance");
  const [newSummary, setNewSummary] = useState("");
  const [newDetail, setNewDetail] = useState("");
  const [newConfidence, setNewConfidence] = useState(0.75);

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const list = await listOrgs();
        setOrgs(list);
        if (list.length && !orgId) setOrgId(list[0].id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load orgs.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!orgId) return;
    void (async () => {
      try {
        const kit = await getActiveBrandKit(orgId);
        setKitId(kit.id);
        const rows = await listBrandInsights(orgId, kit.id, includeArchived);
        setInsights(rows);
      } catch (err) {
        setKitId(null);
        setInsights([]);
        setError(err instanceof Error ? err.message : "No active brand kit.");
      }
    })();
  }, [orgId, includeArchived]);

  async function refresh() {
    if (!orgId || !kitId) return;
    const rows = await listBrandInsights(orgId, kitId, includeArchived);
    setInsights(rows);
  }

  async function onCreate() {
    if (!orgId || !kitId || !newSummary.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createBrandInsight(orgId, kitId, {
        kind: newKind,
        summary: newSummary.trim(),
        detail: newDetail.trim() || undefined,
        confidence: newConfidence,
      });
      setNewSummary("");
      setNewDetail("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create.");
    } finally {
      setBusy(false);
    }
  }

  async function onArchive(id: string, archived: boolean) {
    setBusy(true);
    try {
      await updateBrandInsight(id, { is_archived: !archived });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to archive.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Permanently delete this insight?")) return;
    setBusy(true);
    try {
      await deleteBrandInsight(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Brand · KG write-back"
        title="Brand Insights"
        description="What the platform learned from prior agent runs about this brand. Every active insight above the confidence floor feeds into the next Creatives Agent system prompt."
        actions={<DkBadge tone="brand">§6.2</DkBadge>}
      />

      {orgs.length === 0 ? (
        <DkEmptyState
          icon={<Brain className="h-6 w-6" />}
          title="No Organizations yet"
          description="Create an Organization with an active brand kit to start collecting insights."
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-[260px_1fr_auto]">
            <div>
              <DkLabel htmlFor="bi-org">Organization</DkLabel>
              <DkSelect
                id="bi-org"
                value={orgId}
                onChange={(e) => setOrgId(e.target.value)}
              >
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </DkSelect>
            </div>
            <div className="flex items-end gap-2">
              <DkLabel className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={includeArchived}
                  onChange={(e) => setIncludeArchived(e.target.checked)}
                />
                Show archived
              </DkLabel>
            </div>
            <div className="flex items-end">
              <DkButton onClick={refresh} disabled={busy || !kitId}>
                <RefreshCw className="h-4 w-4" /> Refresh
              </DkButton>
            </div>
          </div>

          {error ? (
            <DkCard>
              <DkCardContent className="text-[var(--dk-danger)]">{error}</DkCardContent>
            </DkCard>
          ) : null}

          {kitId ? (
            <DkCard>
              <DkCardHeader>
                <DkCardTitle>Add an insight</DkCardTitle>
                <DkCardDescription>
                  Human-authored insights are flagged as such and never overwritten by the agent.
                </DkCardDescription>
              </DkCardHeader>
              <DkCardContent className="flex flex-col gap-3">
                <div className="grid gap-3 md:grid-cols-[160px_1fr_120px]">
                  <div>
                    <DkLabel>Kind</DkLabel>
                    <DkSelect
                      value={newKind}
                      onChange={(e) =>
                        setNewKind(e.target.value as BrandInsightKind)
                      }
                    >
                      {KIND_OPTIONS.map((k) => (
                        <option key={k} value={k}>
                          {k}
                        </option>
                      ))}
                    </DkSelect>
                  </div>
                  <div>
                    <DkLabel>Summary</DkLabel>
                    <DkInput
                      placeholder="e.g. Posts shipped Tue 10am UTC outperform Mon by 38%."
                      value={newSummary}
                      onChange={(e) => setNewSummary(e.target.value)}
                    />
                  </div>
                  <div>
                    <DkLabel>Confidence</DkLabel>
                    <DkInput
                      type="number"
                      step="0.05"
                      min={0}
                      max={1}
                      value={newConfidence}
                      onChange={(e) =>
                        setNewConfidence(Number(e.target.value || 0))
                      }
                    />
                  </div>
                </div>
                <div>
                  <DkLabel>Detail (optional)</DkLabel>
                  <DkTextarea
                    rows={3}
                    placeholder="Context, links to the supporting analytics window, etc."
                    value={newDetail}
                    onChange={(e) => setNewDetail(e.target.value)}
                  />
                </div>
                <div>
                  <DkButton onClick={onCreate} disabled={busy || !newSummary.trim()}>
                    <Plus className="h-4 w-4" /> Add insight
                  </DkButton>
                </div>
              </DkCardContent>
            </DkCard>
          ) : null}

          {insights.length === 0 ? (
            <DkEmptyState
              icon={<Brain className="h-6 w-6" />}
              title="No insights yet"
              description="The Analyst Agent writes one of these on every weekly report. You can also seed insights manually above."
            />
          ) : (
            <div className="flex flex-col gap-2">
              {insights.map((i) => (
                <DkCard key={i.id} className={i.is_archived ? "opacity-60" : undefined}>
                  <DkCardContent className="flex flex-wrap items-start gap-3">
                    <DkBadge tone="brand">{i.kind}</DkBadge>
                    <div className="grow">
                      <div className="font-medium">{i.summary}</div>
                      {i.detail ? (
                        <div className="text-sm opacity-70 mt-1">{i.detail}</div>
                      ) : null}
                      <div className="text-xs opacity-60 mt-1">
                        conf {(i.confidence * 100).toFixed(0)}%
                        {i.generated_by_agent
                          ? ` · ${i.generated_by_agent}`
                          : i.is_human_edited
                            ? " · human-authored"
                            : ""}
                        {i.is_archived ? " · archived" : ""}
                      </div>
                    </div>
                    <DkButton
                      variant="ghost"
                      onClick={() => onArchive(i.id, i.is_archived)}
                      disabled={busy}
                    >
                      <Archive className="h-4 w-4" />
                      {i.is_archived ? "Unarchive" : "Archive"}
                    </DkButton>
                    <DkButton
                      variant="ghost"
                      onClick={() => onDelete(i.id)}
                      disabled={busy}
                    >
                      <Trash2 className="h-4 w-4 text-[var(--dk-danger)]" />
                    </DkButton>
                  </DkCardContent>
                </DkCard>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
