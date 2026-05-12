"use client";

import { AlertTriangle, DollarSign, TrendingUp } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function CostsPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · Theme I3"
        title="Cost Tracking"
        description="Aggregate per-workspace LLM / image / video / voice / ad-platform provider spend. Daily budget caps and soft + hard alert thresholds."
        actions={<DkBadge tone="brand">v0.2 · data model live</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <DkCard>
          <DkCardHeader>
            <DollarSign className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Per-provider spend</DkCardTitle>
            <DkCardDescription>
              Anthropic / OpenAI / Replicate / Runway / ElevenLabs / Suno /
              Cartesia / Deepgram — each provider's rolling daily + monthly.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <TrendingUp className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Daily Trend</DkCardTitle>
            <DkCardDescription>
              30-day stacked area chart of spend by category (llm / image /
              video / voice / music / ads / other).
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <AlertTriangle className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Caps + Alerts</DkCardTitle>
            <DkCardDescription>
              Soft cap → email at threshold. Hard cap → block further agent
              dispatches and require admin override.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
