"use client";

import Link from "next/link";
import { Calendar, MessageSquare, Sparkles } from "lucide-react";

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

export default function SmmStationPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · Social Media Manager"
        title="Calendar Station"
        description="The Social Media Manager agent owns the calendar and the DM queue. Drafts content, queues posts, replies to DMs in your brand voice — every outbound action gates through the Approval Inbox."
        actions={<DkBadge tone="brand">v0.2 · coming online</DkBadge>}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        <DkCard hover>
          <DkCardHeader>
            <div className="flex items-start justify-between gap-2">
              <DkCardTitle className="text-base">Calendar</DkCardTitle>
              <Calendar className="h-5 w-5 text-brand" />
            </div>
            <DkCardDescription>
              The week-grid calendar is live now — the SMM agent will start
              filling slots once the Phase-9.x runtime ships. You can already
              schedule posts manually.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent>
            <Link href="/calendar">
              <DkButton variant="secondary" withArrow>
                Open Calendar
              </DkButton>
            </Link>
          </DkCardContent>
        </DkCard>

        <DkCard hover>
          <DkCardHeader>
            <div className="flex items-start justify-between gap-2">
              <DkCardTitle className="text-base">DM Queue</DkCardTitle>
              <MessageSquare className="h-5 w-5 text-brand" />
            </div>
            <DkCardDescription>
              Inbound DMs across X / LinkedIn / Instagram, with brand-voice
              drafts pre-written by the SMM agent. Lands in a follow-up PR.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent>
            <DkButton variant="secondary" disabled>
              Coming Soon
            </DkButton>
          </DkCardContent>
        </DkCard>
      </div>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle className="text-base">In the meantime</DkCardTitle>
          <DkCardDescription>
            Until the agent ships, you can drive the SMM loop manually:
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent className="flex flex-wrap gap-2">
          <Link href="/agents/creatives">
            <DkButton variant="secondary">
              <Sparkles className="h-4 w-4" />
              Generate Variants
            </DkButton>
          </Link>
          <Link href="/calendar">
            <DkButton variant="secondary">Schedule Posts</DkButton>
          </Link>
          <Link href="/inbox">
            <DkButton variant="secondary">Review Approvals</DkButton>
          </Link>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
