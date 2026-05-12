"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApprovalRequestItem,
  ApprovalStatus,
  approveRequest,
  listApprovals,
  rejectRequest,
} from "@/lib/api";

/**
 * Approval Inbox — the human's primary surface for Hard-gate items.
 * The Creatives Agent (and future agents) prepare drafts; humans
 * decide approve / reject here. Approving will (in a later iteration)
 * fire the actual publish; for v0.1 the approval is the demo's end
 * state.
 */
export default function InboxPage() {
  const [items, setItems] = useState<ApprovalRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<ApprovalStatus | "all">("pending");
  const [decisionReason, setDecisionReason] = useState<Record<string, string>>({});
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

  function statusVariant(s: ApprovalStatus) {
    if (s === "pending") return "default";
    if (s === "approved" || s === "auto_approved") return "secondary";
    if (s === "rejected") return "destructive";
    return "outline";
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Approval Inbox</h1>
          <p className="text-sm text-muted-foreground">
            Agent-prepared actions awaiting your decision. Approving
            authorises the action; rejecting kills it with a reason.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="filter" className="text-sm text-muted-foreground">
            Filter:
          </Label>
          <select
            id="filter"
            className="rounded-md border border-border bg-background px-2 py-1 text-sm"
            value={filter}
            onChange={(e) => setFilter(e.target.value as ApprovalStatus | "all")}
          >
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="all">All</option>
          </select>
          <Button size="sm" variant="outline" onClick={() => void refresh()}>
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-muted-foreground">Loading…</p>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            Nothing here. {filter === "pending" ? "No pending items — agents are quiet." : ""}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => {
            const text = (item.payload_json?.text as string | undefined) ?? null;
            const channel = (item.payload_json?.channel as string | undefined) ?? null;
            const brief = (item.payload_json?.brief as string | undefined) ?? null;
            const ownDecision = item.status !== "pending";
            return (
              <Card key={item.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                      <CardTitle className="text-base font-semibold">
                        {item.action_type}
                        {channel ? (
                          <span className="ml-2 text-sm font-normal text-muted-foreground">
                            → {channel}
                          </span>
                        ) : null}
                      </CardTitle>
                      <CardDescription>
                        {item.requested_by_agent ? (
                          <span>
                            Requested by agent{" "}
                            <span className="font-mono">{item.requested_by_agent}</span>
                          </span>
                        ) : (
                          <span>Requested by user</span>
                        )}
                      </CardDescription>
                    </div>
                    <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {text && (
                    <div className="rounded-md border border-border bg-muted/50 p-3 text-sm">
                      {text}
                    </div>
                  )}
                  {brief && (
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Brief:</span> {brief}
                    </p>
                  )}
                  {item.decision_reason && (
                    <p className="text-xs text-muted-foreground">
                      <span className="font-medium">Decision reason:</span>{" "}
                      {item.decision_reason}
                    </p>
                  )}
                  {!ownDecision && (
                    <div className="space-y-2 pt-2">
                      <Input
                        placeholder="Optional reason / note"
                        value={decisionReason[item.id] ?? ""}
                        onChange={(e) =>
                          setDecisionReason((d) => ({ ...d, [item.id]: e.target.value }))
                        }
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => onApprove(item.id)}
                          disabled={busy === item.id}
                        >
                          {busy === item.id ? "…" : "Approve"}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => onReject(item.id)}
                          disabled={busy === item.id}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
