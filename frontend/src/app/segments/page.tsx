"use client";

import { Filter, Plus } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function SegmentsPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Audience · Theme E3"
        title="Segments"
        description="Saved filter expressions over leads + touchpoints. Drives email targeting + ad-platform Custom Audience syncs. AND / OR groups with live counts."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Segment
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<Filter className="h-6 w-6" />}
        title="Segment builder lands next"
        description="The Segment model + migration are in (filter_dsl_json + last_evaluated_count). The builder UI (AND/OR groups, condition picker, live count) + per-platform audience syncs ship as follow-ups."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · Builder: in progress
      </DkBadge>
    </div>
  );
}
