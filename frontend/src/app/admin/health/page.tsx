"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, Loader2, RefreshCw, ServerCrash } from "lucide-react";

import {
  DkBadge,
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkPageHeader,
  DkSkeleton,
} from "@/components/dk";
import { getToken } from "@/lib/auth";

type Check = { ok: boolean; detail: string | null };
type HealthResponse = { all_ok: boolean; checks: Record<string, Check> };

const PRETTY: Record<string, string> = {
  postgres: "PostgreSQL",
  redis: "Redis",
  minio: "MinIO / S3",
  anthropic: "Anthropic API",
  resend: "Resend (email)",
};

export default function AdminHealthPage() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/health/dependencies", {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) throw new Error(await res.text());
      const j = (await res.json()) as HealthResponse;
      setData(j);
      setLastChecked(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Probe failed.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Admin · §6.12"
        title="Dependency health"
        description="Probes Postgres, Redis, MinIO, Anthropic, and Resend in parallel. Used by oncall to triage outages without SSH."
        actions={
          <DkButton onClick={refresh} disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            Re-probe
          </DkButton>
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

      {loading && !data ? (
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <DkSkeleton key={i} className="h-20" />
          ))}
        </div>
      ) : data ? (
        <>
          <DkCard>
            <DkCardContent className="flex items-center gap-3 py-4">
              {data.all_ok ? (
                <CheckCircle2 className="h-5 w-5 text-[var(--dk-success)]" />
              ) : (
                <ServerCrash className="h-5 w-5 text-[var(--dk-danger)]" />
              )}
              <div className="font-semibold">
                {data.all_ok
                  ? "All dependencies healthy"
                  : "One or more dependencies are unhealthy"}
              </div>
              {lastChecked ? (
                <div className="ml-auto text-sm opacity-60">
                  last probed {lastChecked.toLocaleTimeString()}
                </div>
              ) : null}
            </DkCardContent>
          </DkCard>

          <div className="grid gap-3 md:grid-cols-2">
            {Object.entries(data.checks).map(([name, check]) => (
              <DkCard key={name}>
                <DkCardHeader>
                  <DkCardTitle className="text-base">
                    {PRETTY[name] ?? name}
                  </DkCardTitle>
                </DkCardHeader>
                <DkCardContent className="flex items-center gap-2 py-2">
                  <DkBadge tone={check.ok ? "success" : "danger"}>
                    {check.ok ? "ok" : "fail"}
                  </DkBadge>
                  {check.detail ? (
                    <span className="text-sm opacity-70">{check.detail}</span>
                  ) : (
                    <span className="text-sm opacity-50">no detail</span>
                  )}
                </DkCardContent>
              </DkCard>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
