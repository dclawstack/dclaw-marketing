"use client";

import { Clock, Plus } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function TimeTrackingPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Operations · Theme L"
        title="Time Tracking"
        description="Per-task / per-campaign / per-org time logs. Auto-rollup to retainer burn-down. Invoice generation (Stripe + QuickBooks export). Billable vs. non-billable."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Entry
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<Clock className="h-6 w-6" />}
        title="Tracker + invoice gen land next"
        description="The TimeEntry model + migration are in (started_at / ended_at / billable / rate_usd_per_hour). The tracker UI + retainer burn-down + invoice generation ship as follow-ups."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · UI: in progress
      </DkBadge>
    </div>
  );
}
