"use client";

import { motion } from "motion/react";

/** A tiny inline sparkline drawn from a series of close prices. */
export function Sparkline({
  values,
  width = 80,
  height = 24,
  positive,
  stroke = 1.4,
}: {
  values: number[];
  width?: number;
  height?: number;
  /** If unset, the line color follows the direction of the move. */
  positive?: boolean;
  stroke?: number;
}) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const dx = width / (values.length - 1);
  const path = values
    .map((v, i) => {
      const x = i * dx;
      const y = height - ((v - min) / range) * height;
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
  const up = positive ?? (values[values.length - 1] ?? 0) >= (values[0] ?? 0);
  const stroke_color = up ? "#3ecf8e" : "#ef5160";
  return (
    <motion.svg
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden
    >
      <motion.path
        d={path}
        fill="none"
        stroke={stroke_color}
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
      />
    </motion.svg>
  );
}
