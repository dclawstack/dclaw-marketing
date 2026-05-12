import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkAvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string | null;
  alt?: string;
  name?: string;
  size?: "sm" | "md" | "lg";
}

const sizeMap = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-14 w-14 text-md",
} as const;

function initials(name?: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

export const DkAvatar = React.forwardRef<HTMLDivElement, DkAvatarProps>(
  ({ className, src, alt, name, size = "md", ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center overflow-hidden rounded-pill bg-[var(--dk-purple-100)] text-brand font-semibold shrink-0",
        sizeMap[size],
        className,
      )}
      {...props}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={alt ?? name ?? ""}
          className="h-full w-full object-cover"
        />
      ) : (
        <span aria-hidden>{initials(name)}</span>
      )}
    </div>
  ),
);
DkAvatar.displayName = "DkAvatar";
