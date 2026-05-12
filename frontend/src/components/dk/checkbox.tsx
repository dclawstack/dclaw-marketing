"use client";

import * as React from "react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DkCheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {}

export const DkCheckbox = React.forwardRef<HTMLInputElement, DkCheckboxProps>(
  ({ className, checked, disabled, ...props }, ref) => (
    <label
      className={cn(
        "relative inline-flex h-5 w-5 cursor-pointer items-center justify-center rounded-xs border transition-colors duration-fast ease-out-quart",
        checked
          ? "bg-brand border-brand text-white"
          : "bg-white border-[var(--dk-border-strong)] hover:border-brand",
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      <input
        ref={ref}
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        disabled={disabled}
        {...props}
      />
      {checked && <Check className="h-3 w-3" aria-hidden />}
    </label>
  ),
);
DkCheckbox.displayName = "DkCheckbox";
