"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkRadioProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {}

export const DkRadio = React.forwardRef<HTMLInputElement, DkRadioProps>(
  ({ className, checked, disabled, ...props }, ref) => (
    <label
      className={cn(
        "relative inline-flex h-5 w-5 cursor-pointer items-center justify-center rounded-pill border transition-colors duration-fast ease-out-quart",
        checked
          ? "border-brand"
          : "bg-white border-[var(--dk-border-strong)] hover:border-brand",
        disabled && "opacity-50 cursor-not-allowed",
        className,
      )}
    >
      <input
        ref={ref}
        type="radio"
        className="peer sr-only"
        checked={checked}
        disabled={disabled}
        {...props}
      />
      {checked && (
        <span
          className="block h-2.5 w-2.5 rounded-pill bg-brand"
          aria-hidden
        />
      )}
    </label>
  ),
);
DkRadio.displayName = "DkRadio";

export interface DkRadioGroupProps
  extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
}

export const DkRadioGroup = React.forwardRef<
  HTMLDivElement,
  DkRadioGroupProps
>(({ className, orientation = "vertical", ...props }, ref) => (
  <div
    ref={ref}
    role="radiogroup"
    className={cn(
      "flex gap-3",
      orientation === "vertical" ? "flex-col" : "flex-row flex-wrap",
      className,
    )}
    {...props}
  />
));
DkRadioGroup.displayName = "DkRadioGroup";
