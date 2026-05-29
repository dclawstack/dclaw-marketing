"use client";

/**
 * DemoControls — removable landing-page widget that drives the backend
 * /api/v1/demo/* endpoints (status / seed / reset). On seed success it
 * auto-logs-in the returned demo user and stores the JWT, then offers a
 * button into the dashboard.
 *
 * To remove the demo feature, delete this file and the block wrapped in
 * the DEMO CONTROLS comment markers in app/page.tsx (plus the backend
 * demo router — see backend/app/api/v1/demo.py).
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Database,
  Play,
  RefreshCw,
  Terminal,
  Trash2,
} from "lucide-react";

import { login as doLogin } from "@/lib/auth";

interface DemoCredentials {
  email: string;
  password: string;
  name: string;
}

interface DemoStatus {
  enabled: boolean;
  seeded: boolean;
  organization_id: string | null;
  counts: Record<string, number>;
  credentials: DemoCredentials | null;
}

type Phase = "loading" | "ready" | "unavailable";

export function DemoControls() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [busy, setBusy] = useState(false);
  const [signedIn, setSignedIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/demo/status");
      if (!res.ok) throw new Error(`status ${res.status}`);
      const s = (await res.json()) as DemoStatus;
      setStatus(s);
      setPhase(s.enabled ? "ready" : "unavailable");
    } catch {
      // Backend unreachable or demo disabled — hide the live controls.
      setStatus(null);
      setPhase("unavailable");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleSeed() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/demo/seed", { method: "POST" });
      if (!res.ok) throw new Error(`Seed failed (${res.status})`);
      const s = (await res.json()) as DemoStatus;
      setStatus(s);
      if (s.credentials) {
        // Log in as the demo user the seed just created (stores the JWT).
        await doLogin(s.credentials.email, s.credentials.password);
        setSignedIn(true);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Seed failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleReset() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/v1/demo/reset", { method: "DELETE" });
      if (!res.ok) throw new Error(`Reset failed (${res.status})`);
      const s = (await res.json()) as DemoStatus;
      setStatus(s);
      setSignedIn(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="border-y border-[var(--dk-border)] bg-[var(--dk-purple-50)]">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid items-center gap-8 lg:grid-cols-[1fr_auto]">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand">
              <Database className="h-3 w-3" /> Try the demo
            </div>
            <h2 className="mt-3 text-3xl font-bold text-ink">
              Spin up a sample workspace in one click.
            </h2>
            <p className="mt-3 max-w-2xl text-[var(--dk-fg-1)]">
              Seeds a demo organization (Acme Demo Co.) with a brand kit, a
              project, a couple of campaigns, sample leads across the funnel,
              and a loginable demo user. Everything lives under one demo Org so
              Clear removes exactly what was seeded.
            </p>

            {phase === "ready" && status?.seeded && (
              <>
                <p className="mt-3 text-sm text-[var(--dk-fg-1)]">
                  <strong>Seeded:</strong>{" "}
                  {Object.entries(status.counts)
                    .map(([k, v]) => `${v} ${k}`)
                    .join(" · ")}
                </p>
                {status.credentials && (
                  <p className="mt-2 text-xs text-[var(--dk-fg-2)]">
                    Sign in with{" "}
                    <code className="rounded bg-white px-1.5 py-0.5 font-mono text-brand">
                      {status.credentials.email}
                    </code>{" "}
                    / password{" "}
                    <code className="rounded bg-white px-1.5 py-0.5 font-mono text-brand">
                      {status.credentials.password}
                    </code>
                  </p>
                )}
              </>
            )}

            {phase === "unavailable" && (
              <div className="mt-5 rounded-xl border border-[var(--dk-border)] bg-white p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
                  <Terminal className="h-4 w-4 text-brand" />
                  Demo backend not connected
                </div>
                <p className="text-sm text-[var(--dk-fg-2)]">
                  No live API is reachable, or demo mode is off. Run the full
                  stack with{" "}
                  <code className="rounded bg-[var(--dk-gray-50)] px-1 py-0.5 font-mono">
                    ENABLE_DEMO_MODE=true
                  </code>{" "}
                  to activate this section.
                </p>
              </div>
            )}

            {error && (
              <div className="mt-3 rounded-lg border border-[var(--dk-danger)] bg-[var(--dk-danger-bg)] p-3 text-sm text-[var(--dk-danger)]">
                {error}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row lg:flex-col">
            {phase === "loading" && (
              <div className="text-xs text-[var(--dk-fg-2)]">
                Checking demo backend…
              </div>
            )}

            {phase === "ready" && !status?.seeded && (
              <button
                type="button"
                onClick={handleSeed}
                disabled={busy}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white shadow hover:opacity-90 disabled:opacity-50"
              >
                <Play className="h-4 w-4" />
                {busy ? "Seeding…" : "Seed demo data"}
              </button>
            )}

            {phase === "ready" && status?.seeded && (
              <>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white shadow hover:opacity-90"
                >
                  {signedIn ? "Enter the dashboard" : "Open the dashboard"}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <button
                  type="button"
                  onClick={handleSeed}
                  disabled={busy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--dk-border)] bg-white px-5 py-3 text-sm font-semibold text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)] disabled:opacity-50"
                >
                  <RefreshCw className="h-4 w-4" />
                  {busy ? "Re-seeding…" : "Re-seed"}
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={busy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--dk-danger)] bg-white px-5 py-3 text-sm font-semibold text-[var(--dk-danger)] hover:bg-[var(--dk-danger-bg)] disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Clear demo data
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
