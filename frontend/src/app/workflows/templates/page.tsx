"use client";

/**
 * /workflows/templates — visual workflow template catalog (S4-D6).
 *
 * Lists the curated workflow templates from
 * GET /api/v1/workflows/templates, lets the user clone one into the
 * active org as a new Workflow draft.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface TemplateRow {
  key: string;
  label: string;
  description: string;
  dsl: { nodes: { id: string; type: string }[]; edges: { from: string; to: string }[] };
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

export default function WorkflowTemplatesPage() {
  const { currentOrg } = useOrg();
  const [tpls, setTpls] = useState<TemplateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [clonedId, setClonedId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api<TemplateRow[]>("/api/v1/workflows/templates");
      setTpls(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const clone = async (key: string) => {
    if (!currentOrg) return;
    setBusy(key);
    setError(null);
    try {
      const r = await api<{ id: string }>(
        `/api/v1/workflows/templates/${key}/clone`,
        {
          method: "POST",
          body: JSON.stringify({ organization_id: currentOrg.id }),
        },
      );
      setClonedId(r.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clone failed.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-4">
      <DkPageHeader
        eyebrow="Workflows"
        title="Workflow Templates"
        description="Curated production-ready workflows. Clone one into your org and edit."
      />

      {error && (
        <div className="rounded border border-rose-300 bg-rose-50 p-3 text-rose-700 text-sm">
          {error}
        </div>
      )}
      {clonedId && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-3 text-emerald-800 text-sm">
          Cloned. <Link href={`/workflows/${clonedId}`} className="underline">Open editor →</Link>
        </div>
      )}

      {loading ? (
        <DkSkeleton className="h-48" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tpls.map((t) => (
            <DkCard key={t.key}>
              <DkCardHeader>
                <DkCardTitle>{t.label}</DkCardTitle>
              </DkCardHeader>
              <DkCardContent className="space-y-3 text-sm">
                <div>{t.description}</div>
                <div className="text-xs text-slate-500">
                  {t.dsl.nodes.length} nodes · {t.dsl.edges.length} edges
                </div>
                <div className="flex gap-2 pt-1">
                  {t.dsl.nodes.map((n) => (
                    <span
                      key={n.id}
                      className="text-xs px-2 py-0.5 rounded bg-slate-100"
                    >
                      {n.type}
                    </span>
                  ))}
                </div>
                <div className="flex justify-end">
                  <DkButton
                    onClick={() => clone(t.key)}
                    disabled={!currentOrg || busy === t.key}
                  >
                    {busy === t.key ? "Cloning…" : "Clone into org"}
                  </DkButton>
                </div>
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}
    </div>
  );
}
