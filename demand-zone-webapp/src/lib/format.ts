// Formatting helpers — used everywhere a number needs to render consistently.

export function formatPct(n: number, digits = 1, withSign = true): string {
  const sign = withSign && n > 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(digits)}%`;
}

export function formatUsd(n: number, digits = 2): string {
  return `$${n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}`;
}

export function formatUsdCompact(n: number): string {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}

export function formatNum(n: number, digits = 2): string {
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatInt(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatAuc(n: number): string {
  return n.toFixed(4);
}

export function formatConfidence(n: number): string {
  return `${Math.round(n * 100)}%`;
}

// Sentiment → Tailwind utility class.
export function sentimentClass(v: number, kind: "delta" | "value" = "value"): string {
  if (kind === "delta") {
    if (v > 0) return "text-pos";
    if (v < 0) return "text-neg";
  }
  return "text-fg";
}
