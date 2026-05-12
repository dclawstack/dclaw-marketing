"use client";

import { useEffect, useState } from "react";
import { Clock, Plus } from "lucide-react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSkeleton,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface TimeEntry {
  id: string;
  description: string | null;
  hours: number;
  hourly_rate_usd: number | null;
  is_billable: boolean;
  occurred_on: string;
  campaign_id: string | null;
  project_id: string | null;
}

export default function TimeTrackerPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<TimeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const [desc, setDesc] = useState("");
  const [hours, setHours] = useState("");
  const [rate, setRate] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    if (!currentOrg) return;
    setLoading(true);
    const res = await fetch(
      `/api/v1/orgs/${currentOrg.id}/time-entries`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    );
    if (res.ok) setRows(await res.json());
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg]);

  async function submit() {
    if (!currentOrg) return;
    setCreating(true);
    try {
      await fetch(`/api/v1/orgs/${currentOrg.id}/time-entries`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          description: desc || null,
          hours: Number(hours),
          hourly_rate_usd: rate ? Number(rate) : null,
          is_billable: true,
          occurred_on: new Date().toISOString().slice(0, 10),
        }),
      });
      setOpen(false);
      setDesc("");
      setHours("");
      setRate("");
      await load();
    } finally {
      setCreating(false);
    }
  }

  const totalHours = rows.reduce((s, r) => s + r.hours, 0);
  const totalRevenue = rows.reduce(
    (s, r) =>
      s +
      (r.hourly_rate_usd && r.is_billable ? r.hourly_rate_usd * r.hours : 0),
    0,
  );

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 10 — L"
        title="Time tracker"
        description="Log billable + non-billable time. Roll up into invoices from the Invoices page."
        actions={
          <DkButton onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" />
            Log time
          </DkButton>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <DkCard>
          <DkCardContent className="py-5">
            <p className="text-sm text-[var(--dk-fg-2)]">Total hours</p>
            <p className="font-display text-2xl font-semibold">
              {totalHours.toFixed(1)}
            </p>
          </DkCardContent>
        </DkCard>
        <DkCard>
          <DkCardContent className="py-5">
            <p className="text-sm text-[var(--dk-fg-2)]">Billable revenue</p>
            <p className="font-display text-2xl font-semibold">
              ${totalRevenue.toFixed(2)}
            </p>
          </DkCardContent>
        </DkCard>
      </div>

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Recent entries</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="px-0 pt-0">
          {loading ? (
            <div className="px-6 pb-6">
              <DkSkeleton className="h-4 w-1/2" />
            </div>
          ) : rows.length === 0 ? (
            <DkEmptyState
              icon={<Clock className="h-6 w-6" />}
              title="No time logged yet"
              description="Click 'Log time' to add your first entry."
            />
          ) : (
            <DkTable>
              <DkTableHeader>
                <DkTableRow>
                  <DkTableHead>Date</DkTableHead>
                  <DkTableHead>Description</DkTableHead>
                  <DkTableHead className="text-right">Hours</DkTableHead>
                  <DkTableHead className="text-right">Rate</DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {rows.map((r) => (
                  <DkTableRow key={r.id}>
                    <DkTableCell className="font-mono text-sm">
                      {r.occurred_on}
                    </DkTableCell>
                    <DkTableCell>{r.description ?? "—"}</DkTableCell>
                    <DkTableCell className="text-right font-mono">
                      {r.hours.toFixed(1)}
                    </DkTableCell>
                    <DkTableCell className="text-right font-mono">
                      {r.hourly_rate_usd
                        ? `$${r.hourly_rate_usd.toFixed(2)}`
                        : "—"}
                    </DkTableCell>
                  </DkTableRow>
                ))}
              </DkTableBody>
            </DkTable>
          )}
        </DkCardContent>
      </DkCard>

      <DkDialog open={open} onClose={() => !creating && setOpen(false)} size="md">
        <DkDialogHeader
          title="Log time"
          description="Per-day entry. Hours can be fractional (e.g. 1.5)."
          onClose={() => setOpen(false)}
        />
        <DkDialogContent>
          <div className="flex flex-col gap-3">
            <div>
              <DkLabel htmlFor="desc">Description</DkLabel>
              <DkInput
                id="desc"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="What did you work on?"
              />
            </div>
            <div>
              <DkLabel htmlFor="hours" required>Hours</DkLabel>
              <DkInput
                id="hours"
                type="number"
                step="0.25"
                value={hours}
                onChange={(e) => setHours(e.target.value)}
                placeholder="1.5"
              />
            </div>
            <div>
              <DkLabel htmlFor="rate">Hourly rate (USD, optional)</DkLabel>
              <DkInput
                id="rate"
                type="number"
                step="0.01"
                value={rate}
                onChange={(e) => setRate(e.target.value)}
                placeholder="150.00"
              />
            </div>
          </div>
        </DkDialogContent>
        <DkDialogFooter>
          <DkButton
            variant="secondary"
            onClick={() => setOpen(false)}
            disabled={creating}
          >
            Cancel
          </DkButton>
          <DkButton
            onClick={submit}
            disabled={!hours || creating}
            loading={creating}
          >
            Save
          </DkButton>
        </DkDialogFooter>
      </DkDialog>
    </div>
  );
}
