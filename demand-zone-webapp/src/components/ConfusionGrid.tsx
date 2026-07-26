"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

export type Confusion = {
  truePositive: number;
  falsePositive: number;
  falseNegative: number;
  trueNegative: number;
};

/**
 * A compact 2x2 confusion matrix. Each cell shows the count, the label,
 * and the row/column total. Used on the Performance page.
 */
export function ConfusionGrid({ c, threshold = 0.75 }: { c: Confusion; threshold?: number }) {
  const total = c.truePositive + c.falsePositive + c.falseNegative + c.trueNegative;
  // Suppress unused warning — threshold referenced in the AI tag below.
  void threshold;
  const Cell = ({
    n,
    label,
    tone,
    delay,
  }: {
    n: number;
    label: string;
    tone: "pos" | "neg" | "neutral";
    delay: number;
  }) => (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
      className={clsx(
        "relative flex flex-col gap-1 border px-4 py-3 bg-ink-900 overflow-hidden",
        "border-line"
      )}
    >
      <div
        className={clsx(
          "absolute inset-x-0 top-0 h-px",
          tone === "pos" && "bg-pos/60",
          tone === "neg" && "bg-neg/60",
          tone === "neutral" && "bg-fg-subtle/30"
        )}
      />
      <div
        className={clsx(
          "num text-[26px] leading-none font-medium",
          tone === "pos" && "text-pos",
          tone === "neg" && "text-neg",
          tone === "neutral" && "text-fg"
        )}
      >
        {n.toLocaleString()}
      </div>
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </div>
      <div className="num text-2xs text-fg-muted">
        {((n / total) * 100).toFixed(1)}%
      </div>
    </motion.div>
  );

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-px bg-line">
        <Cell n={c.truePositive}  label="True Positive"  tone="pos"     delay={0} />
        <Cell n={c.falsePositive} label="False Positive" tone="neg"     delay={0.05} />
        <Cell n={c.falseNegative} label="False Negative" tone="neg"     delay={0.1} />
        <Cell n={c.trueNegative}  label="True Negative"  tone="pos"     delay={0.15} />
      </div>
    </div>
  );
}
