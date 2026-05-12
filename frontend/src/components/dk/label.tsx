import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkLabelProps
  extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
  description?: string;
}

export const DkLabel = React.forwardRef<HTMLLabelElement, DkLabelProps>(
  ({ className, required, description, children, ...props }, ref) => (
    <div className="flex flex-col gap-1">
      <label
        ref={ref}
        className={cn(
          "text-sm font-semibold text-ink leading-none",
          className,
        )}
        {...props}
      >
        {children}
        {required && (
          <span className="ml-1 text-[var(--dk-danger)]" aria-hidden>
            *
          </span>
        )}
      </label>
      {description && (
        <p className="text-xs text-[var(--dk-fg-2)] leading-normal">
          {description}
        </p>
      )}
    </div>
  ),
);
DkLabel.displayName = "DkLabel";
