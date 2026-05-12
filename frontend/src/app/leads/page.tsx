"use client";

import { useEffect, useState } from "react";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkPageHeader,
  DkSelect,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import { getLeads, Lead, LeadStatus } from "@/lib/api";

const STATUS_TONE: Record<
  LeadStatus,
  "neutral" | "info" | "success" | "brand" | "danger"
> = {
  new: "neutral",
  contacted: "info",
  qualified: "success",
  converted: "brand",
  lost: "danger",
};

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<LeadStatus | "">("");

  useEffect(() => {
    setLoading(true);
    getLeads(
      search || undefined,
      sourceFilter || undefined,
      statusFilter || undefined,
    )
      .then((res) => setLeads(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [search, sourceFilter, statusFilter]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Workspace"
        title="Leads"
        description="Inbound contacts captured across campaigns. Filter by source, search by name or email."
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle className="text-base">Filters</DkCardTitle>
        </DkCardHeader>
        <DkCardContent>
          <div className="flex flex-wrap gap-3">
            <DkInput
              placeholder="Search…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64"
            />
            <DkInput
              placeholder="Source"
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="w-48"
            />
            <DkSelect
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as LeadStatus)}
              className="w-48"
            >
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="qualified">Qualified</option>
              <option value="converted">Converted</option>
              <option value="lost">Lost</option>
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
                  <DkTableHead>Email</DkTableHead>
                  <DkTableHead>Name</DkTableHead>
                  <DkTableHead>Company</DkTableHead>
                  <DkTableHead>Source</DkTableHead>
                  <DkTableHead>Status</DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {leads.length === 0 && (
                  <DkTableRow>
                    <DkTableCell
                      colSpan={5}
                      className="text-center text-[var(--dk-fg-2)] py-8"
                    >
                      No leads found.
                    </DkTableCell>
                  </DkTableRow>
                )}
                {leads.map((l) => (
                  <DkTableRow key={l.id}>
                    <DkTableCell className="font-medium">{l.email}</DkTableCell>
                    <DkTableCell>
                      {l.first_name} {l.last_name}
                    </DkTableCell>
                    <DkTableCell>{l.company || "—"}</DkTableCell>
                    <DkTableCell>{l.source || "—"}</DkTableCell>
                    <DkTableCell>
                      <DkBadge tone={STATUS_TONE[l.status]}>{l.status}</DkBadge>
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
