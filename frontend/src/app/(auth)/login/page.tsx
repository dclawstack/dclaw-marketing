"use client";

import { FormEvent, useState } from "react";

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

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-[calc(100vh-72px)] flex items-center justify-center py-12">
      <DkCard className="w-full max-w-md">
        <DkCardHeader className="gap-3 pt-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/brand/logos/dclaw-icon-purple.svg"
            alt=""
            className="h-10 w-10"
          />
          <DkCardTitle className="text-3xl">DClaw Marketing</DkCardTitle>
          <DkCardDescription>
            Sign in to your workspace.
          </DkCardDescription>
        </DkCardHeader>
        <DkCardContent>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="email" required>
                Email
              </DkLabel>
              <DkInput
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                disabled={submitting}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <DkLabel htmlFor="password" required>
                Password
              </DkLabel>
              <DkInput
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
              disabled={submitting || !email || !password}
            >
              {submitting ? "Signing In" : "Sign In"}
            </DkButton>
            <p className="pt-2 text-center text-sm text-[var(--dk-fg-2)]">
              New users are created by an administrator — contact your admin for an account.
            </p>
          </form>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
