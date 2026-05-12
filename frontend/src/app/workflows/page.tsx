"use client";

import { Plus, Workflow } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function WorkflowsPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Automation · Theme P"
        title="Workflows"
        description="Visual no-code chains — LLM step → tool call → approval gate → conditional → webhook. Magic Loops / Wordware shape. Save reusable templates and share across projects."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Workflow
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<Workflow className="h-6 w-6" />}
        title="Visual builder lands next"
        description="The Workflow model + migration are in (dsl_json column holds nodes / edges / layout). The react-flow editor + step palette + run history ship as follow-up PRs."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · Editor: in progress
      </DkBadge>
    </div>
  );
}
