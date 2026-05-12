"use client";

import * as React from "react";
import {
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

type ToastTone = "success" | "warning" | "danger" | "info";

interface ToastItem {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
  durationMs?: number;
}

interface ToastContextValue {
  push: (t: Omit<ToastItem, "id">) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function useDkToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx)
    throw new Error("useDkToast must be used within <DkToastProvider>");
  return ctx;
}

const toneIcon = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: AlertCircle,
  info: Info,
} as const;

const toneStyles = {
  success: "border-[var(--dk-success)] text-[var(--dk-success)]",
  warning: "border-[var(--dk-warning)] text-[var(--dk-warning)]",
  danger: "border-[var(--dk-danger)] text-[var(--dk-danger)]",
  info: "border-[var(--dk-info)] text-[var(--dk-info)]",
} as const;

export function DkToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = React.useState<ToastItem[]>([]);
  const idRef = React.useRef(0);

  const push = React.useCallback((t: Omit<ToastItem, "id">) => {
    const id = ++idRef.current;
    setItems((prev) => [...prev, { id, ...t }]);
    const ms = t.durationMs ?? 4000;
    setTimeout(() => {
      setItems((prev) => prev.filter((x) => x.id !== id));
    }, ms);
  }, []);

  const dismiss = (id: number) =>
    setItems((prev) => prev.filter((x) => x.id !== id));

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full"
      >
        {items.map((t) => {
          const Icon = toneIcon[t.tone];
          return (
            <div
              key={t.id}
              role="status"
              className={cn(
                "flex items-start gap-3 rounded-2xl border-l-4 bg-white p-4 shadow-md animate-in slide-in-from-right",
                toneStyles[t.tone],
              )}
            >
              <Icon className="h-5 w-5 mt-0.5 shrink-0" aria-hidden />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-ink leading-snug">
                  {t.title}
                </p>
                {t.description && (
                  <p className="mt-0.5 text-sm text-[var(--dk-fg-1)] leading-normal">
                    {t.description}
                  </p>
                )}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss"
                className="text-[var(--dk-fg-muted)] hover:text-ink transition-colors duration-fast"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
