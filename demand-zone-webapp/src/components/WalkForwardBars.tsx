"use client";

import { motion } from "motion/react";

/**
 * Walk-forward fold bars: small mulberry rows for each fold's AUC.
 * Used on the ML terminal page to show cross-validation stability.
 */
export type FoldRow = { fold: number; auc: number; precision: number; recall: number };

export function WalkForwardBars({ rows }: { rows: FoldRow[] }) {
  return (
    <div className="flex flex-col gap-3">
      {rows.map((r, i) => (
        <div
          key={r.fold}
          className="grid grid-cols-[24px_1fr_44px_44px_44px] items-center gap-3"
        >
          <span className="text-2xs text-fg-subtle num">F{r.fold}</span>
          <div>
            <div className="bg-line-faint h-2 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${r.auc * 100}%` }}
                transition={{ duration: 0.7, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] }}
                className="h-full bg-ai"
              />
            </div>
            <div className="mt-1.5 flex items-center gap-2">
              <span className="text-2xs text-fg-subtle">P</span>
              <div className="bg-line-faint h-1 flex-1 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${r.precision * 100}%` }}
                  transition={{ duration: 0.5, delay: i * 0.06 + 0.2 }}
                  className="h-full bg-pos"
                />
              </div>
              <span className="text-2xs text-fg-subtle">R</span>
              <div className="bg-line-faint h-1 flex-1 overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${r.recall * 100}%` }}
                  transition={{ duration: 0.5, delay: i * 0.06 + 0.3 }}
                  className="h-full bg-warn"
                />
              </div>
            </div>
          </div>
          <span className="num text-2xs text-fg-muted text-right">
            {(r.auc * 100).toFixed(1)}
          </span>
          <span className="num text-2xs text-fg-muted text-right">
            {(r.precision * 100).toFixed(0)}
          </span>
          <span className="num text-2xs text-fg-muted text-right">
            {(r.recall * 100).toFixed(0)}
          </span>
        </div>
      ))}
    </div>
  );
}
