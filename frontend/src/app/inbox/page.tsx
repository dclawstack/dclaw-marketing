"use client";

import { useCallback, useEffect, useState } from "react";
import { ListChecks, RefreshCw } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
} from "@/components/dk";
import {
  ApprovalRequestItem,
  ApprovalStatus,
  approveRequest,
  listApprovals,
  rejectRequest,
} from "@/lib/api";

const STATUS_TONE: Record<
  ApprovalStatus,
  "brand" | "success" | "danger" | "neutral" | "warning"
> = {
  pending: "brand",
  approved: "success",
  auto_approved: "success",
  rejected: "danger",
  canceled: "neutral",
  expired: "warning",
};

export default function InboxPage() {
  const [items, setItems] = useState<ApprovalRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ApprovalStatus | "all">("pending");
  const [decisionReason, setDecisionReason] = useState<Record<string, string>>(
    {},
  );
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listApprovals(
        filter === "all" ? {} : { status: filter as ApprovalStatus },
      );
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function onApprove(id: string) {
    setBusy(id);
    try {
      await approveRequest(id, decisionReason[id]);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Approve failed.");
    } finally {
      setBusy(null);
    }
  }

  async function onReject(id: string) {
    if (!decisionReason[id]?.trim()) {
      alert("Please provide a reason when rejecting.");
      return;
    }
    setBusy(id);
    try {
      await rejectRequest(id, decisionReason[id]);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Reject failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Supervision"
        title="Approval Inbox"
        description="Agent-prepared actions awaiting your decision. Approving authorises the action; rejecting kills it with a reason."
        actions={
          <>
            <div className="flex items-center gap-2">
              <DkLabel htmlFor="filter">Filter</DkLabel>
              <DkSelect
                id="filter"
                value={filter}
                onChange={(e) =>
                  setFilter(e.target.value as ApprovalStatus | "all")
                }
                className="w-36"
              >
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="all">All</option>
              </DkSelect>
            </div>
            <DkButton
              variant="secondary"
              size="sm"
              onClick={() => void refresh()}
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </DkButton>
          </>
        }
      />

      {error && (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-[var(--dk-fg-2)]">Loading…</p>
      ) : items.length === 0 ? (
        <DkEmptyState
          icon={<ListChecks className="h-6 w-6" />}
          title="Nothing pending"
          description={
            filter === "pending"
              ? "No approvals waiting — agents are quiet."
              : "No items match this filter."
          }
        />
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => {
            const text =
              (item.payload_json?.text as string | undefined) ?? null;
            const channel =
              (item.payload_json?.channel as string | undefined) ?? null;
            const brief =
              (item.payload_json?.brief as string | undefined) ?? null;
            const decided = item.status !== "pending";
            return (
              <DkCard key={item.id}>
                <DkCardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-col gap-1">
                      <DkCardTitle className="text-base font-semibold">
                        {item.action_type}
                        {channel && (
                          <span className="ml-2 text-sm font-normal text-[var(--dk-fg-2)]">
                            → {channel}
                          </span>
                        )}
                      </DkCardTitle>
                      <DkCardDescription>
                        {item.requested_by_agent ? (
                          <>
                            Requested by agent{" "}
                            <span className="font-mono">
                              {item.requested_by_agent}
                            </span>
                          </>
                        ) : (
                          <>Requested by user</>
                        )}
                      </DkCardDescription>
                    </div>
                    <DkBadge tone={STATUS_TONE[item.status]}>
                      {item.status}
                    </DkBadge>
                  </div>
                </DkCardHeader>
                <DkCardContent className="flex flex-col gap-3">
                  {text && (
                    <div className="rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-3 text-sm leading-relaxed text-[var(--dk-fg-1)]">
                      {text}
                    </div>
                  )}
                  {brief && (
                    <p className="text-xs text-[var(--dk-fg-2)]">
                      <span className="font-semibold text-[var(--dk-fg-1)]">
                        Brief:
                      </span>{" "}
                      {brief}
                    </p>
                  )}
                  {item.decision_reason && (
                    <p className="text-xs text-[var(--dk-fg-2)]">
                      <span className="font-semibold text-[var(--dk-fg-1)]">
                        Decision reason:
                      </span>{" "}
                      {item.decision_reason}
                    </p>
                  )}
                  {!decided && (
                    <div className="flex flex-col gap-2 pt-2">
                      <DkInput
                        placeholder="Optional reason / note"
                        value={decisionReason[item.id] ?? ""}
                        onChange={(e) =>
                          setDecisionReason((d) => ({
                            ...d,
                            [item.id]: e.target.value,
                          }))
                        }
                      />
                      <div className="flex gap-2">
                        <DkButton
                          size="sm"
                          onClick={() => onApprove(item.id)}
                          loading={busy === item.id}
                        >
                          Approve
                        </DkButton>
                        <DkButton
                          size="sm"
                          variant="danger"
                          onClick={() => onReject(item.id)}
                          loading={busy === item.id}
                        >
                          Reject
                        </DkButton>
                      </div>
                    </div>
                  )}
                </DkCardContent>
              </DkCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
