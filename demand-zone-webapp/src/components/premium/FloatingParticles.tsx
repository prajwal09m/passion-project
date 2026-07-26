"use client";

import { motion } from "motion/react";
import { useMemo } from "react";

/**
 * Slow-drifting background particles. Fixed position, pointer-events-none,
 * GPU-friendly. Deterministic positions so the background is stable across
 * renders.
 */
export function FloatingParticles({ count = 22 }: { count?: number }) {
  const seeds = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => ({
        i,
        x: (i * 7919) % 100, // pseudo-random in 0..100
        y: (i * 6271) % 100,
        size: 1 + (i % 3),
        hue: i % 4 === 0 ? "ai" : i % 3 === 0 ? "pos" : "fg",
        duration: 18 + (i % 7) * 2,
        delay: -((i * 1.7) % 10),
      })),
    [count]
  );

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      {/* Soft top-right radial gradient */}
      <div
        className="absolute -top-32 -right-32 h-[480px] w-[480px] rounded-full opacity-40 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(124,140,255,0.25) 0%, rgba(124,140,255,0) 70%)",
        }}
      />
      <div
        className="absolute -bottom-32 -left-32 h-[520px] w-[520px] rounded-full opacity-30 blur-3xl"
        style={{
          background:
            "radial-gradient(circle, rgba(62,207,142,0.18) 0%, rgba(62,207,142,0) 70%)",
        }}
      />
      {seeds.map((s) => (
        <motion.span
          key={s.i}
          className={
            "absolute block rounded-full " +
            (s.hue === "ai"
              ? "bg-ai/40"
              : s.hue === "pos"
              ? "bg-pos/40"
              : "bg-fg/30")
          }
          style={{
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
          }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{
            opacity: [0, 0.55, 0.25, 0.55, 0],
            y: [0, -30, 10, -20, 0],
            x: [0, 12, -8, 6, 0],
          }}
          transition={{
            duration: s.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: s.delay,
          }}
        />
      ))}
    </div>
  );
}
