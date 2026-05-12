"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export interface DkSidebarItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
  disabled?: boolean;
}

export interface DkSidebarGroup {
  label?: string;
  items: DkSidebarItem[];
}

export interface DkSidebarProps {
  groups: DkSidebarGroup[];
  className?: string;
}

export function DkSidebar({ groups, className }: DkSidebarProps) {
  const pathname = usePathname();
  return (
    <aside
      className={cn(
        "w-60 shrink-0 border-r border-[var(--dk-border)] bg-white",
        className,
      )}
    >
      <nav className="flex flex-col gap-6 p-4">
        {groups.map((g, gi) => (
          <div key={g.label ?? `g-${gi}`} className="flex flex-col gap-1">
            {g.label && (
              <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-[var(--dk-fg-muted)]">
                {g.label}
              </p>
            )}
            {g.items.map((it) => {
              const active = pathname === it.href ||
                (it.href !== "/" && pathname?.startsWith(it.href));
              if (it.disabled) {
                return (
                  <span
                    key={it.href}
                    className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-[var(--dk-fg-muted)] cursor-not-allowed"
                  >
                    {it.icon && <span className="h-4 w-4">{it.icon}</span>}
                    <span className="flex-1">{it.label}</span>
                    {it.badge}
                  </span>
                );
              }
              return (
                <Link
                  key={it.href}
                  href={it.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast ease-out-quart",
                    active
                      ? "bg-[var(--dk-purple-50)] text-brand"
                      : "text-[var(--dk-fg-1)] hover:bg-[var(--dk-gray-50)] hover:text-ink",
                  )}
                >
                  {it.icon && <span className="h-4 w-4">{it.icon}</span>}
                  <span className="flex-1">{it.label}</span>
                  {it.badge}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
