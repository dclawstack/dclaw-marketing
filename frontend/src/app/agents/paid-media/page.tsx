"use client";

import { DollarSign, ImagePlus, TrendingUp } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function PaidMediaStationPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · Paid Media Specialist"
        title="Spend Station"
        description="The Paid Media agent generates ad creative, runs A/B tests, shifts budget via a bandit policy, and kills underperforming sets. Every budget move runs through your autonomy posture — large shifts are hard-gate by default."
        actions={<DkBadge tone="brand">v0.2 · coming online</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <DkCard>
          <DkCardHeader>
            <ImagePlus className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Ad Creative</DkCardTitle>
            <DkCardDescription>
              Generates image + video + copy variants per platform spec.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <TrendingUp className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Bandit Policy</DkCardTitle>
            <DkCardDescription>
              Thompson sampling across active variants once minimum impressions
              are reached.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <DollarSign className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Budget Caps</DkCardTitle>
            <DkCardDescription>
              Hard limits from the org's autonomy posture — agent escalates
              before exceeding.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
