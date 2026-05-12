"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { RotateCw } from "lucide-react";

import {
  DkBadge,
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

interface NodeOut {
  node_id: string;
  type: string;
  output: unknown;
  error: string | null;
}

interface RunDetail {
  id: string;
  status: string;
  deferred_reason: string | null;
  error_message: string | null;
  initial_context: Record<string, unknown>;
  final_context: Record<string, unknown> | null;
  node_results: NodeOut[] | null;
  started_at: string;
  completed_at: string | null;
}

export default function WorkflowRunTracePage() {
  const { id } = useParams<{ id: string }>();
  const { currentOrg } = useOrg();
  const [row, setRow] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [resuming, setResuming] = useState(false);

  async function load() {
    if (!currentOrg) return;
    setLoading(true);
    const res = await fetch(
      `/api/v1/orgs/${currentOrg.id}/workflow-runs/${id}`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    );
    if (res.ok) setRow(await res.json());
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg, id]);

  async function resume() {
    if (!currentOrg) return;
    setResuming(true);
    try {
      await fetch(
        `/api/v1/orgs/${currentOrg.id}/workflow-runs/${id}/resume`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${getToken()}` },
        },
      );
      await load();
    } finally {
      setResuming(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workflow run"
        title={row ? `Run ${row.id.slice(0, 8)}` : "Run"}
        description="Per-node execution trace + accumulating context. Paused runs (status=paused) can be resumed once the upstream approval is decided."
        actions={
          row?.status === "paused" ? (
            <DkButton onClick={resume} loading={resuming} disabled={resuming}>
              <RotateCw className="h-4 w-4" />
              Resume
            </DkButton>
          ) : null
        }
      />

      {loading || !row ? (
        <DkSkeleton className="h-32 w-full" />
      ) : (
        <>
          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Status</DkCardTitle>
            </DkCardHeader>
            <DkCardContent className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <DkBadge
                  tone={
                    row.status === "completed"
                      ? "success"
                      : row.status === "failed"
                        ? "danger"
                        : row.status === "paused"
                          ? "warning"
                          : "neutral"
                  }
                >
                  {row.status}
                </DkBadge>
                <span className="font-mono text-xs text-[var(--dk-fg-2)]">
                  started {new Date(row.started_at).toLocaleString()}
                </span>
              </div>
              {row.deferred_reason && (
                <p className="text-sm text-[var(--dk-fg-1)]">
                  Deferred: <span className="font-mono">{row.deferred_reason}</span>
                </p>
              )}
              {row.error_message && (
                <p className="text-sm text-[var(--dk-danger)]">
                  Error: {row.error_message}
                </p>
              )}
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Node trace</DkCardTitle>
            </DkCardHeader>
            <DkCardContent className="flex flex-col gap-3">
              {(row.node_results ?? []).map((n) => (
                <div
                  key={n.node_id}
                  className="rounded-md border border-[var(--dk-border)] p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm">{n.node_id}</span>
                    <DkBadge tone={n.error ? "danger" : "neutral"}>
                      {n.type}
                    </DkBadge>
                  </div>
                  {n.error ? (
                    <pre className="mt-2 text-xs text-[var(--dk-danger)]">
                      {n.error}
                    </pre>
                  ) : (
                    <pre className="mt-2 max-h-32 overflow-auto text-xs font-mono text-[var(--dk-fg-1)]">
                      {JSON.stringify(n.output, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </DkCardContent>
          </DkCard>

          <DkCard>
            <DkCardHeader>
              <DkCardTitle>Final context</DkCardTitle>
            </DkCardHeader>
            <DkCardContent>
              <pre className="max-h-64 overflow-auto text-xs font-mono text-[var(--dk-fg-1)]">
                {JSON.stringify(row.final_context ?? row.initial_context, null, 2)}
              </pre>
            </DkCardContent>
          </DkCard>
        </>
      )}
    </div>
  );
}
