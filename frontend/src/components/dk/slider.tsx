"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface DkSliderProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  showValue?: boolean;
}

export const DkSlider = React.forwardRef<HTMLInputElement, DkSliderProps>(
  ({ className, showValue, value, min = 0, max = 100, ...props }, ref) => (
    <div className="flex items-center gap-3">
      <input
        ref={ref}
        type="range"
        min={min}
        max={max}
        value={value}
        className={cn(
          "w-full h-1 rounded-pill bg-[var(--dk-gray-200)] appearance-none cursor-pointer accent-[var(--dk-purple-700)]",
          "[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-pill [&::-webkit-slider-thumb]:bg-brand [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:cursor-grab [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-fast [&::-webkit-slider-thumb]:hover:scale-110",
          "[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:rounded-pill [&::-moz-range-thumb]:bg-brand [&::-moz-range-thumb]:cursor-grab",
          className,
        )}
        {...props}
      />
      {showValue && (
        <span className="text-sm font-medium tabular-nums text-[var(--dk-fg-1)] w-10 text-right">
          {value}
        </span>
      )}
    </div>
  ),
);
DkSlider.displayName = "DkSlider";
