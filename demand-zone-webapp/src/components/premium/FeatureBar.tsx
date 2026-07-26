"use client";

import { motion } from "motion/react";

/**
 * Horizontal feature-importance bar with a gradient fill, value, and helper.
 */
export function FeatureBar({
  name,
  contribution, // 0..1
  description,
  delay = 0,
}: {
  name: string;
  contribution: number;
  description: string;
  delay?: number;
}) {
  const v = Math.min(1, Math.max(0, contribution));
  return (
    <motion.div
      initial={{ opacity: 0, x: 4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay }}
    >
      <div className="flex items-baseline justify-between gap-2">
        <div className="text-xs text-fg">{name}</div>
        <div className="num text-2xs text-fg-muted">
          {(v * 100).toFixed(0)}%
        </div>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${v * 100}%` }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: delay + 0.1 }}
          className="relative h-full rounded-full"
          style={{
            background:
              "linear-gradient(90deg, #7c8cff 0%, #5b6cff 60%, #3ecf8e 100%)",
          }}
        />
      </div>
      <div className="mt-1 text-2xs text-fg-muted truncate">{description}</div>
    </motion.div>
  );
}
