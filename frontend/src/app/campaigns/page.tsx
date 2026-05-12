"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSelect,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import {
  Campaign,
  CampaignStatus,
  CampaignType,
  getCampaigns,
} from "@/lib/api";

const STATUS_TONE: Record<
  CampaignStatus,
  "brand" | "info" | "success" | "warning" | "neutral"
> = {
  draft: "neutral",
  scheduled: "info",
  active: "success",
  paused: "warning",
  completed: "neutral",
};

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | "">("");
  const [typeFilter, setTypeFilter] = useState<CampaignType | "">("");

  useEffect(() => {
    setLoading(true);
    getCampaigns(statusFilter || undefined, typeFilter || undefined)
      .then((res) => setCampaigns(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [statusFilter, typeFilter]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace"
        title="Campaigns"
        description="Time-boxed initiatives bundling brief, hypothesis, target persona, channels, and KPIs."
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle className="text-base">Filters</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          <div className="flex flex-wrap gap-3">
            <DkSelect
              value={statusFilter}
              onChange={(e) =>
                setStatusFilter(e.target.value as CampaignStatus)
              }
              className="w-48"
            >
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
            </DkSelect>
            <DkSelect
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value as CampaignType)}
              className="w-48"
            >
              <option value="">All Types</option>
              <option value="email">Email</option>
              <option value="social">Social</option>
              <option value="ppc">PPC</option>
              <option value="content">Content</option>
            </DkSelect>
          </div>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardContent className="p-0">
          {loading ? (
            <p className="p-6 text-[var(--dk-fg-2)]">Loading…</p>
          ) : error ? (
            <p className="p-6 text-[var(--dk-danger)]">{error}</p>
          ) : (
            <DkTable>
              <DkTableHeader>
                <DkTableRow>
                  <DkTableHead>Name</DkTableHead>
                  <DkTableHead>Type</DkTableHead>
                  <DkTableHead>Status</DkTableHead>
                  <DkTableHead>Budget</DkTableHead>
                  <DkTableHead>Start</DkTableHead>
                  <DkTableHead>End</DkTableHead>
                  <DkTableHead className="text-right">Actions</DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {campaigns.length === 0 && (
                  <DkTableRow>
                    <DkTableCell
                      colSpan={7}
                      className="text-center text-[var(--dk-fg-2)] py-8"
                    >
                      No campaigns found.
                    </DkTableCell>
                  </DkTableRow>
                )}
                {campaigns.map((c) => (
                  <DkTableRow key={c.id}>
                    <DkTableCell className="font-medium">{c.name}</DkTableCell>
                    <DkTableCell className="capitalize">{c.type}</DkTableCell>
                    <DkTableCell>
                      <DkBadge tone={STATUS_TONE[c.status]}>{c.status}</DkBadge>
                    </DkTableCell>
                    <DkTableCell className="tabular-nums">
                      {c.budget ? `$${c.budget.toFixed(2)}` : "—"}
                    </DkTableCell>
                    <DkTableCell>{c.start_date || "—"}</DkTableCell>
                    <DkTableCell>{c.end_date || "—"}</DkTableCell>
                    <DkTableCell className="text-right">
                      <Link href={`/campaigns/${c.id}`}>
                        <DkButton size="sm" variant="secondary">
                          View
                        </DkButton>
                      </Link>
                    </DkTableCell>
                  </DkTableRow>
                ))}
              </DkTableBody>
            </DkTable>
          )}
        </DkCardContent>
      </DkCard>
    </div>
  );
}
