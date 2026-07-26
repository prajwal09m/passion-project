"use client";

import { clsx } from "clsx";
import type { ReactNode } from "react";

/**
 * Wraps a side-panel block: a panel label row, optional action slot, and
 * content body. Sections are separated with hairline rules. Use this for
 * every block in any right-rail or column.
 */
export function SidebarPanel({
  label,
  trailing,
  children,
  className,
  divider = true,
  bodyClassName,
}: {
  label?: ReactNode;
  trailing?: ReactNode;
  children: ReactNode;
  className?: string;
  divider?: boolean;
  bodyClassName?: string;
}) {
  return (
    <section
      className={clsx(
        divider && "border-b border-line",
        className
      )}
    >
      {(label || trailing) && (
        <header className="flex items-center justify-between px-4 py-2.5">
          {label ? (
            <h3 className="panel-label">{label}</h3>
          ) : (
            <span />
          )}
          {trailing ? <div className="text-2xs text-fg-subtle">{trailing}</div> : null}
        </header>
      )}
      <div className={clsx("px-4 pb-4", bodyClassName)}>{children}</div>
    </section>
  );
}

/**
 * A compact two-column data row used inside SidebarPanels.
 */
export function Kv({
  k,
  v,
  /** Sentiment applies the matching accent color to `v`. */
  sentiment = "neutral",
  mono = true,
}: {
  k: ReactNode;
  v: ReactNode;
  sentiment?: "neutral" | "pos" | "neg" | "ai";
  mono?: boolean;
}) {
  const tone =
    sentiment === "pos"
      ? "text-pos"
      : sentiment === "neg"
      ? "text-neg"
      : sentiment === "ai"
      ? "text-ai"
      : "text-fg";
  return (
    <div className="kv-row">
      <div className="kv-key">{k}</div>
      <div className={clsx("kv-val", mono && "num", tone)}>{v}</div>
    </div>
  );
}
