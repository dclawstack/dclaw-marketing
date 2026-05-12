"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Receipt } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkEmptyState,
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

interface InvoiceRow {
  id: string;
  invoice_number: string;
  total_usd: number;
  status: string;
  issued_at: string;
  due_at: string | null;
  paid_at: string | null;
}

const STATUS_FILTERS = ["all", "draft", "open", "paid", "void", "uncollectible"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

export default function InvoicesListPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<InvoiceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    if (!currentOrg) return;
    setLoading(true);
    const q = filter === "all" ? "" : `?status=${filter}`;
    const r = await fetch(`/api/v1/orgs/${currentOrg.id}/invoices${q}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    setRows(r.ok ? await r.json() : []);
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg, filter]);

  async function act(id: string, verb: "mark-paid" | "void" | "uncollectible") {
    setBusyId(id);
    try {
      await fetch(`/api/v1/invoices/${id}/${verb}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      await load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 10 — L"
        title="Invoices"
        description="Time-entry-rolled-up invoices. Use the filter to scope by status; mark paid / void inline."
      />

      <div className="flex flex-wrap gap-1.5">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setFilter(s)}
            className={
              "rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-fast " +
              (filter === s
                ? "bg-[var(--dk-purple-50)] text-brand"
                : "text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)]")
            }
          >
            {s}
          </button>
        ))}
      </div>

      {loading ? (
        <DkSkeleton className="h-24 w-full" />
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<Receipt className="h-6 w-6" />}
          title="No invoices in this view"
          description="Aggregate billable time entries into a draft invoice from the Time-tracker page."
        />
      ) : (
        <DkCard>
          <DkTable>
            <DkTableHeader>
              <DkTableRow>
                <DkTableHead>Number</DkTableHead>
                <DkTableHead>Status</DkTableHead>
                <DkTableHead className="text-right">Total</DkTableHead>
                <DkTableHead>Issued</DkTableHead>
                <DkTableHead className="text-right">Actions</DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {rows.map((i) => {
                const canPay = i.status !== "paid" && i.status !== "void";
                const canVoid = i.status !== "paid" && i.status !== "void";
                return (
                  <DkTableRow key={i.id}>
                    <DkTableCell className="font-mono text-sm">
                      {i.invoice_number}
                    </DkTableCell>
                    <DkTableCell>
                      <DkBadge
                        tone={
                          i.status === "paid"
                            ? "success"
                            : i.status === "void"
                              ? "neutral"
                              : i.status === "uncollectible"
                                ? "danger"
                                : "warning"
                        }
                      >
                        {i.status}
                      </DkBadge>
                    </DkTableCell>
                    <DkTableCell className="text-right font-mono">
                      ${i.total_usd.toFixed(2)}
                    </DkTableCell>
                    <DkTableCell className="text-sm">
                      {new Date(i.issued_at).toLocaleDateString()}
                    </DkTableCell>
                    <DkTableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
                        {canPay && (
                          <DkButton
                            size="sm"
                            variant="secondary"
                            disabled={busyId === i.id}
                            onClick={() => act(i.id, "mark-paid")}
                          >
                            Mark paid
                          </DkButton>
                        )}
                        {canVoid && (
                          <DkButton
                            size="sm"
                            variant="secondary"
                            disabled={busyId === i.id}
                            onClick={() => act(i.id, "void")}
                          >
                            Void
                          </DkButton>
                        )}
                        <Link href={`/invoices/${i.id}`}>
                          <DkButton size="sm" variant="secondary">
                            Open
                          </DkButton>
                        </Link>
                      </div>
                    </DkTableCell>
                  </DkTableRow>
                );
              })}
            </DkTableBody>
          </DkTable>
        </DkCard>
      )}
    </div>
  );
}
