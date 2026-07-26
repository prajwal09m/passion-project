"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
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

/**
 * The centerpiece chart: candles + demand-zone bands + EMA(20)/EMA(50) overlays.
 * Used on Home (preview) and Analysis (full).
 */
export function DemandZoneChart({
  data,
  zones,
  height = 480,
  showVolume = true,
  ema20 = true,
  ema50 = true,
  highlightZoneIndex = -1,
}: {
  data: Candle[];
  zones: DemandZone[];
  height?: number;
  showVolume?: boolean;
  ema20?: boolean;
  ema50?: boolean;
  /** Index into `zones` to give a premium entrance highlight on mount. */
  highlightZoneIndex?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: "#0c0d10" },
        textColor: "#9ba1ad",
        fontFamily:
          'var(--font-mono), ui-monospace, SFMono-Regular, "SF Mono", monospace',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#15171c", style: LineStyle.Dotted },
        horzLines: { color: "#15171c", style: LineStyle.Dotted },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#2b2f38", width: 1, style: LineStyle.Dashed },
        horzLine: { color: "#2b2f38", width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: { borderColor: "#1f222a" },
      timeScale: {
        borderColor: "#1f222a",
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
    candleRef.current = candle;
    candle.setData(
      data.map((d) => ({
        time: d.time as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    if (ema20) {
      const e20 = chart.addLineSeries({
        color: "#5b6cff",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      e20.setData(
        data.map((d, i) => ({
          time: d.time as Time,
          value: ema(data.slice(0, i + 1).map((x) => x.close), 20),
        }))
      );
    }
    if (ema50) {
      const e50 = chart.addLineSeries({
        color: "#9aa6ff",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      e50.setData(
        data.map((d, i) => ({
          time: d.time as Time,
          value: ema(data.slice(0, i + 1).map((x) => x.close), 50),
        }))
      );
    }

    if (showVolume) {
      const vol = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "vol",
        color: "#1f222a",
      });
      chart.priceScale("vol").applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
        borderVisible: false,
      });
      vol.setData(
        data.map((d) => ({
          time: d.time as Time,
          value: d.volume,
          color: d.close >= d.open ? "#1a3a2c" : "#3a1e22",
        }))
      );
    }

    // Demand zone overlays — drawn as two parallel baseline series so we
    // can vary their opacity per zone, and add a price line marker.
    zones.forEach((z, idx) => {
      const topSeries = chart.addBaselineSeries({
        baseValue: { type: "price", price: z.bottomPrice },
        topLineColor: "transparent",
        topFillColor1: idx === highlightZoneIndex
          ? "rgba(124, 140, 255, 0.18)"
          : "rgba(124, 140, 255, 0.08)",
        topFillColor2: "rgba(124, 140, 255, 0.02)",
        bottomLineColor: "transparent",
        bottomFillColor1: "rgba(124, 140, 255, 0.02)",
        bottomFillColor2: "rgba(124, 140, 255, 0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      const start = data[z.startIdx];
      const end = data[Math.min(z.endIdx, data.length - 1)];
      if (!start || !end) return;
      const series = data
        .slice(z.startIdx, z.endIdx + 1)
        .map((d) => ({ time: d.time as Time, value: z.topPrice }));
      topSeries.setData(series);

      // Add a price line for the zone top — small marker on the right axis.
      topSeries.createPriceLine({
        price: z.topPrice,
        color:
          idx === highlightZoneIndex
            ? "rgba(124,140,255,0.9)"
            : "rgba(124,140,255,0.4)",
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `Z${idx + 1} ${z.bottomPrice.toFixed(2)}–${z.topPrice.toFixed(2)}`,
      });
    });

    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: el.clientWidth });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      candleRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, zones, height, showVolume, ema20, ema50, highlightZoneIndex]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}

function ema(values: number[], period: number): number {
  if (values.length === 0) return 0;
  const k = 2 / (period + 1);
  let emaPrev = values[0]!;
  for (let i = 1; i < values.length; i++) {
    emaPrev = values[i]! * k + emaPrev * (1 - k);
  }
  return emaPrev;
}
