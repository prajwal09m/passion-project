"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import { motion, AnimatePresence } from "motion/react";
import { Pill } from "./Pill";
import { RECENT_SIGNALS, INDEX_TICKS } from "@/data/signals";

/**
 * The product shell. Every page is wrapped with this so the navigation,
 * status bar, and theme are identical everywhere.
 *
 * Layout:
 *   ┌─ 200px left rail ─┬─ thin top status bar (h-7) ──────────────────┐
 *   │ brand / nav /    │ page content (current route)                  │
 *   │ watchlist        │                                              │
 *   └──────────────────┴──────────────────────────────────────────────┘
 */
export function AppShell({
  children,
  currentTicker,
}: {
  children: React.ReactNode;
  /** Optional ticker highlight, e.g. when viewing analysis of NVDA. */
  currentTicker?: string;
}) {
  const path = usePathname() ?? "/";

  // Pro keyboard shortcuts: ⌘/Ctrl + 1..4 jumps between pages.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      const map: Record<string, string> = {
        "1": "/",
        "2": "/insight",
        "3": "/analysis",
        "4": "/performance",
        "5": "/backtest",
      };
      const target = map[e.key];
      if (target) {
        e.preventDefault();
        window.location.href = target;
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="flex min-h-screen bg-ink-950 text-fg">
      <LeftRail active={path} currentTicker={currentTicker} />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopStatusBar ticker={currentTicker} />
        <main className="flex min-h-0 flex-1 flex-col">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={path}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -2 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="flex min-h-0 flex-1 flex-col"
            >
              {children}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}

