"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { DkButton } from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";

/**
 * Client Portal layout — Phase 11 / Theme O.
 *
 * Distinct from the operator-facing app shell at /(auth)/layout.tsx.
 * The Client Portal is a stripped-down white-label surface the agency's
 * customer logs into to:
 *   - approve content their agency drafted
 *   - see the upcoming schedule (read-only)
 *   - view a white-label analytics summary
 *   - browse the approved-content gallery
 *
 * Auth is the same JWT — admin can scope users into a 'client' role
 * (already in OrganizationRole) and route them here on login.
 */
const NAV = [
  { href: "/client", label: "Overview" },
  { href: "/client/approvals", label: "Approvals" },
  { href: "/client/schedule", label: "Schedule" },
  { href: "/client/content", label: "Content" },
  { href: "/client/analytics", label: "Analytics" },
] as const;

export default function ClientPortalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-[var(--dk-bg)] flex flex-col">
      <header className="border-b border-[var(--dk-border)] bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/client"
              className="font-display text-lg font-semibold text-brand"
            >
              Client Portal
            </Link>
            <nav className="flex items-center gap-1">
              {NAV.map((n) => {
                const active = pathname === n.href;
                return (
                  <Link
                    key={n.href}
                    href={n.href}
                    className={
                      "rounded-pill px-3 py-1.5 text-sm transition-colors " +
                      (active
                        ? "bg-[var(--dk-purple-50)] text-brand font-semibold"
                        : "text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)]")
                    }
                  >
                    {n.label}
                  </Link>
                );
              })}
            </nav>
          </div>
          <DkButton variant="ghost" size="sm" onClick={() => void logout()}>
            Sign out
          </DkButton>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8 flex-1 w-full">
        {children}
      </main>
    </div>
  );
}
