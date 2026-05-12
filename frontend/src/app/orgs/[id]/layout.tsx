"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import {
  Building2,
  Palette,
  BookOpen,
  Target,
  FolderKanban,
  Users,
} from "lucide-react";

import { DkBreadcrumb, DkSkeleton } from "@/components/dk";
import { Organization, getOrg } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Tab {
  label: string;
  href: (orgId: string) => string;
  match: (pathname: string, orgId: string) => boolean;
  icon: React.ComponentType<{ className?: string }>;
}

const TABS: Tab[] = [
  {
    label: "Overview",
    href: (id) => `/orgs/${id}`,
    match: (p, id) => p === `/orgs/${id}`,
    icon: Building2,
  },
  {
    label: "Members",
    href: (id) => `/orgs/${id}/members`,
    match: (p, id) => p.startsWith(`/orgs/${id}/members`),
    icon: Users,
  },
  {
    label: "Brand",
    href: (id) => `/orgs/${id}/brand`,
    match: (p, id) => p.startsWith(`/orgs/${id}/brand`),
    icon: Palette,
  },
  {
    label: "Knowledge",
    href: (id) => `/orgs/${id}/knowledge`,
    match: (p, id) => p.startsWith(`/orgs/${id}/knowledge`),
    icon: BookOpen,
  },
  {
    label: "Goals",
    href: (id) => `/orgs/${id}/goals`,
    match: (p, id) => p.startsWith(`/orgs/${id}/goals`),
    icon: Target,
  },
  {
    label: "Projects",
    href: (id) => `/orgs/${id}/projects`,
    match: (p, id) => p.startsWith(`/orgs/${id}/projects`),
    icon: FolderKanban,
  },
];

export default function OrgDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams<{ id: string }>();
  const pathname = usePathname() ?? "";
  const orgId = params.id;
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!orgId) return;
    let cancelled = false;
    setLoading(true);
    getOrg(orgId)
      .then((o) => {
        if (!cancelled) setOrg(o);
      })
      .catch(() => {
        if (!cancelled) setOrg(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgId]);

  return (
    <div className="flex flex-col gap-6">
      <DkBreadcrumb
        items={[
          { label: "Workspaces", href: "/orgs" },
          { label: org?.name ?? (loading ? "…" : "Organization") },
        ]}
      />

      <div className="flex flex-col gap-1">
        <div className="text-xs uppercase tracking-wider text-[var(--dk-fg-3)]">
          {org?.is_external ? "External · Client Org" : "Workspace"}
        </div>
        <h1 className="font-display text-3xl font-semibold text-ink">
          {loading ? <DkSkeleton className="h-9 w-64" /> : org?.name ?? "Not found"}
        </h1>
        {org?.description ? (
          <p className="text-sm text-[var(--dk-fg-2)] max-w-prose">
            {org.description}
          </p>
        ) : null}
      </div>

      {/* Tab bar */}
      <nav
        aria-label="Organization sections"
        className="flex flex-wrap gap-1 border-b border-[var(--dk-border)]"
      >
        {TABS.map((t) => {
          const active = t.match(pathname, orgId);
          const Icon = t.icon;
          return (
            <Link
              key={t.label}
              href={t.href(orgId)}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
                active
                  ? "border-brand text-ink"
                  : "border-transparent text-[var(--dk-fg-2)] hover:text-ink hover:border-[var(--dk-border-strong)]",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </Link>
          );
        })}
      </nav>

      <div>{children}</div>
    </div>
  );
}
