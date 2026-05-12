"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Calendar, CheckCircle2, Image, LineChart } from "lucide-react";

import {
  DkCard,
  DkCardContent,
  DkPageHeader,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface Counts {
  pendingApprovals: number;
  upcomingPosts: number;
  galleryCount: number;
}

export default function ClientPortalHome() {
  const { currentOrg } = useOrg();
  const [counts, setCounts] = useState<Counts>({
    pendingApprovals: 0,
    upcomingPosts: 0,
    galleryCount: 0,
  });

  useEffect(() => {
    if (!currentOrg) return;
    // Best-effort counts; not all endpoints may be present, so each
    // fetch falls back to 0 silently.
    const headers = { Authorization: `Bearer ${getToken()}` };
    Promise.all([
      fetch(`/api/v1/approvals?organization_id=${currentOrg.id}&status=pending`, {
        headers,
      })
        .then((r) => (r.ok ? r.json() : { items: [] }))
        .then((j) => (Array.isArray(j) ? j.length : (j.items?.length ?? 0))),
      fetch(`/api/v1/scheduled-posts?organization_id=${currentOrg.id}`, {
        headers,
      })
        .then((r) => (r.ok ? r.json() : []))
        .then((j: { status: string }[]) =>
          (Array.isArray(j) ? j : []).filter(
            (p) => p.status === "queued" || p.status === "publishing",
          ).length,
        ),
      fetch(`/api/v1/assets?organization_id=${currentOrg.id}`, { headers })
        .then((r) => (r.ok ? r.json() : []))
        .then((j: unknown[]) => (Array.isArray(j) ? j.length : 0)),
    ]).then(([approvals, posts, gallery]) =>
      setCounts({
        pendingApprovals: approvals,
        upcomingPosts: posts,
        galleryCount: gallery,
      }),
    );
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Client Portal"
        title={`Welcome${currentOrg ? `, ${currentOrg.name}` : ""}`}
        description="The work your agency has prepared, organized for review. Approve, browse, and follow what's going live."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Link href="/client/approvals">
          <DkCard hover className="h-full">
            <DkCardContent className="flex flex-col gap-2 py-5">
              <div className="flex items-center justify-between">
                <CheckCircle2 className="h-5 w-5 text-brand" />
                <ArrowRight className="h-4 w-4 text-[var(--dk-fg-2)]" />
              </div>
              <p className="text-sm text-[var(--dk-fg-2)]">Pending approvals</p>
              <p className="font-display text-2xl font-semibold">
                {counts.pendingApprovals}
              </p>
            </DkCardContent>
          </DkCard>
        </Link>
        <Link href="/client/schedule">
          <DkCard hover className="h-full">
            <DkCardContent className="flex flex-col gap-2 py-5">
              <div className="flex items-center justify-between">
                <Calendar className="h-5 w-5 text-brand" />
                <ArrowRight className="h-4 w-4 text-[var(--dk-fg-2)]" />
              </div>
              <p className="text-sm text-[var(--dk-fg-2)]">Upcoming posts</p>
              <p className="font-display text-2xl font-semibold">
                {counts.upcomingPosts}
              </p>
            </DkCardContent>
          </DkCard>
        </Link>
        <Link href="/client/content">
          <DkCard hover className="h-full">
            <DkCardContent className="flex flex-col gap-2 py-5">
              <div className="flex items-center justify-between">
                <Image className="h-5 w-5 text-brand" />
                <ArrowRight className="h-4 w-4 text-[var(--dk-fg-2)]" />
              </div>
              <p className="text-sm text-[var(--dk-fg-2)]">Approved content</p>
              <p className="font-display text-2xl font-semibold">
                {counts.galleryCount}
              </p>
            </DkCardContent>
          </DkCard>
        </Link>
      </div>

      <DkCard>
        <DkCardContent className="flex items-center justify-between py-5">
          <div>
            <p className="font-semibold text-ink">Analytics summary</p>
            <p className="text-sm text-[var(--dk-fg-2)]">
              30-day touchpoints + conversions + revenue
            </p>
          </div>
          <Link href="/client/analytics">
            <span className="inline-flex items-center gap-1 text-sm text-brand hover:text-[var(--dk-purple-900)]">
              View <LineChart className="h-4 w-4" />
            </span>
          </Link>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
