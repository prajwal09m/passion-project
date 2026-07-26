"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

type Sentiment = "bullish" | "bearish" | "neutral";

const SENT_STYLES: Record<Sentiment, { text: string; bg: string; label: string }> = {
  bullish: { text: "text-pos", bg: "bg-pos/[0.08] border-pos/30", label: "Bullish" },
  bearish: { text: "text-neg", bg: "bg-neg/[0.08] border-neg/30", label: "Bearish" },
  neutral: { text: "text-fg-muted", bg: "bg-white/[0.04] border-white/10", label: "Neutral" },
};

export function IndicatorCard({
  name,
  value,
  status,
  score,
  hint,
  delay = 0,
}: {
  name: string;
  value: string;
  status: Sentiment;
  score: number;
  hint?: string;
  delay?: number;
}) {
  const s = SENT_STYLES[status];
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay }}
      className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 hover:bg-white/[0.04] transition-colors"
    >
      <div className="min-w-0">
        <div className="text-2xs uppercase tracking-[0.14em] text-fg-subtle truncate">
          {name}
        </div>
        <div className="num text-[15px] font-medium text-fg mt-1">{value}</div>
        {hint ? (
          <div className="text-2xs text-fg-muted mt-0.5 truncate">{hint}</div>
        ) : null}
      </div>
      <div className="flex flex-col items-end gap-1.5">
        <span
          className={clsx(
            "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.12em]",
            s.bg,
            s.text
          )}
        >
          <span
            className={clsx(
              "block h-1 w-1 rounded-full",
              status === "bullish" && "bg-pos",
              status === "bearish" && "bg-neg",
              status === "neutral" && "bg-fg-muted"
            )}
          />
          {s.label}
        </span>
        <div className="num text-2xs text-fg-muted">{score}</div>
      </div>
    </motion.div>
  );
}
