"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Building2,
  Palette,
  BookOpen,
  Target,
  FolderKanban,
  Users,
} from "lucide-react";

import {
  DkBadge,
  DkBreadcrumb,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { Organization, getOrg } from "@/lib/api";

interface QuickLink {
  label: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
  soon?: boolean;
}

export default function OrgDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
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

  const links: QuickLink[] = org
    ? [
        {
          label: "Members",
          description: "Invite teammates; assign supervision-scope roles.",
          href: `/orgs/${org.id}/members`,
          icon: Users,
          soon: true,
        },
        {
          label: "Brand Kit",
          description: "Palette, typography, voice, do-say / don't-say, personas.",
          href: `/orgs/${org.id}/brand`,
          icon: Palette,
          soon: true,
        },
        {
          label: "Knowledge",
          description: "Ingest URLs, files, repos into the org's knowledge graph.",
          href: `/orgs/${org.id}/knowledge`,
          icon: BookOpen,
          soon: true,
        },
        {
          label: "Goals & Autonomy",
          description: "Objectives, ICPs, budgets, per-action-class trust modes.",
          href: `/orgs/${org.id}/goals`,
          icon: Target,
          soon: true,
        },
        {
          label: "Projects",
          description: "Time-boxed initiatives within this organization.",
          href: `/orgs/${org.id}/projects`,
          icon: FolderKanban,
          soon: true,
        },
      ]
    : [];

  if (loading) {
    return (
      <div className="flex flex-col gap-6">
        <DkSkeleton className="h-8 w-64" />
        <DkSkeleton className="h-16 w-full" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <DkSkeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !org) {
    return (
      <div className="flex flex-col gap-4">
        <DkBreadcrumb
          items={[{ label: "Organizations", href: "/orgs" }, { label: "Error" }]}
        />
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error ?? "Organization not found."}
        </div>
        <div>
          <DkButton variant="secondary" onClick={() => router.push("/orgs")}>
            Back to organizations
          </DkButton>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <DkBreadcrumb
        items={[
          { label: "Organizations", href: "/orgs" },
          { label: org.name },
        ]}
      />

      <DkPageHeader
        eyebrow="Organization"
        title={org.name}
        description={
          org.description ??
          "No description yet. Use the Edit action to add one."
        }
        actions={
          <div className="flex items-center gap-3">
            {org.is_external && <DkBadge tone="info">external</DkBadge>}
            <DkButton variant="secondary" disabled>
              Edit
            </DkButton>
          </div>
        }
      />

      <div className="flex items-center gap-2 text-sm text-[var(--dk-fg-2)]">
        <Building2 className="h-4 w-4" />
        <span className="font-mono">{org.slug}</span>
      </div>

      <div className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">
          Set Up This Organization
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {links.map((l) => {
            const Icon = l.icon;
            const card = (
              <DkCard hover={!l.disabled && !l.soon} className="h-full">
                <DkCardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-md bg-[var(--dk-purple-50)] text-brand shrink-0">
                      <Icon className="h-5 w-5" />
                    </div>
                    {l.soon && <DkBadge tone="brand">soon</DkBadge>}
                  </div>
                  <DkCardTitle className="text-base">{l.label}</DkCardTitle>
                  <DkCardDescription>{l.description}</DkCardDescription>
                </DkCardHeader>
                <DkCardContent />
              </DkCard>
            );
            return l.soon ? (
              <div
                key={l.label}
                aria-disabled
                className="cursor-not-allowed opacity-70"
              >
                {card}
              </div>
            ) : (
              <a key={l.label} href={l.href} className="block">
                {card}
              </a>
            );
          })}
        </div>
      </div>
    </div>
  );
}
