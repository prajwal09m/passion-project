"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

export type FeatureRow = {
  name: string;
  /** Importance, normalized 0..1 after we max-scale against the leader. */
  value: number;
  raw: number;
  direction: "positive" | "negative";
  category?: string;
};

/**
 * Horizontal importance-bar list, with ranks. Used on the Analysis sidebar
 * (Top Features) and on the Performance feature-importance table.
 */
export function FeatureBars({
  features,
  max = 10,
  accent = "ai",
}: {
  features: FeatureRow[];
  max?: number;
  accent?: "ai" | "pos" | "neg";
}) {
  const leader = Math.max(...features.map((f) => f.raw)) || 1;
  const shown = features.slice(0, max);
  return (
    <ol className="flex flex-col gap-2.5">
      {shown.map((f, i) => {
        const pct = (f.raw / leader) * 100;
        const fill =
          accent === "pos"
            ? "bg-pos"
            : accent === "neg"
            ? "bg-neg"
            : "bg-ai";
        return (
          <li key={f.name} className="grid grid-cols-[14px_minmax(0,1fr)_72px] items-center gap-2.5">
            <span className="text-2xs text-fg-subtle num text-right">
              {(i + 1).toString().padStart(2, "0")}
            </span>
            <div className="min-w-0">
              <div className="flex items-center justify-between">
                <div className="truncate text-xs text-fg">{f.name}</div>
                <div className="num text-2xs text-fg-muted ml-2">
                  {f.raw.toFixed(4)}
                </div>
              </div>
              <div className="mt-1 h-1 w-full bg-line-faint overflow-hidden">
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
            <div
              className={clsx(
                "num text-2xs text-right",
                f.direction === "negative" ? "text-neg" : "text-pos"
              )}
            >
              {f.direction === "negative" ? "−" : "+"}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
