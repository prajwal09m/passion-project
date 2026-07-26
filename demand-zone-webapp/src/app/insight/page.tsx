"use client";

import { useState, useEffect, useMemo, Suspense, useCallback, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Activity,
  BarChart3,
  Newspaper,
  Shield,
  Eye,
  Save,
  Share2,
  Bell,
  Sparkles,
  Loader2,
  AlertTriangle,
} from "lucide-react";

import { AppShell } from "@/components/AppShell";
import { GlassCard } from "@/components/premium/GlassCard";
import { FloatingParticles } from "@/components/premium/FloatingParticles";
import { ConfidenceGauge } from "@/components/premium/ConfidenceGauge";
import { IndicatorCard } from "@/components/premium/IndicatorCard";
import { RiskGauge } from "@/components/premium/RiskGauge";
import { FeatureBar } from "@/components/premium/FeatureBar";
import { ReasoningItem } from "@/components/premium/ReasoningItem";
import { ActionButton } from "@/components/premium/ActionButton";
import { TickerSearch } from "@/components/premium/TickerSearch";
import { ModelInfo } from "@/components/premium/ModelInfo";
import { PremiumChart, type PremiumZone } from "@/components/premium/PremiumChart";
import { ProgressStages } from "@/components/premium/ProgressStages";
import { PREMIUM_TOOLS, PREMIUM_TIMEFRAMES } from "@/components/premium/timeframes";
import {
  fetchPredictionWithProgress,
  type PredictResponse,
  type TickerInfo,
  type TradeSetup,
  type Recommendation,
} from "@/lib/api";
import { formatPct, formatInt } from "@/lib/format";

// ─── Constants (stable values that aren't prediction-dependent) ──────

