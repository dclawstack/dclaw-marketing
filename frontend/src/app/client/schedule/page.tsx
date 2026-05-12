"use client";

import { useEffect, useState } from "react";
import { Calendar } from "lucide-react";

import {
  DkBadge,
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

interface PostRow {
  id: string;
  channel: string;
  status: string;
  scheduled_at: string;
  copy: string | null;
}

export default function ClientSchedulePage() {
  const { currentOrg } = useOrg();
  const [rows, setRows] = useState<PostRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!currentOrg) return;
    setLoading(true);
    fetch(`/api/v1/scheduled-posts?organization_id=${currentOrg.id}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : []))
      .then((j: PostRow[]) =>
        setRows(
          (Array.isArray(j) ? j : [])
            .filter(
              (p) =>
                p.status === "queued" ||
                p.status === "publishing" ||
                p.status === "published",
            )
            .sort(
              (a, b) =>
                new Date(a.scheduled_at).getTime() -
                new Date(b.scheduled_at).getTime(),
            ),
        ),
      )
      .finally(() => setLoading(false));
  }, [currentOrg]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Client Portal"
        title="Schedule"
        description="Posts queued + recently published across your connected channels. Read-only — your agency manages the calendar."
      />
      {loading ? (
        <DkSkeleton className="h-32 w-full" />
      ) : rows.length === 0 ? (
        <DkEmptyState
          icon={<Calendar className="h-6 w-6" />}
          title="Nothing on the calendar yet"
          description="When your agency schedules a post, you'll see it here."
        />
      ) : (
        <DkCard>
          <DkTable>
            <DkTableHeader>
              <DkTableRow>
                <DkTableHead>When</DkTableHead>
                <DkTableHead>Channel</DkTableHead>
                <DkTableHead>Status</DkTableHead>
                <DkTableHead>Copy</DkTableHead>
              </DkTableRow>
            </DkTableHeader>
            <DkTableBody>
              {rows.map((r) => (
                <DkTableRow key={r.id}>
                  <DkTableCell className="font-mono text-sm">
                    {new Date(r.scheduled_at).toLocaleString()}
                  </DkTableCell>
                  <DkTableCell>
                    <DkBadge tone="info">{r.channel}</DkBadge>
                  </DkTableCell>
                  <DkTableCell>
                    <DkBadge
                      tone={
                        r.status === "published"
                          ? "success"
                          : r.status === "failed"
                            ? "danger"
                            : "warning"
                      }
                    >
                      {r.status}
                    </DkBadge>
                  </DkTableCell>
                  <DkTableCell className="max-w-md text-sm text-[var(--dk-fg-1)] line-clamp-2">
                    {r.copy ?? "—"}
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
