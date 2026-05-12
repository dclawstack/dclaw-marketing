"use client";

import Link from "next/link";
import { ArrowRight, Inbox, Mail, Workflow } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function EmailHubPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Channel · Theme C3"
        title="Email"
        description="Transactional + newsletter + multi-step sequences. Templates and sequence definitions are stored locally; provider adapters (Resend / SendGrid / Mailchimp / Beehiiv / Substack) wire in per-PR."
        actions={<DkBadge tone="brand">v0.2 · data model live</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Link href="/email/templates" className="block">
          <DkCard hover className="h-full">
            <DkCardHeader>
              <Mail className="h-5 w-5 text-brand" />
              <DkCardTitle className="text-base flex items-center gap-2">
                Templates
                <ArrowRight className="h-4 w-4 ml-auto" />
              </DkCardTitle>
              <DkCardDescription>
                Subject + HTML/text body + merge fields. Reusable across
                campaigns and sequences.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent />
          </DkCard>
        </Link>
        <Link href="/email/sequences" className="block">
          <DkCard hover className="h-full">
            <DkCardHeader>
              <Workflow className="h-5 w-5 text-brand" />
              <DkCardTitle className="text-base flex items-center gap-2">
                Sequences
                <ArrowRight className="h-4 w-4 ml-auto" />
              </DkCardTitle>
              <DkCardDescription>
                Multi-step flows — email → wait → branch → linkedin DM →
                webhook. Visual flow editor lands in a follow-up.
              </DkCardDescription>
            </DkCardHeader>
            <DkCardContent />
          </DkCard>
        </Link>
      </div>
      <DkCard>
        <DkCardHeader>
          <Inbox className="h-5 w-5 text-brand" />
          <DkCardTitle className="text-base">Campaigns</DkCardTitle>
          <DkCardDescription>
            One-shot broadcasts (vs. a Sequence which is multi-step). Schedule
            a send, target a segment, watch the open/click/bounce counters.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent>
          <DkButton variant="secondary" disabled>
            Coming Soon
          </DkButton>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
