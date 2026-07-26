"use client";

import { clsx } from "clsx";

/**
 * Tiny horizontal bar — used in stat strips for one-line metrics with a
 * "fill bar" feel. Value supplied in 0..1.
 */
export function MiniBar({
  value,
  tone = "ai",
  height = 3,
}: {
  value: number; // 0..1
  tone?: "ai" | "pos" | "neg";
  height?: number;
}) {
  const v = Math.min(1, Math.max(0, value));
  const fill: Record<typeof tone, string> = {
    ai: "bg-ai",
    pos: "bg-pos",
    neg: "bg-neg",
  } as const;
  return (
    <div
      className="w-full bg-line overflow-hidden"
      style={{ height }}
      aria-hidden
    >
      <div
        className={clsx("h-full", fill[tone])}
        style={{ width: `${v * 100}%` }}
      />
    </div>
  );
}
