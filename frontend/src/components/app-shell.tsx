"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { DkButton, DkAvatar, DkOrgSwitcher } from "@/components/dk";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

/**
 * Top-level app shell.
 *
 * Wraps every authenticated route in a sticky, brand-vocabulary top
 * nav and a brand-locked content container (max-w 1280px, 24px
 * gutters, 24px top padding).
 *
 * Auth pages (login / first-login / forgot-password) render edge-to-
 * edge with no nav.
 */
const AUTH_PATHS = new Set(["/login", "/first-login", "/forgot-password"]);

interface NavItem {
  label: string;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/" },
  { label: "Calendar", href: "/calendar" },
  { label: "Creatives", href: "/agents/creatives" },
  { label: "Inbox", href: "/inbox" },
  { label: "Library", href: "/library" },
  { label: "Orgs", href: "/orgs" },
  { label: "Campaigns", href: "/campaigns" },
  { label: "Leads", href: "/leads" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  if (AUTH_PATHS.has(pathname)) {
    return (
      <main className="mx-auto w-full max-w-container px-6 py-6">
        {children}
      </main>
    );
  }

  return (
    <>
      <header
        className={cn(
          // Sticky glass-blur header per BRAND_GUIDELINES §10 (transparency / blur).
          "sticky top-0 z-40 border-b border-[var(--dk-border)]",
          "bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/75",
        )}
      >
        <nav className="mx-auto flex h-[72px] max-w-container items-center gap-8 px-6">
          <Link
            href="/"
            className="flex items-center gap-2.5 group shrink-0"
            aria-label="DClaw Marketing — home"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/brand/logos/dclaw-icon-purple.svg"
              alt=""
              width={28}
              height={28}
              className="h-7 w-7 transition-transform duration-fast ease-out-quart group-hover:scale-105"
            />
            <span className="font-display text-lg font-bold tracking-snug text-ink leading-none">
              DClaw <span className="text-brand">Marketing</span>
            </span>
          </Link>

          {user && (
            <div className="hidden md:block shrink-0">
              <DkOrgSwitcher />
            </div>
          )}

          <div className="flex flex-1 items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <NavLink key={item.href} item={item} pathname={pathname} />
            ))}
            {user?.is_superuser && (
              <NavLink
                item={{ label: "Admin", href: "/admin/users" }}
                pathname={pathname}
                matchPrefix="/admin"
              />
            )}
          </div>

          {user && (
            <div className="flex items-center gap-3 shrink-0">
              <Link
                href="/settings/profile"
                className="flex items-center gap-3 rounded-md px-1 py-1 hover:bg-[var(--dk-gray-50)] transition-colors duration-fast"
                aria-label="Account settings"
              >
                <div className="hidden sm:flex flex-col items-end leading-tight">
                  <span className="text-sm font-medium text-ink">
                    {user.full_name ?? user.email}
                  </span>
                  {user.full_name && (
                    <span className="text-xs text-[var(--dk-fg-2)]">
                      {user.email}
                    </span>
                  )}
                </div>
                <DkAvatar
                  size="sm"
                  name={user.full_name ?? user.email}
                />
              </Link>
              <DkButton
                variant="secondary"
                size="sm"
                onClick={() => logout()}
              >
                Sign Out
              </DkButton>
            </div>
          )}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-container px-6 py-8">
        {children}
      </main>
    </>
  );
}

function NavLink({
  item,
  pathname,
  matchPrefix,
}: {
  item: NavItem;
  pathname: string;
  matchPrefix?: string;
}) {
  const active = matchPrefix
    ? pathname?.startsWith(matchPrefix)
    : pathname === item.href ||
      (item.href !== "/" && pathname?.startsWith(item.href));
  return (
    <Link
      href={item.href}
      className={cn(
        "rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast ease-out-quart",
        active
          ? "text-brand bg-[var(--dk-purple-50)]"
          : "text-[var(--dk-fg-1)] hover:text-ink hover:bg-[var(--dk-gray-50)]",
      )}
    >
      {item.label}
    </Link>
  );
}
