"use client";

import { DkAgentChat, DkEmptyState, DkPageHeader } from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { Sparkles } from "lucide-react";

export default function ConductorPage() {
  const { currentOrg } = useOrg();

  return (
    <div className="flex flex-col gap-6">
      <DkPageHeader
        eyebrow="Agent · Manager Station"
        title="Conductor"
        description="Tell me a goal or a brief. I'll decompose it into role-agent tasks and route the right things to your Approval Inbox. Outbound posting is hard-gate by default — nothing goes live without you."
      />

      {!currentOrg ? (
        <DkEmptyState
          icon={<Sparkles className="h-6 w-6" />}
          title="Pick an organization"
          description="Conductor threads are org-scoped — use the switcher in the nav."
        />
      ) : (
        <DkAgentChat kind="conductor" />
      )}
    </div>
  );
}
