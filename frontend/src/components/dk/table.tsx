import * as React from "react";
import { cn } from "@/lib/utils";

export const DkTable = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => (
  <div className="w-full overflow-x-auto rounded-2xl border border-[var(--dk-border)] bg-white shadow-xs">
    <table
      ref={ref}
      className={cn("w-full text-sm border-collapse", className)}
      {...props}
    />
  </div>
));
DkTable.displayName = "DkTable";

export const DkTableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn(
      "bg-[var(--dk-purple-50)] text-xs uppercase tracking-wide text-[var(--dk-fg-2)]",
      className,
    )}
    {...props}
  />
));
DkTableHeader.displayName = "DkTableHeader";

export const DkTableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn("divide-y divide-[var(--dk-border)]", className)}
    {...props}
  />
));
DkTableBody.displayName = "DkTableBody";

export const DkTableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      "hover:bg-[var(--dk-bg-tint)] transition-colors duration-fast ease-out-quart",
      className,
    )}
    {...props}
  />
));
DkTableRow.displayName = "DkTableRow";

export const DkTableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      "px-4 py-3 text-left font-semibold text-[var(--dk-fg-2)]",
      className,
    )}
    {...props}
  />
));
DkTableHead.displayName = "DkTableHead";

export const DkTableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn("px-4 py-3 align-middle text-ink", className)}
    {...props}
  />
));
DkTableCell.displayName = "DkTableCell";
