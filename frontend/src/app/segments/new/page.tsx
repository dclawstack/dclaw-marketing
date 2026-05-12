"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Save } from "lucide-react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

const PRESETS: { label: string; dsl: string }[] = [
  {
    label: "MQL leads",
    dsl: JSON.stringify({ stage: "mql" }, null, 2),
  },
  {
    label: "High-scoring leads (≥60)",
    dsl: JSON.stringify({ score__gte: 60 }, null, 2),
  },
  {
    label: "Recent activity (any stage)",
    dsl: JSON.stringify(
      { any_of: [{ stage: "mql" }, { stage: "sql" }, { stage: "customer" }] },
      null,
      2,
    ),
  },
];

export default function NewSegmentPage() {
  const router = useRouter();
  const { currentOrg } = useOrg();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [dsl, setDsl] = useState(PRESETS[0].dsl);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!currentOrg) return;
    setSaving(true);
    setError(null);
    try {
      const parsed = JSON.parse(dsl);
      const res = await fetch(
        `/api/v1/orgs/${currentOrg.id}/segments`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            slug: slug || name.toLowerCase().replace(/\s+/g, "-"),
            name,
            filter_dsl_json: parsed,
          }),
        },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }
      router.push("/segments");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save segment.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 7 — Segments"
        title="New segment"
        description="A segment is a saved filter. Used by email campaigns + ad custom-audience syncs. The DSL is a flat dict — keys with comparator suffixes (__gte, __in, __contains, __startswith) plus an optional any_of OR group."
        actions={
          <DkButton onClick={submit} disabled={saving || !name} loading={saving}>
            <Save className="h-4 w-4" />
            Save segment
          </DkButton>
        }
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Identification</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div>
            <DkLabel htmlFor="name" required>Name</DkLabel>
            <DkInput
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="High-intent MQLs"
            />
          </div>
          <div>
            <DkLabel htmlFor="slug">Slug (optional)</DkLabel>
            <DkInput
              id="slug"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              placeholder="high-intent-mqls"
            />
          </div>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Filter DSL</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div className="flex gap-2 flex-wrap">
            {PRESETS.map((p) => (
              <DkButton
                key={p.label}
                size="sm"
                variant="secondary"
                onClick={() => setDsl(p.dsl)}
              >
                {p.label}
              </DkButton>
            ))}
          </div>
          <textarea
            value={dsl}
            onChange={(e) => setDsl(e.target.value)}
            spellCheck={false}
            rows={12}
            className="font-mono text-sm rounded-md border border-[var(--dk-border-strong)] px-3 py-2 focus-visible:outline-none focus-visible:border-brand"
          />
          {error && (
            <p className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]">
              {error}
            </p>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
