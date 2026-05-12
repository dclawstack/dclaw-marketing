"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";

/**
 * Top-level shell with nav. Hides the nav on auth pages so login /
 * first-login render full-screen.
 */
const AUTH_PATHS = new Set(["/login", "/first-login", "/forgot-password"]);

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  if (AUTH_PATHS.has(pathname)) {
    return <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>;
  }

  return (
    <>
      <nav className="border-b border-border bg-background">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <Link href="/" className="text-lg font-bold text-ink">
            DClaw Marketing
          </Link>
          <div className="flex flex-1 gap-4 text-sm">
            <Link href="/" className="text-muted-foreground hover:text-ink">
              Dashboard
            </Link>
            <Link href="/agents/creatives" className="text-muted-foreground hover:text-ink">
              Creatives
            </Link>
            <Link href="/inbox" className="text-muted-foreground hover:text-ink">
              Inbox
            </Link>
            <Link href="/campaigns" className="text-muted-foreground hover:text-ink">
              Campaigns
            </Link>
            <Link href="/leads" className="text-muted-foreground hover:text-ink">
              Leads
            </Link>
            {user?.is_superuser && (
              <Link href="/admin/users" className="text-muted-foreground hover:text-ink">
                Admin
              </Link>
            )}
          </div>
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">
                {user.full_name ?? user.email}
              </span>
              <Button variant="outline" size="sm" onClick={() => logout()}>
                Sign out
              </Button>
            </div>
          )}
        </div>
      </nav>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
    </>
  );
}
