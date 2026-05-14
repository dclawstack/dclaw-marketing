"use client";

import Link from "next/link";

import { DkButton } from "@/components/dk";
import { useModelGate } from "@/lib/use-model-gate";

/**
 * Renders an inline onboarding prompt when the requested component has
 * missing required capabilities (S4-M15).
 *
 * Returns null when the component is fully available.
 */
export function ModelGateBanner({
  component,
  label,
}: {
  component: string;
  label?: string;
}) {
  const { gated, missing, loading } = useModelGate(component);
  if (loading || !gated) return null;
  return (
    <div className="rounded border border-amber-300 bg-amber-50 p-3 mb-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm">
          <div className="font-medium text-amber-900">
            {label || component.replace(/_/g, " ")} is missing a model
          </div>
          <div className="text-xs text-amber-800 mt-0.5">
            Required capability {missing.length > 1 ? "ies" : ""}: {missing.join(", ")}
          </div>
        </div>
        <Link href="/admin/models">
          <DkButton size="sm">Add a provider</DkButton>
        </Link>
      </div>
    </div>
  );
}
