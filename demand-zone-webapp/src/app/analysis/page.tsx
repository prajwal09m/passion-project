"use client";

import { useState, useMemo, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { Stat } from "@/components/Stat";
import { Pill } from "@/components/Pill";
import { SidebarPanel, Kv } from "@/components/SidebarPanel";
import { DemandZoneChart } from "@/components/DemandZoneChart";
import { ConfidenceArc } from "@/components/ConfidenceArc";
import { SegTabs } from "@/components/SegTabs";
import { SignalCard } from "@/components/SignalCard";
import { FeatureBars } from "@/components/FeatureBars";
import { CHART_DATA, ZONES, RECENT_SIGNALS, TICKERS } from "@/data/signals";
import { TOP_FEATURES } from "@/data/features";
import { BACKTEST } from "@/data/metrics";
import { formatPct, formatUsd } from "@/lib/format";

const TF_OPTS = [
  { value: "1D", label: "1D" },
  { value: "5D", label: "5D" },
  { value: "1M", label: "1M" },
  { value: "3M", label: "3M" },
  { value: "1Y", label: "1Y" },
  { value: "ALL", label: "ALL" },
];

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div />}>
      <AnalysisPageInner />
    </Suspense>
  );
}

function AnalysisPageInner() {
  const sp = useSearchParams();
  const initial = (sp?.get("ticker") ?? "NVDA") as keyof typeof CHART_DATA;
  const [ticker, setTicker] = useState<keyof typeof CHART_DATA>(initial);
  const [tf, setTf] = useState<(typeof TF_OPTS)[number]["value"]>("3M");
  const data = CHART_DATA[ticker]!;
  const zones = ZONES[ticker]!;
  const meta = TICKERS.find((t) => t.symbol === ticker)!;
  const confidence = useMemo(() => meta.confidence, [meta]);
  const last = data[data.length - 1]!;
  const prev = data[data.length - 2]!;
  const change = last.close / prev.close - 1;

  // Derived objectives — entry is zone top, stop is zone bottom (5% buffer).
  const zone = zones[0]!;
  const entry = +zone.topPrice.toFixed(2);
  const stop = +(zone.bottomPrice * 0.95).toFixed(2);
  const target = +(entry * 1.15).toFixed(2);

  return (
    <AppShell currentTicker={ticker}>
      {/* Ticker + metrics bar */}
      <div className="flex items-center justify-between border-b border-line bg-ink-900 px-5 py-3">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <input
              value={ticker}
              onChange={(e) =>
                setTicker(e.target.value.toUpperCase() as keyof typeof CHART_DATA)
              }
              className="num w-24 bg-transparent border border-line px-2.5 py-1.5 text-sm focus:outline-none focus:border-ai"
              maxLength={5}
            />
            <div className="flex items-center gap-2">
              <span className="text-2xs text-fg-subtle">{meta.sector}</span>
              <Pill variant="pos">{change > 0 ? "POS" : "NEG"}</Pill>
            </div>
          </div>
          <div className="divider-y" />
          <div className="flex items-center gap-6">
            <Stat
              label="Last"
              value={`$${last.close.toFixed(2)}`}
              sentiment={change >= 0 ? "pos" : "neg"}
              emphasised
              delay={0}
            />
            <Stat label="Δ" value={formatPct(change)} sentiment={change >= 0 ? "pos" : "neg"} delay={0.04} />
            <Stat label="High"  value={`$${Math.max(...data.slice(-30).map(d => d.high)).toFixed(2)}`} delay={0.08} />
            <Stat label="Low"   value={`$${Math.min(...data.slice(-30).map(d => d.low)).toFixed(2)}`} delay={0.12} />
            <Stat label="Volume" value={`${(last.volume / 1_000_000).toFixed(1)}M`} delay={0.16} />
            <Stat label="52-wk Δ" value={formatPct(last.close / (last.close * 1.18) - 1)} delay={0.2} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <SegTabs value={tf} onChange={setTf} options={TF_OPTS} />
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px]">
        {/* Main chart */}
        <div className="flex min-h-0 flex-col border-r border-line">
          <div className="flex items-center justify-between px-5 py-2 border-b border-line bg-ink-900/70">
            <div className="flex items-center gap-3 text-2xs">
              <span className="num text-fg-muted">AAPL · {tf}</span>
              <span className="text-fg-subtle">·</span>
              <span className="num text-ai">EMA 20 / 50</span>
              <span className="text-fg-subtle">·</span>
              <span className="num text-pos">VOL</span>
            </div>
            <div className="flex items-center gap-3 text-2xs">
              <span className="num text-fg-subtle">Z1 ▼</span>
              <span className="num text-fg">${zone.bottomPrice.toFixed(2)}–${zone.topPrice.toFixed(2)}</span>
              <span className="text-fg-subtle">·</span>
              <span className="num text-pos">Strength {zone.strength}</span>
              <span className="text-fg-subtle">·</span>
              <span className={zone.fresh ? "num text-pos" : "num text-fg-muted"}>
                {zone.fresh ? "Fresh · 1d" : "Tested · 6d"}
              </span>
            </div>
          </div>
          <div className="min-h-0 flex-1">
            <DemandZoneChart
              data={data}
              zones={zones}
              height={620}
              highlightZoneIndex={0}
            />
          </div>
          {/* Mini reasoning strip */}
          <div className="grid grid-cols-3 border-t border-line bg-ink-900 text-xs">
            <div className="border-r border-line p-3.5">
              <div className="panel-label mb-2">Why this signal?</div>
              <div className="text-xs leading-relaxed text-fg-muted">
                {ticker} is sitting <span className="num text-fg">
                  ${(last.close - zone.bottomPrice).toFixed(2)}
                </span> above its fresh demand zone at <span className="num text-fg">
                  ${zone.bottomPrice.toFixed(2)}
                </span>. Base range <span className="num text-pos">top-1 feature rank</span>, EMA50 slope positive, XLY sector confirms momentum.
              </div>
            </div>
            <div className="border-r border-line p-3.5">
              <div className="panel-label mb-2">Entry · Stop · Target</div>
              <div className="grid grid-cols-3 gap-3">
                <TradeSpec label="Entry" value={`$${entry.toFixed(2)}`} tone="neutral" />
                <TradeSpec label="Stop"  value={`$${stop.toFixed(2)}`}  tone="neg" />
                <TradeSpec label="Target" value={`$${target.toFixed(2)}`} tone="pos" />
              </div>
              <div className="mt-2 grid grid-cols-3 gap-3">
                <TradeSpec label="R:R" value="3.0" tone="ai" small />
                <TradeSpec label="Edge" value={'+$' + (target - entry).toFixed(2)} tone="pos" small />
                <TradeSpec label="Risk" value={'$' + (entry - stop).toFixed(2)} tone="neg" small />
              </div>
            </div>
            <div className="p-3.5">
              <div className="panel-label mb-2">Top Features</div>
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

        {/* Right rail */}
        <aside className="flex min-h-0 flex-col bg-ink-900 overflow-y-auto">
          <SidebarPanel
            label="AI Prediction"
            trailing={<Pill variant="ai" dot>LIVE</Pill>}
          >
            <div className="flex flex-col items-center -mt-2">
              <ConfidenceArc value={confidence} size={160} thickness={7} />
              <div className="mt-3 flex items-center gap-2">
                <Pill variant="pos">BUY</Pill>
                <span className="num text-2xs text-fg-muted">
                  σ ≥ 0.75
                </span>
              </div>
            </div>
          </SidebarPanel>

          <SidebarPanel label="Prediction Detail">
            <Kv k="Signal"        v="BUY"                         sentiment="pos" />
            <Kv k="Confidence"    v={`${(confidence * 100).toFixed(1)}%`} sentiment="ai" />
            <Kv k="Expected Gain" v={formatPct(0.15)}           sentiment="pos" />
            <Kv k="Stop Loss"     v={formatPct(-0.05)}          sentiment="neg" />
            <Kv k="Holding"       v="20 days" />
            <Kv k="R:R"           v="3.0" />
          </SidebarPanel>

          <SidebarPanel label="Demand Zone Telemetry">
            <Kv k="Zone Floor"  v={`$${zone.bottomPrice.toFixed(2)}`} sentiment="ai" />
            <Kv k="Zone Ceil"   v={`$${zone.topPrice.toFixed(2)}`} />
            <Kv k="Width"       v={`${(zone.topPrice - zone.bottomPrice).toFixed(2)} (~${(((zone.topPrice - zone.bottomPrice) / zone.bottomPrice) * 100).toFixed(1)}%)`} />
            <Kv k="Touches"     v={zone.touches.toString()} />
            <Kv k="Strength"    v={zone.strength} sentiment={zone.strength === "High" ? "pos" : "neutral"} />
            <Kv k="Freshness"   v={zone.fresh ? "1 day" : "6 days"} sentiment={zone.fresh ? "pos" : "neutral"} />
            <Kv k="Departure Vol ×" v="1.42×" />
            <Kv k="Rejection"   v="Wick 62% body" />
          </SidebarPanel>

          <SidebarPanel
            label="Other Tickers"
            trailing={<Link href="/analysis" className="num text-2xs text-ai">All →</Link>}
          >
            <ul className="-mx-4 -mb-4">
              {RECENT_SIGNALS.slice(0, 5).map((s) => (
                <li key={s.ticker} className="border-t border-line-faint first:border-t-0">
                  <SignalCard
                    ticker={s.ticker}
                    name={s.name}
                    signal={s.signal}
                    confidence={s.confidence}
                    zonePrice={s.zonePrice}
                    meta={<span className="num">{(s.confidence * 100).toFixed(0)}%</span>}
                  />
                </li>
              ))}
            </ul>
          </SidebarPanel>

          <SidebarPanel label="System" divider>
            <Kv k="Account Equity"   v={formatUsd(BACKTEST.initialCapital + 698, 0)} sentiment="pos" />
            <Kv k="Open Positions"   v="2 / 5" />
            <Kv k="Risk / Trade"     v={BACKTEST.riskPerTrade} />
            <Kv k="Capital Reserved" v={formatUsd(2434, 0)} />
            <Kv k="Cash available"   v={formatUsd(29356, 0)} />
          </SidebarPanel>
        </aside>
      </div>
    </AppShell>
  );
}

function TradeSpec({
  label,
  value,
  tone,
  small = false,
}: {
  label: string;
  value: string;
  tone: "pos" | "neg" | "neutral" | "ai";
  small?: boolean;
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
    <div>
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </div>
      <div
        className={
          "num leading-none mt-1.5 " +
          color +
          " " +
          (small ? "text-[12px]" : "text-[15px]") +
          " font-medium"
        }
      >
        {value}
      </div>
    </div>
  );
}
