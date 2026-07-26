"use client";

import { clsx } from "clsx";
import type { ReactNode } from "react";

type Variant = "pos" | "neg" | "neutral" | "ai" | "warn";

const STYLES: Record<Variant, string> = {
  pos:     "text-pos border-pos/40 bg-pos/[0.08]",
  neg:     "text-neg border-neg/40 bg-neg/[0.08]",
  neutral: "text-fg-muted border-line bg-transparent",
  ai:      "text-ai border-ai/40 bg-ai/[0.08]",
  warn:    "text-warn border-warn/40 bg-warn/[0.08]",
};

export function Pill({
  variant = "neutral",
  children,
  dot = false,
  className,
}: {
  variant?: Variant;
  children: ReactNode;
  /** Show a 6px status dot to the left of the label. */
  dot?: boolean;
  className?: string;
}) {
  const dotColor: Record<Variant, string> = {
    pos: "bg-pos",
    neg: "bg-neg",
    neutral: "bg-fg-muted",
    ai: "bg-ai",
    warn: "bg-warn",
  };
  return (
    <span className={clsx("pill", STYLES[variant], className)}>
      {dot && (
        <span
          className={clsx(
            "inline-block h-1.5 w-1.5 rounded-full",
            dotColor[variant],
            variant === "ai" && "animate-data-pulse"
          )}
        />
      )}
      {children}
    </span>
  );
}
