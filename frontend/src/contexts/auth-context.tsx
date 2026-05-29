"use client";

/**
 * Auth context — exposes the current user + login/logout to client
 * components. Bootstraps from localStorage on mount.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { AuthUser, clearToken, getUser, login as doLogin, logout as doLogout } from "@/lib/auth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refresh: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    setUser(getUser());
    setLoading(false);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const u = await doLogin(email, password);
      setUser(u);
      if (u.password_reset_required) {
        router.push("/first-login");
      } else {
        router.push("/dashboard");
      }
      return u;
    },
    [router],
  );

  const logout = useCallback(async () => {
    await doLogout();
    setUser(null);
    router.push("/login");
  }, [router]);

  const refresh = useCallback(() => {
    setUser(getUser());
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
