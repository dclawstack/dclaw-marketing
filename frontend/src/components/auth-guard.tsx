"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";

import { useAuth } from "@/contexts/auth-context";

/**
 * Client-side route guard. Auth pages (/login, /first-login, etc.)
 * are exempt; everything else requires an authenticated user with no
 * pending password reset.
 */
const AUTH_PATHS = new Set(["/login", "/first-login", "/forgot-password"]);

// Public, non-gated routes. "/" is the marketing landing page — anyone
// can view it whether signed in or not.
const PUBLIC_PATHS = new Set(["/"]);

function isAuthPath(pathname: string): boolean {
  return AUTH_PATHS.has(pathname);
}

function isPublicPath(pathname: string): boolean {
  return PUBLIC_PATHS.has(pathname);
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;

    // Public landing renders for everyone — no redirect either way.
    if (isPublicPath(pathname)) return;

    if (isAuthPath(pathname)) {
      // On auth pages: if user is already signed in and doesn't need
      // a reset, send them to the dashboard.
      if (user && !user.password_reset_required && pathname !== "/first-login") {
        router.replace("/dashboard");
      }
      return;
    }

    // Protected pages:
    if (!user) {
      router.replace("/login");
      return;
    }
    if (user.password_reset_required) {
      router.replace("/first-login");
    }
  }, [loading, user, pathname, router]);

  if (isPublicPath(pathname)) {
    // Public landing renders unconditionally for anon + signed-in users,
    // even before auth bootstrap finishes (no gating, no loading flash).
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }

  if (isAuthPath(pathname)) {
    // Auth pages render unconditionally (the effect above handles
    // the "already-signed-in" redirect)
    return <>{children}</>;
  }

  if (!user || user.password_reset_required) {
    // Redirect is in flight; render nothing to avoid a flash
    return null;
  }

  return <>{children}</>;
}
