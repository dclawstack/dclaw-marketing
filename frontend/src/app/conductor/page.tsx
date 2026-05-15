"use client";

/**
 * /conductor — unified Conductor surface (S5-CDR-A).
 *
 * Single page combining the chat surface (DkAgentChat — primary) with the
 * legacy brief-decompose-dispatch orchestrator (collapsible secondary). The
 * threads sidebar and ModelSettingsPanel are shared. /agent redirects here.
 *
 * Future Sprint 5 issues layer on top of this page:
 *   - #B: drag-drop file upload + vision
 *   - #C: Claude Agent SDK + tool fleet (folds brief-orchestrate into chat)
 *   - #D: streaming + extended thinking
 *   - #E: web search + research modes
 *   - #F: voice / prompt library / slash / message ops / markdown polish
 */

import { useCallback, useEffect, useState } from "react";
import { Loader2, Play, Sparkles } from "lucide-react";

import {
  DkAgentChat,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkPageHeader,
  DkTextarea,
} from "@/components/dk";
import { ModelSettingsPanel } from "@/components/model-settings-panel";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface Thread {
  id: string;
  title: string;
  kind: string;
  updated_at: string;
}

interface DispatchResult {
  agent: string;
  intent: string | null;
  text: string;
  model_id: string | null;
  resolved_by: string | null;
}

interface Plan {
  tasks: { agent: string; intent: string; input: string }[];
  rationale: string;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  if (r.status === 204) return undefined as T;
  return r.json();
}

export default function ConductorPage() {
  const { currentOrg } = useOrg();
  const orgId = currentOrg?.id;

  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThread, setActiveThread] = useState<string | null>(null);
  const [brief, setBrief] = useState("");
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [results, setResults] = useState<DispatchResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refreshThreads = useCallback(async () => {
    if (!orgId) return;
    try {
      const list = await api<Thread[]>(
        `/api/v1/orgs/${orgId}/agent-threads`,
      );
      setThreads(list);
    } catch {
      /* swallow */
    }
  }, [orgId]);

  useEffect(() => {
    refreshThreads();
  }, [refreshThreads]);

  const dispatch = async () => {
    if (!brief.trim() || !orgId) return;
    setBusy(true);
    setError(null);
    setPlan(null);
    setResults([]);
    try {
      const out = await api<{ plan: Plan; results: DispatchResult[] }>(
        "/api/v1/conductor/dispatch",
        {
          method: "POST",
          body: JSON.stringify({
            organization_id: orgId,
            brief,
          }),
        },
      );
      setPlan(out.plan);
      setResults(out.results);
      refreshThreads();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dispatch failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <DkPageHeader
        eyebrow="Agent · Manager Station"
        title="Conductor"
        description="Your agentic chatbot for running the entire platform — chat, plan, and operate every feature from one place. Outbound posting is hard-gate by default — nothing goes live without you."
      />

      {!currentOrg ? (
        <DkEmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="Pick an organization"
          description="Conductor threads are org-scoped — use the switcher in the nav."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
          {/* LEFT — threads sidebar (visual today; chat-thread wiring lands in S5-CDR-F polish) */}
          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Threads</DkCardTitle>
            </DkCardHeader>
            <DkCardContent className="space-y-2 text-sm">
              {threads.length === 0 ? (
                <div className="text-slate-500 text-xs">No threads yet.</div>
              ) : (
                threads.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveThread(t.id)}
                    className={`block w-full text-left px-2 py-1.5 rounded ${
                      activeThread === t.id ? "bg-slate-100" : "hover:bg-slate-50"
                    }`}
                  >
                    <div className="font-medium truncate">{t.title || "(untitled)"}</div>
                    <div className="text-xs text-slate-400 truncate">{t.kind}</div>
                  </button>
                ))
              )}
            </DkCardContent>
          </DkCard>

          {/* RIGHT — model selector (page-level, visible by default), chat, and legacy orchestrate panel */}
          <div className="space-y-4">
            <ModelSettingsPanel orgId={orgId!} defaultOpen />

            {/* PRIMARY: chat */}
            <DkAgentChat kind="conductor" />

            {/* SECONDARY: brief → decompose → dispatch (collapsed by default; folded into chat via tool-calls in S5-CDR-C) */}
            <details className="rounded-lg border border-[var(--dk-border)] bg-white">
              <summary className="cursor-pointer select-none px-4 py-3 text-sm font-medium text-[var(--dk-fg-1)]">
                Orchestrate from a brief
              </summary>
              <div className="space-y-3 border-t border-[var(--dk-border)] p-4">
                <DkTextarea
                  rows={4}
                  value={brief}
                  onChange={(e) => setBrief(e.target.value)}
                  placeholder="e.g. We're launching v1.1.2 next week. Plan a 1-week multi-channel push…"
                />
                <div className="flex justify-end gap-2">
                  <DkButton onClick={dispatch} disabled={busy || !brief.trim()}>
                    {busy ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    {busy ? "Dispatching…" : "Dispatch"}
                  </DkButton>
                </div>
                {error && (
                  <div className="text-rose-600 text-sm">{error}</div>
                )}

                {plan && (
                  <DkCard>
                    <DkCardHeader>
                      <DkCardTitle>
                        <Sparkles className="w-4 h-4 inline mr-1" /> Plan
                      </DkCardTitle>
                    </DkCardHeader>
                    <DkCardContent>
                      <div className="text-sm text-slate-700 mb-2">{plan.rationale}</div>
                      <ul className="space-y-1 text-sm">
                        {plan.tasks.map((t, i) => (
                          <li key={i} className="border-l-2 border-brand pl-2">
                            <span className="font-medium">{t.agent}</span> · {t.intent}
                          </li>
                        ))}
                      </ul>
                    </DkCardContent>
                  </DkCard>
                )}

                {results.map((r, i) => (
                  <DkCard key={i}>
                    <DkCardHeader>
                      <DkCardTitle>
                        {r.agent} <span className="text-xs text-slate-400">{r.model_id}</span>
                      </DkCardTitle>
                    </DkCardHeader>
                    <DkCardContent className="text-sm whitespace-pre-wrap">
                      {r.text}
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            </details>
          </div>
        </div>
      )}
    </div>
  );
}
