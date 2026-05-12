import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkEmptyStateProps
  extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export const DkEmptyState = React.forwardRef<HTMLDivElement, DkEmptyStateProps>(
  ({ className, icon, title, description, actions, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-[var(--dk-border-strong)] bg-white px-6 py-12 text-center",
        className,
      )}
      {...props}
    >
      {icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--dk-purple-50)] text-brand">
          {icon}
        </div>
      )}
      <div className="flex flex-col gap-1 max-w-md">
        <h3 className="font-display text-xl font-semibold leading-snug text-ink">
          {title}
        </h3>
        {description && (
          <p className="text-sm leading-relaxed text-[var(--dk-fg-2)]">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-3 pt-2">{actions}</div>
      )}
    </div>
  ),
);
DkEmptyState.displayName = "DkEmptyState";
