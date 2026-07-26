"use client";

import { clsx } from "clsx";
import { Pill } from "./Pill";
import type { ReactNode } from "react";

export type SignalProps = {
  ticker: string;
  name: string;
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number;
  zonePrice: number;
  /** Optional micro sparkline */
  spark?: ReactNode;
  /** Right-side metadata (e.g., age) */
  meta?: ReactNode;
};

export function SignalCard(p: SignalProps) {
  const tone =
    p.signal === "BUY"
      ? "pos"
      : p.signal === "SELL"
      ? "neg"
      : "neutral";
  return (
    <div className="group flex items-center justify-between gap-3 px-3 py-2.5 hover:bg-ink-850 cursor-pointer transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <Pill variant={tone}>{p.signal}</Pill>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-fg">{p.ticker}</span>
            <ConfidenceTick value={p.confidence} />
          </div>
          <div className="text-2xs text-fg-subtle truncate">{p.name}</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {p.spark}
        <div className="text-right">
          <div className="num text-2xs text-fg-muted">
            ${p.zonePrice.toFixed(2)}
          </div>
          {p.meta ? (
            <div className="text-2xs text-fg-subtle">{p.meta}</div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function ConfidenceTick({ value }: { value: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-12 bg-line overflow-hidden">
        <div
          className={clsx(
            "h-full",
            value >= 0.7 ? "bg-pos" : value >= 0.55 ? "bg-ai" : "bg-fg-subtle"
          )}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className="num text-2xs text-fg-muted">
        {Math.round(value * 100)}
      </span>
    </div>
  );
}
