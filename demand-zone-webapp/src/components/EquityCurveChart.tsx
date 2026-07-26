"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  LineStyle,
  type Time,
} from "lightweight-charts";

type Pt = { date: string; equity: number; benchmark: number; drawdown: number };

/**
 * Equity curve comparison: strategy vs benchmark, plus a drawdown sub-area.
 * Premium moment: animejs "scan-x" sweep + dot pulse on mount.
 */
export function EquityCurveChart({
  points,
  height = 380,
}: {
  points: Pt[];
  height?: number;
}) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const eqRef = useRef<HTMLDivElement | null>(null);
  const ddRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!eqRef.current) return;
    const eqEl = eqRef.current;
    const ddEl = ddRef.current;

    const eq = createChart(eqEl, {
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
      rightPriceScale: { borderColor: "#1f222a" },
      timeScale: {
        borderColor: "#1f222a",
        timeVisible: true,
        tickMarkFormatter: (t: Time) => {
          if (typeof t === "string") return t.slice(5);
          return "";
        },
      },
      width: eqEl.clientWidth,
      height,
    });

    eq.priceScale("right").applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.1 },
    });

    const eqSeries = eq.addLineSeries({
      color: "#3ecf8e",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    eqSeries.setData(points.map((p) => ({ time: p.date as Time, value: p.equity })));
    const benchSeries = eq.addLineSeries({
      color: "#9aa6ff",
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    benchSeries.setData(points.map((p) => ({ time: p.date as Time, value: p.benchmark })));
    eq.timeScale().fitContent();

    // Drawdown sub-chart beneath.
    let ddChart: ReturnType<typeof createChart> | null = null;
    if (ddEl) {
      ddChart = createChart(ddEl, {
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
        rightPriceScale: { borderColor: "#1f222a", invertScale: true },
        timeScale: {
          borderColor: "#1f222a",
          timeVisible: true,
          tickMarkFormatter: (t: Time) => (typeof t === "string" ? t.slice(5) : ""),
        },
        width: ddEl.clientWidth,
        height: 130,
      });
      ddChart.priceScale("right").applyOptions({
        scaleMargins: { top: 0.15, bottom: 0.05 },
      });
      const ddSeries = ddChart.addAreaSeries({
        topColor: "rgba(239, 81, 96, 0.35)",
        bottomColor: "rgba(239, 81, 96, 0.02)",
        lineColor: "#ef5160",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ddSeries.setData(points.map((p) => ({ time: p.date as Time, value: p.drawdown })));
      ddChart.timeScale().fitContent();
      eq.timeScale().subscribeVisibleLogicalRangeChange((r) => {
        if (r && ddChart) ddChart.timeScale().setVisibleLogicalRange(r);
      });
    }

    const onResize = () => {
      eq.applyOptions({ width: eqEl.clientWidth });
      if (ddChart && ddEl) ddChart.applyOptions({ width: ddEl.clientWidth });
    };
    window.addEventListener("resize", onResize);

    // Premium entrance — "data ink" sweep + equity dot pulse using CSS animations.
    // The scan-sweep and equity-dot classes have keyframe animations defined in globals.css
    // that trigger on mount. No JS animation library needed for this effect.
    if (wrapRef.current) {
      // Trigger a reflow to restart the CSS animations on mount
      const sweeps = wrapRef.current.querySelectorAll<HTMLElement>(".scan-sweep");
      sweeps.forEach((el) => {
        el.style.animation = "none";
        void el.offsetHeight; // force reflow
        el.style.animation = "";
      });
      const dots = wrapRef.current.querySelectorAll<HTMLElement>(".equity-dot");
      dots.forEach((el) => {
        el.style.animation = "none";
        void el.offsetHeight;
        el.style.animation = "";
      });
    }

    return () => {
      window.removeEventListener("resize", onResize);
      eq.remove();
      if (ddChart) ddChart.remove();
    };
  }, [points, height]);

  // Visible absolute-positioned dots that the animejs timeline animates.
  return (
    <div ref={wrapRef} className="flex flex-col">
      <div ref={eqRef} className="relative">
        <div
          className="scan-sweep pointer-events-none absolute top-0 bottom-0 left-0 w-20"
          style={{
            background:
              "linear-gradient(90deg, rgba(124,140,255,0) 0%, rgba(124,140,255,0.18) 50%, rgba(124,140,255,0) 100%)",
          }}
        />
        <div className="equity-dot pointer-events-none absolute top-[42%] left-[70%] h-2 w-2 -translate-x-1/2 -translate-y-1/2 bg-pos/80" />
        <div className="equity-dot pointer-events-none absolute top-[52%] left-[80%] h-2 w-2 -translate-x-1/2 -translate-y-1/2 bg-pos/80" />
        <div className="equity-dot pointer-events-none absolute top-[56%] left-[88%] h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 bg-ai/80" />
      </div>
      <div ref={ddRef} className="border-t border-line relative">
        <div
          className="scan-sweep pointer-events-none absolute top-0 bottom-0 left-0 w-20"
          style={{
            background:
              "linear-gradient(90deg, rgba(239,81,96,0) 0%, rgba(239,81,96,0.18) 50%, rgba(239,81,96,0) 100%)",
          }}
        />
      </div>
    </div>
  );
}
