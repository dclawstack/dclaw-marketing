"use client";

import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowUpRight, BookOpen, Link2, Loader2, Minus, Search, ShieldAlert } from "lucide-react";

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
  DkTabs,
  DkTabsContent,
  DkTabsList,
  DkTabsTrigger,
  DkTextarea,
} from "@/components/dk";
import { AeoWidget } from "@/components/aeo-widget";
import {
  getRankingDelta,
  listOrgs,
  listSeoAudit,
  runSeoAudit,
  suggestInternalLinks,
  type Organization,
  type SeoAuditFinding,
  type SeoInternalLink,
  type SeoRankingDelta,
} from "@/lib/api";

const severityTone: Record<string, "neutral" | "warning" | "danger" | "brand"> = {
  low: "neutral",
  medium: "warning",
  high: "danger",
};

export default function SeoStationPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Audit
  const [findings, setFindings] = useState<SeoAuditFinding[]>([]);
  const [auditDomain, setAuditDomain] = useState("");
  const [auditing, setAuditing] = useState(false);

  // Ranking delta
  const [deltas, setDeltas] = useState<SeoRankingDelta[]>([]);

  // Internal links
  const [draft, setDraft] = useState("");
  const [links, setLinks] = useState<SeoInternalLink[]>([]);
  const [suggesting, setSuggesting] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const list = await listOrgs();
        setOrgs(list);
        if (list.length > 0 && !orgId) setOrgId(list[0].id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load orgs.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!orgId) return;
    void (async () => {
      try {
        const [a, d] = await Promise.all([
          listSeoAudit(orgId, { days: 30, limit: 50 }),
          getRankingDelta(orgId, 7),
        ]);
        setFindings(a);
        setDeltas(d);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load SEO data.");
      }
    })();
  }, [orgId]);

  async function onRunAudit() {
    if (!orgId || !auditDomain.trim()) return;
    setAuditing(true);
    setError(null);
    try {
      await runSeoAudit(orgId, auditDomain.trim());
      const a = await listSeoAudit(orgId, { domain: auditDomain.trim(), days: 30 });
      setFindings(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Audit failed.");
    } finally {
      setAuditing(false);
    }
  }

  async function onSuggestLinks() {
    if (!orgId || !draft.trim()) return;
    setSuggesting(true);
    setError(null);
    setLinks([]);
    try {
      const out = await suggestInternalLinks(orgId, draft, 5);
      setLinks(out);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Internal-link suggest failed.");
    } finally {
      setSuggesting(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · SEO Specialist"
        title="Search Station"
        description="Run a site audit, watch your SERP positions, and let the agent suggest internal links pulled straight from your Knowledge Graph."
        actions={<DkBadge tone="brand">Theme H</DkBadge>}
      />

      <AeoWidget orgId={orgId} />

      {orgs.length === 0 ? (
        <DkEmptyState
          icon={<Search className="h-6 w-6" />}
          title="No Organizations yet"
          description="Create an Organization to start the SEO Agent."
        />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-[260px_1fr]">
            <div>
              <DkLabel htmlFor="seo-org">Organization</DkLabel>
              <DkSelect
                id="seo-org"
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
            {error ? (
              <DkCard>
                <DkCardContent className="text-[var(--dk-danger)]">{error}</DkCardContent>
              </DkCard>
            ) : null}
          </div>

          <DkTabs defaultValue="audit">
            <DkTabsList>
              <DkTabsTrigger value="audit">
                <ShieldAlert className="h-4 w-4" /> Site audit
              </DkTabsTrigger>
              <DkTabsTrigger value="ranking">
                <Search className="h-4 w-4" /> Ranking delta
              </DkTabsTrigger>
              <DkTabsTrigger value="links">
                <Link2 className="h-4 w-4" /> Internal links
              </DkTabsTrigger>
            </DkTabsList>

            {/* AUDIT */}
            <DkTabsContent value="audit">
              <DkCard>
                <DkCardHeader>
                  <DkCardTitle>Run an audit</DkCardTitle>
                  <DkCardDescription>
                    Crawls via the Ahrefs MCP adapter. Findings persist to the audit
                    trail so the dashboard can chart them over time.
                  </DkCardDescription>
                </DkCardHeader>
                <DkCardContent className="flex flex-col gap-3 md:flex-row md:items-end">
                  <div className="grow">
                    <DkLabel htmlFor="audit-domain">Domain</DkLabel>
                    <DkInput
                      id="audit-domain"
                      placeholder="example.com"
                      value={auditDomain}
                      onChange={(e) => setAuditDomain(e.target.value)}
                    />
                  </div>
                  <DkButton onClick={onRunAudit} disabled={auditing || !auditDomain.trim()}>
                    {auditing ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {auditing ? "Auditing…" : "Run audit"}
                  </DkButton>
                </DkCardContent>
              </DkCard>

              {findings.length === 0 ? (
                <DkEmptyState
                  icon={<ShieldAlert className="h-6 w-6" />}
                  title="No findings yet"
                  description="Run an audit to surface broken links, missing meta, thin content, and slow pages."
                />
              ) : (
                <div className="flex flex-col gap-2">
                  {findings.map((f) => (
                    <DkCard key={f.id}>
                      <DkCardContent className="flex flex-wrap items-center gap-3">
                        <DkBadge tone={severityTone[f.severity ?? ""] ?? "neutral"}>
                          {f.severity ?? "info"}
                        </DkBadge>
                        <span className="font-medium">{f.kind ?? "finding"}</span>
                        <span className="text-sm opacity-80">{f.url ?? f.domain}</span>
                        {f.detail ? (
                          <span className="text-sm opacity-60 ml-auto">{f.detail}</span>
                        ) : null}
                      </DkCardContent>
                    </DkCard>
                  ))}
                </div>
              )}
            </DkTabsContent>

            {/* RANKING DELTA */}
            <DkTabsContent value="ranking">
              {deltas.length === 0 ? (
                <DkEmptyState
                  icon={<Search className="h-6 w-6" />}
                  title="No ranking data yet"
                  description="Configure tracked keywords on the Org's constraints (seo.tracked_keywords) — daily snapshots start tomorrow at 07:15 UTC."
                />
              ) : (
                <div className="grid gap-2 md:grid-cols-2">
                  {deltas.map((d) => {
                    const trend =
                      d.delta == null
                        ? null
                        : d.delta > 0
                          ? "down"
                          : d.delta < 0
                            ? "up"
                            : "flat";
                    return (
                      <DkCard key={d.keyword}>
                        <DkCardContent className="flex items-center gap-3">
                          <span className="font-medium grow">{d.keyword}</span>
                          <span className="text-sm opacity-70">
                            {d.previous ?? "—"} → {d.current ?? "—"}
                          </span>
                          {trend === "up" ? (
                            <ArrowUpRight className="h-4 w-4 text-green-600" />
                          ) : trend === "down" ? (
                            <ArrowDownRight className="h-4 w-4 text-red-600" />
                          ) : (
                            <Minus className="h-4 w-4 opacity-50" />
                          )}
                        </DkCardContent>
                      </DkCard>
                    );
                  })}
                </div>
              )}
            </DkTabsContent>

            {/* INTERNAL LINKS */}
            <DkTabsContent value="links">
              <DkCard>
                <DkCardHeader>
                  <DkCardTitle>Suggest internal links</DkCardTitle>
                  <DkCardDescription>
                    Paste a draft. The agent embeds it and finds the most-similar
                    URL / git pages in your Knowledge Graph.
                  </DkCardDescription>
                </DkCardHeader>
                <DkCardContent className="flex flex-col gap-3">
                  <DkTextarea
                    rows={6}
                    placeholder="Paste a draft (or a paragraph) here…"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                  />
                  <div>
                    <DkButton onClick={onSuggestLinks} disabled={suggesting || !draft.trim()}>
                      {suggesting ? <Loader2 className="h-4 w-4 animate-spin" /> : <BookOpen className="h-4 w-4" />}
                      {suggesting ? "Searching…" : "Suggest links"}
                    </DkButton>
                  </div>
                </DkCardContent>
              </DkCard>

              {links.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {links.map((l) => (
                    <DkCard key={l.chunk_id}>
                      <DkCardContent className="flex flex-wrap items-center gap-3">
                        <DkBadge tone="brand">{l.source_type}</DkBadge>
                        <a
                          className="font-medium underline-offset-4 hover:underline"
                          href={l.source_reference}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {l.anchor || l.source_reference}
                        </a>
                        <span className="ml-auto text-sm opacity-60">
                          sim {(l.similarity * 100).toFixed(0)}%
                        </span>
                      </DkCardContent>
                    </DkCard>
                  ))}
                </div>
              ) : null}
            </DkTabsContent>
          </DkTabs>
        </>
      )}
    </div>
  );
}
