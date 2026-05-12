"use client";

import { useEffect, useState } from "react";
import { Loader2, Sparkles, Copy } from "lucide-react";

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
import { listOrgs, type Organization } from "@/lib/api";
import { getToken } from "@/lib/auth";

type HooksResponse = { hooks: string[]; model: string; stub: boolean };

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(init?.headers as Record<string, string> | undefined),
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function HooksLabPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState("");
  const [draft, setDraft] = useState("");
  const [n, setN] = useState(30);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<HooksResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const list = await listOrgs();
        setOrgs(list);
        if (list.length && !orgId) setOrgId(list[0].id);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load orgs.");
      }
    })();
  }, []);

  async function generate() {
    if (!orgId || !draft.trim()) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const data = await authFetch<HooksResponse>("/api/v1/hooks/generate", {
        method: "POST",
        body: JSON.stringify({
          organization_id: orgId,
          draft_text: draft,
          n,
        }),
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed.");
    } finally {
      setBusy(false);
    }
  }

  function copy(hook: string) {
    if (typeof navigator !== "undefined") {
      navigator.clipboard?.writeText(hook).catch(() => null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme B6 · Content polish"
        title="Hook &amp; Headline Lab"
        description="Paste a draft, get N hook / headline candidates ranked by an LLM. Brand voice applied when an active BrandKit is configured."
        actions={<DkBadge tone="brand">delight feature</DkBadge>}
      />

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Inputs</DkCardTitle>
          <DkCardDescription>
            Up to ~10,000 chars; the more context, the sharper the hooks.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="grid gap-3 md:grid-cols-[220px_120px_1fr]">
          <div>
            <DkLabel>Organization</DkLabel>
            <DkSelect value={orgId} onChange={(e) => setOrgId(e.target.value)}>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </DkSelect>
          </div>
          <div>
            <DkLabel>How many</DkLabel>
            <DkInput
              type="number"
              min={1}
              max={60}
              value={n}
              onChange={(e) =>
                setN(Math.min(60, Math.max(1, Number(e.target.value || 30))))
              }
            />
          </div>
          <div>
            <DkLabel>Draft</DkLabel>
            <DkTextarea
              rows={5}
              placeholder="Paste a draft, a brief, or even a bullet outline…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
          </div>
          <div className="md:col-span-3">
            <DkButton onClick={generate} disabled={busy || !draft.trim() || !orgId}>
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate {n}
            </DkButton>
          </div>
        </DkCardContent>
      </DkCard>

      {result ? (
        <>
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">
              {result.hooks.length} hooks
            </h2>
            <DkBadge tone={result.stub ? "warning" : "success"}>
              {result.model}
              {result.stub ? " · stub" : ""}
            </DkBadge>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {result.hooks.map((h, i) => (
              <DkCard key={i}>
                <DkCardContent className="flex items-center gap-2 py-2">
                  <span className="font-mono text-xs opacity-50 w-6 text-right">
                    {i + 1}
                  </span>
                  <span className="grow text-sm">{h}</span>
                  <DkButton
                    variant="ghost"
                    size="sm"
                    onClick={() => copy(h)}
                    aria-label="Copy hook"
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </DkButton>
                </DkCardContent>
              </DkCard>
            ))}
          </div>
        </>
      ) : !busy ? (
        <DkEmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="Nothing generated yet"
          description="Paste a draft above and click Generate."
        />
      ) : null}
    </div>
  );
}
