"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, X } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

interface ApprovalRow {
  id: string;
  action_type: string;
  target_type: string | null;
  summary: string | null;
  status: string;
  payload_json: Record<string, unknown> | null;
  created_at: string;
}

export default function ClientApprovalsPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<ApprovalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    if (!currentOrg) return;
    setLoading(true);
    const res = await fetch(
      `/api/v1/approvals?organization_id=${currentOrg.id}&status=pending`,
      { headers: { Authorization: `Bearer ${getToken()}` } },
    );
    if (res.ok) {
      const j = await res.json();
      setRows(Array.isArray(j) ? j : (j.items ?? []));
    }
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg]);

  async function decide(id: string, decision: "approve" | "reject") {
    setBusy(id);
    try {
      await fetch(`/api/v1/approvals/${id}/${decision}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      await load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Client Portal"
        title="Approvals"
        description="Content your agency has drafted and asked you to review. Approving fires the action; rejecting puts it back on the drawing board."
      />
      {loading ? (
        <DkSkeleton className="h-32 w-full" />
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<CheckCircle2 className="h-6 w-6" />}
          title="Nothing pending"
          description="When your agency files something for approval, it'll show up here."
        />
      ) : (
        <div className="flex flex-col gap-4">
          {rows.map((r) => (
            <DkCard key={r.id}>
              <DkCardContent className="flex flex-col gap-3 py-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <DkBadge tone="warning">{r.action_type}</DkBadge>
                    <p className="mt-2 text-sm text-[var(--dk-fg-1)]">
                      {r.summary ?? "(no summary)"}
                    </p>
                    <p className="mt-1 text-xs font-mono text-[var(--dk-fg-2)]">
                      filed {new Date(r.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <DkButton
                      size="sm"
                      variant="danger"
                      onClick={() => decide(r.id, "reject")}
                      disabled={busy === r.id}
                    >
                      <X className="h-4 w-4" />
                      Reject
                    </DkButton>
                    <DkButton
                      size="sm"
                      onClick={() => decide(r.id, "approve")}
                      disabled={busy === r.id}
                      loading={busy === r.id}
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      Approve
                    </DkButton>
                  </div>
                </div>
              </DkCardContent>
            </DkCard>
          ))}
        </div>
      )}
    </div>
  );
}
