"use client";

import { FormEvent, useState } from "react";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkInput,
  DkLabel,
  DkPageHeader,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";
import { changePassword } from "@/lib/auth";

export default function PasswordSettingsPage() {
  const { refresh } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (next.length < 10) {
      setError("Password must be at least 10 characters.");
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (next === current) {
      setError("New password must differ from your current password.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(current, next);
      refresh();
      setSuccess(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <DkPageHeader
        eyebrow="Account · Security"
        title="Password"
        description="Use a long, unique password. We store an Argon2 hash; never the plaintext."
      />

      <DkCard>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="current" required>
                Current password
              </DkLabel>
              <DkInput
                id="current"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <DkLabel
                htmlFor="next"
                required
                description="At least 10 characters; must differ from your email's local part."
              >
                New password
              </DkLabel>
              <DkInput
                id="next"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={next}
                onChange={(e) => setNext(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="confirm" required>
                Confirm new password
              </DkLabel>
              <DkInput
                id="confirm"
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                disabled={submitting}
                required
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
            {success && (
              <div
                role="status"
                className="rounded-md border border-[var(--dk-success)] bg-[var(--dk-success-bg)] px-3 py-2 text-sm text-[var(--dk-success)]"
              >
                Password updated.
              </div>
            )}

            <div className="pt-2">
              <DkButton
                type="submit"
                loading={submitting}
                disabled={submitting || !current || !next || !confirm}
              >
                Update Password
              </DkButton>
            </div>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
