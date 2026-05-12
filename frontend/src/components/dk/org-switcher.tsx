"use client";

import * as React from "react";
import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/utils";
import { useOrg } from "@/contexts/org-context";

/**
 * Org switcher dropdown — appears in the top nav between the logo and
 * the main nav links. Click to open a popover listing the user's
 * organizations + a "Create organization" link.
 */
export function DkOrgSwitcher() {
  const { orgs, currentOrg, setCurrentOrg, loading } = useOrg();
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-[var(--dk-border)] bg-white px-3 py-1.5 text-sm text-[var(--dk-fg-2)] min-w-[180px]">
        <Building2 className="h-4 w-4" />
        <span>Loading…</span>
      </div>
    );
  }

  if (orgs.length === 0) {
    return (
      <Link
        href="/orgs/new"
        className="flex items-center gap-2 rounded-md border border-dashed border-[var(--dk-border-strong)] bg-white px-3 py-1.5 text-sm font-medium text-brand hover:bg-[var(--dk-purple-50)] transition-colors duration-fast min-w-[180px]"
      >
        <Plus className="h-4 w-4" />
        Create your first organization
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={cn(
          "flex items-center gap-2 rounded-md border bg-white px-3 py-1.5 text-sm font-medium transition-all duration-fast ease-out-quart min-w-[200px]",
          open
            ? "border-brand shadow-[0_0_0_3px_var(--dk-purple-100)]"
            : "border-[var(--dk-border-strong)] hover:border-brand",
        )}
      >
        <Building2 className="h-4 w-4 text-brand shrink-0" />
        <span className="flex-1 text-left text-ink truncate">
          {currentOrg?.name ?? "Select organization"}
        </span>
        <ChevronsUpDown className="h-3.5 w-3.5 text-[var(--dk-fg-2)] shrink-0" />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 top-full mt-1.5 z-50 w-72 rounded-2xl border border-[var(--dk-border)] bg-white shadow-md overflow-hidden"
        >
          <div className="px-3 py-2 border-b border-[var(--dk-border)]">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--dk-fg-muted)]">
              Organizations
            </p>
          </div>
          <div className="max-h-64 overflow-auto py-1">
            {orgs.map((o) => {
              const active = o.id === currentOrg?.id;
              return (
                <button
                  key={o.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => {
                    setCurrentOrg(o);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2 px-3 py-2 text-sm text-left transition-colors duration-fast",
                    active
                      ? "bg-[var(--dk-purple-50)] text-brand"
                      : "text-ink hover:bg-[var(--dk-gray-50)]",
                  )}
                >
                  <Building2 className="h-4 w-4 shrink-0" />
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="truncate font-medium">{o.name}</span>
                    <span className="text-xs text-[var(--dk-fg-2)] font-mono">
                      {o.slug}
                    </span>
                  </div>
                  {active && <Check className="h-4 w-4 shrink-0" />}
                </button>
              );
            })}
          </div>
          <div className="border-t border-[var(--dk-border)]">
            <Link
              href="/orgs/new"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-3 py-2.5 text-sm font-medium text-brand hover:bg-[var(--dk-purple-50)] transition-colors duration-fast"
            >
              <Plus className="h-4 w-4" />
              Create organization
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
