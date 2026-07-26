"use client";

import { clsx } from "clsx";

/**
 * TradingView-style segmented tab control.
 * Used in timeframes, panel switchers, etc.
 */
export function SegTabs<T extends string>({
  value,
  onChange,
  options,
  className,
}: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={clsx(
        "flex h-7 items-center gap-0 border border-line bg-ink-900",
        className
      )}
    >
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            data-active={active}
            onClick={() => onChange(o.value)}
            className={clsx(
              "seg-btn h-full",
              active && "bg-ink-850",
              active && "text-fg"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
