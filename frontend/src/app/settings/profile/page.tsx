"use client";

import {
  DkAvatar,
  DkBadge,
  DkCard,
  DkCardContent,
  DkPageHeader,
} from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";

export default function ProfileSettingsPage() {
  const { user, loading } = useAuth();

  if (loading || !user) {
    return <p className="text-[var(--dk-fg-2)]">Loading…</p>;
  }

  const rows: { label: string; value: React.ReactNode }[] = [
    { label: "Email", value: <span className="font-mono">{user.email}</span> },
    { label: "Full name", value: user.full_name ?? "—" },
    {
      label: "Status",
      value: user.is_active ? (
        <DkBadge tone="success">active</DkBadge>
      ) : (
        <DkBadge tone="neutral">revoked</DkBadge>
      ),
    },
    {
      label: "Role",
      value: user.is_superuser ? (
        <DkBadge tone="brand">admin</DkBadge>
      ) : (
        <DkBadge tone="neutral">user</DkBadge>
      ),
    },
    {
      label: "Verified",
      value: user.is_verified ? (
        <DkBadge tone="success">yes</DkBadge>
      ) : (
        <DkBadge tone="warning">pending</DkBadge>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <DkPageHeader
        eyebrow="Account"
        title="Profile"
        description="Your DClaw Marketing identity. Email and full name updates land in a future iteration — let your admin know if you need a correction now."
      />

      <DkCard>
        <DkCardContent>
          <div className="flex items-center gap-4 pb-4">
            <DkAvatar size="lg" name={user.full_name ?? user.email} />
            <div className="flex flex-col">
              <p className="font-display text-xl font-semibold text-ink">
                {user.full_name ?? user.email}
              </p>
              {user.full_name && (
                <p className="text-sm text-[var(--dk-fg-2)]">{user.email}</p>
              )}
            </div>
          </div>
          <dl className="divide-y divide-[var(--dk-border)]">
            {rows.map((r) => (
              <div
                key={r.label}
                className="grid grid-cols-[160px_1fr] gap-4 py-3 items-center"
              >
                <dt className="text-sm font-medium text-[var(--dk-fg-2)]">
                  {r.label}
                </dt>
                <dd className="text-sm text-ink">{r.value}</dd>
              </div>
            ))}
          </dl>
        </DkCardContent>
      </DkCard>
    </div>
  );
}