const TIMEFRAMES = ["1m", "5m", "15m", "1H", "4H", "1D", "1W"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

// Static ticker symbols for suggestions (not dependent on API)
const SUGGESTION_TICKERS = [
  "NVDA", "AAPL", "MSFT", "AMZN", "TSLA", "META", "GOOGL",
  "LLY", "JPM", "AVGO", "AMD", "COIN", "PLTR", "UBER", "SHOP",
  "CRM", "NFLX", "ORCL", "BA", "DIS", "PYPL", "SQ", "SNAP",
];

const MARKET_STATUS_MAP: Record<string, "OPEN" | "PRE" | "POST" | "CLOSED"> = {
  OPEN: "OPEN", REGULAR: "OPEN",
  PRE: "PRE", PREPRE: "PRE", PRE_MARKET: "PRE",
  POST: "POST", POSTPOST: "POST", AFTER_HOURS: "POST",
};

export default function Page() {
  return (
    <Suspense fallback={<div />}>
      <InsightPage />
    </Suspense>
  );
}

function InsightPage() {
  const sp = useSearchParams();
  const initial = (sp?.get("ticker") ?? "NVDA").toUpperCase();
  const [ticker, setTicker] = useState<string>(initial);
  const [tf, setTf] = useState<Timeframe>("1D");
  const [tool, setTool] = useState<string>("cross");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PredictResponse | null>(null);
  const [progressStage, setProgressStage] = useState("Initializing");
  const [progressPct, setProgressPct] = useState(0);

  // Fetch prediction on ticker change with progress tracking
  const loadPrediction = useCallback(async (symbol: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setProgressStage("Initializing");
    setProgressPct(0);
    try {
      const result = await fetchPredictionWithProgress(
        symbol,
        (stage, pct) => {
          setProgressStage(stage);
          setProgressPct(pct);
        },
        signal,
      );
      setData(result);
    } catch (err) {
      if (err instanceof Error && err.message === "Aborted") return;
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadPrediction(ticker, controller.signal);
    return () => controller.abort();
  }, [ticker, loadPrediction]);

  const suggestions = useMemo(
    () =>
      SUGGESTION_TICKERS.filter(
        (s) => s.startsWith(search.toUpperCase()) && search.length > 0 && s !== ticker
      ),
    [search, ticker]
  );

  // ─── Loading state ────────────────────────────────────────────────
  if (!data && loading) {
    return (
      <AppShell currentTicker={ticker}>
        <FloatingParticles />
        <div className="relative z-10">
          <ProgressStages currentStage={progressStage} progress={progressPct} ticker={ticker} />
        </div>
      </AppShell>
    );
  }

  // ─── Error state ──────────────────────────────────────────────────
  if (!data && error) {
    return (
      <AppShell currentTicker={ticker}>
        <FloatingParticles />
        <div className="relative z-10 flex items-center justify-center min-h-[60vh]">
          <div className="flex flex-col items-center gap-4 text-center max-w-md">
            <AlertTriangle className="h-10 w-10 text-warn" />
            <p className="text-fg font-medium">Prediction Unavailable</p>
            <p className="text-fg-muted text-sm">{error}</p>
            <button
              onClick={() => loadPrediction(ticker)}
              className="inline-flex items-center gap-2 rounded-lg border border-ai/30 bg-ai/10 px-4 py-2 text-ai text-sm hover:bg-ai/15 transition-colors"
            >
              <RefreshCw className="h-4 w-4" /> Retry
            </button>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!data) return null;

  // ─── Data mapping ─────────────────────────────────────────────────
  const t = data.ticker;
  const positive = t.change >= 0;
  const previous = data.candles.length > 1
    ? data.candles[data.candles.length - 2]!.close
    : t.price;
  const marketStatus = MARKET_STATUS_MAP[t.market_status] ?? "OPEN";

  const demandZones: PremiumZone[] = data.zones
    .filter((z) => z.side === "demand")
    .map((z) => ({
      startIdx: Math.max(0, data.candles.length - 10 - z.age_days),
      endIdx: data.candles.length - 1,
      topPrice: z.upper_bound,
      bottomPrice: z.lower_bound,
      strength: z.strength as "High" | "Medium" | "Low",
      fresh: z.fresh,
      touches: z.touches,
      side: "demand" as const,
      createdAt: z.created_at,
      winRate: z.win_rate,
      avgBounce: z.avg_bounce_pct,
      avgDuration: z.avg_duration_days,
    }));

  const supplyZones: PremiumZone[] = data.zones
    .filter((z) => z.side === "supply")
    .map((z) => ({
      startIdx: Math.max(0, data.candles.length - 10 - z.age_days),
      endIdx: data.candles.length - 1,
      topPrice: z.upper_bound,
      bottomPrice: z.lower_bound,
      strength: z.strength as "High" | "Medium" | "Low",
      fresh: z.fresh,
      touches: z.touches,
      side: "supply" as const,
      createdAt: z.created_at,
      winRate: z.win_rate,
      avgBounce: z.avg_bounce_pct,
      avgDuration: z.avg_duration_days,
    }));

  // Map technical indicators to the IndicatorCard format
  const indicatorList = data.technicals
    ? [
        { key: "rsi", name: "RSI (14)", ...data.technicals.rsi, hint: "" },
        { key: "macd", name: "MACD", ...data.technicals.macd, hint: "" },
        { key: "adx", name: "ADX (14)", ...data.technicals.adx, hint: "" },
        { key: "atr", name: "ATR (14)", ...data.technicals.atr, hint: "" },
        { key: "vwap", name: "VWAP", ...data.technicals.vwap, hint: "" },
        { key: "ema20", name: "EMA 20", ...data.technicals.ema20, hint: "" },
        { key: "ema50", name: "EMA 50", ...data.technicals.ema50, hint: "" },
        { key: "ema200", name: "EMA 200", ...data.technicals.ema200, hint: "" },
        { key: "volume", name: "Volume", ...data.technicals.volume, hint: "" },
        { key: "rvol", name: "Relative Volume", ...data.technicals.rvol, hint: "" },
        { key: "trend", name: "Trend Score", ...data.technicals.trend, hint: "" },
      ]
    : [];

  return (
    <AppShell currentTicker={ticker}>
      <FloatingParticles />
      <div className="relative z-10">
        {/* Loading overlay */}
        {loading && (
          <div className="absolute top-2 right-5 z-30 flex items-center gap-2 rounded-lg border border-ai/20 bg-ai/10 px-3 py-1.5 text-ai text-xs">
            <Loader2 className="h-3 w-3 animate-spin" />
            Updating…
          </div>
        )}

        <Header
          t={t}
          search={search}
          onSearch={setSearch}
          suggestions={suggestions}
          onPick={setTicker}
          tf={tf}
          onTf={setTf}
          onRefresh={() => loadPrediction(ticker)}
          positive={positive}
          marketStatus={marketStatus}
        />

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_420px] gap-5 p-5">
          {/* LEFT — chart column */}
          <div className="flex flex-col gap-5 min-w-0">
            <ChartPanel
              candles={data.candles}
              demandZones={demandZones}
              supplyZones={supplyZones}
              predictedPath={data.predicted_path}
              tradeSetup={data.trade_setup}
              t={t}
              tool={tool}
              onTool={setTool}
            />

            {/* Action buttons row */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              <ActionButton variant="primary" icon={<Sparkles className="h-4 w-4" />} delay={0.0}>
                Execute Paper Trade
              </ActionButton>
              <ActionButton icon={<Bell className="h-4 w-4" />} delay={0.05}>
                Set Alert
              </ActionButton>
              <ActionButton icon={<Save className="h-4 w-4" />} delay={0.1}>
                Save Trade
              </ActionButton>
              <ActionButton icon={<Share2 className="h-4 w-4" />} delay={0.15}>
                Export Analysis
              </ActionButton>
              <ActionButton icon={<Eye className="h-4 w-4" />} delay={0.2}>
                Watchlist
              </ActionButton>
            </div>

            {/* AI Reasoning + Features */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <GlassCard delay={0.15} className="p-5">
                <SectionHeader
                  icon={<Sparkles className="h-3.5 w-3.5 text-ai" />}
                  title="AI Reasoning"
                  trailing={`${data.model_name}`}
                />
                <p className="text-[13px] leading-relaxed text-fg-muted mb-4 mt-2">
                  Our model predicts a{" "}
                  <span className={data.recommendation === "BUY" ? "text-pos font-medium" : data.recommendation === "SELL" ? "text-neg font-medium" : "text-warn font-medium"}>
                    {data.recommendation === "BUY" ? "HIGH probability long trade" : data.recommendation === "SELL" ? "HIGH probability short trade" : "NEUTRAL outlook"}
                  </span>{" "}
                  based on real-time demand zone analysis, technical indicators, and market context.
                  Confidence: {(data.confidence * 100).toFixed(0)}%.
                  {data.reasoning.length > 0
                    ? ` Top factors include ${data.reasoning[0]!.text.toLowerCase()}.`
                    : ""}
                </p>
                <ul className="flex flex-col gap-0.5">
                  {data.reasoning.map((r, i) => (
                    <li key={r.text}>
                      <ReasoningItem text={r.text} weight={r.weight} delay={0.2 + i * 0.04} />
                    </li>
                  ))}
                </ul>
              </GlassCard>

              <GlassCard delay={0.2} className="p-5">
                <SectionHeader
                  icon={<BarChart3 className="h-3.5 w-3.5 text-ai" />}
                  title="Feature Importance"
                  trailing={data.model_name}
                />
                <div className="mt-3 flex flex-col gap-3.5">
                  {data.feature_importance.map((f, i) => (
                    <FeatureBar
                      key={f.name}
                      name={f.name}
                      contribution={f.contribution}
                      description={f.description}
                      delay={0.25 + i * 0.04}
                    />
                  ))}
                </div>
              </GlassCard>
            </div>

            {/* Indicators + Risk */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <GlassCard delay={0.25} className="p-5 lg:col-span-2">
                <SectionHeader
                  icon={<Activity className="h-3.5 w-3.5 text-ai" />}
                  title="Technical Indicators"
                  trailing="Computed from live data"
                />
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {indicatorList.map((ind, i) => (
                    <IndicatorCard
                      key={ind.key}
                      name={ind.name}
                      value={typeof ind.value === "number" ? ind.value.toFixed(2) : String(ind.value)}
                      status={ind.status}
                      score={ind.score}
                      hint={ind.hint || ""}
                      delay={0.28 + i * 0.03}
                    />
                  ))}
                </div>
              </GlassCard>

              {/* Risk metrics derived from model output */}
              <GlassCard delay={0.3} className="p-5">
                <SectionHeader
                  icon={<Shield className="h-3.5 w-3.5 text-ai" />}
                  title="Risk Analysis"
                  trailing="Model-derived"
                />
                <div className="mt-3 grid grid-cols-2 gap-2.5">
                  <RiskGauge name="Confidence" value={data.confidence} tone="pos" detail={`${(data.confidence * 100).toFixed(0)}%`} delay={0.32} />
                  <RiskGauge name="Stop Prob" value={data.probability_stop} tone={data.probability_stop > 0.5 ? "neg" : "pos"} detail={`${(data.probability_stop * 100).toFixed(0)}%`} delay={0.36} />
                  <RiskGauge name="Stop Loss" value={data.stop_loss_pct} tone="neg" detail={`${(data.stop_loss_pct * 100).toFixed(1)}%`} delay={0.40} />
                  <RiskGauge name="Risk/Reward" value={Math.min(data.trade_setup.risk_reward / 5, 1)} tone="pos" detail={`${data.trade_setup.risk_reward.toFixed(1)}x`} delay={0.44} />
                  <RiskGauge name="Expected" value={Math.max(0, data.expected_return)} tone="pos" detail={`+${(data.expected_return * 100).toFixed(1)}%`} delay={0.48} />
                  <RiskGauge name="Model Risk" value={1 - data.confidence} tone={data.confidence > 0.7 ? "pos" : "neg"} detail={data.model_name} delay={0.52} />
                </div>
              </GlassCard>
            </div>

            {/* News — kept as static since we don't have a news API, but marked clearly */}
            <GlassCard delay={0.35} className="p-5">
              <SectionHeader
                icon={<Newspaper className="h-3.5 w-3.5 text-fg-muted" />}
                title="News & Sentiment"
                trailing="Coming soon — API integration pending"
              />
              <p className="text-2xs text-fg-muted mt-2">
                News sentiment analysis will be available in a future update. All other data on this page
                is generated in real-time by the ML pipeline.
              </p>
            </GlassCard>

            {/* Model info — dynamic from metadata */}
            <ModelInfo
              modelName={data.model_name}
              metadata={data.model_metadata}
            />
          </div>

          {/* RIGHT — AI analysis panel */}
          <aside className="flex flex-col gap-5 min-w-0">
            <SignalCard
              recommendation={data.recommendation}
              confidence={data.confidence}
              hitProbability={data.probability_target}
              stopProbability={data.probability_stop}
              expectedReturn={data.expected_return}
              stopLoss={data.stop_loss_pct}
              holdingDays={data.holding_days}
              t={t}
              previous={previous}
              positive={positive}
            />
            <TradeSetupCard
              setup={data.trade_setup}
              positive={positive}
            />
          </aside>
        </div>
      </div>
    </AppShell>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function Header({
  t,
  search,
  onSearch,
  suggestions,
  onPick,
  tf,
  onTf,
  onRefresh,
  positive,
  marketStatus,
}: {
  t: TickerInfo;
  search: string;
  onSearch: (v: string) => void;
  suggestions: string[];
  onPick: (v: string) => void;
  tf: Timeframe;
  onTf: (v: Timeframe) => void;
  onRefresh: () => void;
  positive: boolean;
  marketStatus: "OPEN" | "PRE" | "POST" | "CLOSED";
}) {
  return (
    <header className="sticky top-7 z-20 border-b border-white/[0.06] bg-ink-950/80 backdrop-blur-xl">
      <div className="flex items-center justify-between gap-4 px-5 py-3">
        <div className="flex items-center gap-4 min-w-0">
          <TickerSearch
            value={search}
            placeholder={t.symbol}
            onChange={onSearch}
            onSubmit={() => {
              const trimmed = search.trim().toUpperCase();
              if (trimmed && trimmed !== t.symbol) {
                onPick(trimmed);
                onSearch("");
              }
            }}
            suggestions={suggestions}
            onPick={(s) => {
              onPick(s);
              onSearch("");
            }}
          />
          <div className="hidden md:flex flex-col min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[18px] font-semibold text-fg truncate">
                {t.name || t.symbol}
              </span>
              <span className="num text-2xs text-fg-muted">
                {t.exchange}
              </span>
            </div>
            <div className="text-2xs text-fg-muted truncate">
              {t.sector || "N/A"} · {t.industry || "N/A"}
            </div>
          </div>
          <div className="hidden lg:block w-px h-10 bg-white/[0.06]" />
          <div className="hidden lg:flex items-center gap-6">
            <PriceStat label="Price" value={`$${t.price.toFixed(2)}`} accent={positive ? "pos" : "neg"} />
            <PriceStat
              label="Change"
              value={`${positive ? "+" : ""}${t.change_abs.toFixed(2)} (${formatPct(t.change)})`}
              accent={positive ? "pos" : "neg"}
            />
            <PriceStat label="Volume" value={`${(t.volume / 1_000_000).toFixed(1)}M`} />
            <PriceStat label="Mkt Cap" value={formatMarketCap(t.market_cap)} />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <MarketStatus status={marketStatus} />
          <div className="hidden md:flex items-center gap-1 rounded-xl border border-white/[0.06] bg-white/[0.02] p-0.5">
            {TIMEFRAMES.map((f) => (
              <button
                key={f}
                onClick={() => onTf(f)}
                className={
                  "num h-7 px-2.5 text-[11px] font-medium tracking-wider rounded-lg transition-colors " +
                  (tf === f
                    ? "bg-ai text-white"
                    : "text-fg-muted hover:text-fg")
                }
              >
                {f}
              </button>
            ))}
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onRefresh}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.06] bg-white/[0.02] text-fg-muted hover:text-fg hover:bg-white/[0.04] transition-colors"
            aria-label="Refresh"
          >
            <RefreshCw className="h-4 w-4" />
          </motion.button>
        </div>
      </div>
    </header>
  );
}

function PriceStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "pos" | "neg";
}) {
  const color =
    accent === "pos" ? "text-pos" : accent === "neg" ? "text-neg" : "text-fg";
  return (
    <div className="flex flex-col gap-0.5">
      <div className="text-2xs uppercase tracking-[0.14em] text-fg-subtle">
        {label}
      </div>
      <div className={`num text-[14px] font-medium ${color}`}>{value}</div>
    </div>
  );
}

function MarketStatus({ status }: { status: "OPEN" | "PRE" | "POST" | "CLOSED" }) {
  const variant =
    status === "OPEN"
      ? { color: "text-pos", bg: "bg-pos/10 border-pos/30", dot: "bg-pos" }
      : status === "PRE"
      ? { color: "text-warn", bg: "bg-warn/10 border-warn/30", dot: "bg-warn" }
      : status === "POST"
      ? { color: "text-ai", bg: "bg-ai/10 border-ai/30", dot: "bg-ai" }
      : { color: "text-fg-muted", bg: "bg-white/[0.04] border-white/10", dot: "bg-fg-muted" };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.14em] font-medium ${variant.color} ${variant.bg}`}
    >
      <motion.span
        animate={{ opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.6, repeat: Infinity }}
        className={`block h-1.5 w-1.5 rounded-full ${variant.dot}`}
      />
      {status === "OPEN" ? "Market Open" : status === "PRE" ? "Pre-Market" : status === "POST" ? "After Hours" : "Closed"}
    </span>
  );
}

function SectionHeader({
  icon,
  title,
  trailing,
}: {
  icon: ReactNode;
  title: string;
  trailing?: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-[13px] font-medium text-fg">{title}</h2>
      </div>
      {trailing && (
        <span className="text-2xs text-fg-muted uppercase tracking-[0.12em]">
          {trailing}
        </span>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function ChartPanel({
  candles,
  demandZones,
  supplyZones,
  predictedPath,
  tradeSetup,
  t,
  tool,
  onTool,
}: {
  candles: { time: string; open: number; high: number; low: number; close: number; volume: number }[];
  demandZones: PremiumZone[];
  supplyZones: PremiumZone[];
  predictedPath: { time: string; value: number }[];
  tradeSetup: TradeSetup;
  t: TickerInfo;
  tool: string;
  onTool: (v: string) => void;
}) {
  return (
    <GlassCard delay={0.05} className="p-0" intensity="default">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <span className="num text-[18px] font-semibold text-fg">
            {t.symbol}
          </span>
          <span className="text-2xs text-fg-muted truncate max-w-[320px]">
            {t.description?.slice(0, 120) || ""}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {PREMIUM_TOOLS.map((toolItem) => (
            <motion.button
              key={toolItem.key}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => onTool(toolItem.key)}
              className={
                "flex h-8 w-8 items-center justify-center rounded-lg border transition-colors " +
                (tool === toolItem.key
                  ? "border-ai/40 bg-ai/15 text-ai"
                  : "border-white/[0.06] bg-white/[0.02] text-fg-muted hover:text-fg hover:bg-white/[0.04]")
              }
              title={toolItem.label}
              aria-label={toolItem.label}
            >
              {toolItem.icon}
            </motion.button>
          ))}
        </div>
      </div>
      <div className="relative">
        <PremiumChart
          data={candles}
          demandZones={demandZones}
          supplyZones={supplyZones}
          height={540}
          predictedPath={predictedPath}
          trades={{
            entry: tradeSetup.entry,
            stop: tradeSetup.stop_loss,
            target: tradeSetup.take_profit,
            current: t.price,
          }}
        />
      </div>
      <div className="flex items-center justify-between border-t border-white/[0.06] px-5 py-2.5 text-2xs text-fg-muted">
        <div className="flex items-center gap-3">
          {PREMIUM_TIMEFRAMES.map((tf) => (
            <span key={tf} className="num text-fg-muted">
              {tf}
            </span>
          ))}
        </div>
        <div className="num">
          D{demandZones.length} · S{supplyZones.length} · Entry ${tradeSetup.entry.toFixed(2)}
        </div>
      </div>
    </GlassCard>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function SignalCard({
  recommendation,
  confidence,
  hitProbability,
  stopProbability,
  expectedReturn,
  stopLoss,
  holdingDays,
  t,
  previous,
  positive,
}: {
  recommendation: Recommendation;
  confidence: number;
  hitProbability: number;
  stopProbability: number;
  expectedReturn: number;
  stopLoss: number;
  holdingDays: number;
  t: TickerInfo;
  previous: number;
  positive: boolean;
}) {
  return (
    <GlassCard delay={0.1} intensity="glow" className="p-5">
      <SectionHeader
        icon={<Sparkles className="h-3.5 w-3.5 text-ai" />}
        title="AI Signal"
        trailing={`${t.symbol} · ${recommendation} signal`}
      />

      <div className="flex flex-col items-center mt-4">
        <ConfidenceGauge
          value={confidence}
          recommendation={recommendation}
          size={210}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <ProbRow label="Hit-Target" value={hitProbability} tone="pos" />
        <ProbRow label="Hit-Stop" value={stopProbability} tone="neg" />
        <ProbRow label="Expected Return" value={expectedReturn} tone="pos" prefix="+" suffix="%" />
        <ProbRow label="Stop Loss" value={stopLoss} tone="neg" suffix="%" />
        <ProbRow label="Holding" value={holdingDays} suffix="d" tone="neutral" format="raw" />
        <ProbRow label="Risk Level" value={1 - confidence} tone={confidence > 0.7 ? "pos" : "neg"} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.14em] font-medium ${
            recommendation === "BUY"
              ? "border-pos/30 bg-pos/10 text-pos"
              : recommendation === "SELL"
              ? "border-neg/30 bg-neg/10 text-neg"
              : "border-warn/30 bg-warn/10 text-warn"
          }`}
        >
          {recommendation === "BUY" ? "Strong Buy" : recommendation === "SELL" ? "Strong Sell" : "Hold"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-fg-muted">
          {t.sector || "N/A"}
        </span>
        <span className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-fg-muted">
          Beta {(t.beta || 1).toFixed(2)}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-4">
        <MiniStat label="Open" value={`$${t.open.toFixed(2)}`} />
        <MiniStat label="High" value={`$${t.high.toFixed(2)}`} />
        <MiniStat label="Low" value={`$${t.low.toFixed(2)}`} />
        <MiniStat label="Prev" value={`$${previous.toFixed(2)}`} />
        <MiniStat label="52w H" value={`$${t.week_high_52.toFixed(2)}`} />
        <MiniStat label="52w L" value={`$${t.week_low_52.toFixed(2)}`} />
      </div>
    </GlassCard>
  );
}

function ProbRow({
  label,
  value,
  tone,
  prefix = "",
  suffix = "",
  format = "pct",
}: {
  label: string;
  value: number;
  tone: "pos" | "neg" | "neutral";
  prefix?: string;
  suffix?: string;
  format?: "pct" | "raw";
}) {
  const color =
    tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : "text-fg";
  const display =
    format === "pct"
      ? `${prefix}${(value * 100).toFixed(1)}${suffix}`
      : `${prefix}${value}${suffix}`;
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
      <span className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </span>
      <span className={`num text-[13px] font-medium ${color}`}>{display}</span>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {label}
      </div>
      <div className="num text-xs text-fg mt-0.5">{value}</div>
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────── */

function TradeSetupCard({
  setup,
  positive,
}: {
  setup: TradeSetup;
  positive: boolean;
}) {
  const expectedPct = ((setup.take_profit / setup.entry - 1) * 100).toFixed(1);
  const riskPct = ((1 - setup.stop_loss / setup.entry) * 100).toFixed(1);
  return (
    <GlassCard delay={0.15} className="p-5">
      <SectionHeader
        icon={<TrendingUp className="h-3.5 w-3.5 text-ai" />}
        title="Trade Setup"
        trailing="Risk-aware position sizing"
      />

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <SetupRow k="Entry Price" v={`$${setup.entry.toFixed(2)}`} />
        <SetupRow k="Current" v={`$${setup.entry.toFixed(2)}`} accent={positive ? "pos" : "neg"} />
        <SetupRow k="Stop Loss" v={`$${setup.stop_loss.toFixed(2)}`} accent="neg" />
        <SetupRow k="Take Profit" v={`$${setup.take_profit.toFixed(2)}`} accent="pos" />
        <SetupRow k="Risk / Reward" v={setup.risk_reward.toFixed(1)} accent="ai" />
        <SetupRow k="Position Size" v={`${(setup.position_pct * 100).toFixed(1)}%`} />
        <SetupRow k="Suggested Shares" v={setup.shares.toLocaleString()} />
        <SetupRow k="Capital Required" v={`$${formatInt(setup.capital)}`} />
        <SetupRow k="Potential Profit" v={`$${formatInt(setup.profit)}`} accent="pos" />
        <SetupRow k="Potential Loss" v={`$${formatInt(setup.loss)}`} accent="neg" />
        <SetupRow k="Kelly %" v={`${(setup.kelly_pct * 100).toFixed(1)}%`} accent="ai" />
        <SetupRow k="Risk %" v={`${(setup.risk_pct * 100).toFixed(1)}%`} accent="neg" />
      </div>

      <div className="mt-4 flex items-center justify-between rounded-lg border border-pos/20 bg-pos/[0.06] px-3 py-2.5">
        <div className="flex items-center gap-2">
          {positive ? (
            <TrendingUp className="h-4 w-4 text-pos" />
          ) : (
            <TrendingDown className="h-4 w-4 text-neg" />
          )}
          <div>
            <div className="text-2xs uppercase tracking-[0.14em] text-fg-muted">
              Expected
            </div>
            <div className="num text-[13px] font-medium text-fg">
              ${formatInt(setup.profit)} · +{expectedPct}%
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xs uppercase tracking-[0.14em] text-fg-muted">
            Risk
          </div>
          <div className="num text-[13px] font-medium text-neg">              ${formatInt(setup.loss)} · -{riskPct}%
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

function SetupRow({
  k,
  v,
  accent,
}: {
  k: string;
  v: string;
  accent?: "pos" | "neg" | "ai";
}) {
  const color =
    accent === "pos"
      ? "text-pos"
      : accent === "neg"
      ? "text-neg"
      : accent === "ai"
      ? "text-ai"
      : "text-fg";
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2">
      <span className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">
        {k}
      </span>
      <span className={`num text-[13px] font-medium ${color}`}>{v}</span>
    </div>
  );
}

function formatMarketCap(n: number): string {
  if (!n) return "—";
  if (n >= 1_000_000_000_000) return `$${(n / 1_000_000_000_000).toFixed(2)}T`;
  if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  return `$${n.toFixed(0)}`;
}
