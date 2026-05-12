"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { FolderKanban, Plus } from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { Organization, Project, getOrg, listProjects } from "@/lib/api";

const STATUS_TONE = {
  active: "success",
  paused: "warning",
  archived: "neutral",
} as const;

export default function ProjectsListPage() {
  const params = useParams<{ id: string }>();
  const orgId = params?.id ?? "";

  const [org, setOrg] = useState<Organization | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);
    try {
      const [o, p] = await Promise.all([getOrg(orgId), listProjects(orgId)]);
      setOrg(o);
      setProjects(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          {
            label: org?.name ?? "…",
            href: orgId ? `/orgs/${orgId}` : "/orgs",
          },
          { label: "Projects" },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization · Initiatives"
        title="Projects"
        description="Time-boxed initiatives inside this organization. Each project carries its own brief, team assignments, channel selection, and trust-mode overrides."
        actions={
          <Link href={`/orgs/${orgId}/projects/new`}>
            <DkButton>
              <Plus className="h-4 w-4" />
              New Project
            </DkButton>
          </Link>
        }
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <DkSkeleton key={i} className="h-36" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <DkEmptyState
          icon={<FolderKanban className="h-6 w-6" />}
          title="No projects yet"
          description="A Project is a time-boxed initiative — a campaign launch, a content sprint, a brand refresh. Start with one to organize agent runs and approvals."
          actions={
            <Link href={`/orgs/${orgId}/projects/new`}>
              <DkButton withArrow>Create Your First Project</DkButton>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <DkCard key={p.id} hover className="h-full">
              <DkCardContent className="flex flex-col gap-3 py-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand">
                      <FolderKanban className="h-5 w-5" />
                    </div>
                    <div className="flex flex-col">
                      <h3 className="font-display text-lg font-semibold leading-snug text-ink">
                        {p.name}
                      </h3>
                      <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                        {p.slug}
                      </span>
                    </div>
                  </div>
                  <DkBadge tone={STATUS_TONE[p.status]}>{p.status}</DkBadge>
                </div>
                {p.description && (
                  <p className="text-sm leading-relaxed text-[var(--dk-fg-1)] line-clamp-3">
                    {p.description}
                  </p>
                )}
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}
    </div>
  );
}
