"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { getToken } from "@/lib/auth";
import {
  BarChart3,
  Bot,
  Box,
  Calendar,
  Inbox as InboxIcon,
  Layers,
  LayoutDashboard,
  LibrarySquare,
  Mail,
  Megaphone,
  Network,
  Palette,
  Plug,
  Search,
  Settings,
  Shield,
  Workflow,
  type LucideIcon,
} from "lucide-react";

import { DkButton, DkAvatar, DkOrgSwitcher } from "@/components/dk";
import { AgentDock } from "@/components/agent-dock";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

const AUTH_PATHS = new Set(["/login", "/first-login", "/forgot-password"]);

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  matchPrefix?: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
  /** Visible only if the user is a superadmin OR an org-admin on at least one
   * org. Org-level admin status is detected via the auth context. */
  adminOnly?: boolean;
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard },
    ],
  },
  {
    label: "Work",
    items: [
      { label: "Conductor", href: "/agent", icon: Bot },
      { label: "Inbox", href: "/inbox", icon: InboxIcon },
      { label: "Calendar", href: "/calendar", icon: Calendar },
    ],
  },
  {
    label: "Content",
    items: [
      { label: "Creatives", href: "/agents/creatives", icon: Palette },
      { label: "Library", href: "/library", icon: LibrarySquare },
      { label: "Workflows", href: "/workflows", icon: Workflow },
    ],
  },
  {
    label: "Channels",
    items: [
      { label: "Channels", href: "/channels", icon: Megaphone },
      { label: "Email", href: "/email", icon: Mail },
      { label: "Ads", href: "/ads", icon: Layers },
    ],
  },
  {
    label: "Insights",
    items: [
      { label: "SEO", href: "/agents/seo", icon: Search },
      { label: "Analytics", href: "/analytics", icon: BarChart3 },
      { label: "Knowledge", href: "/knowledge", icon: Network },
    ],
  },
  {
    label: "Admin",
    adminOnly: true,
    items: [
      { label: "Integrations", href: "/integrations", icon: Plug },
      { label: "Orgs", href: "/orgs", icon: Settings },
      {
        label: "Users",
        href: "/admin/users",
        icon: Shield,
        matchPrefix: "/admin/users",
      },
      {
        label: "Models",
        href: "/admin/models",
        icon: Box,
        matchPrefix: "/admin/models",
      },
    ],
  },
];

interface AdminOrgStatus {
  is_superuser: boolean;
  admin_org_ids: string[];
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [adminStatus, setAdminStatus] = useState<AdminOrgStatus | null>(null);

  useEffect(() => {
    if (!user) {
      setAdminStatus(null);
      return;
    }
    fetch("/api/v1/me/admin-orgs", {
      headers: { Authorization: `Bearer ${getToken()}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then(setAdminStatus)
      .catch(() => setAdminStatus(null));
  }, [user]);

  const isAdmin =
    !!user?.is_superuser ||
    (adminStatus?.admin_org_ids?.length ?? 0) > 0;

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
          // Sticky glass-blur header per BRAND_GUIDELINES §10.
          "sticky top-0 z-40 border-b border-[var(--dk-border)]",
          "bg-white/85 backdrop-blur supports-[backdrop-filter]:bg-white/75",
        )}
      >
        <nav className="mx-auto flex h-[72px] items-center gap-6 px-6">
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

          <div className="flex-1" />

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
                <DkAvatar size="sm" name={user.full_name ?? user.email} />
              </Link>
              <DkButton variant="secondary" size="sm" onClick={() => logout()}>
                Sign Out
              </DkButton>
            </div>
          )}
        </nav>
      </header>

      <div className="flex">
        <aside
          className={cn(
            "sticky top-[72px] z-30 h-[calc(100vh-72px)] w-60 shrink-0",
            "border-r border-[var(--dk-border)] bg-white",
            "overflow-y-auto py-4",
          )}
          aria-label="Primary navigation"
        >
          <nav className="flex flex-col gap-5 px-3">
            {NAV_GROUPS.filter((g) => !g.adminOnly || isAdmin).map((group) => (
              <div key={group.label} className="flex flex-col gap-1">
                <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-[var(--dk-fg-2)]">
                  {group.label}
                </p>
                {group.items.map((item) => (
                  <SidebarLink
                    key={item.href}
                    item={item}
                    pathname={pathname}
                  />
                ))}
              </div>
            ))}
          </nav>
        </aside>

        <main className="flex-1 min-w-0 px-6 py-8">
          <div className="mx-auto w-full max-w-container">{children}</div>
        </main>
      </div>

      <AgentDock />
    </>
  );
}

function SidebarLink({
  item,
  pathname,
}: {
  item: NavItem;
  pathname: string;
}) {
  const Icon = item.icon;
  const active = item.matchPrefix
    ? pathname?.startsWith(item.matchPrefix)
    : pathname === item.href ||
      (item.href !== "/" && pathname?.startsWith(item.href));
  return (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium",
        "transition-colors duration-fast ease-out-quart",
        active
          ? "text-brand bg-[var(--dk-purple-50)]"
          : "text-[var(--dk-fg-1)] hover:text-ink hover:bg-[var(--dk-gray-50)]",
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span>{item.label}</span>
    </Link>
  );
}
