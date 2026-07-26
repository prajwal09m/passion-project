"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";

/**
 * Radial SVG arc that conveys a 0..1 confidence value.
 * Used on the Analysis page as the centerpiece of the AI Prediction panel.
 */
export function ConfidenceArc({
  value,
  label = "CONFIDENCE",
  size = 160,
  thickness = 7,
}: {
  value: number; // 0..1
  label?: string;
  size?: number;
  thickness?: number;
}) {
  const v = Math.min(1, Math.max(0, value));
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * (1 - v);

  return (
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
          stroke="#1f222a"
          strokeWidth={thickness}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="url(#aiGrad)"
          strokeWidth={thickness}
          strokeLinecap="round"
          initial={{ strokeDasharray: `0 ${c}` }}
          animate={{ strokeDasharray: `${c - dash} ${c}` }}
          transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        />
        <defs>
          <linearGradient id="aiGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#5b6cff" />
            <stop offset="100%" stopColor="#9aa6ff" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="num text-[38px] leading-none font-medium text-fg">
          <CountUp to={v * 100} decimals={0} suffix="%" />
        </div>
        <div className="mt-1.5 text-2xs uppercase tracking-[0.15em] text-fg-subtle">
          {label}
        </div>
      </div>
    </div>
  );
}

/** Smooth count-up animation, used for the centered percent. */
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
    const dur = 1100;
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
