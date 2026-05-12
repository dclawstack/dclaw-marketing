"use client";

import { useEffect, useState } from "react";
import { Flame, Loader2, RefreshCw } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkEmptyState,
  DkPageHeader,
  DkSelect,
} from "@/components/dk";
import { useOrg } from "@/contexts/org-context";
import { getToken } from "@/lib/auth";

type HeatmapResponse = {
  organization_id: string;
  window_days: number;
  channel: string | null;
  total: number;
  max: number;
  grid: number[][]; // 7×24
};

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

async function authFetch<T>(path: string): Promise<T> {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function cellColor(count: number, max: number): string {
  if (max === 0 || count === 0) return "var(--dk-gray-100)";
  const ratio = count / max;
  // Interpolate purple-50 → purple-900
  // Map ratio [0,1] to alpha [0.08, 1.0]
  const alpha = 0.08 + ratio * 0.92;
  return `rgba(74, 56, 120, ${alpha.toFixed(3)})`;
}

export default function HeatmapPage() {
  const { currentOrg } = useOrg();
  const [data, setData] = useState<HeatmapResponse | null>(null);
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!currentOrg) return;
    setLoading(true);
    setError(null);
    try {
      const d = await authFetch<HeatmapResponse>(
        `/api/v1/orgs/${currentOrg.id}/analytics/heatmap?days=${days}`,
      );
      setData(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load heatmap.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [currentOrg, days]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Analytics · Theme F2"
        title="Content performance heatmap"
        description="Day-of-week × hour-of-day touchpoint density over the selected window. Surfaces 'when is my audience actually paying attention?' without leaving the dashboard."
        actions={
          <div className="flex items-center gap-2">
            <DkSelect
              value={String(days)}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-32"
            >
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
              <option value="180">180 days</option>
            </DkSelect>
            <DkButton onClick={refresh} disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
              Refresh
            </DkButton>
          </div>
        }
      />

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
          icon={<Flame className="h-6 w-6" />}
          title="Pick an organization"
          description="Heatmap is per-Org — use the workspace switcher."
        />
      ) : !data ? (
        <DkEmptyState
          icon={<Flame className="h-6 w-6" />}
          title="Loading…"
          description="Aggregating touchpoints."
        />
      ) : data.total === 0 ? (
        <DkEmptyState
          icon={<Flame className="h-6 w-6" />}
          title="No touchpoints in window"
          description="Drive some traffic (publish posts, run ads) and come back."
        />
      ) : (
        <>
          <div className="flex items-center gap-2 text-sm opacity-70">
            <DkBadge tone="brand">{data.total.toLocaleString()} touchpoints</DkBadge>
            <span>over the last {data.window_days} days</span>
            <span className="ml-auto text-xs opacity-60">
              max cell = {data.max}
            </span>
          </div>

          <DkCard>
            <DkCardContent>
              <div className="overflow-x-auto">
                <table className="border-collapse text-xs">
                  <thead>
                    <tr>
                      <th className="w-12 p-1"></th>
                      {Array.from({ length: 24 }, (_, h) => (
                        <th
                          key={h}
                          className="p-1 text-center font-mono text-[10px] opacity-60 w-8"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.grid.map((row, dayIdx) => (
                      <tr key={dayIdx}>
                        <td className="pr-2 font-mono text-[10px] opacity-60 text-right">
                          {DAYS[dayIdx]}
                        </td>
                        {row.map((count, hr) => (
                          <td
                            key={hr}
                            className="border border-white"
                            title={`${DAYS[dayIdx]} ${hr}:00 — ${count} touchpoints`}
                            style={{
                              backgroundColor: cellColor(count, data.max),
                              width: 28,
                              height: 22,
                            }}
                          >
                            <span
                              className="block text-center font-mono leading-none"
                              style={{
                                color:
                                  count > data.max * 0.5
                                    ? "white"
                                    : "var(--dk-fg-2)",
                                fontSize: "9px",
                              }}
                            >
                              {count > 0 ? count : ""}
                            </span>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DkCardContent>
          </DkCard>

          <div className="flex items-center gap-2 text-xs opacity-60">
            <span>Low</span>
            <div className="h-3 w-32 rounded-sm bg-gradient-to-r from-[var(--dk-gray-100)] to-[#4A3878]" />
            <span>High</span>
          </div>
        </>
      )}
    </div>
  );
}
