"use client";

import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";
import type { DemandZone } from "@/data/signals";

type Candle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type PremiumZone = DemandZone & {
  createdAt?: string;
  winRate?: number;
  avgBounce?: number;
  avgDuration?: number;
  side: "demand" | "supply";
};

export type PremiumChartProps = {
  data: Candle[];
  demandZones: PremiumZone[];
  supplyZones: PremiumZone[];
  height?: number;
  ema20?: boolean;
  ema50?: boolean;
  ema200?: boolean;
  vwap?: boolean;
  trades: {
    entry: number;
    stop: number;
    target: number;
    current: number;
  };
  predictedPath?: { time: string; value: number }[];
};

/**
 * The premium chart: candles + demand (green) + supply (red) zones + EMAs +
 * VWAP + prediction path + entry/SL/TP horizontal lines + zone tooltip.
 */
export function PremiumChart({
  data,
  demandZones,
  supplyZones,
  height = 540,
  ema20 = true,
  ema50 = true,
  ema200 = true,
  vwap = true,
  trades,
  predictedPath,
}: PremiumChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [tip, setTip] = useState<{
    x: number;
    y: number;
    zone: PremiumZone;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "rgba(12,13,16,0.0)" },
        textColor: "#9ba1ad",
        fontFamily:
          'var(--font-mono), ui-monospace, SFMono-Regular, "SF Mono", monospace',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(124,140,255,0.4)", width: 1, style: LineStyle.Dashed },
        horzLine: { color: "rgba(124,140,255,0.4)", width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
        scaleMargins: { top: 0.08, bottom: 0.22 },
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        secondsVisible: false,
      },
      width: el.clientWidth,
      height,
    });
    chartRef.current = chart;

    const candle = chart.addCandlestickSeries({
      upColor: "#3ecf8e",
      downColor: "#ef5160",
      borderVisible: false,
      wickUpColor: "#3ecf8e",
      wickDownColor: "#ef5160",
    });
    candle.setData(
      data.map((d) => ({
        time: d.time as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    // Volume histogram
    const vol = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
      color: "rgba(255,255,255,0.1)",
    });
    chart.priceScale("vol").applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
      borderVisible: false,
    });
    vol.setData(
      data.map((d) => ({
        time: d.time as Time,
        value: d.volume,
        color: d.close >= d.open ? "rgba(62,207,142,0.35)" : "rgba(239,81,96,0.35)",
      }))
    );

    // EMAs
    if (ema20) {
      const s = chart.addLineSeries({
        color: "#5b6cff",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s.setData(data.map((d, i) => ({ time: d.time as Time, value: ema(data.slice(0, i + 1).map((x) => x.close), 20) })));
    }
    if (ema50) {
      const s = chart.addLineSeries({
        color: "#9aa6ff",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s.setData(data.map((d, i) => ({ time: d.time as Time, value: ema(data.slice(0, i + 1).map((x) => x.close), 50) })));
    }
    if (ema200) {
      const s = chart.addLineSeries({
        color: "#cdd5ff",
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s.setData(data.map((d, i) => ({ time: d.time as Time, value: ema(data.slice(0, i + 1).map((x) => x.close), 200) })));
    }
    if (vwap) {
      const s = chart.addLineSeries({
        color: "#e0a458",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s.setData(data.map((d, i) => ({
        time: d.time as Time,
        value: vwapSeries(data.slice(0, i + 1)),
      })));
    }

    // Demand zones (green)
    demandZones.forEach((z) => {
      const series = chart.addBaselineSeries({
        baseValue: { type: "price", price: z.bottomPrice },
        topLineColor: "transparent",
        topFillColor1: "rgba(62,207,142,0.18)",
        topFillColor2: "rgba(62,207,142,0.02)",
        bottomLineColor: "transparent",
        bottomFillColor1: "rgba(62,207,142,0.02)",
        bottomFillColor2: "rgba(62,207,142,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const start = data[z.startIdx];
      const end = data[Math.min(z.endIdx, data.length - 1)];
      if (!start || !end) return;
      series.setData(
        data.slice(z.startIdx, z.endIdx + 1).map((d) => ({
          time: d.time as Time,
          value: z.topPrice,
        }))
      );
      series.createPriceLine({
        price: z.topPrice,
        color: "rgba(62,207,142,0.5)",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `D${z.touches}× Demand`,
      });
    });

    // Supply zones (red)
    supplyZones.forEach((z) => {
      const series = chart.addBaselineSeries({
        baseValue: { type: "price", price: z.bottomPrice },
        topLineColor: "transparent",
        topFillColor1: "rgba(239,81,96,0.15)",
        topFillColor2: "rgba(239,81,96,0.02)",
        bottomLineColor: "transparent",
        bottomFillColor1: "rgba(239,81,96,0.02)",
        bottomFillColor2: "rgba(239,81,96,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const start = data[z.startIdx];
      const end = data[Math.min(z.endIdx, data.length - 1)];
      if (!start || !end) return;
      series.setData(
        data.slice(z.startIdx, z.endIdx + 1).map((d) => ({
          time: d.time as Time,
          value: z.topPrice,
        }))
      );
      series.createPriceLine({
        price: z.topPrice,
        color: "rgba(239,81,96,0.5)",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `S${z.touches}× Supply`,
      });
    });

    // Predicted path
    if (predictedPath && predictedPath.length > 0) {
      const last = data[data.length - 1]!;
      const series = chart.addLineSeries({
        color: "#7c8cff",
        lineWidth: 2,
        lineStyle: LineStyle.Dotted,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      series.setData([
        { time: last.time as Time, value: trades.current },
        ...predictedPath.map((p) => ({ time: p.time as Time, value: p.value })),
      ]);
    }

    // Trade lines: entry / stop / target
    candle.createPriceLine({
      price: trades.entry,
      color: "#7c8cff",
      lineWidth: 1,
      lineStyle: LineStyle.Solid,
      axisLabelVisible: true,
      title: "Entry",
    });
    candle.createPriceLine({
      price: trades.stop,
      color: "#ef5160",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Stop",
    });
    candle.createPriceLine({
      price: trades.target,
      color: "#3ecf8e",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: "Target",
    });

    chart.timeScale().fitContent();

    // Crosshair tooltip — show "what zone is the cursor over?"
    chart.subscribeCrosshairMove((p: MouseEventParams) => {
      if (!p.time || !p.point) {
        setTip(null);
        return;
      }
      const price = candle.coordinateToPrice(p.point.y);
      if (price == null) {
        setTip(null);
        return;
      }
      const all = [...demandZones, ...supplyZones];
      const hit = all.find(
        (z) => price >= z.bottomPrice && price <= z.topPrice
      );
      if (!hit) {
        setTip(null);
        return;
      }
      setTip({
        x: p.point.x,
        y: p.point.y,
        zone: hit,
      });
    });

    const onResize = () => chart.applyOptions({ width: el.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, demandZones, supplyZones, height, ema20, ema50, ema200, vwap, predictedPath, trades.entry, trades.stop, trades.target, trades.current]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full" style={{ height }} />
      {tip && (
        <div
          className="pointer-events-none absolute z-20 rounded-lg border border-white/10 bg-ink-900/95 backdrop-blur-xl shadow-2xl px-3 py-2 min-w-[200px]"
          style={{
            left: tip.x + 12,
            top: tip.y - 12,
          }}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="block h-1.5 w-1.5 rounded-full"
              style={{
                background: tip.zone.side === "demand" ? "#3ecf8e" : "#ef5160",
              }}
            />
            <span
              className="text-[10px] uppercase tracking-[0.14em] font-semibold"
              style={{
                color: tip.zone.side === "demand" ? "#3ecf8e" : "#ef5160",
              }}
            >
              {tip.zone.side} · {tip.zone.strength}
            </span>
          </div>
          <div className="num text-2xs text-fg-muted">
            ${tip.zone.bottomPrice.toFixed(2)} – ${tip.zone.topPrice.toFixed(2)}
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1">
            <div className="text-2xs text-fg-subtle">Strength</div>
            <div className="num text-2xs text-fg text-right">
              {Math.round(((tip.zone.touches ?? 0) / 4) * 100)}/100
            </div>
            <div className="text-2xs text-fg-subtle">Win Rate</div>
            <div className="num text-2xs text-pos text-right">
              {tip.zone.winRate != null
                ? `${Math.round(tip.zone.winRate * 100)}%`
                : "—"}
            </div>
            <div className="text-2xs text-fg-subtle">Retests</div>
            <div className="num text-2xs text-fg text-right">
              {tip.zone.touches ?? 0}
            </div>
            <div className="text-2xs text-fg-subtle">Created</div>
            <div className="num text-2xs text-fg text-right">
              {tip.zone.createdAt ?? "—"}
            </div>
            <div className="text-2xs text-fg-subtle">Avg Bounce</div>
            <div className="num text-2xs text-pos text-right">
              {tip.zone.avgBounce != null
                ? `+${(tip.zone.avgBounce * 100).toFixed(1)}%`
                : "—"}
            </div>
            <div className="text-2xs text-fg-subtle">Avg Duration</div>
            <div className="num text-2xs text-fg text-right">
              {tip.zone.avgDuration != null
                ? `${tip.zone.avgDuration}d`
                : "—"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ema(values: number[], period: number): number {
  if (values.length === 0) return 0;
  const k = 2 / (period + 1);
  let prev = values[0]!;
  for (let i = 1; i < values.length; i++) {
    prev = values[i]! * k + prev * (1 - k);
  }
  return prev;
}

function vwapSeries(candles: Candle[]): number {
  let pv = 0;
  let v = 0;
  for (const c of candles) {
    const tp = (c.high + c.low + c.close) / 3;
    pv += tp * c.volume;
    v += c.volume;
  }
  return v === 0 ? candles[candles.length - 1]!.close : pv / v;
}
