"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Workflow } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
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

interface WorkflowRow {
  id: string;
  organization_id: string;
  slug: string;
  name: string;
  description: string | null;
  status: string;
}

export default function WorkflowsListPage() {
  const { currentOrg, loading: orgLoading } = useOrg();
  const [rows, setRows] = useState<WorkflowRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentOrg) {
      setRows([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    fetch(`/api/v1/orgs/${currentOrg.id}/workflows`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.text().then((t) => Promise.reject(new Error(t))),
      )
      .then(setRows)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load workflows."),
      )
      .finally(() => setLoading(false));
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 10 — P"
        title="Workflows"
        description="Visual no-code DAGs of LLM + tool-call + approval nodes. Each workflow can be run on demand; paused runs (approval / branch) resume from the run-detail page."
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      {orgLoading || loading ? (
        <DkCard>
          <DkCardContent className="flex flex-col gap-3 py-6">
            <DkSkeleton className="h-5 w-1/3" />
            <DkSkeleton className="h-4 w-2/3" />
          </DkCardContent>
        </DkCard>
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<Workflow className="h-6 w-6" />}
          title="No workflows yet"
          description="The workflow runner can pause on approval, branch on conditions, and call any MCP tool. Create one via POST /api/v1/workflows."
        />
      ) : (
        <DkCard>
          <DkTable>
            <DkTableHeader>
              <DkTableRow>
                <DkTableHead>Name</DkTableHead>
                <DkTableHead>Slug</DkTableHead>
                <DkTableHead>Status</DkTableHead>
                <DkTableHead></DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {rows.map((w) => (
                <DkTableRow key={w.id}>
                  <DkTableCell className="font-semibold">{w.name}</DkTableCell>
                  <DkTableCell className="font-mono text-sm">
                    {w.slug}
                  </DkTableCell>
                  <DkTableCell>
                    <DkBadge
                      tone={w.status === "active" ? "success" : "neutral"}
                    >
                      {w.status}
                    </DkBadge>
                  </DkTableCell>
                  <DkTableCell className="text-right">
                    <Link href={`/workflows/${w.id}`}>
                      <DkButton size="sm" variant="secondary">
                        Open
                      </DkButton>
                    </Link>
                  </DkTableCell>
                </DkTableRow>
              ))}
            </DkTableBody>
          </DkTable>
        </DkCard>
      )}
    </div>
  );
}
