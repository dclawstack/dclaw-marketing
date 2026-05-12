"use client";

import { AlertTriangle, BarChart3, FileText } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function AnalystStationPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · Analyst"
        title="Insights Station"
        description="The Analyst agent computes daily rollups, detects anomalies, and writes the Monday-morning narrative report. Read-only by design — no outbound actions, only insights."
        actions={<DkBadge tone="brand">v0.2 · coming online</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <DkCard>
          <DkCardHeader>
            <BarChart3 className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Daily Rollups</DkCardTitle>
            <DkCardDescription>
              Per-channel reach, engagement, conversions, spend, CAC.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <AlertTriangle className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Anomaly Detection</DkCardTitle>
            <DkCardDescription>
              Flags step-changes (3σ on rolling baseline) with attribution to
              the most likely cause.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <FileText className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Weekly Narrative</DkCardTitle>
            <DkCardDescription>
              Monday-morning report — what worked, what didn't, what to test
              next.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
