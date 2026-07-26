"use client";

import { AppShell } from "@/components/AppShell";
import { Stat } from "@/components/Stat";
import { Pill } from "@/components/Pill";
import { SidebarPanel, Kv } from "@/components/SidebarPanel";
import { EquityCurveChart } from "@/components/EquityCurveChart";
import { DataTable } from "@/components/DataTable";
import { AsciiEquity } from "@/components/AsciiEquity";
import { DistributionBars } from "@/components/PnlDistributionChart";
import { BACKTEST, PIPELINE } from "@/data/metrics";
import { EQUITY_CURVE, TRADES, type Trade } from "@/data/signals";
import { formatUsd, formatPct } from "@/lib/format";

export default function BacktestPage() {
  return (
    <AppShell>
      {/* Hero — equity ASCII + headline numbers, no marketing copy */}
      <div className="border-b border-line bg-ink-900">
        <div className="grid grid-cols-[1fr_auto] items-end gap-8 px-6 py-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-[15px] font-medium text-fg">Backtest</span>
              <Pill variant="ai">{BACKTEST.period}</Pill>
              <Pill variant="neutral">Capacity-limited</Pill>
            </div>
            <div className="mt-2 num text-[14px] leading-none text-ai">
              <AsciiEquity
                values={EQUITY_CURVE.map((p) => p.equity)}
                width={140}
              />
            </div>
          </div>
          <div className="grid grid-cols-6 gap-8">
            <Stat
              label="Total Return"
              value={formatPct(BACKTEST.totalReturn)}
              sentiment="pos"
              emphasised
              delay={0}
            />
            <Stat
              label="Win Rate"
              value={formatPct(BACKTEST.winRate, 0, false)}
              delay={0.05}
            />
            <Stat
              label="Sharpe"
              value={BACKTEST.sharpe.toFixed(2)}
              sentiment="ai"
              delay={0.1}
            />
            <Stat
              label="Sortino"
              value={BACKTEST.sortino.toFixed(2)}
              delay={0.15}
            />
            <Stat
              label="Max DD"
              value={formatPct(BACKTEST.maxDrawdown)}
              sentiment="neg"
              delay={0.2}
            />
            <Stat
              label="Profit Factor"
              value={BACKTEST.profitFactor.toFixed(2)}
              delay={0.25}
            />
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-h-0 flex-col border-r border-line overflow-y-auto">
          <section className="border-b border-line">
            <div className="flex items-center justify-between border-b border-line bg-ink-900 px-5 py-3">
              <div className="flex items-center gap-3">
                <span className="block h-3 w-px bg-ai" />
                <h2 className="text-[12.5px] font-medium text-fg">Equity Curve</h2>
                <span className="num text-2xs text-fg-subtle">
                  vs. benchmark (SPY)
                </span>
              </div>
              <div className="flex items-center gap-3 text-2xs">
                <Legend label="Strategy" tone="pos" />
                <Legend label="SPY" tone="ai" />
                <Legend label="Drawdown" tone="neg" />
              </div>
            </div>
            <div className="bg-ink-900">
              <EquityCurveChart points={EQUITY_CURVE} height={340} />
            </div>
          </section>

          {/* Trade History */}
          <section className="border-b border-line">
            <div className="flex items-center justify-between border-b border-line bg-ink-900 px-5 py-3">
              <div className="flex items-center gap-3">
                <span className="block h-3 w-px bg-ai" />
                <h2 className="text-[12.5px] font-medium text-fg">Trade Ledger</h2>
                <span className="num text-2xs text-fg-subtle">
                  {TRADES.length} entries · audit log attached
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Pill variant="pos">{TRADES.filter((t) => t.status === "win").length} wins</Pill>
                <Pill variant="neg">{TRADES.filter((t) => t.status === "loss").length} losses</Pill>
                <Pill variant="neutral">{formatPct(BACKTEST.winRate, 0, false)} rate</Pill>
              </div>
            </div>
            <DataTable<Trade>
              rows={TRADES}
              rowKey={(t) => t.id}
              maxHeight="420px"
              columns={[
                { key: "id", header: "#" },
                { key: "ticker", header: "Ticker", cell: (r) => <span className="num">{r.ticker}</span> },
                { key: "entry", header: "Entry", cell: (r) => <span className="num">{r.entry.slice(5)}</span> },
                { key: "exit",  header: "Exit",  cell: (r) => <span className="num">{r.exit?.slice(5) ?? "—"}</span> },
                {
                  key: "entryPrice",
                  header: "Entry $",
                  align: "right",
                  numeric: true,
                  cell: (r) => formatUsd(r.entryPrice, 2),
                },
                {
                  key: "exitPrice",
                  header: "Exit $",
                  align: "right",
                  numeric: true,
                  cell: (r) => (r.exitPrice == null ? "—" : formatUsd(r.exitPrice, 2)),
                },
                {
                  key: "return",
                  header: "Return",
                  align: "right",
                  numeric: true,
                  cell: (r) => (
                    <span className={r.return > 0 ? "text-pos" : "text-neg"}>
                      {r.return > 0 ? "+" : ""}
                      {(r.return * 100).toFixed(2)}%
                    </span>
                  ),
                },
                { key: "days", header: "Days", align: "right", numeric: true },
                {
                  key: "exitReason",
                  header: "Exit",
                  align: "center",
                  cell: (r) =>
                    r.exitReason === "TP" ? (
                      <Pill variant="pos">TP</Pill>
                    ) : r.exitReason === "SL" ? (
                      <Pill variant="neg">SL</Pill>
                    ) : (
                      <Pill variant="neutral">TIME</Pill>
                    ),
                },
                {
                  key: "confidence",
                  header: "Conf",
                  align: "right",
                  numeric: true,
                  cell: (r) => `${(r.confidence * 100).toFixed(0)}%`,
                },
              ]}
            />
          </section>

          {/* Distribution metrics */}
          <section className="grid grid-cols-2 divide-x divide-line">
            <div>
              <div className="flex items-center gap-3 border-b border-line bg-ink-900 px-5 py-3">
                <span className="block h-3 w-px bg-ai" />
                <h2 className="text-[12.5px] font-medium text-fg">Return by Outcome</h2>
              </div>
              <div className="px-5 py-4">
                <DistributionBars
                  rows={[
                    { label: "Wins", value: TRADES.filter((t) => t.status === "win").length, tone: "pos" },
                    { label: "Losses", value: TRADES.filter((t) => t.status === "loss").length, tone: "neg" },
                    { label: "Avg Win",  value: BACKTEST.avgWin,  tone: "pos" },
                    { label: "Avg Loss", value: BACKTEST.avgLoss, tone: "neg" },
                    { label: "Avg Hold (days)", value: BACKTEST.avgDurationDays, tone: "neutral" },
                  ]}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-3 border-b border-line bg-ink-900 px-5 py-3">
                <span className="block h-3 w-px bg-ai" />
                <h2 className="text-[12.5px] font-medium text-fg">Risk Profile</h2>
              </div>
              <div className="px-5 py-4 grid grid-cols-2 gap-x-6 gap-y-1">
                <Kv k="Sharpe"          v={BACKTEST.sharpe.toFixed(2)} sentiment="ai" />
                <Kv k="Sortino"         v={BACKTEST.sortino.toFixed(2)} />
                <Kv k="Calmar"          v={BACKTEST.calmar.toFixed(2)} />
                <Kv k="Profit Factor"   v={BACKTEST.profitFactor.toFixed(2)} />
                <Kv k="Max Drawdown"    v={formatPct(BACKTEST.maxDrawdown)} sentiment="neg" />
                <Kv k="Avg Win Hold"    v={`${BACKTEST.winDuration} d`} />
                <Kv k="Avg Loss Hold"   v={`${BACKTEST.lossDuration} d`} />
                <Kv k="Volatility (ann)" v="18.5%" />
              </div>
            </div>
          </section>
        </div>

        {/* Side rail — backtest configuration / system notes */}
        <aside className="flex min-h-0 flex-col bg-ink-900 overflow-y-auto">
          <SidebarPanel label="Configuration" trailing={<Pill variant="ai">HARD-CODED</Pill>}>
            <Kv k="Initial Capital" v={formatUsd(BACKTEST.initialCapital, 0)} />
            <Kv k="Risk / Trade"    v={BACKTEST.riskPerTrade} />
            <Kv k="Max Positions"   v={String(BACKTEST.maxPositions)} />
            <Kv k="Commission"      v={BACKTEST.commission} sentiment="neutral" />
            <Kv k="Slippage"        v={BACKTEST.slippage} sentiment="neutral" />
            <Kv k="Universe"        v={PIPELINE.universe} />
            <Kv k="Hit-Target"      v={formatPct(0.15)} sentiment="pos" />
            <Kv k="Stop Loss"       v={formatPct(-0.05)} sentiment="neg" />
            <Kv k="Holding"         v="20 days" />
          </SidebarPanel>

          <SidebarPanel label="Caveats" divider>
            <ul className="flex flex-col gap-2.5 text-xs text-fg-muted leading-relaxed">
              <li className="flex gap-2">
                <span className="text-warn mt-0.5">◆</span>
                8-trade sample is <span className="num text-fg">insufficient</span> for statistical confidence.
              </li>
              <li className="flex gap-2">
                <span className="text-warn mt-0.5">◆</span>
                Threshold σ ≥ 0.75 was validation-selected; not tuned for test set.
              </li>
              <li className="flex gap-2">
                <span className="text-neg mt-0.5">◆</span>
                Strategies reading <span className="num text-fg">+6.98%</span> should be paired with stress tests.
              </li>
            </ul>
          </SidebarPanel>

          <SidebarPanel label="Decision">
            <div className="flex flex-col gap-3">
              <div className="text-[13px] leading-relaxed text-fg">
                <span className="num text-ai">{formatPct(BACKTEST.totalReturn)}</span>{" "}
                on held-out data with a small sample — read as research signal,
                not deployable strategy. Recommended next: paper-trade,
                extend horizon, add slippage stress.
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button className="border border-line px-3 py-2 text-[12px] text-fg hover:bg-ink-850 transition-colors">
                  Paper-trade
                </button>
                <button className="border border-line px-3 py-2 text-[12px] text-ai hover:bg-ink-850 transition-colors">
                  Stress + slippage ×3
                </button>
              </div>
            </div>
          </SidebarPanel>
        </aside>
      </div>
    </AppShell>
  );
}

function Legend({ label, tone }: { label: string; tone: "pos" | "ai" | "neg" }) {
  const color =
    tone === "pos" ? "bg-pos" : tone === "neg" ? "bg-neg" : "bg-ai";
  return (
    <span className="flex items-center gap-1.5 num">
      <span className={"block h-1 w-3 " + color} />
      <span className="text-fg-muted">{label}</span>
    </span>
  );
}
