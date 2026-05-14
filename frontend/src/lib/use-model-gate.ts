/**
 * Model gate hook (S4-M15).
 *
 * `useModelGate("creatives_agent")` returns `{loading, gated, missing,
 * componentStatus}` so a page can short-circuit to an onboarding modal
 * when the org's Feature Availability matrix reports a required
 * capability is missing.
 *
 * Companion `<ModelGateBanner />` renders the standard onboarding
 * prompt (which links to /admin/models).
 */

import { useCallback, useEffect, useState } from "react";

import { getToken } from "@/lib/auth";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export interface ComponentAvailability {
  required: string[];
  covered: string[];
  missing: string[];
  status: "full" | "partial" | "none";
}

interface FeatureAvailability {
  components: Record<string, ComponentAvailability>;
  capabilities: Record<string, { available: boolean; model_count: number; healthy_count: number }>;
}

interface GateState {
  loading: boolean;
  error: string | null;
  gated: boolean; // true when component is "none" or "partial" with required missing
  missing: string[];
  componentStatus: ComponentAvailability["status"] | null;
}

export function useModelGate(component: string): GateState {
  const [state, setState] = useState<GateState>({
    loading: true,
    error: null,
    gated: false,
    missing: [],
    componentStatus: null,
  });

  const fetchOnce = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const r = await fetch(`${API}/api/v1/models/feature-availability`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
      const data = (await r.json()) as FeatureAvailability;
      const comp = data.components[component];
      if (!comp) {
        setState({
          loading: false,
          error: null,
          gated: false,
          missing: [],
          componentStatus: null,
        });
        return;
      }
      setState({
        loading: false,
        error: null,
        gated: comp.status !== "full",
        missing: comp.missing,
        componentStatus: comp.status,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : "Unknown",
      }));
    }
  }, [component]);

  useEffect(() => {
    fetchOnce();
  }, [fetchOnce]);

  return state;
}
