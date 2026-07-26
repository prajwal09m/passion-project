"use client";

import { motion } from "motion/react";
import { useEffect, useState } from "react";

/**
 * Animated large circular gauge for the AI Confidence centerpiece.
 * Uses an SVG ring with a gradient stroke that lights up and a glow.
 */
export function ConfidenceGauge({
  value,           // 0..1
  size = 220,
  thickness = 14,
  label = "AI CONFIDENCE",
  recommendation,  // "BUY" | "SELL" | "HOLD"
}: {
  value: number;
  size?: number;
  thickness?: number;
  label?: string;
  recommendation?: "BUY" | "SELL" | "HOLD";
}) {
  const v = Math.min(1, Math.max(0, value));
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * (1 - v);

  const recColor =
    recommendation === "BUY"
      ? "#3ecf8e"
      : recommendation === "SELL"
      ? "#ef5160"
      : "#9ba1ad";

  const recGradient: [string, string] =
    recommendation === "BUY"
      ? ["#3ecf8e", "#9be7c4"]
      : recommendation === "SELL"
      ? ["#ef5160", "#f6a8af"]
      : ["#9ba1ad", "#cdd2dc"];

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Soft glow */}
      <div
        className="absolute inset-0 rounded-full blur-2xl opacity-50"
        style={{
          background: `radial-gradient(circle, ${recColor}22 0%, transparent 65%)`,
        }}
        aria-hidden
      />
      <svg width={size} height={size} className="-rotate-90 relative">
        <defs>
          <linearGradient id="confGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor={recGradient[0]} />
            <stop offset="100%" stopColor={recGradient[1]} />
          </linearGradient>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={thickness}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#confGrad)"
          strokeWidth={thickness}
          strokeLinecap="round"
          initial={{ strokeDasharray: `0 ${c}` }}
          animate={{ strokeDasharray: `${c - dash} ${c}` }}
          transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
          style={{
            filter: `drop-shadow(0 0 8px ${recColor}88)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="num text-[64px] leading-none font-medium"
          style={{ color: recColor }}
        >
          <CountUp to={v * 100} decimals={0} suffix="%" />
        </div>
        <div className="mt-2 text-2xs uppercase tracking-[0.18em] text-fg-subtle">
          {label}
        </div>
        {recommendation && (
          <div
            className="mt-3 px-3 py-1 rounded-full text-[10px] uppercase tracking-[0.18em] font-semibold"
            style={{
              color: recColor,
              background: `${recColor}1A`,
              border: `1px solid ${recColor}33`,
            }}
          >
            {recommendation} SIGNAL
          </div>
        )}
      </div>
    </div>
  );
}

function CountUp({
  to,
  decimals = 0,
  suffix = "",
}: {
  to: number;
  decimals?: number;
  suffix?: string;
}) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const dur = 1400;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setV(eased * to);
      if (p < 1) raf = requestAnimationFrame(tick);
      else setV(to);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return (
    <span>
      {v.toFixed(decimals)}
      {suffix}
    </span>
  );
}
