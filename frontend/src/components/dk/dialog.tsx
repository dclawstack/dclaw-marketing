"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DkDialogProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
}

const sizeMap = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
} as const;

export function DkDialog({
  open,
  onClose,
  children,
  size = "md",
}: DkDialogProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-[2px] animate-in fade-in duration-base"
      onClick={onClose}
    >
      <div
        className={cn(
          "w-full bg-white rounded-2xl shadow-lg overflow-hidden",
          sizeMap[size],
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  );
}

export function DkDialogHeader({
  title,
  description,
  onClose,
}: {
  title: string;
  description?: string;
  onClose?: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-6 pt-6">
      <div className="flex-1">
        <h2 className="font-display text-2xl font-semibold text-ink leading-snug">
          {title}
        </h2>
        {description && (
          <p className="mt-1 text-sm text-[var(--dk-fg-2)] leading-normal">
            {description}
          </p>
        )}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          aria-label="Close"
          className="rounded-pill p-1 text-[var(--dk-fg-2)] hover:bg-[var(--dk-gray-100)] hover:text-ink transition-colors duration-fast"
        >
          <X className="h-5 w-5" />
        </button>
      )}
    </div>
  );
}

export function DkDialogContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-6 py-4", className)} {...props} />;
}

export function DkDialogFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-3 px-6 pb-6 pt-2",
        className,
      )}
      {...props}
    />
  );
}
