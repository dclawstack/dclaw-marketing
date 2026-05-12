"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChevronRight, Play } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface RunRow {
  id: string;
  workflow_id: string;
  status: string;
  deferred_reason: string | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export default function WorkflowDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { currentOrg } = useOrg();
  const [runs, setRuns] = useState<RunRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [kicking, setKicking] = useState(false);

  async function load() {
    if (!currentOrg) return;
    setLoading(true);
    const res = await fetch(
      `/api/v1/orgs/${currentOrg.id}/workflows/${id}/runs`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    );
    if (res.ok) setRuns(await res.json());
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg, id]);

  async function kickRun() {
    if (!currentOrg) return;
    setKicking(true);
    try {
      await fetch(
        `/api/v1/orgs/${currentOrg.id}/workflows/${id}/runs`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ initial_context: {} }),
        },
      );
      await load();
    } finally {
      setKicking(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workflow"
        title="Run history"
        description="Every execution of this workflow's DAG. Click a run to inspect per-node trace + final context."
        actions={
          <DkButton onClick={kickRun} disabled={kicking} loading={kicking}>
            <Play className="h-4 w-4" />
            Start new run
          </DkButton>
        }
      />
      <DkCard>
        <DkCardHeader>
          <DkCardTitle>{runs.length} runs</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="px-0 pt-0">
          {loading ? (
            <div className="px-6 pb-6">
              <DkSkeleton className="h-4 w-2/3" />
            </div>
          ) : runs.length === 0 ? (
            <p className="px-6 pb-6 text-sm text-[var(--dk-fg-2)]">
              No runs yet — click <span className="font-semibold">Start new run</span> above.
            </p>
          ) : (
            <DkTable>
              <DkTableHeader>
                <DkTableRow>
                  <DkTableHead>Started</DkTableHead>
                  <DkTableHead>Status</DkTableHead>
                  <DkTableHead>Deferred reason</DkTableHead>
                  <DkTableHead></DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {runs.map((r) => (
                  <DkTableRow key={r.id}>
                    <DkTableCell className="font-mono text-sm">
                      {new Date(r.started_at).toLocaleString()}
                    </DkTableCell>
                    <DkTableCell>
                      <DkBadge
                        tone={
                          r.status === "completed"
                            ? "success"
                            : r.status === "failed"
                              ? "danger"
                              : r.status === "paused"
                                ? "warning"
                                : "neutral"
                        }
                      >
                        {r.status}
                      </DkBadge>
                    </DkTableCell>
                    <DkTableCell className="text-sm text-[var(--dk-fg-1)]">
                      {r.deferred_reason ?? r.error_message ?? "—"}
                    </DkTableCell>
                    <DkTableCell className="text-right">
                      <Link href={`/workflows/runs/${r.id}`}>
                        <DkButton size="sm" variant="ghost">
                          Trace
                          <ChevronRight className="h-4 w-4" />
                        </DkButton>
                      </Link>
                    </DkTableCell>
                  </DkTableRow>
                ))}
              </DkTableBody>
            </DkTable>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
