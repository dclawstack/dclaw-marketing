"use client";

import { Plus, Workflow } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function EmailSequencesPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Email · Theme E4"
        title="Sequences"
        description="Multi-step automations — email → wait → branch → DM → webhook. Conductor or SMM agent can drop a draft sequence into the queue."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Sequence
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<Workflow className="h-6 w-6" />}
        title="Visual flow builder lands next"
        description="The EmailSequence + EmailSequenceStep models are live. The react-flow-based visual editor (drag steps, configure delays, set branch conditions) ships alongside the sequence-runner Celery task in a follow-up."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · Runner: in progress
      </DkBadge>
    </div>
  );
}
