"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export const DkCard = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { hover?: boolean; tinted?: boolean }
>(({ className, hover = false, tinted = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-2xl border border-[var(--dk-border)] shadow-sm transition-all duration-base ease-out-quart",
      tinted ? "bg-[var(--dk-bg-tint)]" : "bg-white",
      hover &&
        "hover:-translate-y-[3px] hover:shadow-md hover:border-[var(--dk-border-brand)]",
      className,
    )}
    {...props}
  />
));
DkCard.displayName = "DkCard";

export const DkCardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("p-6 pb-2 flex flex-col gap-1", className)}
    {...props}
  />
));
DkCardHeader.displayName = "DkCardHeader";

export const DkCardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-display text-2xl font-semibold leading-snug text-ink",
      className,
    )}
    {...props}
  />
));
DkCardTitle.displayName = "DkCardTitle";

export const DkCardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn(
      "text-sm leading-normal text-[var(--dk-fg-2)]",
      className,
    )}
    {...props}
  />
));
DkCardDescription.displayName = "DkCardDescription";

export const DkCardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("px-6 py-4 text-[var(--dk-fg-1)]", className)}
    {...props}
  />
));
DkCardContent.displayName = "DkCardContent";

export const DkCardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "px-6 pb-6 pt-2 flex items-center gap-3 border-t border-[var(--dk-border)] mt-2",
      className,
    )}
    {...props}
  />
));
DkCardFooter.displayName = "DkCardFooter";
