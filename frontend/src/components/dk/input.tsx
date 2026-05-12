"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const DkInput = React.forwardRef<HTMLInputElement, DkInputProps>(
  ({ className, invalid, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-md border bg-white px-3 text-md font-sans text-ink placeholder:text-[var(--dk-fg-muted)] transition-shadow duration-fast ease-out-quart focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-[var(--dk-gray-50)] disabled:text-[var(--dk-fg-2)]",
        invalid
          ? "border-[var(--dk-danger)] focus-visible:shadow-[0_0_0_3px_var(--dk-danger-bg)] focus-visible:border-[var(--dk-danger)]"
          : "border-[var(--dk-border-strong)] focus-visible:border-brand focus-visible:shadow-[0_0_0_3px_var(--dk-purple-100)]",
        className,
      )}
      {...props}
    />
  ),
);
DkInput.displayName = "DkInput";
