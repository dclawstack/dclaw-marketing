"use client";

import Link from "next/link";
import { Building2, Plus } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";

export default function OrgsListPage() {
  const { orgs, loading, error } = useOrg();

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace"
        title="Organizations"
        description="Every brand kit, project, knowledge base, and connected social account is scoped to an Organization. Create as many as you need."
        actions={
          <Link href="/orgs/new">
            <DkButton>
              <Plus className="h-4 w-4" />
              New Organization
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
            <DkCard key={i}>
              <DkCardContent className="flex flex-col gap-3 py-6">
                <DkSkeleton className="h-5 w-2/3" />
                <DkSkeleton className="h-4 w-full" />
                <DkSkeleton className="h-4 w-4/5" />
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      ) : orgs.length === 0 ? (
        <DkEmptyState
          icon={<Building2 className="h-6 w-6" />}
          title="No organizations yet"
          description="An organization is the top container for your brand kit, knowledge base, projects, and connected accounts. Start with one for the company you're working in."
          actions={
            <Link href="/orgs/new">
              <DkButton withArrow>Create Your First Organization</DkButton>
            </Link>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {orgs.map((o) => (
            <Link key={o.id} href={`/orgs/${o.id}`} className="block group">
              <DkCard hover className="h-full">
                <DkCardContent className="flex flex-col gap-3 py-6">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand">
                        <Building2 className="h-5 w-5" />
                      </div>
                      <div className="flex flex-col">
                        <h3 className="font-display text-lg font-semibold leading-snug text-ink group-hover:text-brand transition-colors duration-fast">
                          {o.name}
                        </h3>
                        <span className="text-xs font-mono text-[var(--dk-fg-2)]">
                          {o.slug}
                        </span>
                      </div>
                    </div>
                    {o.is_external && (
                      <DkBadge tone="info">external</DkBadge>
                    )}
                  </div>
                  {o.description && (
                    <p className="text-sm leading-relaxed text-[var(--dk-fg-1)] line-clamp-3">
                      {o.description}
                    </p>
                  )}
                </DkCardContent>
              </DkCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
