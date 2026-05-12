import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const dkChip = cva(
  "inline-flex items-center gap-1.5 rounded-pill px-3 py-1 text-xs font-semibold tracking-wide leading-none whitespace-nowrap",
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
    defaultVariants: { tone: "brand" },
  },
);

export interface DkChipProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof dkChip> {}

export const DkChip = React.forwardRef<HTMLSpanElement, DkChipProps>(
  ({ className, tone, ...props }, ref) => (
    <span ref={ref} className={cn(dkChip({ tone }), className)} {...props} />
  ),
);
DkChip.displayName = "DkChip";
