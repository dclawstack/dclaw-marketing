import * as React from "react";
import { cn } from "@/lib/utils";

export const DkEyebrow = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn(
      "text-sm font-semibold uppercase tracking-[0.04em] text-brand",
      className,
    )}
    {...props}
  />
));
DkEyebrow.displayName = "DkEyebrow";
