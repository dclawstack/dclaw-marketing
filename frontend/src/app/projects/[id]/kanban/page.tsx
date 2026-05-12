"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Plus, Trash2 } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkDialog,
  DkDialogContent,
  DkDialogFooter,
  DkDialogHeader,
  DkInput,
  DkLabel,
  DkPageHeader,
  DkSelect,
  DkSkeleton,
  DkTextarea,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

type KanbanStatus = "todo" | "in_progress" | "blocked" | "done";

interface KanbanTask {
  id: string;
  title: string;
  status: KanbanStatus;
  assignee_user_id?: string | null;
  due_date?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

const COLUMNS: { status: KanbanStatus; label: string }[] = [
  { status: "todo", label: "To do" },
  { status: "in_progress", label: "In progress" },
  { status: "blocked", label: "Blocked" },
  { status: "done", label: "Done" },
];

const STATUS_TONE: Record<KanbanStatus, "neutral" | "warning" | "danger" | "success"> = {
  todo: "neutral",
  in_progress: "warning",
  blocked: "danger",
  done: "success",
};

export default function ProjectKanbanPage() {
  const params = useParams<{ id: string }>();
  const projectId = params?.id ?? "";

  const [tasks, setTasks] = useState<KanbanTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);

  const [title, setTitle] = useState("");
  const [status, setStatus] = useState<KanbanStatus>("todo");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    if (!projectId) return;
    setLoading(true);
    const r = await fetch(`/api/v1/projects/${projectId}/tasks`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    setTasks(r.ok ? await r.json() : []);
    setLoading(false);
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  async function create() {
    if (!title.trim()) return;
    setCreating(true);
    try {
      await fetch(`/api/v1/projects/${projectId}/tasks`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${getToken()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title.trim(),
          status,
          notes: notes.trim() || null,
        }),
      });
      setTitle("");
      setNotes("");
      setStatus("todo");
      setOpen(false);
      await load();
    } finally {
      setCreating(false);
    }
  }

  async function move(task: KanbanTask, next: KanbanStatus) {
    await fetch(`/api/v1/projects/${projectId}/tasks/${task.id}`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${getToken()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: next }),
    });
    await load();
  }

  async function remove(task: KanbanTask) {
    if (!confirm(`Delete "${task.title}"?`)) return;
    await fetch(`/api/v1/projects/${projectId}/tasks/${task.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${getToken()}` },
    });
    await load();
  }

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Theme K — Project ops"
        title="Kanban"
        description="Lightweight project task board. Move cards through columns; track who owns what."
        actions={
          <DkButton onClick={() => setOpen(true)}>
            <Plus className="h-4 w-4" />
            New task
          </DkButton>
        }
      />

      {loading ? (
        <DkSkeleton className="h-48 w-full" />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {COLUMNS.map((col) => {
            const colTasks = tasks.filter((t) => t.status === col.status);
            return (
              <div
                key={col.status}
                className="flex flex-col gap-2 rounded-lg bg-[var(--dk-gray-50)] p-3"
              >
                <div className="flex items-center justify-between px-1">
                  <span className="text-sm font-semibold uppercase tracking-wide text-[var(--dk-fg-2)]">
                    {col.label}
                  </span>
                  <DkBadge tone={STATUS_TONE[col.status]}>
                    {colTasks.length}
                  </DkBadge>
                </div>
                <div className="flex flex-col gap-2">
                  {colTasks.length === 0 && (
                    <p className="px-1 py-2 text-xs text-[var(--dk-fg-2)]">
                      No tasks.
                    </p>
                  )}
                  {colTasks.map((t) => (
                    <DkCard key={t.id}>
                      <DkCardContent className="flex flex-col gap-2 py-3">
                        <p className="text-sm font-medium leading-snug">
                          {t.title}
                        </p>
                        {t.notes && (
                          <p className="text-xs text-[var(--dk-fg-2)] line-clamp-3">
                            {t.notes}
                          </p>
                        )}
                        <div className="flex items-center gap-1.5 flex-wrap pt-1">
                          {COLUMNS.filter((c) => c.status !== col.status).map(
                            (c) => (
                              <DkButton
                                key={c.status}
                                size="sm"
                                variant="secondary"
                                onClick={() => move(t, c.status)}
                              >
                                → {c.label}
                              </DkButton>
                            ),
                          )}
                          <button
                            type="button"
                            onClick={() => remove(t)}
                            className="ml-auto rounded p-1 text-[var(--dk-fg-2)] hover:bg-[var(--dk-danger-bg)] hover:text-[var(--dk-danger)] transition-colors"
                            aria-label="Delete task"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </DkCardContent>
                    </DkCard>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <DkDialog open={open} onClose={() => !creating && setOpen(false)} size="md">
        <DkDialogHeader title="New task" onClose={() => setOpen(false)} />
        <DkDialogContent className="flex flex-col gap-3">
          <div>
            <DkLabel htmlFor="t-title" required>
              Title
            </DkLabel>
            <DkInput
              id="t-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <DkLabel htmlFor="t-status" required>
              Status
            </DkLabel>
            <DkSelect
              id="t-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as KanbanStatus)}
            >
              {COLUMNS.map((c) => (
                <option key={c.status} value={c.status}>
                  {c.label}
                </option>
              ))}
            </DkSelect>
          </div>
          <div>
            <DkLabel htmlFor="t-notes">Notes</DkLabel>
            <DkTextarea
              id="t-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
            />
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
          <DkButton onClick={create} disabled={!title.trim() || creating}>
            Create
          </DkButton>
        </DkDialogFooter>
      </DkDialog>
    </div>
  );
}
