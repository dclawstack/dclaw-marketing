"use client";

import { useEffect, useState } from "react";
import { Copy, Loader2, Recycle } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTextarea,
} from "@/components/dk";
import { listOrgs, type Organization } from "@/lib/api";
import { getToken } from "@/lib/auth";

type Result = { channel: string; output: string; model: string; stub: boolean };

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

const CHANNELS = [
  "linkedin",
  "x",
  "x_thread",
  "instagram",
  "threads",
  "blog",
  "newsletter",
  "bluesky",
  "tiktok_caption",
  "youtube_description",
];

export default function RepurposePage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [orgId, setOrgId] = useState("");
  const [source, setSource] = useState("");
  const [selected, setSelected] = useState<Set<string>>(
    new Set(["x", "linkedin", "instagram"]),
  );
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Result[]>([]);
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

  function toggle(c: string) {
    const next = new Set(selected);
    if (next.has(c)) next.delete(c);
    else next.add(c);
    setSelected(next);
  }

  async function run() {
    if (!orgId || !source.trim() || selected.size === 0) return;
    setBusy(true);
    setError(null);
    setResults([]);
    try {
      const data = await authFetch<{ results: Result[] }>(
        "/api/v1/repurpose",
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: orgId,
            source_text: source,
            target_channels: Array.from(selected),
          }),
        },
      );
      setResults(data.results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Repurpose failed.");
    } finally {
      setBusy(false);
    }
  }

  function copy(text: string) {
    if (typeof navigator !== "undefined") {
      navigator.clipboard?.writeText(text).catch(() => null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme B4 · Content polish"
        title="Repurposing Engine"
        description="Paste one piece of source copy. Pick channels. Get channel-shaped variants honouring each platform's character limit and native voice."
        actions={<DkBadge tone="brand">Sprint 3 · SP3-11</DkBadge>}
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
          <DkCardTitle>Source &amp; targets</DkCardTitle>
          <DkCardDescription>
            Up to 20,000 chars. Each selected channel gets one rewritten output.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div className="grid gap-3 md:grid-cols-[220px_1fr]">
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
              <DkLabel>Source copy</DkLabel>
              <DkTextarea
                rows={6}
                placeholder="Paste a draft or finalised piece of copy…"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </div>
          </div>
          <div>
            <DkLabel>Target channels</DkLabel>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {CHANNELS.map((c) => {
                const active = selected.has(c);
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => toggle(c)}
                    className={
                      "rounded-md px-3 py-1 text-sm font-medium border " +
                      (active
                        ? "border-brand bg-[var(--dk-purple-50)] text-brand"
                        : "border-[var(--dk-border)] text-[var(--dk-fg-2)] hover:bg-[var(--dk-gray-50)]")
                    }
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>
          <div>
            <DkButton
              onClick={run}
              disabled={busy || !source.trim() || selected.size === 0 || !orgId}
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Recycle className="h-4 w-4" />
              )}
              Repurpose for {selected.size} channel{selected.size === 1 ? "" : "s"}
            </DkButton>
          </div>
        </DkCardContent>
      </DkCard>

      {results.map((r) => (
        <DkCard key={r.channel}>
          <DkCardHeader>
            <div className="flex items-center justify-between gap-2">
              <DkCardTitle>{r.channel}</DkCardTitle>
              <div className="flex items-center gap-2">
                <DkBadge tone={r.stub ? "warning" : "success"}>{r.model}</DkBadge>
                <DkButton variant="ghost" size="sm" onClick={() => copy(r.output)}>
                  <Copy className="h-3.5 w-3.5" /> Copy
                </DkButton>
              </div>
            </div>
          </DkCardHeader>
          <DkCardContent>
            <pre className="whitespace-pre-wrap font-sans text-sm leading-snug">
              {r.output}
            </pre>
          </DkCardContent>
        </DkCard>
      ))}
    </div>
  );
}
