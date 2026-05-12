import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value: number; // 0–100
  tone?: "brand" | "success" | "warning" | "danger";
  showLabel?: boolean;
}

const toneMap = {
  brand: "bg-brand",
  success: "bg-[var(--dk-success)]",
  warning: "bg-[var(--dk-warning)]",
  danger: "bg-[var(--dk-danger)]",
} as const;

export const DkProgress = React.forwardRef<HTMLDivElement, DkProgressProps>(
  (
    { className, value, tone = "brand", showLabel = false, ...props },
    ref,
  ) => {
    const v = Math.max(0, Math.min(100, value));
    return (
      <div
        ref={ref}
        className={cn("flex items-center gap-3", className)}
        {...props}
      >
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={v}
          className="flex-1 h-2 rounded-pill bg-[var(--dk-gray-100)] overflow-hidden"
        >
          <div
            className={cn(
              "h-full transition-all duration-base ease-out-quart",
              toneMap[tone],
            )}
            style={{ width: `${v}%` }}
          />
        </div>
        {showLabel && (
          <span className="text-sm font-medium tabular-nums text-[var(--dk-fg-2)]">
            {Math.round(v)}%
          </span>
        )}
      </div>
    );
  },
);
DkProgress.displayName = "DkProgress";
