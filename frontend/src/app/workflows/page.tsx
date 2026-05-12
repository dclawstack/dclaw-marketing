"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Copy, FileBox, Workflow } from "lucide-react";

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
  is_template?: boolean;
  cloned_from_workflow_id?: string | null;
}

interface WorkflowTemplateRow {
  id: string;
  organization_id: string;
  slug: string;
  name: string;
  description: string | null;
  is_template: boolean;
}

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
  if (res.status === 204) return undefined as T;
  return res.json();
}

export default function WorkflowsListPage() {
  const { currentOrg, loading: orgLoading } = useOrg();
  const [rows, setRows] = useState<WorkflowRow[]>([]);
  const [templates, setTemplates] = useState<WorkflowTemplateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cloningId, setCloningId] = useState<string | null>(null);

  async function refresh(orgId: string) {
    setLoading(true);
    setError(null);
    try {
      const [list, tpls] = await Promise.all([
        authFetch<WorkflowRow[]>(`/api/v1/orgs/${orgId}/workflows`),
        authFetch<WorkflowTemplateRow[]>(
          `/api/v1/orgs/${orgId}/workflow-templates`,
        ),
      ]);
      setRows(list);
      setTemplates(tpls);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workflows.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!currentOrg) {
      setRows([]);
      setTemplates([]);
      setLoading(false);
      return;
    }
    void refresh(currentOrg.id);
  }, [currentOrg]);

  async function cloneTemplate(tpl: WorkflowTemplateRow) {
    if (!currentOrg) return;
    const slug = prompt(
      "Slug for the clone in this Org:",
      `${tpl.slug}-${Date.now().toString(36)}`,
    );
    if (!slug) return;
    setCloningId(tpl.id);
    try {
      await authFetch(
        `/api/v1/orgs/${tpl.organization_id}/workflows/${tpl.id}/clone`,
        {
          method: "POST",
          body: JSON.stringify({
            target_organization_id: currentOrg.id,
            slug,
            name: `${tpl.name} (cloned)`,
          }),
        },
      );
      await refresh(currentOrg.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Clone failed.");
    } finally {
      setCloningId(null);
    }
  }

  async function toggleTemplate(w: WorkflowRow) {
    if (!currentOrg) return;
    const next = !w.is_template;
    try {
      await authFetch(
        `/api/v1/orgs/${currentOrg.id}/workflows/${w.id}/template?is_template=${next}`,
        { method: "PATCH" },
      );
      await refresh(currentOrg.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Template toggle failed.");
    }
  }

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
      ) : (
        <>
          {/* Templates section */}
          {templates.length > 0 ? (
            <div className="flex flex-col gap-3">
              <h2 className="font-display text-lg font-semibold text-ink">
                <FileBox className="inline-block h-5 w-5 mr-1 -mt-0.5" />
                Templates
                <span className="ml-2 text-sm font-normal text-[var(--dk-fg-2)]">
                  ({templates.length})
                </span>
              </h2>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {templates.map((t) => (
                  <DkCard key={t.id}>
                    <DkCardContent className="flex flex-col gap-2 py-4">
                      <div className="font-semibold">{t.name}</div>
                      <div className="text-xs font-mono opacity-60">
                        {t.slug}
                      </div>
                      {t.description ? (
                        <div className="text-sm opacity-80">
                          {t.description}
                        </div>
                      ) : null}
                      <div className="flex gap-2 pt-2">
                        <DkButton
                          size="sm"
                          onClick={() => cloneTemplate(t)}
                          loading={cloningId === t.id}
                        >
                          <Copy className="h-3.5 w-3.5" /> Clone to this Org
                        </DkButton>
                        <Link href={`/workflows/${t.id}`}>
                          <DkButton size="sm" variant="ghost">
                            Open
                          </DkButton>
                        </Link>
                      </div>
                    </DkCardContent>
                  </DkCard>
                ))}
              </div>
            </div>
          ) : null}

          {rows.length === 0 ? (
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
                      <DkTableCell className="font-semibold">
                        {w.name}
                        {w.is_template ? (
                          <DkBadge tone="brand" className="ml-2">
                            template
                          </DkBadge>
                        ) : null}
                        {w.cloned_from_workflow_id ? (
                          <DkBadge tone="info" className="ml-2">
                            cloned
                          </DkBadge>
                        ) : null}
                      </DkTableCell>
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
                      <DkTableCell className="text-right space-x-1">
                        <DkButton
                          size="sm"
                          variant="ghost"
                          onClick={() => toggleTemplate(w)}
                          aria-label={
                            w.is_template ? "Unmark template" : "Mark as template"
                          }
                        >
                          {w.is_template ? "Unmark" : "Mark template"}
                        </DkButton>
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
        </>
      )}
    </div>
  );
}
