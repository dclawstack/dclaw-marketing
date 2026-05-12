import * as React from "react";
import { cn } from "@/lib/utils";

export const DkSkeleton = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "animate-pulse rounded-md bg-[var(--dk-gray-100)]",
      className,
    )}
    {...props}
  />
));
DkSkeleton.displayName = "DkSkeleton";
