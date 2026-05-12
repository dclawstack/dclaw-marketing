import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const dkBadge = cva(
  "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium leading-tight",
  {
    variants: {
      tone: {
        brand: "bg-[var(--dk-purple-100)] text-brand",
        neutral: "bg-[var(--dk-gray-100)] text-[var(--dk-fg-1)]",
        success: "bg-[var(--dk-success-bg)] text-[var(--dk-success)]",
        warning: "bg-[var(--dk-warning-bg)] text-[var(--dk-warning)]",
        danger: "bg-[var(--dk-danger-bg)] text-[var(--dk-danger)]",
        info: "bg-[var(--dk-info-bg)] text-[var(--dk-info)]",
        outline:
          "bg-white text-[var(--dk-fg-1)] border border-[var(--dk-border-strong)]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface DkBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof dkBadge> {}

export const DkBadge = React.forwardRef<HTMLSpanElement, DkBadgeProps>(
  ({ className, tone, ...props }, ref) => (
    <span ref={ref} className={cn(dkBadge({ tone }), className)} {...props} />
  ),
);
DkBadge.displayName = "DkBadge";
