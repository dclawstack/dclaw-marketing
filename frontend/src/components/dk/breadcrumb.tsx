import * as React from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DkBreadcrumbItem {
  label: string;
  href?: string;
}

export interface DkBreadcrumbProps
  extends React.HTMLAttributes<HTMLElement> {
  items: DkBreadcrumbItem[];
}

export function DkBreadcrumb({ className, items, ...props }: DkBreadcrumbProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn(
        "flex items-center gap-1.5 text-sm text-[var(--dk-fg-2)]",
        className,
      )}
      {...props}
    >
      {items.map((it, i) => {
        const isLast = i === items.length - 1;
        return (
          <React.Fragment key={`${it.label}-${i}`}>
            {it.href && !isLast ? (
              <Link
                href={it.href}
                className="hover:text-brand transition-colors duration-fast"
              >
                {it.label}
              </Link>
            ) : (
              <span
                aria-current={isLast ? "page" : undefined}
                className={isLast ? "font-medium text-ink" : ""}
              >
                {it.label}
              </span>
            )}
            {!isLast && (
              <ChevronRight
                className="h-3.5 w-3.5 text-[var(--dk-fg-muted)]"
                aria-hidden
              />
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}
