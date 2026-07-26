"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

type Sentiment = "bullish" | "neutral" | "bearish";

const SENTIMENT: Record<Sentiment, { label: string; dot: string; text: string }> = {
  bullish: { label: "Bullish", dot: "bg-pos", text: "text-pos" },
  neutral: { label: "Neutral", dot: "bg-fg-muted", text: "text-fg-muted" },
  bearish: { label: "Bearish", dot: "bg-neg", text: "text-neg" },
};

export function NewsItem({
  source,
  age,
  headline,
  sentiment,
  score,
  summary,
  delay = 0,
}: {
  source: string;
  age: string;
  headline: string;
  sentiment: Sentiment;
  score: number; // -1..1
  summary: string;
  delay?: number;
}) {
  const s = SENTIMENT[sentiment];
  return (
    <motion.article
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay }}
      className="flex flex-col gap-1.5 rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 hover:bg-white/[0.04] transition-colors"
    >
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-[0.14em] text-fg-muted">
            {source}
          </span>
          <span className="text-2xs text-fg-subtle">·</span>
          <span className="num text-2xs text-fg-subtle">{age}</span>
        </div>
        <span
          className={clsx(
            "inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] uppercase tracking-[0.12em]",
            "border-white/10",
            s.text
          )}
        >
          <span className={clsx("block h-1 w-1 rounded-full", s.dot)} />
          {s.label}
        </span>
      </header>
      <h3 className="text-[13px] font-medium text-fg leading-snug">{headline}</h3>
      <p className="text-2xs text-fg-muted leading-relaxed">{summary}</p>
      <div className="flex items-center gap-2 pt-1">
        <div className="relative h-1 w-full overflow-hidden rounded-full bg-white/[0.05]">
          <div
            className="absolute top-0 bottom-0 bg-fg-subtle/30"
            style={{ left: "50%", width: 1 }}
          />
          <motion.div
            initial={{ scaleX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.6, delay: delay + 0.1 }}
            className={clsx(
              "h-full origin-left",
              sentiment === "bullish" && "bg-pos",
              sentiment === "bearish" && "bg-neg",
              sentiment === "neutral" && "bg-fg-muted"
            )}
            style={{
              width: `${Math.abs(score) * 50}%`,
              marginLeft: score >= 0 ? "50%" : `${50 - Math.abs(score) * 50}%`,
            }}
          />
        </div>
        <span className="num text-2xs text-fg-muted w-8 text-right">
          {(score * 100).toFixed(0)}
        </span>
      </div>
    </motion.article>
  );
}
