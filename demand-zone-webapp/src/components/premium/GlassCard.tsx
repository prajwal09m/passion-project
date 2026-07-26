"use client";

import { motion, type HTMLMotionProps } from "motion/react";
import { clsx } from "clsx";
import { type ReactNode, forwardRef } from "react";

type GlassCardProps = HTMLMotionProps<"div"> & {
  children: ReactNode;
  className?: string;
  /** Visual intensity — `soft` for quiet panels, `default` for hero cards, `glow` for the centerpiece. */
  intensity?: "soft" | "default" | "glow";
  /** Stagger component entrance by route or section. */
  delay?: number;
};

const TONES = {
  soft: {
    bg: "from-white/[0.025] to-white/[0.01]",
    border: "from-white/[0.06] via-white/[0.04] to-white/[0.06]",
    glow: "",
  },
  default: {
    bg: "from-white/[0.04] to-white/[0.015]",
    border: "from-white/[0.10] via-white/[0.05] to-white/[0.10]",
    glow: "",
  },
  glow: {
    bg: "from-ai/[0.08] via-white/[0.04] to-pos/[0.04]",
    border: "from-ai/40 via-white/10 to-pos/40",
    glow: "shadow-[0_0_60px_-15px_rgba(124,140,255,0.4)]",
  },
} as const;

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  function GlassCard(
    { children, className, intensity = "default", delay = 0, ...rest },
    ref
  ) {
    const tone = TONES[intensity];
    return (
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay }}
        className={clsx(
          "relative rounded-2xl overflow-hidden",
          tone.glow,
          className
        )}
        {...rest}
      >
        {/* Gradient border via mask */}
        <div
          className={clsx(
            "pointer-events-none absolute inset-0 rounded-2xl p-px",
            "bg-gradient-to-b",
            tone.border
          )}
          aria-hidden
        >
          <div className="h-full w-full rounded-2xl bg-ink-950/85 backdrop-blur-xl" />
        </div>
        {/* Body background gradient */}
        <div
          className={clsx(
            "pointer-events-none absolute inset-0 bg-gradient-to-br",
            tone.bg
          )}
          aria-hidden
        />
        <div className="relative">{children}</div>
      </motion.div>
    );
  }
);
