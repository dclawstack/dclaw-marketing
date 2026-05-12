"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkSwitchProps
  extends Omit<
    React.InputHTMLAttributes<HTMLInputElement>,
    "type" | "size"
  > {}

export const DkSwitch = React.forwardRef<HTMLInputElement, DkSwitchProps>(
  ({ className, checked, disabled, ...props }, ref) => (
    <label
      className={cn(
        "relative inline-flex h-6 w-11 cursor-pointer items-center rounded-pill transition-colors duration-fast ease-out-quart",
        checked ? "bg-brand" : "bg-[var(--dk-gray-300)]",
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
      <span
        className={cn(
          "absolute left-0.5 inline-block h-5 w-5 transform rounded-pill bg-white shadow-sm transition-transform duration-fast ease-out-quart",
          checked ? "translate-x-5" : "translate-x-0",
        )}
        aria-hidden
      />
    </label>
  ),
);
DkSwitch.displayName = "DkSwitch";
