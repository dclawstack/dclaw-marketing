import * as React from "react";
import { cn } from "@/lib/utils";
import { DkEyebrow } from "./eyebrow";

export interface DkPageHeaderProps
  extends React.HTMLAttributes<HTMLDivElement> {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

export const DkPageHeader = React.forwardRef<HTMLDivElement, DkPageHeaderProps>(
  ({ className, eyebrow, title, description, actions, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "flex flex-col gap-4 pb-6 border-b border-[var(--dk-border)] md:flex-row md:items-end md:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col gap-2 max-w-2xl">
        {eyebrow && <DkEyebrow>{eyebrow}</DkEyebrow>}
        <h1 className="font-display text-3xl md:text-4xl font-bold leading-snug tracking-snug text-ink">
          {title}
        </h1>
        {description && (
          <p className="text-md leading-relaxed text-[var(--dk-fg-1)]">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-3 shrink-0">{actions}</div>
      )}
    </div>
  ),
);
DkPageHeader.displayName = "DkPageHeader";
