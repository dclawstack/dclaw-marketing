"use client";

/**
 * /settings/2fa — TOTP enrollment + recovery codes UI (S4-G1).
 */

import { useEffect, useState } from "react";
import { Shield, ShieldCheck } from "lucide-react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
  DkPageHeader,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";
import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface SetupResponse {
  otpauth_url: string;
  secret_b32: string;
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

export default function TwoFAPage() {
  const { user } = useAuth();
  const enabled = !!(user as any)?.totp_enabled;
  const [setup, setSetup] = useState<SetupResponse | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [recovery, setRecovery] = useState<string[] | null>(null);

  const begin = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<SetupResponse>("/api/v1/me/2fa/setup", { method: "POST" });
      setSetup(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Setup failed.");
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/me/2fa/verify", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      setSuccess("2FA enabled.");
      try {
        const rc = await api<{ codes: string[] }>(
          "/api/v1/me/2fa/recovery-codes",
          { method: "POST" },
        );
        setRecovery(rc.codes);
      } catch {
        /* swallow */
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verify failed.");
    } finally {
      setBusy(false);
    }
  };

  const disable = async () => {
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/me/2fa/disable", {
        method: "POST",
        body: JSON.stringify({ code }),
      });
      setSuccess("2FA disabled.");
      setSetup(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Disable failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4 max-w-2xl">
      <DkPageHeader
        eyebrow="Security"
        title="Two-factor authentication"
        description="Add a TOTP authenticator (Google Authenticator, 1Password, Authy)."
      />

      {error && (
        <div className="rounded border border-rose-300 bg-rose-50 p-3 text-rose-700 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded border border-emerald-300 bg-emerald-50 p-3 text-emerald-800 text-sm">
          <ShieldCheck className="w-4 h-4 inline mr-1" /> {success}
        </div>
      )}

      <DkCard>
        <DkCardHeader>
          <DkCardTitle>
            <Shield className="w-4 h-4 inline mr-1" />
            {enabled ? "2FA is enabled" : "2FA is off"}
          </DkCardTitle>
        </DkCardHeader>
        <DkCardContent className="space-y-3">
          {!setup && !enabled && (
            <DkButton onClick={begin} disabled={busy}>
              {busy ? "Starting…" : "Set up 2FA"}
            </DkButton>
          )}
          {setup && (
            <>
              <div className="text-sm">
                Scan this URL with your authenticator, then enter the 6-digit code:
              </div>
              <pre className="text-xs bg-slate-100 p-2 rounded break-all">
                {setup.otpauth_url}
              </pre>
              <div>
                <DkLabel>Code</DkLabel>
                <DkInput
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="000000"
                  inputMode="numeric"
                />
              </div>
              <DkButton onClick={verify} disabled={busy || code.length !== 6}>
                Verify + enable
              </DkButton>
            </>
          )}
          {enabled && (
            <>
              <DkLabel>Enter a current code to disable</DkLabel>
              <DkInput
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="000000"
                inputMode="numeric"
              />
              <DkButton onClick={disable} disabled={busy || code.length !== 6}>
                Disable 2FA
              </DkButton>
            </>
          )}
        </DkCardContent>
      </DkCard>

      {recovery && (
        <DkCard>
          <DkCardHeader>
            <DkCardTitle>Recovery codes</DkCardTitle>
          </DkCardHeader>
          <DkCardContent>
            <div className="text-xs text-slate-500 mb-2">
              Store these somewhere safe. Each can be used once if you lose your
              authenticator.
            </div>
            <pre className="text-xs bg-slate-100 p-2 rounded">
              {recovery.join("\n")}
            </pre>
          </DkCardContent>
        </DkCard>
      )}
    </div>
  );
}
