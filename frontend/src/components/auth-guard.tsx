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

function isAuthPath(pathname: string): boolean {
  return AUTH_PATHS.has(pathname);
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;

    if (isAuthPath(pathname)) {
      // On auth pages: if user is already signed in and doesn't need
      // a reset, send them to the dashboard.
      if (user && !user.password_reset_required && pathname !== "/first-login") {
        router.replace("/");
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
