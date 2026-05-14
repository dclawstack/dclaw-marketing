"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Maximize2, MessageSquare, X } from "lucide-react";

import { DkAgentChat, DkButton } from "@/components/dk";
import { ModelSettingsPanel } from "@/components/model-settings-panel";
import { useOrg } from "@/contexts/org-context";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "dclaw.agent-dock.open.v1";

/**
 * Global agent chat dock — floating bubble at the bottom-right of every
 * page. Clicking opens a 420px slide-in panel with the Conductor agent.
 *
 * State persists in localStorage so the user's preference survives
 * navigation. The dock hides itself on auth-only routes (login, etc.) —
 * those routes don't render the AppShell, so this component never
 * reaches them.
 */
// S4-C1/C2 — page-to-context map: which slice of the platform the
// docked Conductor should focus on while the user is on that route.
const PAGE_CONTEXT: { match: RegExp; label: string }[] = [
  { match: /^\/calendar/, label: "calendar" },
  { match: /^\/leads/, label: "leads" },
  { match: /^\/agents\/creatives/, label: "creatives" },
  { match: /^\/agents\/seo/, label: "seo" },
  { match: /^\/agents\/smm/, label: "smm" },
  { match: /^\/agents\/paid-media/, label: "paid_media" },
  { match: /^\/agents\/analyst/, label: "analyst" },
  { match: /^\/inbox/, label: "inbox" },
  { match: /^\/campaigns/, label: "campaigns" },
  { match: /^\/admin\/models/, label: "model_registry" },
];

export function AgentDock() {
  const { currentOrg } = useOrg();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const pageContext =
    PAGE_CONTEXT.find((p) => p.match.test(pathname || ""))?.label ?? "general";

  useEffect(() => {
    if (typeof window === "undefined") return;
    setOpen(window.localStorage.getItem(STORAGE_KEY) === "1");
  }, []);

  function toggle() {
    setOpen((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      }
      return next;
    });
  }

  // Hide entirely when no Org is in scope — the agent chat needs an Org id
  // to find-or-create its thread.
  if (!currentOrg) return null;

  return (
    <>
      {/* Trigger button — always visible */}
      <button
        type="button"
        onClick={toggle}
        aria-label={open ? "Close Conductor chat" : "Open Conductor chat"}
        className={cn(
          "fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full px-4 py-3 shadow-lg transition-colors",
          "bg-brand text-white hover:bg-[var(--dk-purple-800)]",
        )}
      >
        {open ? (
          <X className="h-5 w-5" />
        ) : (
          <MessageSquare className="h-5 w-5" />
        )}
        <span className="hidden sm:inline text-sm font-medium">
          {open ? "Close" : "Conductor"}
        </span>
      </button>

      {/* Slide-in panel */}
      <aside
        aria-hidden={!open}
        className={cn(
          "fixed top-0 right-0 z-40 h-full w-[420px] max-w-[100vw] bg-white border-l border-[var(--dk-border)] shadow-2xl transition-transform duration-200",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex h-full flex-col">
          <header className="flex items-center justify-between border-b border-[var(--dk-border)] px-4 py-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-[var(--dk-fg-3)]">
                Conductor · {pageContext}
              </div>
              <div className="font-medium">{currentOrg.name}</div>
            </div>
            <div className="flex items-center gap-1">
              <Link href="/conductor" title="Open full-screen">
                <DkButton variant="ghost" size="sm" aria-label="Full-screen">
                  <Maximize2 className="h-4 w-4" />
                </DkButton>
              </Link>
              <DkButton
                variant="ghost"
                size="sm"
                onClick={toggle}
                aria-label="Close dock"
              >
                <X className="h-4 w-4" />
              </DkButton>
            </div>
          </header>
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="px-3 pt-3">
              <ModelSettingsPanel orgId={currentOrg.id} />
            </div>
            <div className="flex-1 overflow-hidden">
              {open ? <DkAgentChat kind="conductor" /> : null}
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
