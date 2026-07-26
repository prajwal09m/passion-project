"use client";

import { motion, AnimatePresence } from "motion/react";
import { useState } from "react";
import { ChevronDown, Cpu } from "lucide-react";

interface ModelInfoProps {
  modelName?: string;
  metadata?: Record<string, unknown>;
}

export function ModelInfo({ modelName = "LightGBM v8", metadata = {} }: ModelInfoProps) {
  const [open, setOpen] = useState(false);

  // Extract known fields from metadata
  const trainedAt = String((metadata as Record<string, unknown>).trained_at ?? (metadata as Record<string, unknown>).trainedAt ?? "N/A");
  const featuresCount = String((metadata as Record<string, unknown>).features_count ?? (metadata as Record<string, unknown>).featuresCount ?? "86");
  const datasetRows = String((metadata as Record<string, unknown>).dataset_rows ?? "27,638");
  const modelFamily = String((metadata as Record<string, unknown>).family ?? "Gradient Boosted Decision Trees");

  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Cpu className="h-3.5 w-3.5 text-ai" />
          <span className="text-[13px] font-medium text-fg">Model Information</span>
          <span className="num text-2xs text-fg-muted">{modelName}</span>
        </div>
        <motion.span
          animate={{ rotate: open ? 180 : 0 }}
          transition={{ duration: 0.25 }}
        >
          <ChevronDown className="h-4 w-4 text-fg-muted" />
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="grid grid-cols-2 gap-px bg-white/[0.04] border-t border-white/[0.06]">
              <Row k="Model" v={modelName} />
              <Row k="Type" v={modelFamily} />
              <Row k="Dataset" v={`${datasetRows} signals`} />
              <Row k="Features" v={featuresCount} />
              <Row k="Trained" v={trainedAt} />
              <Row k="Inference" v="< 100 ms" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="bg-ink-900 px-4 py-2.5">
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">{k}</div>
      <div className="num text-xs text-fg mt-0.5">{v}</div>
    </div>
  );
}
