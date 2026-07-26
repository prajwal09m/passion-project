"use client";

/**
 * Inline ASCII sparkline — used in backtest header for a cinematic look.
 * (Compact, terminal-flavored representation of the equity curve).
 */
export function AsciiEquity({
  width = 90,
  values,
}: {
  width?: number;
  values: number[];
}) {
  if (values.length === 0) return null;
  const blocks = "▁▂▃▄▅▆▇█";
  // Resample into ~width points.
  const step = Math.max(1, Math.floor(values.length / width));
  const sampled: number[] = [];
  for (let i = 0; i < values.length; i += step) sampled.push(values[i]!);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return (
    <span
      className="num text-ai"
      style={{
        fontFamily:
          'var(--font-mono), ui-monospace, "SF Mono", monospace',
        letterSpacing: "0.02em",
      }}
      aria-hidden
    >
      {sampled.map((v) => {
        const idx = Math.min(blocks.length - 1, Math.floor(((v - min) / range) * (blocks.length - 1)));
        return blocks[idx];
      })}
    </span>
  );
}
