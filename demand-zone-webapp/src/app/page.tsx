"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";
import { Stat } from "@/components/Stat";
import { Pill } from "@/components/Pill";
import { DemandZoneChart } from "@/components/DemandZoneChart";
import { SignalCard } from "@/components/SignalCard";
import { SidebarPanel, Kv } from "@/components/SidebarPanel";
import { SegTabs } from "@/components/SegTabs";
import { Sparkline } from "@/components/Sparkline";
import { FeatureBars } from "@/components/FeatureBars";
import { MiniBar } from "@/components/MiniHistogram";
import { HEADLINE_METRICS, BACKTEST, PIPELINE } from "@/data/metrics";
import { TOP_FEATURES } from "@/data/features";
import { CHART_DATA, ZONES, RECENT_SIGNALS, TICKERS } from "@/data/signals";
import { formatConfidence, formatPct, formatUsd } from "@/lib/format";

const SPARK_INPUT = [
  100, 100.4, 100.9, 100.7, 101.5, 101.7, 102.0, 102.3, 102.1, 102.8, 103.2, 103.5, 103.7,
];

export default function Home() {
  const [ticker, setTicker] = useState<"NVDA" | "AAPL" | "MSFT">("NVDA");
  const data = CHART_DATA[ticker]!;
  const zones = ZONES[ticker]!;

  return (
    <AppShell>
      {/* Hero strip — KPIs only. No marketing copy. */}
      <div className="border-b border-line bg-ink-900">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-6 px-6 py-4">
          <div className="flex items-baseline gap-3">
            <span className="text-[15px] font-medium text-fg">Demand Zone AI</span>
            <span className="num text-2xs text-fg-subtle">
              {PIPELINE.dateRange.start} → {PIPELINE.dateRange.end}
            </span>
          </div>
          <div className="hidden md:flex items-center gap-7">
            {HEADLINE_METRICS.map((m, i) => (
              <Stat
                key={m.key}
                label={m.label}
                value={m.format === "auc" ? m.value.toFixed(4) : `${(m.value * 100).toFixed(1)}%`}
                sentiment={m.sentiment === "ai" ? "ai" : m.sentiment === "neutral" ? "neutral" : "neutral"}
                delay={i * 0.05}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Pill variant="ai" dot>AI</Pill>
            <Pill variant="neutral">{PIPELINE.modelFamily}</Pill>
          </div>
        </div>
      </div>

      {/* Quick ticker switcher */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-line overflow-x-auto scrollbar-none">
        {(["NVDA", "AAPL", "MSFT", "AMZN", "TSLA", "META", "GOOGL", "BRK.B", "JPM", "LLY"] as const).map(
          (sym) => (
            <button
              key={sym}
              onClick={() => setTicker(sym as typeof ticker)}
              className={
                "num h-6 px-2.5 text-[11px] tracking-wider uppercase border " +
                (ticker === sym
                  ? "border-line-strong text-fg bg-ink-850"
                  : "border-transparent text-fg-muted hover:text-fg")
              }
            >
              {sym}
            </button>
          )
        )}
      </div>

      {/* Main: take the user's first question "what should I look at?" */}
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px]">
        {/* Chart column */}
        <div className="flex min-h-0 flex-col border-r border-line">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <div className="flex items-baseline gap-6">
              <div>
                <div className="num text-[22px] leading-none font-semibold tracking-tight text-fg">
                  {ticker}
                </div>
                <div className="text-2xs text-fg-subtle mt-1">
                  {TICKERS.find((t) => t.symbol === ticker)?.name ?? ""}
                </div>
              </div>
              <div className="flex items-center gap-5">
                <Stat
                  label="Last"
                  value={`$${data[data.length - 1]!.close.toFixed(2)}`}
                  sentiment="pos"
                  emphasised={false}
                />
            <Stat
              label="Δ Day"
              value={formatPct(
                data[data.length - 1]!.close / data[data.length - 2]!.close - 1
              )}
              sentiment={data[data.length - 1]!.close >= data[data.length - 2]!.close ? "pos" : "neg"}
            />
                <Stat
                  label="Zone Low"
                  value={`$${zones[0]!.bottomPrice.toFixed(2)}`}
                  sentiment="ai"
                />
                <Stat
                  label="Touches"
                  value={zones[0]!.touches.toString()}
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Pill variant="pos">BUY</Pill>
              <Pill variant="ai" dot>AI</Pill>
              <SegTabs
                value="1D"
                onChange={() => {}}
                options={[
                  { value: "1D", label: "1D" },
                  { value: "1W", label: "1W" },
                  { value: "1M", label: "1M" },
                  { value: "3M", label: "3M" },
                  { value: "1Y", label: "1Y" },
                ]}
              />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden">
            <DemandZoneChart
              data={data}
              zones={zones}
              height={520}
              highlightZoneIndex={0}
            />
          </div>

          {/* Take the user's second question "why does the model think this?" */}
          <div className="grid grid-cols-3 border-t border-line bg-ink-900">
            <div className="border-r border-line p-4">
              <div className="panel-label mb-2">Why BUY?</div>
              <div className="text-xs text-fg-muted leading-relaxed">
                Fresh demand zone established at{" "}
                <span className="num text-fg">${zones[0]!.bottomPrice.toFixed(2)}</span>
                {" — "}consolidation range <span className="num text-fg">{(zones[0]!.topPrice - zones[0]!.bottomPrice).toFixed(2)}</span> points,
                rejection wick <span className="num text-pos">{(0.62 * 100).toFixed(0)}%</span> of body,
                SPY regime positive, sector ETF XLY momentum confirms.
              </div>
              <div className="mt-3 flex items-center gap-2">
                <Pill variant="ai">Base Range %</Pill>
                <Pill variant="ai">Zone Width %</Pill>
                <Pill variant="ai">SPY 50d</Pill>
              </div>
            </div>

            <div className="border-r border-line p-4">
              <div className="panel-label mb-2">Risk Profile</div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                <Kv k="Entry" v="$891.40" mono />
                <Kv k="Stop" v="$846.83" mono sentiment="neg" />
                <Kv k="Target" v="$1,025.11" mono sentiment="pos" />
                <Kv k="R:R" v="3.0" mono sentiment="ai" />
                <Kv k="Holding" v="20 days" mono />
                <Kv k="Confidence" v="81%" mono sentiment="ai" />
              </div>
            </div>

            <div className="p-4">
              <div className="panel-label mb-2 flex items-center justify-between">
                <span>Top Features</span>
                <Link href="/performance" className="num text-2xs text-ai">
                  Audit →
                </Link>
              </div>
              <FeatureBars
                features={TOP_FEATURES.slice(0, 5).map((f) => ({
                  name: f.displayName,
                  value: f.importance / 0.0281,
                  raw: f.importance,
                  direction: f.direction,
                }))}
              />
            </div>
          </div>
        </div>

        {/* Side rail — live signals and quick stats. */}
        <aside className="flex min-h-0 flex-col bg-ink-900">
          <SidebarPanel
            label="Model Telemetry"
            trailing={<Pill variant="ai" dot>LIVE</Pill>}
          >
            <div className="flex flex-col gap-2">
              <Kv k="Inference" v="0.41 ms" mono />
              <div className="h-px bg-line my-1" />
              <Kv k="Daily Features" v={PIPELINE.features} mono />
              <Kv k="Window" v="20 sessions" mono />
              <Kv k="Universe" v={`${PIPELINE.universe.split(" ")[0]} ${PIPELINE.universe.split(" ")[1]} (${TICKERS.length})`} mono />
            </div>
            <div className="mt-3 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-2xs text-fg-subtle">Hit-Target WF AUC</span>
                <span className="num text-2xs text-pos">+12pp</span>
              </div>
              <MiniBar value={0.762} tone="pos" />
            </div>
          </SidebarPanel>

          {/* Live signals list. The user's third question "what's actionable now?" */}
          <SidebarPanel
            label="Actionable Now"
            trailing={<Link href="/analysis?ticker=NVDA" className="num text-2xs text-ai">Open →</Link>}
          >
            <ul className="-mx-4 -mb-4">
              {RECENT_SIGNALS.slice(0, 6).map((s) => (
                <li key={s.ticker} className="border-t border-line-faint first:border-t-0">
                  <SignalCard
                    ticker={s.ticker}
                    name={s.name}
                    signal={s.signal}
                    confidence={s.confidence}
                    zonePrice={s.zonePrice}
                    meta={<span className="num">{(s.confidence * 100).toFixed(0)}% · {s.ageHours}h</span>}
                    spark={<Sparkline values={SPARK_INPUT} positive={s.confidence > 0.7} />}
                  />
                </li>
              ))}
            </ul>
          </SidebarPanel>

          <SidebarPanel label="Last Backtest" divider>
            <div className="grid grid-cols-3 gap-2">
              <BacktestCell label="Return" value={formatPct(BACKTEST.totalReturn)} tone="pos" />
              <BacktestCell label="Win" value={formatPct(BACKTEST.winRate, 0, false)} tone="neutral" />
              <BacktestCell label="Sharpe" value={BACKTEST.sharpe.toFixed(2)} tone="ai" />
            </div>
            <div className="mt-3 num text-2xs text-fg-subtle">
              {BACKTEST.period} · ε {BACKTEST.trades} trades
            </div>
            <Link
              href="/backtest"
              className="mt-3 block text-center border border-line px-3 py-2 text-xs text-fg hover:bg-ink-850 transition-colors"
            >
              Open audit ledger
            </Link>
          </SidebarPanel>

          <SidebarPanel label="System">
            <Kv k="Equity Band" v="100% of price" mono />
            <Kv k="Risk / Trade" v={BACKTEST.riskPerTrade} mono />
            <Kv k="Commission"  v={BACKTEST.commission} mono />
            <Kv k="Slippage"    v={BACKTEST.slippage} mono />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-xs text-fg-muted">Initial Capital</span>
              <span className="num text-xs text-fg">
                {formatUsd(BACKTEST.initialCapital, 0)}
              </span>
            </div>
          </SidebarPanel>
        </aside>
      </div>
    </AppShell>
  );
}

function BacktestCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "pos" | "neg" | "neutral" | "ai";
}) {
  const color =
    tone === "pos"
      ? "text-pos"
      : tone === "neg"
      ? "text-neg"
      : tone === "ai"
      ? "text-ai"
      : "text-fg";
  return (
    <div className="border border-line bg-ink-900 px-2.5 py-2">
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </div>
      <div className={"num text-[15px] leading-none mt-1.5 " + color}>{value}</div>
    </div>
  );
}


