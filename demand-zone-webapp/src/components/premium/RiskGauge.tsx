"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";

type Tone = "pos" | "neg" | "neutral";

const TONE_COLOR: Record<Tone, string> = {
  pos: "#3ecf8e",
  neg: "#ef5160",
  neutral: "#9ba1ad",
};

export function RiskGauge({
  name,
  value, // 0..1
  tone,
  detail,
  delay = 0,
  size = 88,
}: {
  name: string;
  value: number;
  tone: Tone;
  detail: string;
  delay?: number;
  size?: number;
}) {
  const v = Math.min(1, Math.max(0, value));
  const r = (size - 8) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * (1 - v);
  const color = TONE_COLOR[tone];

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay }}
      className="flex flex-col items-center gap-2 rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-3"
    >
      <div
        className="relative flex items-center justify-center"
        style={{ width: size, height: size }}
      >
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={4}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={4}
            strokeLinecap="round"
            initial={{ strokeDasharray: `0 ${c}` }}
            animate={{ strokeDasharray: `${c - dash} ${c}` }}
            transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1], delay: delay + 0.1 }}
          />
        </svg>
        <div
          className="num absolute text-[15px] font-medium"
          style={{ color }}
        >
          {Math.round(v * 100)}
        </div>
      </div>
      <div className="text-center">
        <div className="text-2xs uppercase tracking-[0.14em] text-fg-subtle">
          {name}
        </div>
        <div className="text-2xs text-fg-muted mt-0.5">{detail}</div>
      </div>
    </motion.div>
  );
}
