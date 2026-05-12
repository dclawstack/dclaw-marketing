"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Building2 } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkSkeleton,
} from "@/components/dk";
import { Organization, getOrg } from "@/lib/api";

/**
 * Overview tab — surfaced as the default route under the
 * `/orgs/[id]/layout.tsx` tabbed shell. Renders Org meta + a quick
 * launchpad of the most common next actions.
 */
export default function OrgOverviewTab() {
  const params = useParams<{ id: string }>();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id) return;
    setLoading(true);
    getOrg(params.id)
      .then(setOrg)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load org."),
      )
      .finally(() => setLoading(false));
  }, [params?.id]);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <DkSkeleton key={i} className="h-32" />
        ))}
      </div>
    );
  }

  if (error || !org) {
    return (
      <div
        role="alert"
        className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
      >
        {error ?? "Organization not found."}
      </div>
    );
  }

  const quickActions = [
    { label: "Connect a social channel", href: "/channels" },
    { label: "Add knowledge sources", href: `/orgs/${org.id}/knowledge` },
    { label: "Set goals + autonomy posture", href: `/orgs/${org.id}/goals` },
    { label: "Create a project", href: `/orgs/${org.id}/projects/new` },
    { label: "Invite a teammate", href: `/orgs/${org.id}/members` },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-4 md:grid-cols-3">
        <DkCard>
          <DkCardHeader>
            <DkCardTitle className="text-base">Slug</DkCardTitle>
          </DkCardHeader>
          <DkCardContent>
            <div className="flex items-center gap-2 text-sm font-mono">
              <Building2 className="h-4 w-4 text-brand" />
              {org.slug}
            </div>
          </DkCardContent>
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <DkCardTitle className="text-base">Mode</DkCardTitle>
          </DkCardHeader>
          <DkCardContent>
            <DkBadge tone={org.is_external ? "info" : "brand"}>
              {org.is_external ? "External / Client" : "Internal"}
            </DkBadge>
          </DkCardContent>
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <DkCardTitle className="text-base">Description</DkCardTitle>
          </DkCardHeader>
          <DkCardContent>
            <p className="text-sm opacity-80">
              {org.description || (
                <span className="opacity-60">No description yet.</span>
              )}
            </p>
          </DkCardContent>
        </DkCard>
      </div>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Quick actions</DkCardTitle>
          <DkCardDescription>
            The five highest-leverage moves for a new workspace. Use the tabs
            above to dive into any one in detail.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-wrap gap-2">
          {quickActions.map((a) => (
            <Link
              key={a.href}
              href={a.href}
              className="inline-flex items-center gap-1.5 rounded-md bg-[var(--dk-purple-50)] px-3 py-1.5 text-sm text-brand font-medium hover:bg-[var(--dk-purple-100)] transition-colors"
            >
              {a.label}
            </Link>
          ))}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
