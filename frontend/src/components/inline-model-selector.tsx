"use client";

/**
 * Inline model selector (S4-M16).
 *
 * Drop-in on any action page that wants to let the operator pick which
 * model runs the current action. Reads available entries for the
 * capability + writes UserModelPreference on change.
 */

import { useCallback, useEffect, useState } from "react";

import { DkSelect } from "@/components/dk";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface ModelEntryRow {
  id: string;
  display_name: string;
  capabilities: string[];
}

interface ResolvedRow {
  capability: string;
  resolved_by: string;
  model_entry_id: string | null;
}

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

export function InlineModelSelector({
  orgId,
  capability,
  label,
  className,
}: {
  orgId: string;
  capability: string;
  label?: string;
  className?: string;
}) {
  const [entries, setEntries] = useState<ModelEntryRow[]>([]);
  const [current, setCurrent] = useState<string>("");
  const [resolvedBy, setResolvedBy] = useState<string>("");

  const refresh = useCallback(async () => {
    try {
      const [e, r] = await Promise.all([
        api<ModelEntryRow[]>(`/api/v1/models/entries?capability=${capability}`),
        api<ResolvedRow[]>(
          `/api/v1/models/resolved-assignments?organization_id=${orgId}`,
        ),
      ]);
      setEntries(e);
      const row = r.find((x) => x.capability === capability);
      setCurrent(row?.model_entry_id ?? "");
      setResolvedBy(row?.resolved_by ?? "");
    } catch {
      /* swallow — UI shows blank */
    }
  }, [capability, orgId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const set = async (id: string) => {
    if (!id) return;
    setCurrent(id);
    await api("/api/v1/models/user-preferences", {
      method: "PUT",
      body: JSON.stringify({
        organization_id: orgId,
        capability,
        model_entry_id: id,
      }),
    });
    setResolvedBy("user");
  };

  return (
    <div className={`flex items-center gap-2 text-xs ${className ?? ""}`}>
      <span className="text-slate-500">{label ?? "Model:"}</span>
      <DkSelect value={current} onChange={(e) => set(e.target.value)}>
        <option value="">— pick —</option>
        {entries.map((e) => (
          <option key={e.id} value={e.id}>
            {e.display_name}
          </option>
        ))}
      </DkSelect>
      <span className="text-slate-400">{resolvedBy && `(${resolvedBy})`}</span>
    </div>
  );
}
