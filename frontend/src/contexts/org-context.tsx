"use client";

/**
 * Org context — exposes the list of organizations the current user
 * belongs to and the currently-selected one. Persists the selection
 * to localStorage so it survives reloads.
 *
 * Every page that operates on org-scoped resources (brand kits, KG,
 * projects, goals, etc.) should consume `useOrg().currentOrg` and
 * pass `currentOrg.id` to the relevant API call.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { Organization, listOrgs } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

const STORAGE_KEY = "dclaw_current_org_id";

interface OrgContextValue {
  orgs: Organization[];
  currentOrg: Organization | null;
  loading: boolean;
  error: string | null;
  setCurrentOrg: (org: Organization) => void;
  refresh: () => Promise<void>;
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export function OrgProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [currentOrgId, setCurrentOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!user) {
      setOrgs([]);
      setCurrentOrgId(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const list = await listOrgs();
      setOrgs(list);

      // Pick: stored choice if still valid; else first org; else null.
      const stored =
        typeof window !== "undefined"
          ? localStorage.getItem(STORAGE_KEY)
          : null;
      const valid = list.find((o) => o.id === stored);
      const next = valid?.id ?? list[0]?.id ?? null;
      setCurrentOrgId(next);
      if (next && typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, next);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load orgs.");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const setCurrentOrg = useCallback((org: Organization) => {
    setCurrentOrgId(org.id);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, org.id);
    }
  }, []);

  const currentOrg = useMemo(
    () => orgs.find((o) => o.id === currentOrgId) ?? null,
    [orgs, currentOrgId],
  );

  const value = useMemo<OrgContextValue>(
    () => ({ orgs, currentOrg, loading, error, setCurrentOrg, refresh }),
    [orgs, currentOrg, loading, error, setCurrentOrg, refresh],
  );

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>;
}

export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext);
  if (!ctx) throw new Error("useOrg must be used within <OrgProvider>");
  return ctx;
}
