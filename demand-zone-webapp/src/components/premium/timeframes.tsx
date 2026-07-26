"use client";

import { Activity, BarChart3, Crosshair, Maximize2, Pencil, Type } from "lucide-react";
import type { ReactNode } from "react";

export const PREMIUM_TIMEFRAMES = ["1D", "1W", "1M", "YTD", "ALL"] as const;

export const PREMIUM_TOOLS: ReadonlyArray<{
  key: string;
  label: string;
  icon: ReactNode;
}> = [
  { key: "cross",   label: "Crosshair", icon: <Crosshair className="h-4 w-4" /> },
  { key: "trend",   label: "Trend line", icon: <Activity className="h-4 w-4" /> },
  { key: "fib",     label: "Fibonacci", icon: <BarChart3 className="h-4 w-4" /> },
  { key: "text",    label: "Text",      icon: <Type className="h-4 w-4" /> },
  { key: "draw",    label: "Draw",      icon: <Pencil className="h-4 w-4" /> },
  { key: "full",    label: "Fullscreen", icon: <Maximize2 className="h-4 w-4" /> },
];
