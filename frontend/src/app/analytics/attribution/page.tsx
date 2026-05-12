"use client";

import { BarChart3, GitBranch, Sparkles, TrendingUp } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function AttributionPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Analytics · Theme E6"
        title="Attribution"
        description="Touchpoint-level attribution from raw events to closed-won revenue. First-touch, last-touch, linear, time-decay, and Markov models compute daily — drill into any conversion to see the contributing touch sequence."
        actions={<DkBadge tone="brand">v0.2 · data model live</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <DkCard>
          <DkCardHeader>
            <BarChart3 className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Sankey View</DkCardTitle>
            <DkCardDescription>
              Channel → campaign → conversion flow, sized by attributed amount.
              Lands once the attribution job wires up.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <GitBranch className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Multi-Model Compare</DkCardTitle>
            <DkCardDescription>
              Compare credit across 5 attribution models side-by-side for any
              conversion window.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <TrendingUp className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Cohort Tables</DkCardTitle>
            <DkCardDescription>
              First-touch month vs. conversion month, with conversion rate +
              average revenue.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <Sparkles className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Analyst Agent Narrative</DkCardTitle>
            <DkCardDescription>
              Plain-English summary of attribution shifts week-over-week,
              produced by the Analyst Agent (Phase 9.x).
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
