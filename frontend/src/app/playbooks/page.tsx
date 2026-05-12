"use client";

import { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkInput,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface Playbook {
  id: string;
  slug: string;
  name: string;
  kind: string;
  description: string | null;
  body_markdown: string;
}

export default function PlaybooksListPage() {
  const { currentOrg } = useOrg();
  const [all, setAll] = useState<Playbook[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/orgs/${currentOrg.id}/playbooks`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then(setAll)
      .finally(() => setLoading(false));
  }, [currentOrg]);

  const filtered = q
    ? all.filter(
        (p) =>
          p.name.toLowerCase().includes(q.toLowerCase()) ||
          p.slug.toLowerCase().includes(q.toLowerCase()) ||
          (p.description ?? "").toLowerCase().includes(q.toLowerCase()),
      )
    : all;

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 10 — N"
        title="Playbooks"
        description="Reusable prompts, briefs, and SOPs. Agents call these by slug; humans copy-edit the markdown."
      />

      <DkInput
        placeholder="Search by name, slug, or description…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      {loading ? (
        <DkSkeleton className="h-32 w-full" />
      ) : filtered.length === 0 ? (
        <DkEmptyState
          icon={<BookOpen className="h-6 w-6" />}
          title={q ? "No matches" : "No playbooks yet"}
          description={
            q
              ? "Try a different search term."
              : "Create a playbook via POST /api/v1/playbooks. Agents can then call it by slug."
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((p) => (
            <DkCard key={p.id} hover>
              <DkCardContent className="flex flex-col gap-3 py-5">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-display text-lg font-semibold leading-snug text-ink">
                    {p.name}
                  </h3>
                  <DkBadge tone="info">{p.kind}</DkBadge>
                </div>
                <span className="font-mono text-xs text-[var(--dk-fg-2)]">
                  {p.slug}
                </span>
                {p.description && (
                  <p className="text-sm text-[var(--dk-fg-1)] line-clamp-3">
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
