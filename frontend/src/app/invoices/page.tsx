"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Receipt } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
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

export default function InvoicesListPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<InvoiceRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/orgs/${currentOrg.id}/invoices`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then(setRows)
      .finally(() => setLoading(false));
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Phase 10 — L"
        title="Invoices"
        description="Time-entry-rolled-up invoices sent via Stripe / QuickBooks. Each row links to the hosted-pay URL."
      />
      {loading ? (
        <DkSkeleton className="h-24 w-full" />
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<Receipt className="h-6 w-6" />}
          title="No invoices yet"
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
                <DkTableHead></DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {rows.map((i) => (
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
                    <Link href={`/invoices/${i.id}`}>
                      <DkButton size="sm" variant="secondary">
                        Open
                      </DkButton>
                    </Link>
                  </DkTableCell>
                </DkTableRow>
              ))}
            </DkTableBody>
          </DkTable>
        </DkCard>
      )}
    </div>
  );
}
