"use client";

import { motion } from "motion/react";
import { Check } from "lucide-react";

export function ReasoningItem({
  text,
  weight = 0.8,
  delay = 0,
}: {
  text: string;
  weight?: number;
  delay?: number;
}) {
  const v = Math.min(1, Math.max(0, weight));
  return (
    <motion.div
      initial={{ opacity: 0, x: 4 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay }}
      className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-white/[0.03] transition-colors"
    >
      <span
        className="flex h-5 w-5 items-center justify-center rounded-full bg-pos/[0.10] border border-pos/30"
        style={{
          boxShadow: `0 0 12px -2px rgba(62,207,142,${v * 0.4})`,
        }}
      >
        <Check className="h-3 w-3 text-pos" strokeWidth={3} />
      </span>
      <span className="flex-1 text-xs text-fg">{text}</span>
      <div className="hidden sm:flex items-center gap-1.5">
        <div className="h-1 w-12 overflow-hidden rounded-full bg-white/[0.05]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${v * 100}%` }}
            transition={{ duration: 0.7, delay: delay + 0.1 }}
            className="h-full bg-pos"
          />
        </div>
        <span className="num text-2xs text-fg-muted">
          {Math.round(v * 100)}
        </span>
      </div>
    </motion.div>
  );
}
