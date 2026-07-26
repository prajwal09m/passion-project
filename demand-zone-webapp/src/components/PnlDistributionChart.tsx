"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

export type Distribution = {
  label: string;
  value: number;          // count or $
  tone: "pos" | "neg" | "neutral";
  pct?: number;          // optional normalized 0..1 fill
};

/**
 * Compact horizontal bars showing a distribution. Used on Backtest for
 * win/loss/avg metrics in one block.
 */
export function DistributionBars({
  rows,
  height = 10,
}: {
  rows: Distribution[];
  height?: number;
}) {
  const max = Math.max(...rows.map((r) => Math.abs(r.value)));
  return (
    <div className="flex flex-col gap-3">
      {rows.map((r, i) => {
        const pct = (Math.abs(r.value) / (max || 1)) * 100;
        const fill =
          r.tone === "pos"
            ? "bg-pos"
            : r.tone === "neg"
            ? "bg-neg"
            : "bg-fg-subtle";
        return (
          <div key={r.label} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-fg-muted">{r.label}</span>
                <span
                  className={clsx(
                    "num text-xs",
                    r.tone === "pos" && "text-pos",
                    r.tone === "neg" && "text-neg",
                    r.tone === "neutral" && "text-fg"
                  )}
                >
                  {r.value.toLocaleString()}
                </span>
              </div>
              <div
                className="mt-1.5 w-full bg-line overflow-hidden"
                style={{ height }}
                aria-hidden
              >
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{
                    duration: 0.7,
                    ease: [0.16, 1, 0.3, 1],
                    delay: 0.05 * i,
                  }}
                  className={clsx("h-full", fill)}
                />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
