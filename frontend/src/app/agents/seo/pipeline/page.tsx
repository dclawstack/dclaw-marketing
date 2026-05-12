"use client";

import { useState } from "react";
import { Search, FileText, Sparkles } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkTextarea,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

interface KeywordItem {
  keyword: string;
  score: number;
  rationale: string;
}

interface OutlineSection {
  heading: string;
  bullets: string[];
}

interface Outline {
  keyword: string;
  title: string;
  meta_description: string;
  target_word_count: number;
  sections: OutlineSection[];
}

export default function SeoPipelinePage() {
  const [stage, setStage] = useState<"keywords" | "outline" | "draft">("keywords");

  // Brand context
  const [voice, setVoice] = useState("direct, practical, no fluff");
  const [audience, setAudience] = useState(
    "B2B founders running a marketing team of 1–3",
  );
  const [pillars, setPillars] = useState(
    "agentic workflows, lead enrichment, attribution",
  );

  // Stage state
  const [keywords, setKeywords] = useState<KeywordItem[]>([]);
  const [pickedKw, setPickedKw] = useState("");
  const [outline, setOutline] = useState<Outline | null>(null);
  const [draftMd, setDraftMd] = useState("");
  const [busy, setBusy] = useState(false);

  function brandContext() {
    return {
      voice_summary: voice,
      audience,
      pillars: pillars.split(",").map((s) => s.trim()).filter(Boolean),
    };
  }

  async function runKeywords() {
    setBusy(true);
    try {
      const r = await fetch("/api/v1/seo/pipeline/keywords", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ brand_context: brandContext(), count: 8 }),
      });
      const data = await r.json();
      setKeywords(data.items || []);
    } finally {
      setBusy(false);
    }
  }

  async function runOutline(kw: string) {
    setPickedKw(kw);
    setBusy(true);
    try {
      const r = await fetch("/api/v1/seo/pipeline/outline", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ keyword: kw, target_word_count: 1200 }),
      });
      setOutline(await r.json());
      setStage("outline");
    } finally {
      setBusy(false);
    }
  }

  async function runDraft() {
    if (!outline) return;
    setBusy(true);
    try {
      const r = await fetch("/api/v1/seo/pipeline/draft", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          keyword: pickedKw,
          outline,
          brand_context: brandContext(),
        }),
      });
      const data = await r.json();
      setDraftMd(data.markdown || "");
      setStage("draft");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme H2"
        title="SEO blog pipeline"
        description="Walks keyword → outline → draft. Each step is deterministic in v0.2.x; agent-driven once the SEO Agent ships."
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Brand context</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="grid gap-3 sm:grid-cols-3">
          <div>
            <DkLabel htmlFor="bp-voice">Voice</DkLabel>
            <DkInput
              id="bp-voice"
              value={voice}
              onChange={(e) => setVoice(e.target.value)}
            />
          </div>
          <div>
            <DkLabel htmlFor="bp-aud">Audience</DkLabel>
            <DkInput
              id="bp-aud"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />
          </div>
          <div>
            <DkLabel htmlFor="bp-pillars">Pillars (comma-sep)</DkLabel>
            <DkInput
              id="bp-pillars"
              value={pillars}
              onChange={(e) => setPillars(e.target.value)}
            />
          </div>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>1. Keyword candidates</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-3">
          <DkButton onClick={runKeywords} disabled={busy}>
            <Search className="h-4 w-4" />
            Generate keywords
          </DkButton>
          {keywords.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {keywords.map((k) => (
                <button
                  key={k.keyword}
                  type="button"
                  onClick={() => runOutline(k.keyword)}
                  disabled={busy}
                  className="flex items-start justify-between gap-3 rounded-md border border-[var(--dk-border)] bg-white p-3 text-left hover:border-brand transition-colors"
                >
                  <div>
                    <p className="font-medium text-sm">{k.keyword}</p>
                    <p className="text-xs text-[var(--dk-fg-2)]">
                      {k.rationale}
                    </p>
                  </div>
                  <DkBadge tone={k.score >= 80 ? "success" : "neutral"}>
                    {k.score}
                  </DkBadge>
                </button>
              ))}
            </div>
          )}
        </DkCardContent>
      </DkCard>

      {outline && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>2. Outline for &ldquo;{pickedKw}&rdquo;</DkCardTitle>
          </DkCardHeader>
          <DkCardContent className="flex flex-col gap-3">
            <p className="text-sm font-medium">{outline.title}</p>
            <p className="text-xs text-[var(--dk-fg-2)]">
              {outline.meta_description}
            </p>
            <ol className="flex flex-col gap-2 pl-4 list-decimal">
              {outline.sections.map((s, i) => (
                <li key={i} className="text-sm">
                  <p className="font-medium">{s.heading}</p>
                  <ul className="pl-4 list-disc text-[var(--dk-fg-2)]">
                    {s.bullets.map((b, j) => (
                      <li key={j}>{b}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
            <DkButton onClick={runDraft} disabled={busy}>
              <FileText className="h-4 w-4" />
              Draft the post
            </DkButton>
          </DkCardContent>
        </DkCard>
      )}

      {draftMd && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>3. Draft</DkCardTitle>
          </DkCardHeader>
          <DkCardContent>
            <DkTextarea
              value={draftMd}
              onChange={(e) => setDraftMd(e.target.value)}
              rows={20}
              className="font-mono text-xs"
            />
          </DkCardContent>
        </DkCard>
      )}
    </div>
  );
}
