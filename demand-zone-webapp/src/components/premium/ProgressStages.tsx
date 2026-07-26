"use client";

import { motion, AnimatePresence } from "motion/react";
import { Check, Loader2, Sparkles } from "lucide-react";

export interface ProgressStage {
  label: string;
  key: string;
}

const STAGES: ProgressStage[] = [
  { label: "Validating ticker", key: "validating" },
  { label: "Downloading historical market data", key: "downloading" },
  { label: "Calculating technical indicators", key: "indicators" },
  { label: "Detecting demand and supply zones", key: "zones" },
  { label: "Generating ML feature vector", key: "features" },
  { label: "Running AI inference", key: "inference" },
  { label: "Computing risk metrics and trade setup", key: "risk" },
  { label: "Preparing interactive charts", key: "charts" },
];

interface ProgressStagesProps {
  currentStage: string;
  progress: number;
  ticker: string;
}

/**
 * Multi-stage loading progress display.
 * Shows each pipeline stage with a checkmark when complete,
 * a spinner for the current stage, and pending for upcoming stages.
 */
export function ProgressStages({ currentStage, progress, ticker }: ProgressStagesProps) {
  const currentIdx = STAGES.findIndex(
    (s) => currentStage.toLowerCase().includes(s.key) || s.label.toLowerCase().includes(currentStage.toLowerCase())
  );

  return (
    <div className="flex flex-col items-center gap-6 min-h-[50vh] justify-center">
      {/* Header */}
      <div className="flex flex-col items-center gap-2">
        <motion.div
          animate={{ scale: [1, 1.08, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        >
          <Sparkles className="h-8 w-8 text-ai" />
        </motion.div>
        <h2 className="text-[15px] font-medium text-fg">Analyzing {ticker}</h2>
        <p className="text-2xs text-fg-muted uppercase tracking-[0.12em]">
          AI pipeline in progress
        </p>
      </div>

      {/* Progress bar */}
      <div className="w-full max-w-sm">
        <div className="h-1 w-full rounded-full bg-white/[0.06] overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-ai"
            initial={{ width: "0%" }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>
        <div className="mt-1 text-right num text-2xs text-fg-muted">{progress}%</div>
      </div>

      {/* Stages */}
      <div className="flex flex-col gap-1 w-full max-w-sm">
        {STAGES.map((stage, i) => {
          const done = i < currentIdx;
          const active = i === currentIdx;
          const pending = i > currentIdx;

          return (
            <div
              key={stage.key}
              className="flex items-center gap-3 px-3 py-2"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center">
                {done ? (
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.2 }}
                  >
                    <Check className="h-4 w-4 text-pos" />
                  </motion.span>
                ) : active ? (
                  <Loader2 className="h-4 w-4 text-ai animate-spin" />
                ) : (
                  <span className="block h-1.5 w-1.5 rounded-full bg-white/[0.08]" />
                )}
              </span>
              <span
                className={`text-[13px] transition-colors ${
                  done ? "text-pos" : active ? "text-ai font-medium" : "text-fg-muted"
                }`}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
