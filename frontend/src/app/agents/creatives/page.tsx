"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
        setError(err instanceof Error ? err.message : "Failed to load Orgs.");
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">Creatives Station</h1>
        <p className="text-sm text-muted-foreground">
          Hand the Creatives Agent a brief. It pulls your brand kit and
          retrieves relevant context from your knowledge graph, then drafts{" "}
          {nVariants} variants. Each lands in the Approval Inbox — the agent
          never publishes on its own.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run the Creatives Agent</CardTitle>
          <CardDescription>
            Outputs are pending until a reviewer approves in{" "}
            <Link href="/inbox" className="font-medium underline">
              Inbox
            </Link>
            .
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {orgs.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No Organizations available. Ask an admin to create one (or sign in
              as a superuser to create one yourself).
            </p>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="org">Organization</Label>
                <select
                  id="org"
                  className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  value={orgId}
                  onChange={(e) => setOrgId(e.target.value)}
                >
                  {orgs.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name} ({o.slug})
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="channel">Channel</Label>
                  <select
                    id="channel"
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                    value={channel}
                    onChange={(e) => setChannel(e.target.value)}
                  >
                    <option value="linkedin">LinkedIn</option>
                    <option value="x">X / Twitter</option>
                    <option value="instagram">Instagram</option>
                    <option value="threads">Threads</option>
                    <option value="bluesky">Bluesky</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="n">Number of variants</Label>
                  <Input
                    id="n"
                    type="number"
                    min={1}
                    max={10}
                    value={nVariants}
                    onChange={(e) => setNVariants(Number(e.target.value) || 3)}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="brief">Brief</Label>
                <textarea
                  id="brief"
                  className="min-h-[120px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                  placeholder="What do you want the agent to write about?"
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                />
              </div>
              {error && (
                <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </div>
              )}
              <Button
                onClick={() => void onGenerate()}
                disabled={!orgId || brief.length < 4 || generating}
              >
                {generating ? "Generating…" : "Generate variants"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Generated variants</CardTitle>
            <CardDescription>
              All {results.length} are queued in the{" "}
              <Link href="/inbox" className="font-medium underline">
                Approval Inbox
              </Link>
              .
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {results.map((r, i) => (
              <div
                key={r.approval_request_id}
                className="rounded-md border border-border bg-muted/30 p-3"
              >
                <div className="mb-2 flex items-center gap-2">
                  <Badge>Variant {i + 1}</Badge>
                  <span className="text-xs text-muted-foreground">
                    approval #{r.approval_request_id.slice(0, 8)}
                  </span>
                </div>
                <p className="whitespace-pre-wrap text-sm">{r.variant}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
