"use client";

import { Plus, Target } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

const PLATFORMS = [
  { id: "meta", label: "Meta Ads", note: "Facebook + Instagram" },
  { id: "google", label: "Google Ads", note: "Search + YouTube + Display" },
  { id: "linkedin", label: "LinkedIn Ads", note: "B2B sponsored content" },
  { id: "tiktok", label: "TikTok Ads", note: "Spark + In-Feed" },
  { id: "x", label: "X Ads", note: "Promoted tweets + Takeovers" },
];

export default function AdsPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Channel · Theme C4"
        title="Ads"
        description="Push generated creatives + targeting + budgets as draft ad sets to Meta / Google / LinkedIn / TikTok / X. Human approves and launches — large budget moves are hard-gate by default."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Ad Campaign
          </DkButton>
        }
      />

      <DkEmptyState
        icon={<Target className="h-6 w-6" />}
        title="Ad Campaign builder lands next"
        description="AdAccount + AdCampaign + AdSet models + migration are in. The cross-platform table view + budget planner + per-platform draft push ship as follow-ups."
      />

      <div className="flex flex-col gap-3">
        <h2 className="font-display text-lg font-semibold text-ink">
          Supported platforms
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PLATFORMS.map((p) => (
            <DkCard key={p.id}>
              <DkCardHeader>
                <DkCardTitle className="text-base flex items-center gap-2">
                  {p.label}
                  <DkBadge tone="brand">soon</DkBadge>
                </DkCardTitle>
                <DkCardDescription>{p.note}</DkCardDescription>
              </DkCardHeader>
              <DkCardContent />
            </DkCard>
          ))}
        </div>
      </div>
    </div>
  );
}
