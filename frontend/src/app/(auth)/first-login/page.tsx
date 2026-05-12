"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  DkButton,
  DkCard,
  DkCardContent,
  DkCardDescription,
  DkCardHeader,
  DkCardTitle,
  DkInput,
  DkLabel,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";
import { changePassword } from "@/lib/auth";

/**
 * Mandatory password-reset page. Reached after first login with an
 * admin-issued temp password. Cannot be skipped — middleware/guard
 * redirects here whenever password_reset_required is true.
 */
export default function FirstLoginPage() {
  const { user, refresh } = useAuth();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user && !user.password_reset_required) {
      router.replace("/");
    }
  }, [user, router]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 10) {
      setError("Password must be at least 10 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (newPassword === currentPassword) {
      setError("New password must differ from your current password.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword(currentPassword, newPassword);
      refresh();
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Password change failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-[calc(100vh-72px)] flex items-center justify-center py-12">
      <DkCard className="w-full max-w-md">
        <DkCardHeader className="gap-2 pt-8">
          <DkCardTitle className="text-2xl">Set Your Password</DkCardTitle>
          <DkCardDescription>
            Your admin issued a temporary password. Replace it before continuing.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="current">Current (temp) password</DkLabel>
              <DkInput
                id="current"
                type="password"
                autoComplete="current-password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <DkLabel
                htmlFor="new"
                description="At least 10 characters; must differ from your email's local part."
              >
                New password
              </DkLabel>
              <DkInput
                id="new"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="confirm">Confirm new password</DkLabel>
              <DkInput
                id="confirm"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={submitting}
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
            <DkButton
              type="submit"
              className="w-full mt-2"
              loading={submitting}
              disabled={
                submitting ||
                !currentPassword ||
                !newPassword ||
                !confirmPassword
              }
            >
              {submitting ? "Saving" : "Set Password and Continue"}
            </DkButton>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
