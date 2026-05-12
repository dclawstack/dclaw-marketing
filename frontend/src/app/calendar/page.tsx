"use client";

import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Plus,
  Send,
  Trash2,
  X,
} from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkEmptyState,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkSkeleton,
  DkTextarea,
} from "@/components/dk";
import {
  ScheduledPost,
  ScheduledPostChannel,
  cancelScheduledPost,
  createScheduledPost,
  listScheduledPosts,
  publishScheduledPostNow,
} from "@/lib/api";
import { useOrg } from "@/contexts/org-context";
import { cn } from "@/lib/utils";

// Channel → brand-coherent color (semantic only; not literal brand colors).
const CHANNEL_COLOR: Record<ScheduledPostChannel, string> = {
  linkedin: "var(--dk-purple-700)",
  x: "var(--dk-ink)",
  instagram: "var(--dk-info)",
  threads: "var(--dk-gray-700)",
  bluesky: "var(--dk-info)",
  facebook: "var(--dk-purple-500)",
  youtube: "var(--dk-danger)",
  tiktok: "var(--dk-gray-800)",
  newsletter: "var(--dk-success)",
  blog: "var(--dk-warning)",
};

const STATUS_TONE = {
  queued: "brand",
  publishing: "info",
  published: "success",
  failed: "danger",
  cancelled: "neutral",
  would_publish: "warning",
} as const;

function startOfWeek(d: Date): Date {
  const x = new Date(d);
  const dow = x.getDay(); // 0 Sun..6 Sat — we want Monday start
  const diff = (dow + 6) % 7;
  x.setDate(x.getDate() - diff);
  x.setHours(0, 0, 0, 0);
  return x;
}

function fmtIsoLocalForInput(d: Date): string {
  // datetime-local input wants YYYY-MM-DDTHH:mm in local time
  const off = d.getTimezoneOffset();
  const local = new Date(d.getTime() - off * 60_000);
  return local.toISOString().slice(0, 16);
}

