"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles } from "lucide-react";

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
  GenerateResultItem,
  Organization,
  generateCreatives,
  listOrgs,
} from "@/lib/api";

/**
 * Creatives Agent runner — submit a brief, get N variants, each
 * queued in the Approval Inbox.
 */
export default function CreativesStationPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState<string>("");
  const [brief, setBrief] = useState("");
  const [channel, setChannel] = useState("linkedin");
  const [nVariants, setNVariants] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [results, setResults] = useState<GenerateResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);

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

  async function onGenerate() {
    if (!orgId) return;
    setGenerating(true);
    setError(null);
    setResults([]);
    try {
      const response = await generateCreatives({
        organization_id: orgId,
        brief,
        n_variants: nVariants,
        channel,
      });
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · Creatives"
        title="Creatives Station"
        description={`Hand the Creatives Agent a brief — it pulls your active brand kit, retrieves relevant context from your knowledge graph, and drafts variants. Outputs land in the Approval Inbox; the agent never publishes on its own.`}
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Run the Creatives Agent</DkCardTitle>
          <DkCardDescription>
            Outputs are pending until a reviewer approves in the{" "}
            <Link href="/inbox" className="font-medium text-brand hover:underline">
              Inbox
            </Link>
            .
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-4">
          {orgs.length === 0 ? (
            <DkEmptyState
              icon={<Sparkles className="h-6 w-6" />}
              title="No organizations yet"
              description="Ask an admin to create one — or sign in as a superuser to create one yourself."
            />
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <DkLabel htmlFor="org">Organization</DkLabel>
                <DkSelect
                  id="org"
                  value={orgId}
                  onChange={(e) => setOrgId(e.target.value)}
                >
                  {orgs.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name} ({o.slug})
                    </option>
                  ))}
                </DkSelect>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <DkLabel htmlFor="channel">Channel</DkLabel>
                  <DkSelect
                    id="channel"
                    value={channel}
                    onChange={(e) => setChannel(e.target.value)}
                  >
                    <option value="linkedin">LinkedIn</option>
                    <option value="x">X / Twitter</option>
                    <option value="instagram">Instagram</option>
                    <option value="threads">Threads</option>
                    <option value="bluesky">Bluesky</option>
                  </DkSelect>
                </div>
                <div className="flex flex-col gap-1.5">
                  <DkLabel htmlFor="n">Number of variants</DkLabel>
                  <DkInput
                    id="n"
                    type="number"
                    min={1}
                    max={10}
                    value={nVariants}
                    onChange={(e) =>
                      setNVariants(Number(e.target.value) || 3)
                    }
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1.5">
                <DkLabel
                  htmlFor="brief"
                  description="One paragraph. The clearer the intent, the better the variants."
                >
                  Brief
                </DkLabel>
                <DkTextarea
                  id="brief"
                  rows={5}
                  placeholder="Announce the Q2 release — lead with the customer outcome, friendly but professional…"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                />
              </div>

              {error && (
                <div
                  role="alert"
                  className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
                >
                  {error}
                </div>
              )}

              <DkButton
                onClick={() => void onGenerate()}
                disabled={!orgId || brief.length < 4 || generating}
                loading={generating}
                withArrow={!generating}
              >
                {generating ? "Generating" : "Generate Variants"}
              </DkButton>
            </>
          )}
        </DkCardContent>
      </DkCard>

      {results.length > 0 && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Generated Variants</DkCardTitle>
            <DkCardDescription>
              All {results.length} are queued in the{" "}
              <Link href="/inbox" className="font-medium text-brand hover:underline">
                Approval Inbox
              </Link>
              .
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            {results.map((r, i) => (
              <div
                key={r.approval_request_id}
                className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-4"
              >
                <div className="mb-2 flex items-center gap-2">
                  <DkBadge tone="brand">Variant {i + 1}</DkBadge>
                  <span className="text-xs text-[var(--dk-fg-2)] font-mono">
                    approval #{r.approval_request_id.slice(0, 8)}
                  </span>
                </div>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--dk-fg-1)]">
                  {r.variant}
                </p>
              </div>
            ))}
          </DkCardContent>
        </DkCard>
      )}
    </div>
  );
}
