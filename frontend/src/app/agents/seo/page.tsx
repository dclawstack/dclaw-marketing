"use client";

import { BookOpen, FileText, Search } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function SeoStationPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Agent · SEO Specialist"
        title="Search Station"
        description="The SEO agent researches keywords, builds topic-cluster outlines, drafts long-form posts, and suggests internal-linking — then queues each draft through the editorial review flow."
        actions={<DkBadge tone="brand">v0.2 · coming online</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-3">
        <DkCard>
          <DkCardHeader>
            <Search className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Keyword Pipeline</DkCardTitle>
            <DkCardDescription>
              Pulled via Ahrefs / SEMrush MCP once connected.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <FileText className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Outline → Draft</DkCardTitle>
            <DkCardDescription>
              Each topic cluster becomes an outline, then a draft, scored
              for brand-voice fit.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <BookOpen className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Internal Linking</DkCardTitle>
            <DkCardDescription>
              Suggests anchors + targets pulled from the Knowledge Graph.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
