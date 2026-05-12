"use client";

import { Mail, Plus } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkEmptyState,
  DkPageHeader,
} from "@/components/dk";

export default function EmailTemplatesPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Email · Theme C3"
        title="Templates"
        description="Subject + HTML/text body + merge fields. Versioned per workspace."
        actions={
          <DkButton disabled>
            <Plus className="h-4 w-4" />
            New Template
          </DkButton>
        }
      />
      <DkEmptyState
        icon={<Mail className="h-6 w-6" />}
        title="Template editor lands next"
        description="The EmailTemplate model + migration are in. The editor (rich-text + merge-field picker + preview) ships in a follow-up PR alongside the Resend / SendGrid adapter."
      />
      <DkBadge tone="info" className="self-start">
        Backend: ✓ ready · Frontend: in progress
      </DkBadge>
    </div>
  );
}
