"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { ArrowRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const dkButton = cva(
  "inline-flex items-center justify-center gap-2 font-semibold transition-all duration-base ease-out-quart focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white disabled:pointer-events-none disabled:opacity-50 whitespace-nowrap select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-brand text-white hover:bg-[var(--dk-purple-800)] active:bg-[var(--dk-purple-900)] hover:shadow-brand focus-visible:ring-brand/40",
        secondary:
          "bg-white text-ink border border-[var(--dk-border-strong)] hover:border-brand hover:text-brand focus-visible:ring-brand/40",
        ghost:
          "text-brand hover:text-[var(--dk-purple-900)] focus-visible:ring-brand/40 px-0",
        danger:
          "bg-danger text-white hover:bg-[#8a1d17] focus-visible:ring-danger/40",
        ink:
          "bg-ink text-white hover:bg-[var(--dk-gray-800)] focus-visible:ring-brand/40",
      },
      size: {
        sm: "h-9 px-4 text-sm rounded-pill",
        md: "h-11 px-6 text-md rounded-pill",
        lg: "h-12 px-8 text-md rounded-pill",
        icon: "h-10 w-10 rounded-pill",
      },
    },
    compoundVariants: [
      { variant: "ghost", size: "sm", class: "h-auto px-0" },
      { variant: "ghost", size: "md", class: "h-auto px-0" },
      { variant: "ghost", size: "lg", class: "h-auto px-0" },
    ],
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface DkButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof dkButton> {
  loading?: boolean;
  withArrow?: boolean;
}

export const DkButton = React.forwardRef<HTMLButtonElement, DkButtonProps>(
  (
    {
      className,
      variant,
      size,
      loading,
      withArrow,
      disabled,
      children,
      ...props
    },
    ref,
  ) => (
    <button
      ref={ref}
      className={cn(dkButton({ variant, size }), className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {children}
      {withArrow && !loading && (
        <ArrowRight className="h-4 w-4 transition-transform duration-fast ease-out-quart group-hover:translate-x-0.5" />
      )}
    </button>
  ),
);
DkButton.displayName = "DkButton";
