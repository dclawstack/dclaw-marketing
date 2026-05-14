"use client";

/**
 * AEO Score widget (S4-K3) — embedded under /agents/seo.
 *
 * Paste a page's HTML/markdown, see the score + weak-spots + an
 * optional LLM-driven rewrite via /api/v1/aeo/suggest-rewrite.
 */

import { useState } from "react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkTextarea,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface WeakSpot {
  name: string;
  passes: boolean;
  weight: number;
  note: string;
}

interface ScoreResult {
  score: number;
  weak_spots: WeakSpot[];
  rewrite?: string | null;
}

export function AeoWidget({ orgId }: { orgId?: string }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [busy, setBusy] = useState<"score" | "fix" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const call = async (path: string, body: object) => {
    const r = await fetch(`${API}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getToken()}`,
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
    return r.json();
  };

  const score = async () => {
    setBusy("score");
    setError(null);
    try {
      const r = await call("/api/v1/aeo/score", { text });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Score failed");
    } finally {
      setBusy(null);
    }
  };

  const fix = async () => {
    setBusy("fix");
    setError(null);
    try {
      const r = await call("/api/v1/aeo/suggest-rewrite", {
        text,
        organization_id: orgId ?? null,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fix failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <DkCard>
      <DkCardHeader>
        <DkCardTitle>AEO score</DkCardTitle>
      </DkCardHeader>
      <DkCardContent className="space-y-3">
        <DkTextarea
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste page HTML or markdown…"
        />
        <div className="flex gap-2">
          <DkButton onClick={score} disabled={busy !== null || !text.trim()}>
            {busy === "score" ? "Scoring…" : "Score"}
          </DkButton>
          <DkButton
            variant="secondary"
            onClick={fix}
            disabled={busy !== null || !text.trim()}
          >
            {busy === "fix" ? "Rewriting…" : "Suggest rewrite"}
          </DkButton>
        </div>
        {error && <div className="text-rose-600 text-sm">{error}</div>}
        {result && (
          <div className="space-y-2 text-sm">
            <div className="text-lg font-medium">
              Score: {result.score}/100
            </div>
            {result.weak_spots.length > 0 && (
              <ul className="list-disc pl-5 text-xs">
                {result.weak_spots.map((w) => (
                  <li key={w.name}>
                    <span className="font-medium">{w.name}</span> (-{w.weight}):{" "}
                    {w.note}
                  </li>
                ))}
              </ul>
            )}
            {result.rewrite && (
              <div>
                <div className="text-xs text-slate-500 mt-2">Rewrite</div>
                <pre className="whitespace-pre-wrap text-xs bg-slate-50 p-2 rounded">
                  {result.rewrite}
                </pre>
              </div>
            )}
          </div>
        )}
      </DkCardContent>
    </DkCard>
  );
}
