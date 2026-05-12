"use client";

import { useEffect, useState } from "react";
import { History, RefreshCw } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkTable,
  DkTableBody,
  DkTableCell,
  DkTableHead,
  DkTableHeader,
  DkTableRow,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type AuditEvent = {
  id: string;
  organization_id: string | null;
  actor_kind: "user" | "agent" | "system";
  actor_user_id: string | null;
  actor_agent: string | null;
  action_type: string;
  target_type: string | null;
  target_id: string | null;
  payload_json: Record<string, unknown> | null;
  result: "success" | "failure";
  error_message: string | null;
  created_at: string;
};

type ListResponse = {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
};

const ACTOR_TONE: Record<AuditEvent["actor_kind"], "brand" | "info" | "neutral"> =
  {
    user: "brand",
    agent: "info",
    system: "neutral",
  };

export default function AdminAuditPage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [actionType, setActionType] = useState("");
  const [actorKind, setActorKind] = useState<"" | AuditEvent["actor_kind"]>("");
  const [days, setDays] = useState(7);
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    setError(null);
    const qs = new URLSearchParams({
      days: String(days),
      limit: String(limit),
      offset: String(offset),
    });
    if (actionType) qs.set("action_type", actionType);
    if (actorKind) qs.set("actor_kind", actorKind);
    fetch(`/api/v1/orgs/${currentOrg.id}/audit-events?${qs}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) =>
        r.ok ? r.json() : r.text().then((t) => Promise.reject(new Error(t))),
      )
      .then((j: ListResponse) => {
        setRows(j.items);
        setTotal(j.total);
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load audit log."),
      )
      .finally(() => setLoading(false));
  }, [currentOrg, actionType, actorKind, days, offset, limit]);

  function fmt(s: string) {
    try {
      return new Date(s).toLocaleString();
    } catch {
      return s;
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · A4"
        title="Audit log"
        description="Every consequential action — agent runs, approvals, publishes, spend, MCP tool calls — is recorded here for compliance and replay."
      />

      <div className="grid gap-3 md:grid-cols-[1fr_180px_140px_auto]">
        <div>
          <DkLabel>Action type</DkLabel>
          <DkInput
            placeholder="e.g. approval.approved"
            value={actionType}
            onChange={(e) => {
              setActionType(e.target.value);
              setOffset(0);
            }}
          />
        </div>
        <div>
          <DkLabel>Actor</DkLabel>
          <DkSelect
            value={actorKind}
            onChange={(e) => {
              setActorKind(e.target.value as "" | AuditEvent["actor_kind"]);
              setOffset(0);
            }}
          >
            <option value="">Any</option>
            <option value="user">User</option>
            <option value="agent">Agent</option>
            <option value="system">System</option>
          </DkSelect>
        </div>
        <div>
          <DkLabel>Window (days)</DkLabel>
          <DkInput
            type="number"
            min={1}
            max={365}
            value={days}
            onChange={(e) => {
              setDays(Math.max(1, Number(e.target.value || 7)));
              setOffset(0);
            }}
          />
        </div>
        <div className="flex items-end">
          <DkButton onClick={() => setOffset(0)} disabled={loading}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </DkButton>
        </div>
      </div>

      {error ? (
        <div
          role="alert"
          className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
        >
          {error}
        </div>
      ) : null}

      {!currentOrg ? (
        <DkEmptyState
          icon={<History className="h-6 w-6" />}
          title="Pick an organization"
          description="Audit events are org-scoped — use the workspace switcher."
        />
      ) : rows.length === 0 && !loading ? (
        <DkEmptyState
          icon={<History className="h-6 w-6" />}
          title="No audit events match"
          description="Try widening the time window or clearing the action-type filter."
        />
      ) : (
        <>
          <DkCard>
            <DkTable>
              <DkTableHeader>
                <DkTableRow>
                  <DkTableHead>When</DkTableHead>
                  <DkTableHead>Actor</DkTableHead>
                  <DkTableHead>Action</DkTableHead>
                  <DkTableHead>Target</DkTableHead>
                  <DkTableHead>Result</DkTableHead>
                </DkTableRow>
              </DkTableHeader>
              <DkTableBody>
                {rows.map((r) => (
                  <DkTableRow key={r.id}>
                    <DkTableCell className="font-mono text-xs">
                      {fmt(r.created_at)}
                    </DkTableCell>
                    <DkTableCell>
                      <DkBadge tone={ACTOR_TONE[r.actor_kind]}>
                        {r.actor_kind}
                      </DkBadge>
                      {r.actor_agent ? (
                        <span className="ml-2 text-xs opacity-70">
                          {r.actor_agent}
                        </span>
                      ) : null}
                    </DkTableCell>
                    <DkTableCell className="font-mono text-xs">
                      {r.action_type}
                    </DkTableCell>
                    <DkTableCell className="font-mono text-xs">
                      {r.target_type ? `${r.target_type}:${r.target_id ?? "?"}` : "—"}
                    </DkTableCell>
                    <DkTableCell>
                      <DkBadge
                        tone={r.result === "success" ? "success" : "danger"}
                      >
                        {r.result}
                      </DkBadge>
                    </DkTableCell>
                  </DkTableRow>
                ))}
              </DkTableBody>
            </DkTable>
          </DkCard>
          <div className="flex items-center justify-between text-sm opacity-70">
            <span>
              Showing {Math.min(rows.length, total)} of {total}
            </span>
            <div className="flex gap-2">
              <DkButton
                variant="ghost"
                size="sm"
                disabled={offset === 0 || loading}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Prev
              </DkButton>
              <DkButton
                variant="ghost"
                size="sm"
                disabled={offset + limit >= total || loading}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </DkButton>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
