"use client";

/**
 * Conductor Model Settings panel (S4-M14).
 *
 * Renders one row per capability with a dropdown of model entries that
 * support the capability. Writes UserModelPreference (or
 * OrgModelAssignment if the caller is admin and `level="org"`) via the
 * Sprint-4 endpoints.
 */

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

import { DkButton, DkSelect } from "@/components/dk";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface ModelEntryRow {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  capabilities: string[];
  status: string;
}

interface ResolvedRow {
  capability: string;
  resolved_by: string;
  model_entry_id: string | null;
  model_id: string | null;
  provider_type: string | null;
}

const HEADLINE_CAPS = [
  "text",
  "embedding",
  "image_generation",
  "text_to_speech",
  "text_to_video",
  "text_to_music",
  "audio_transcription",
] as const;

const CAP_LABEL: Record<string, string> = {
  text: "Text / Chat",
  embedding: "Embeddings",
  image_generation: "Image Generation",
  text_to_speech: "Voice (TTS)",
  text_to_video: "Video",
  text_to_music: "Music",
  audio_transcription: "Transcription",
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
      ...(init?.headers || {}),
    },
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  if (r.status === 204) return undefined as T;
  return r.json();
}

export function ModelSettingsPanel({
  orgId,
  level = "user",
  defaultOpen = false,
}: {
  orgId: string;
  level?: "user" | "org";
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [entries, setEntries] = useState<ModelEntryRow[]>([]);
  const [resolved, setResolved] = useState<ResolvedRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [e, r] = await Promise.all([
        api<ModelEntryRow[]>("/api/v1/models/entries"),
        api<ResolvedRow[]>(
          `/api/v1/models/resolved-assignments?organization_id=${orgId}`,
        ),
      ]);
      setEntries(e);
      setResolved(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const save = async (capability: string, modelEntryId: string) => {
    const path =
      level === "org" ? "/api/v1/models/org-assignments" : "/api/v1/models/user-preferences";
    try {
      await api(path, {
        method: "PUT",
        body: JSON.stringify({
          organization_id: orgId,
          capability,
          model_entry_id: modelEntryId,
        }),
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  };

  return (
    <div className="border rounded-md">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium hover:bg-slate-50"
      >
        Model Settings
        {open ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>
      {open && (
        <div className="border-t p-3 space-y-2">
          {error && <div className="text-rose-600 text-xs">{error}</div>}
          {loading ? (
            <div className="text-xs text-slate-500">Loading…</div>
          ) : (
            <div className="space-y-2">
              {HEADLINE_CAPS.map((cap) => {
                const opts = entries.filter((e) => e.capabilities.includes(cap));
                const current = resolved.find((r) => r.capability === cap);
                return (
                  <div key={cap} className="flex items-center gap-2 text-sm">
                    <div className="w-32 text-xs text-slate-600">
                      {CAP_LABEL[cap]}
                    </div>
                    <DkSelect
                      className="flex-1"
                      value={current?.model_entry_id ?? ""}
                      onChange={(e) => {
                        if (e.target.value) save(cap, e.target.value);
                      }}
                    >
                      <option value="">— not selected —</option>
                      {opts.map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.display_name}
                        </option>
                      ))}
                    </DkSelect>
                    <div className="text-xs text-slate-400 w-16 text-right">
                      {current?.resolved_by ?? "—"}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
