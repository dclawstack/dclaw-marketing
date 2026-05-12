"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import { KeyRound, User } from "lucide-react";

import { DkSidebar, DkSidebarGroup } from "@/components/dk";

const GROUPS: DkSidebarGroup[] = [
  {
    label: "Account",
    items: [
      { label: "Profile", href: "/settings/profile", icon: <User className="h-4 w-4" /> },
      { label: "Password", href: "/settings/password", icon: <KeyRound className="h-4 w-4" /> },
    ],
  },
];

export default function SettingsLayout({ children }: { children: ReactNode }) {
  // We don't actually use pathname here; DkSidebar reads it internally.
  // (kept the import to opt into client-side rendering for future
  // tab-specific behavior.)
  usePathname();
  return (
    <div className="flex gap-8">
      <DkSidebar groups={GROUPS} className="border-r-0" />
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  );
}
