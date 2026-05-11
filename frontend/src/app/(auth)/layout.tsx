import type { ReactNode } from "react";

/**
 * Auth pages layout — centered card on a brand background.
 * AppShell hides the global nav on these routes, so this is the
 * full visible surface.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="-mx-4 -my-6 flex min-h-screen items-center justify-center bg-muted px-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
