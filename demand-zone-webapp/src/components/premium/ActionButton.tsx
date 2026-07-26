"use client";

import { motion } from "motion/react";
import { clsx } from "clsx";
import { type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const STYLES: Record<Variant, string> = {
  primary:
    "bg-ai text-white border-ai/40 hover:bg-ai/90 shadow-[0_0_24px_-8px_rgba(124,140,255,0.6)]",
  secondary:
    "bg-white/[0.05] text-fg border-white/10 hover:bg-white/[0.10]",
  ghost:
    "bg-transparent text-fg border-white/10 hover:bg-white/[0.04]",
  danger:
    "bg-neg/[0.10] text-neg border-neg/30 hover:bg-neg/[0.18]",
};

export function ActionButton({
  children,
  icon,
  variant = "secondary",
  onClick,
  delay = 0,
}: {
  children: ReactNode;
  icon?: ReactNode;
  variant?: Variant;
  onClick?: () => void;
  delay?: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1], delay }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={clsx(
        "flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-[13px] font-medium transition-colors",
        STYLES[variant]
      )}
    >
      {icon}
      {children}
    </motion.button>
  );
}
