"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Play } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface AdSet {
  id: string;
  name: string;
  platform: string;
  status: string;
  daily_budget_usd: number | null;
  external_campaign_id: string | null;
  bandit_state: Record<string, unknown> | null;
}

export default function AdSetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { currentOrg } = useOrg();
  const [row, setRow] = useState<AdSet | null>(null);
  const [loading, setLoading] = useState(true);
  const [budget, setBudget] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/orgs/${currentOrg.id}/ad-sets/${id}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((j: AdSet | null) => {
        setRow(j);
        if (j) setBudget(String(j.daily_budget_usd ?? ""));
      })
      .finally(() => setLoading(false));
  }, [currentOrg, id]);

  async function launchOnProvider() {
    if (!currentOrg || !row) return;
    setCreating(true);
    try {
      // Generic 'launch ad set' kicks the per-platform adapter
      // (meta / google / linkedin) on the backend.
      await fetch(
        `/api/v1/orgs/${currentOrg.id}/ad-sets/${id}/launch`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getToken()}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            daily_budget_usd: Number(budget) || 0,
          }),
        },
      );
      // refresh
      const res = await fetch(
        `/api/v1/orgs/${currentOrg.id}/ad-sets/${id}`,
        { headers: { Authorization: `Bearer ${getToken()}` } },
      );
      if (res.ok) setRow(await res.json());
    } finally {
      setCreating(false);
    }
  }

  if (loading || !row) {
    return <DkSkeleton className="h-48 w-full" />;
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 7 — Ads"
        title={row.name}
        description={`${row.platform} ad set · daily $${(row.daily_budget_usd ?? 0).toFixed(2)}`}
        actions={
          <DkBadge
            tone={
              row.status === "active"
                ? "success"
                : row.status === "paused"
                  ? "warning"
                  : "neutral"
            }
          >
            {row.status}
          </DkBadge>
        }
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Budget + launch</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex items-end gap-3">
          <div className="flex-1">
            <DkLabel htmlFor="budget">Daily budget (USD)</DkLabel>
            <DkInput
              id="budget"
              type="number"
              step="0.01"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="25.00"
            />
          </div>
          <DkButton
            onClick={launchOnProvider}
            disabled={creating || !budget}
            loading={creating}
          >
            <Play className="h-4 w-4" />
            Launch on {row.platform}
          </DkButton>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>External provider</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="flex flex-col gap-2 text-sm">
          <p>
            <span className="text-[var(--dk-fg-2)]">Provider:</span>{" "}
            <span className="font-semibold">{row.platform}</span>
          </p>
          <p>
            <span className="text-[var(--dk-fg-2)]">External campaign id:</span>{" "}
            <span className="font-mono">
              {row.external_campaign_id ?? "—"}
            </span>
          </p>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>A/B bandit state</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          <pre className="max-h-32 overflow-auto text-xs font-mono text-[var(--dk-fg-1)]">
            {JSON.stringify(row.bandit_state ?? {}, null, 2)}
          </pre>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