function fmtDay(d: Date): string {
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function fmtTime(d: Date): string {
  return d.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function CalendarPage() {
  const { currentOrg } = useOrg();
  const [weekAnchor, setWeekAnchor] = useState<Date>(() => startOfWeek(new Date()));
  const [posts, setPosts] = useState<ScheduledPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);

  const weekStart = useMemo(() => weekAnchor, [weekAnchor]);
  const weekEnd = useMemo(() => {
    const x = new Date(weekStart);
    x.setDate(x.getDate() + 7);
    return x;
  }, [weekStart]);

  const refresh = useCallback(async () => {
    if (!currentOrg) {
      setPosts([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await listScheduledPosts(currentOrg.id, {
        from: weekStart.toISOString(),
        to: weekEnd.toISOString(),
      });
      setPosts(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load.");
    } finally {
      setLoading(false);
    }
  }, [currentOrg, weekStart, weekEnd]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  function navigateWeek(deltaDays: number) {
    const x = new Date(weekStart);
    x.setDate(x.getDate() + deltaDays);
    setWeekAnchor(startOfWeek(x));
  }

  async function publishNow(p: ScheduledPost) {
    if (!currentOrg) return;
    setBusyId(p.id);
    try {
      await publishScheduledPostNow(currentOrg.id, p.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Publish-now failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function cancel(p: ScheduledPost) {
    if (!currentOrg) return;
    if (!confirm(`Cancel this post on ${p.channel}?`)) return;
    setBusyId(p.id);
    try {
      await cancelScheduledPost(currentOrg.id, p.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Cancel failed.");
    } finally {
      setBusyId(null);
    }
  }

  const days = useMemo(() => {
    return Array.from({ length: 7 }).map((_, i) => {
      const d = new Date(weekStart);
      d.setDate(d.getDate() + i);
      return d;
    });
  }, [weekStart]);

  const byDay = useMemo(() => {
    const map = new Map<string, ScheduledPost[]>();
    for (const p of posts) {
      const d = new Date(p.scheduled_at);
      const key = d.toDateString();
      const arr = map.get(key) ?? [];
      arr.push(p);
      map.set(key, arr);
    }
    for (const arr of Array.from(map.values())) {
      arr.sort(
        (a, b) =>
          new Date(a.scheduled_at).getTime() -
          new Date(b.scheduled_at).getTime(),
      );
    }
    return map;
  }, [posts]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow={currentOrg ? `Workspace · ${currentOrg.name}` : "Workspace"}
        title="Calendar"
        description="Every scheduled post across every channel. Click a chip for details; use the action buttons to publish-now or cancel. The dispatcher polls every 60 seconds."
        actions={
          <DkButton onClick={() => setCreateOpen(true)} disabled={!currentOrg}>
            <Plus className="h-4 w-4" />
            Schedule Post
          </DkButton>
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

      {!currentOrg ? (
        <DkEmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="Pick an organization"
          description="The calendar is org-scoped — use the switcher in the nav to choose one."
        />
      ) : (
        <>
          {/* Week nav */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <DkButton
                size="sm"
                variant="secondary"
                aria-label="Previous week"
                onClick={() => navigateWeek(-7)}
              >
                <ChevronLeft className="h-4 w-4" />
              </DkButton>
              <DkButton
                size="sm"
                variant="secondary"
                onClick={() => setWeekAnchor(startOfWeek(new Date()))}
              >
                This Week
              </DkButton>
              <DkButton
                size="sm"
                variant="secondary"
                aria-label="Next week"
                onClick={() => navigateWeek(7)}
              >
                <ChevronRight className="h-4 w-4" />
              </DkButton>
            </div>
            <p className="text-sm font-medium text-ink">
              {fmtDay(days[0])} – {fmtDay(days[6])}
            </p>
          </div>

          {/* Week grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-7 gap-2">
              {Array.from({ length: 7 }).map((_, i) => (
                <DkSkeleton key={i} className="h-64" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-7 gap-2">
              {days.map((d) => {
                const isToday = d.toDateString() === new Date().toDateString();
                const items = byDay.get(d.toDateString()) ?? [];
                return (
                  <DkCard
                    key={d.toISOString()}
                    className={cn(
                      "min-h-[12rem] flex flex-col",
                      isToday && "border-brand",
                    )}
                  >
                    <div
                      className={cn(
                        "px-3 py-2 border-b text-xs font-semibold uppercase tracking-wide",
                        isToday
                          ? "border-[var(--dk-purple-200)] text-brand bg-[var(--dk-purple-50)]"
                          : "border-[var(--dk-border)] text-[var(--dk-fg-2)]",
                      )}
                    >
                      {d.toLocaleDateString(undefined, {
                        weekday: "short",
                      })}{" "}
                      <span className="text-ink font-bold">
                        {d.getDate()}
                      </span>
                    </div>
                    <DkCardContent className="p-2 flex-1 flex flex-col gap-1.5">
                      {items.length === 0 && (
                        <p className="text-xs text-[var(--dk-fg-muted)] text-center pt-4">
                          Empty
                        </p>
                      )}
                      {items.map((p) => (
                        <ChipItem
                          key={p.id}
                          post={p}
                          busy={busyId === p.id}
                          onPublishNow={() => publishNow(p)}
                          onCancel={() => cancel(p)}
                        />
                      ))}
                    </DkCardContent>
                  </DkCard>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* Create dialog */}
      {currentOrg && (
        <CreateDialog
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreated={() => {
            setCreateOpen(false);
            void refresh();
          }}
          orgId={currentOrg.id}
        />
      )}
    </div>
  );
}

function ChipItem({
  post,
  busy,
  onPublishNow,
  onCancel,
}: {
  post: ScheduledPost;
  busy: boolean;
  onPublishNow: () => void;
  onCancel: () => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="flex flex-col">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-left text-xs leading-snug bg-white border hover:shadow-sm transition-all duration-fast"
        style={{
          borderColor: CHANNEL_COLOR[post.channel],
          borderLeftWidth: 3,
        }}
      >
        <span className="font-mono text-[10px] text-[var(--dk-fg-2)]">
          {fmtTime(new Date(post.scheduled_at))}
        </span>
        <span className="font-semibold text-ink capitalize">
          {post.channel}
        </span>
      </button>
      {open && (
        <div className="mt-1 mb-1 rounded-md border border-[var(--dk-border)] bg-[var(--dk-bg-tint)] p-2 flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-1">
            <DkBadge tone={STATUS_TONE[post.status]} className="text-[10px]">
              {post.status}
            </DkBadge>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close"
              className="text-[var(--dk-fg-2)] hover:text-ink"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
          {post.copy && (
            <p className="whitespace-pre-wrap text-xs text-[var(--dk-fg-1)]">
              {post.copy.length > 200
                ? post.copy.slice(0, 200) + "…"
                : post.copy}
            </p>
          )}
          {(post.status === "queued" || post.status === "would_publish") && (
            <div className="flex gap-1 pt-1">
              {post.status === "queued" && (
                <button
                  onClick={onPublishNow}
                  disabled={busy}
                  className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-semibold text-brand hover:bg-[var(--dk-purple-100)] disabled:opacity-50"
                >
                  <Send className="h-3 w-3" />
                  Publish now
                </button>
              )}
              <button
                onClick={onCancel}
                disabled={busy}
                className="flex items-center gap-1 rounded-md px-1.5 py-1 text-[10px] font-semibold text-[var(--dk-danger)] hover:bg-[var(--dk-danger-bg)] disabled:opacity-50"
              >
                <Trash2 className="h-3 w-3" />
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function CreateDialog({
  open,
  onClose,
  onCreated,
  orgId,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
  orgId: string;
}) {
  const [channel, setChannel] = useState<ScheduledPostChannel>("linkedin");
  const [when, setWhen] = useState(() =>
    fmtIsoLocalForInput(new Date(Date.now() + 60 * 60 * 1000)),
  );
  const [copy, setCopy] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      await createScheduledPost(orgId, {
        channel,
        scheduled_at: new Date(when).toISOString(),
        copy: copy || undefined,
      });
      onCreated();
      setCopy("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <DkDialog open={open} onClose={onClose} size="md">
      <DkDialogHeader
        title="Schedule Post"
        description="The post lands on the calendar and gets dispatched at the scheduled time. The publisher is stubbed in Phase 4 — it'll log a would_publish status until the Phase 5 channel adapters land."
        onClose={onClose}
      />
      <DkDialogContent className="flex flex-col gap-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="ch" required>
              Channel
            </DkLabel>
            <DkSelect
              id="ch"
              value={channel}
              onChange={(e) =>
                setChannel(e.target.value as ScheduledPostChannel)
              }
            >
              {(Object.keys(CHANNEL_COLOR) as ScheduledPostChannel[]).map(
                (c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ),
              )}
            </DkSelect>
          </div>
          <div className="flex flex-col gap-1.5">
            <DkLabel htmlFor="when" required>
              Scheduled at
            </DkLabel>
            <DkInput
              id="when"
              type="datetime-local"
              value={when}
              onChange={(e) => setWhen(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <DkLabel htmlFor="copy">Copy</DkLabel>
          <DkTextarea
            id="copy"
            rows={5}
            placeholder="What does this post say?"
            value={copy}
            onChange={(e) => setCopy(e.target.value)}
          />
        </div>
        {error && (
          <div
            role="alert"
            className="rounded-md border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] px-3 py-2 text-sm text-[var(--dk-danger)]"
          >
            {error}
          </div>
        )}
      </DkDialogContent>
      <DkDialogFooter>
        <DkButton variant="secondary" onClick={onClose}>
          Cancel
        </DkButton>
        <DkButton
          onClick={handleSubmit}
          loading={submitting}
          disabled={!when || submitting}
        >
          Schedule
        </DkButton>
      </DkDialogFooter>
    </DkDialog>
  );
}
