"use client";

import { clsx } from "clsx";
import { motion } from "motion/react";
import { type ReactNode } from "react";

type Sentiment = "neutral" | "pos" | "neg" | "ai";

const COLOR: Record<Sentiment, string> = {
  neutral: "text-fg",
  pos: "text-pos",
  neg: "text-neg",
  ai: "text-ai",
};

export function Stat({
  label,
  value,
  hint,
  sentiment = "neutral",
  emphasised = false,
  mono = true,
  delay = 0,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  sentiment?: Sentiment;
  emphasised?: boolean;
  mono?: boolean;
  /** Used to stagger Motion.dev entrance across a stats strip. */
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay }}
      className="flex flex-col gap-1"
    >
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </div>
      <div
        className={clsx(
          "leading-none",
          mono && "num",
          emphasised ? "text-[28px] font-medium tracking-tight" : "text-[15px] font-medium",
          COLOR[sentiment]
        )}
      >
        {value}
      </div>
      {hint ? (
        <div className="text-2xs text-fg-subtle">{hint}</div>
      ) : null}
    </motion.div>
  );
}
