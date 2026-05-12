"use client";

import { BookOpen, Plus } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function PlaybooksPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Knowledge Base · Theme N"
        title="Playbooks &amp; SOPs"
        description="Reusable prompts, briefs, SOPs, playbooks. AI-searchable across the org. Agents propose new SOPs derived from successful patterns."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Playbook
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<BookOpen className="h-6 w-6" />}
        title="Editor + agent search land next"
        description="The Playbook model is in (kinds: prompt / brief / sop / playbook; markdown body). The editor + semantic-search hook into the Knowledge Graph ship as follow-ups."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · Editor: in progress
      </DkBadge>
    </div>
  );
}
