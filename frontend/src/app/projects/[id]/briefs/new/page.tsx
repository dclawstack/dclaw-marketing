"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
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

const PRESETS = [
  {
    label: "Product launch",
    body: `## Objective\nDrive awareness + signups for [product] launch.\n\n## Hypothesis\nOur target persona will respond to [angle].\n\n## Channels\n- LinkedIn\n- X\n- Bluesky\n- Newsletter\n\n## KPIs\n- Signups\n- Sign-up CTR\n- Cost per signup`,
  },
  {
    label: "SEO refresh",
    body: `## Objective\nReclaim top-10 rankings for [cluster].\n\n## Hypothesis\nUpdated content + internal-linking will move us from #14 → #6.\n\n## Tasks\n- Audit existing pages\n- Topic-cluster planner\n- Re-publish + internal links\n- Track ranking deltas`,
  },
  {
    label: "Newsletter reboot",
    body: `## Objective\n2x open-rate on the monthly newsletter.\n\n## Tactics\n- Stronger subject lines (A/B 4 variants)\n- Shorter sections, more visuals\n- One CTA per issue\n\n## KPIs\n- Open rate\n- Click-through rate\n- Unsubscribe rate`,
  },
];

export default function NewBriefPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { currentOrg } = useOrg();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState(PRESETS[0].body);
  const [objective, setObjective] = useState("");
  const [persona, setPersona] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!currentOrg) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(
        `/api/v1/orgs/${currentOrg.id}/projects/${id}/briefs`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            title,
            body_markdown: body,
            objective: objective || null,
            persona: persona || null,
          }),
        },
      );
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }
      router.push(`/projects/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save brief.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 3 — Briefs"
        title="New brief"
        description="The brief is what an agent reads to plan a campaign. Markdown body + a few structured fields. Pick a template to start, then edit."
        actions={
          <DkButton onClick={submit} disabled={saving || !title} loading={saving}>
            <Save className="h-4 w-4" />
            Save brief
          </DkButton>
        }
      />

      <div className="flex gap-2 flex-wrap">
        {PRESETS.map((p) => (
          <DkButton
            key={p.label}
            size="sm"
            variant="secondary"
            onClick={() => setBody(p.body)}
          >
            {p.label}
          </DkButton>
        ))}
      </div>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Structured fields</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <div>
            <DkLabel htmlFor="title" required>Title</DkLabel>
            <DkInput
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Q3 product launch"
            />
          </div>
          <div>
            <DkLabel htmlFor="obj">Objective</DkLabel>
            <DkInput
              id="obj"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="Drive 500 signups in 30 days"
            />
          </div>
          <div>
            <DkLabel htmlFor="persona">Target persona</DkLabel>
            <DkInput
              id="persona"
              value={persona}
              onChange={(e) => setPersona(e.target.value)}
              placeholder="Senior agency owner, 10+ years, US/UK"
            />
          </div>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Brief body (Markdown)</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            spellCheck={false}
            rows={18}
            className="w-full font-mono text-sm rounded-md border border-[var(--dk-border-strong)] px-3 py-2 focus-visible:outline-none focus-visible:border-brand"
          />
          {error && (
            <p className="mt-2 rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]">
              {error}
            </p>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
