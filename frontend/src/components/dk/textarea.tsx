"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkTextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const DkTextarea = React.forwardRef<
  HTMLTextAreaElement,
  DkTextareaProps
>(({ className, invalid, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full rounded-md border bg-white px-3 py-2 text-md font-sans text-ink placeholder:text-[var(--dk-fg-muted)] transition-shadow duration-fast ease-out-quart focus-visible:outline-none disabled:cursor-not-allowed disabled:bg-[var(--dk-gray-50)] disabled:text-[var(--dk-fg-2)] resize-y",
      invalid
        ? "border-[var(--dk-danger)] focus-visible:shadow-[0_0_0_3px_var(--dk-danger-bg)] focus-visible:border-[var(--dk-danger)]"
        : "border-[var(--dk-border-strong)] focus-visible:border-brand focus-visible:shadow-[0_0_0_3px_var(--dk-purple-100)]",
      className,
    )}
    {...props}
  />
));
DkTextarea.displayName = "DkTextarea";
