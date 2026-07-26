"use client";

import { Search } from "lucide-react";
import { motion } from "motion/react";
import { clsx } from "clsx";

export function TickerSearch({
  value,
  placeholder = "TICKER",
  onChange,
  onSubmit,
  suggestions,
  onPick,
}: {
  value: string;
  placeholder?: string;
  onChange: (v: string) => void;
  onSubmit?: () => void;
  suggestions: string[];
  onPick: (s: string) => void;
}) {
  return (
    <div className="relative">
      <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 backdrop-blur-xl focus-within:border-ai/40 transition-colors">
        <Search className="h-3.5 w-3.5 text-fg-muted" />
        <input
          value={value}
          onChange={(e) => onChange(e.target.value.toUpperCase().slice(0, 5))}
          onKeyDown={(e) => {
            if (e.key === "Enter" && onSubmit) {
              e.preventDefault();
              onSubmit();
            }
          }}
          className="num bg-transparent text-[15px] font-medium text-fg outline-none w-20 tracking-wider"
          placeholder={placeholder}
          aria-label="Ticker search"
        />
      </div>
      {suggestions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="absolute z-30 mt-1 w-full overflow-hidden rounded-xl border border-white/10 bg-ink-900/95 backdrop-blur-xl shadow-2xl"
        >
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              className={clsx(
                "block w-full px-3 py-2 text-left text-xs text-fg-muted hover:bg-white/[0.06] hover:text-fg num tracking-wider"
              )}
            >
              {s}
            </button>
          ))}
        </motion.div>
      )}
    </div>
  );
}
