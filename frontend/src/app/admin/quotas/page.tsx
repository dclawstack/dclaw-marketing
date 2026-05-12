"use client";

import { CircleAlert, Gauge } from "lucide-react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
} from "@/components/dk";

export default function QuotasPage() {
  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · Theme I1"
        title="Rate Limits & Quotas"
        description="Sliding-window quotas per channel and per provider. Circuit-breaker trips when a provider returns sustained 5xx; auto-resets after the cooldown."
        actions={<DkBadge tone="brand">v0.2 · data model live</DkBadge>}
      />
      <div className="grid gap-4 md:grid-cols-2">
        <DkCard>
          <DkCardHeader>
            <Gauge className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Live counters</DkCardTitle>
            <DkCardDescription>
              "X: 47 / 300 today · LinkedIn: 12 / 100 · …" — each row updated
              atomically before any outbound call.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
        <DkCard>
          <DkCardHeader>
            <CircleAlert className="h-5 w-5 text-brand" />
            <DkCardTitle className="text-base">Circuit Breakers</DkCardTitle>
            <DkCardDescription>
              Cuts traffic to a flapping provider after N consecutive 5xx;
              cooldown decays exponentially with jitter.
            </DkCardDescription>
          </DkCardHeader>
          <DkCardContent />
        </DkCard>
      </div>
    </div>
  );
}
