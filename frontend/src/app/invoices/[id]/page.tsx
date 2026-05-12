"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import {
  DkBadge,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
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

interface LineItem {
  id: string;
  position: number;
  description: string;
  quantity: number;
  unit_price_usd: number;
  amount_usd: number;
}

interface InvoiceDetail {
  id: string;
  invoice_number: string;
  status: string;
  subtotal_usd: number;
  tax_usd: number;
  total_usd: number;
  currency: string;
  issued_at: string;
  due_at: string | null;
  paid_at: string | null;
  stripe_invoice_id: string | null;
  quickbooks_invoice_id: string | null;
  notes: string | null;
  line_items: LineItem[];
}

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { currentOrg } = useOrg();
  const [row, setRow] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/orgs/${currentOrg.id}/invoices/${id}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then(setRow)
      .finally(() => setLoading(false));
  }, [currentOrg, id]);

  if (loading || !row) {
    return <DkSkeleton className="h-48 w-full" />;
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Invoice"
        title={row.invoice_number}
        description={
          row.notes ??
          "Auto-generated invoice. Line items aggregated from TimeEntry rows."
        }
        actions={
          <DkBadge
            tone={
              row.status === "paid"
                ? "success"
                : row.status === "void"
                  ? "neutral"
                  : "warning"
            }
          >
            {row.status}
          </DkBadge>
        }
      />

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>Line items</DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="px-0 pt-0">
          <DkTable>
            <DkTableHeader>
              <DkTableRow>
                <DkTableHead>Description</DkTableHead>
                <DkTableHead className="text-right">Qty</DkTableHead>
                <DkTableHead className="text-right">Unit</DkTableHead>
                <DkTableHead className="text-right">Amount</DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {row.line_items.map((li) => (
                <DkTableRow key={li.id}>
                  <DkTableCell>{li.description}</DkTableCell>
                  <DkTableCell className="text-right font-mono">
                    {li.quantity}
                  </DkTableCell>
                  <DkTableCell className="text-right font-mono">
                    ${li.unit_price_usd.toFixed(2)}
                  </DkTableCell>
                  <DkTableCell className="text-right font-mono">
                    ${li.amount_usd.toFixed(2)}
                  </DkTableCell>
                </DkTableRow>
              ))}
            </DkTableBody>
          </DkTable>
        </DkCardContent>
      </DkCard>

      <DkCard>
        <DkCardContent className="flex flex-col gap-1 text-right">
          <p className="text-sm text-[var(--dk-fg-2)]">
            Subtotal: <span className="font-mono">${row.subtotal_usd.toFixed(2)}</span>
          </p>
          <p className="text-sm text-[var(--dk-fg-2)]">
            Tax: <span className="font-mono">${row.tax_usd.toFixed(2)}</span>
          </p>
          <p className="text-lg font-semibold">
            Total: <span className="font-mono">${row.total_usd.toFixed(2)}</span>
          </p>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
