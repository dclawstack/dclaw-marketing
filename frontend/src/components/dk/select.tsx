"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DkSelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const DkSelect = React.forwardRef<HTMLSelectElement, DkSelectProps>(
  ({ className, invalid, children, ...props }, ref) => (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "h-11 w-full appearance-none rounded-md border bg-white px-3 pr-9 text-md font-sans text-ink transition-shadow duration-fast ease-out-quart focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-[var(--dk-gray-50)] disabled:text-[var(--dk-fg-2)]",
          invalid
            ? "border-[var(--dk-danger)] focus-visible:shadow-[0_0_0_3px_var(--dk-danger-bg)] focus-visible:border-[var(--dk-danger)]"
            : "border-[var(--dk-border-strong)] focus-visible:border-brand focus-visible:shadow-[0_0_0_3px_var(--dk-purple-100)]",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--dk-fg-2)]"
        aria-hidden
      />
    </div>
  ),
);
DkSelect.displayName = "DkSelect";