function LeftRail({
  active,
  currentTicker,
}: {
  active: string;
  currentTicker?: string;
}) {
  return (
    <aside
      className="sticky top-0 flex h-screen w-[200px] shrink-0 flex-col border-r border-line bg-ink-900"
      aria-label="Primary navigation"
    >
      <Link href="/" className="flex items-center gap-2.5 border-b border-line px-4 py-3.5 group">
        <DzaiMark />
        <div className="leading-tight">
          <div className="text-[13px] font-semibold tracking-tight text-fg">DZAI</div>
          <div className="num text-2xs text-fg-subtle">v6.0</div>
        </div>
      </Link>

      <div className="px-3 pt-3">
        <div className="panel-label px-1 pb-2">Terminal</div>
        <ul className="flex flex-col gap-0.5">
          <NavItem href="/"            label="Home"     hint="⌘1" active={active === "/"} />
          <NavItem href="/insight"     label="Insight"  hint="⌘2" active={active.startsWith("/insight")} />
          <NavItem href="/analysis"    label="Analysis" hint="⌘3" active={active.startsWith("/analysis")} />
          <NavItem href="/performance" label="Model"    hint="⌘4" active={active.startsWith("/performance")} />
          <NavItem href="/backtest"    label="Backtest" hint="⌘5" active={active.startsWith("/backtest")} />
        </ul>
      </div>

<div className="mt-4 px-3">
        <div className="flex items-center justify-between px-1 pb-2">
          <span className="panel-label">Live</span>
          <Pill variant="ai" dot>AI</Pill>
        </div>
        <ul className="flex flex-col">
          {RECENT_SIGNALS.slice(0, 4).map((s) => (
            <li key={s.ticker}>
              <Link
                href={`/analysis?ticker=${s.ticker}`}
                className="flex items-center justify-between px-1.5 py-1.5 -mx-1.5 hover:bg-ink-850 cursor-pointer"
              >
                <span className="num text-xs text-fg-muted">{s.ticker}</span>
                <span
                  className={clsx(
                    "num text-[11px]",
                    s.signal === "BUY"
                      ? "text-pos"
                      : s.signal === "SELL"
                      ? "text-neg"
                      : "text-fg-muted"
                  )}
                >
                  {s.signal} · {(s.confidence * 100).toFixed(0)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex-1" />

      <div className="border-t border-line px-4 py-2.5">
        <div className="flex items-center justify-between">
          <span className="num text-2xs text-fg-subtle">SESSION</span>
          <span className="flex items-center gap-1.5">
            <span className="block h-1.5 w-1.5 rounded-full bg-pos animate-data-pulse" />
            <span className="num text-2xs text-pos">LIVE</span>
          </span>
        </div>
        <div className="mt-1.5 num text-2xs text-fg-subtle">
          σ 0.75 · 42 / 86 feats
        </div>
      </div>
    </aside>
  );
}

function NavItem({
  href,
  label,
  hint,
  active,
}: {
  href: string;
  label: string;
  hint?: string;
  active: boolean;
}) {
  return (
    <li>
      <Link
        href={href}
        className={clsx(
          "group flex items-center justify-between px-1.5 py-1.5 -mx-1.5",
          active
            ? "bg-ink-850 text-fg"
            : "text-fg-muted hover:text-fg hover:bg-ink-850"
        )}
      >
        <span className="flex items-center gap-2">
          {active && <span className="block h-3 w-px bg-ai" aria-hidden />}
          <span className={clsx("text-[13px]", active && "font-medium")}>
            {label}
          </span>
        </span>
        {hint ? <span className="num text-2xs text-fg-subtle">{hint}</span> : null}
      </Link>
    </li>
  );
}

function TopStatusBar({ ticker }: { ticker?: string }) {
  const now = useNow();
  return (
    <div className="sticky top-0 z-30 flex h-7 items-center justify-between border-b border-line bg-ink-900/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-ink-900/80">
      <div className="flex items-center gap-4 text-2xs">
        <span
          className="num text-fg-muted"
          // Server renders the placeholder; client re-renders with the live
          // time after mount to avoid SSR/CSR hydration mismatch.
          suppressHydrationWarning
        >
          {now ? formatDate(now) : "—"}
        </span>
        <span className="text-fg-subtle">·</span>
        <span className="num text-ai">USD/EQUITY</span>
        {ticker && (
          <>
            <span className="text-fg-subtle">·</span>
            <span className="num text-fg">{ticker}</span>
          </>
        )}
      </div>
      <div className="flex items-center gap-4 text-2xs">
        {INDEX_TICKS.map((t) => (
          <IndexTick key={t.label} {...t} />
        ))}
        <span
          className="block h-1.5 w-1.5 rounded-full bg-pos animate-data-pulse"
          aria-label="heartbeat"
        />
        <span className="num text-fg-subtle">pulse</span>
      </div>
    </div>
  );
}

function IndexTick({
  label,
  value,
  change,
  tone,
}: {
  label: string;
  value: string;
  change: string;
  tone?: "pos" | "neg";
}) {
  const t =
    tone ??
    (change.startsWith("+") ? "pos" : change.startsWith("-") ? "neg" : "neutral");
  const color =
    t === "pos" ? "text-pos" : t === "neg" ? "text-neg" : "text-fg-muted";
  return (
    <span className="num flex items-center gap-1.5">
      <span className="text-fg-subtle">{label}</span>
      <span className="text-fg">{value}</span>
      <span className={color}>{change}</span>
    </span>
  );
}

/**
 * Returns the current Date, but NOT during SSR. The hook returns `null` on
 * the server and on the first client render, then starts ticking once the
 * component is mounted. This keeps the SSR HTML and the first client render
 * byte-identical (no `new Date()` shape mismatch) and avoids hydration
 * warnings from text content like "18:40:32" vs "18:40:33".
 */
function useNow(): Date | null {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function formatDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

function DzaiMark() {
  return (
    <span className="flex h-7 w-7 items-center justify-center border border-line bg-ink-850">
      <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden>
        <rect x="3" y="9"  width="18" height="2" fill="#5b6cff" />
        <rect x="3" y="13" width="18" height="2" fill="#9aa6ff" />
        <rect x="3" y="17" width="10" height="2" fill="#3ecf8e" />
      </svg>
    </span>
  );
}
