"use client";

import { AppShell } from "@/components/AppShell";
import { Stat } from "@/components/Stat";
import { Pill } from "@/components/Pill";
import { SidebarPanel, Kv } from "@/components/SidebarPanel";
import { DataTable } from "@/components/DataTable";
import { ConfusionGrid } from "@/components/ConfusionGrid";
import { WalkForwardBars } from "@/components/WalkForwardBars";
import { FeatureBars } from "@/components/FeatureBars";
import {
  PIPELINE,
  HEADLINE_METRICS,
  CONFUSION,
  WALK_FORWARD,
} from "@/data/metrics";
import { TOP_FEATURES } from "@/data/features";
import { formatAuc, formatPct } from "@/lib/format";
import { motion } from "motion/react";
import { clsx } from "clsx";

type ModelRow = {
  name: string;
  auc: number;
  precision: number;
  recall: number;
  f1: number;
  selected: boolean;
};

const MODELS: ModelRow[] = [
  { name: "Random Forest", auc: 0.6890, precision: 0.3750, recall: 0.0048, f1: 0.0094, selected: true },
  { name: "XGBoost",       auc: 0.6712, precision: 0.2981, recall: 0.0127, f1: 0.0246, selected: false },
  { name: "LightGBM",      auc: 0.6583, precision: 0.2419, recall: 0.0194, f1: 0.0366, selected: false },
];

export default function PerformancePage() {
  return (
    <AppShell>
      {/* KPI strip */}
      <div className="border-b border-line bg-ink-900">
        <div className="grid grid-cols-[auto_1fr_auto] items-center gap-6 px-6 py-4">
          <div className="flex items-baseline gap-3">
            <span className="text-[15px] font-medium text-fg">Model</span>
            <span className="num text-2xs text-fg-subtle">{PIPELINE.model}</span>
          </div>
          <div className="hidden md:grid grid-cols-6 gap-8">
            {HEADLINE_METRICS.map((m, i) => (
              <Stat
                key={m.key}
                label={m.label}
                value={
                  m.format === "auc" ? m.value.toFixed(4) : formatPct(m.value, 1, false)
                }
                sentiment={m.sentiment === "ai" ? "ai" : "neutral"}
                delay={i * 0.05}
              />
            ))}
          </div>
          <div className="flex items-center gap-2">
            <Pill variant="ai">{PIPELINE.modelFamily}</Pill>
            <Pill variant="pos">PROD</Pill>
          </div>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-h-0 flex-col border-r border-line overflow-y-auto">
          {/* MODEL COMPARISON + TRAINING STATS */}
          <section className="border-b border-line">
            <div className="grid grid-cols-2 divide-x divide-line">
              <div>
                <HeaderRow title="Model Comparison" trailing={`Trained ${PIPELINE.trainedAt}`} />
                <DataTable<ModelRow>
                  rows={MODELS}
                  rowKey={(r) => r.name}
                  columns={[
                    { key: "name", header: "Model" },
                    {
                      key: "auc",
                      header: "AUC",
                      align: "right",
                      numeric: true,
                      cell: (r) => formatAuc(r.auc),
                    },
                    {
                      key: "precision",
                      header: "Precision",
                      align: "right",
                      numeric: true,
                      cell: (r) => formatPct(r.precision, 2, false),
                    },
                    {
                      key: "recall",
                      header: "Recall",
                      align: "right",
                      numeric: true,
                      cell: (r) => formatPct(r.recall, 2, false),
                    },
                    {
                      key: "f1",
                      header: "F1",
                      align: "right",
                      numeric: true,
                      cell: (r) => r.f1.toFixed(4),
                    },
                    {
                      key: "selected",
                      header: "Status",
                      align: "center",
                      cell: (r) =>
                        r.selected ? (
                          <Pill variant="ai">PROD</Pill>
                        ) : (
                          <Pill variant="neutral">SHADOW</Pill>
                        ),
                    },
                  ]}
                />
              </div>
              <div>
                <HeaderRow title="Training Statistics" />
                <div className="px-5 pt-2 pb-5 grid grid-cols-2 gap-x-6 gap-y-1">
                  <Kv k="Random Seed"      v={String(PIPELINE.randomSeed)} />
                  <Kv k="Cross-Validation" v="5-fold chronological" />
                  <Kv k="Features"         v={String(PIPELINE.features)} />
                  <Kv k="Threshold"        v={`σ ≥ ${PIPELINE.threshold.toFixed(2)}`} />
                  <Kv k="Stop Loss"        v={formatPct(-0.05)} sentiment="neg" />
                  <Kv k="Target Gain"      v={formatPct(0.15)}  sentiment="pos" />
                  <Kv k="Holding Period"   v="20 days" />
                  <Kv k="Output"           v="Hit-Target ≥ +15% in 20d" />
                  <Kv k="Universe"         v={PIPELINE.universe} />
                  <Kv k="Date Range"       v={`${PIPELINE.dateRange.start} → ${PIPELINE.dateRange.end}`} />
                  <Kv k="Dataset Size"     v={PIPELINE.dataset} />
                  <Kv k="Splits"           v="Train / Val / Test" />
                </div>
              </div>
            </div>
          </section>

          {/* FEATURE IMPORTANCE */}
          <section className="border-b border-line">
            <HeaderRow
              title="Feature Importance — Top 10"
              trailing={`Out-of-sample test, ${PIPELINE.holdoutPeriod.start} → ${PIPELINE.holdoutPeriod.end}`}
            />
            <div className="grid grid-cols-[1fr_220px] divide-x divide-line">
              <div className="px-5 py-4">
                <FeatureBars
                  features={TOP_FEATURES.map((f) => ({
                    name: f.displayName,
                    value: f.importance / 0.0281,
                    raw: f.importance,
                    direction: f.direction,
                  }))}
                  max={10}
                  accent="ai"
                />
              </div>
              <div className="px-5 py-4 flex flex-col gap-2.5">
                <div className="panel-label mb-1">By Category</div>
                {categoryBreakdown(TOP_FEATURES).map((row, i) => (
                  <motion.div
                    key={row.label}
                    initial={{ opacity: 0, x: 4 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, delay: 0.05 * i }}
                    className="flex items-center justify-between gap-3"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          "block h-1.5 w-1.5",
                          row.tone === "ai" && "bg-ai",
                          row.tone === "pos" && "bg-pos",
                          row.tone === "warn" && "bg-warn"
                        )}
                      />
                      <span className="text-xs text-fg-muted">{row.label}</span>
                    </div>
                    <span className="num text-2xs text-fg">{row.share}%</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </section>

          {/* CONFUSION + WALK-FORWARD */}
          <section className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] divide-x divide-line">
            <div>
              <HeaderRow
                title="Confusion Matrix"
                trailing={`Threshold ${PIPELINE.threshold.toFixed(2)} · test set`}
              />
              <div className="px-5 pb-5">
                <ConfusionGrid c={CONFUSION} threshold={PIPELINE.threshold} />
                <div className="mt-4 grid grid-cols-3 gap-px bg-line">
                  <DerivedStat label="Precision" value={formatPct(CONFUSION.precision, 1, false)} tone="pos" />
                  <DerivedStat label="Recall"    value={formatPct(CONFUSION.recall, 1, false)}       tone="warn" />
                  <DerivedStat label="F1"        value={CONFUSION.f1.toFixed(4)}                    tone="ai" />
                </div>
              </div>
            </div>
            <div>
              <HeaderRow
                title="Walk-Forward Folds"
                trailing="5 split ‑ chronological"
              />
              <div className="px-5 py-4">
                <div className="grid grid-cols-[24px_1fr_44px_44px_44px] gap-3 pb-2 text-2xs text-fg-subtle uppercase tracking-[0.12em] border-b border-line">
                  <span />
                  <span>AUC · Precision · Recall</span>
                  <span className="text-right">AUC</span>
                  <span className="text-right">P</span>
                  <span className="text-right">R</span>
                </div>
                <div className="mt-2">
                  <WalkForwardBars rows={WALK_FORWARD} />
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Right rail: telemetry + selection rationale */}
        <aside className="flex min-h-0 flex-col bg-ink-900 overflow-y-auto">
          <SidebarPanel label="Run" trailing={<Pill variant="ai" dot>LIVE</Pill>}>
            <Kv k="Trained"   v={PIPELINE.trainedAt} />
            <Kv k="Seed"      v={String(PIPELINE.randomSeed)} />
            <Kv k="Splits"    v="chronological" />
            <Kv k="Threshold" v={`σ ≥ ${PIPELINE.threshold.toFixed(2)}`} sentiment="ai" />
            <Kv k="Universe"  v={PIPELINE.universe} />
            <Kv k="Dataset"   v={PIPELINE.dataset} />
            <Kv k="Coverage"  v={`${PIPELINE.dateRange.start} → ${PIPELINE.dateRange.end}`} />
          </SidebarPanel>

          <SidebarPanel label="Selection Rationale">
            <p className="text-xs leading-relaxed text-fg-muted">
              We selected Random Forest for production based on held-out AUC
              and walk-forward stability. Although it under-predicts positives
              at σ ≥ 0.75, it ranks prospective high-confluence setups above
              baselines in 4 of 5 walk-forward folds.
            </p>

            <div className="mt-4 grid gap-2">
              <CriterionRow k="Held-out AUC"      weight={0.40} score={0.6 * 0.689} />
              <CriterionRow k="Walk-forward AUC"  weight={0.30} score={0.6 * 0.762} />
              <CriterionRow k="Stability (σ_auc)" weight={0.20} score={0.6 * 0.72} />
              <CriterionRow k="Inference Latency"  weight={0.10} score={0.6 * 0.46} />
            </div>
            <div className="mt-4 border-t border-line pt-3 flex items-center justify-between">
              <span className="text-2xs text-fg-subtle">Composite score</span>
              <span className="num text-[15px] text-ai font-medium">
                0.604 / 1.000
              </span>
            </div>
          </SidebarPanel>

          <SidebarPanel label="Risks" divider>
            <ul className="flex flex-col gap-2 text-xs text-fg-muted leading-relaxed">
              <li className="flex gap-2">
                <span className="text-neg mt-0.5">◆</span>
                Low recall at high σ — few trades, hard to evaluate from 8-position sample.
              </li>
              <li className="flex gap-2">
                <span className="text-warn mt-0.5">◆</span>
                Sub-$10 universe does not generalize (AUC 0.49 held-out).
              </li>
              <li className="flex gap-2">
                <span className="text-ai mt-0.5">◆</span>
                Forward-return ranker is weak: Spearman ρ = 0.09.
              </li>
            </ul>
          </SidebarPanel>
        </aside>
      </div>
    </AppShell>
  );
}

function HeaderRow({ title, trailing }: { title: string; trailing?: string }) {
  return (
    <div className="flex items-center justify-between px-5 py-3 border-b border-line bg-ink-900">
      <div className="flex items-center gap-3">
        <span className="block h-3 w-px bg-ai" />
        <h2 className="text-[12.5px] font-medium text-fg">{title}</h2>
      </div>
      {trailing ? <span className="num text-2xs text-fg-subtle">{trailing}</span> : null}
    </div>
  );
}

function DerivedStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "pos" | "neg" | "ai" | "warn";
}) {
  const color =
    tone === "pos" ? "text-pos" : tone === "neg" ? "text-neg" : tone === "warn" ? "text-warn" : "text-ai";
  return (
    <div className="bg-ink-900 px-3 py-2">
      <div className="text-2xs uppercase tracking-[0.12em] text-fg-subtle">{label}</div>
      <div className={"num text-[15px] mt-1 " + color}>{value}</div>
    </div>
  );
}

function CriterionRow({ k, weight, score }: { k: string; weight: number; score: number }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-fg-muted">{k}</span>
        <span className="num text-2xs text-fg-muted">
          w {weight.toFixed(2)} · score {score.toFixed(2)}
        </span>
      </div>
      <div className="mt-1 h-1 bg-line overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(1, score / (weight || 1)) * 100}%` }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="h-full bg-ai"
        />
      </div>
    </div>
  );
}

function categoryBreakdown(
  fs: typeof TOP_FEATURES,
) {
  const totals = new Map<string, number>();
  fs.forEach((f) => totals.set(f.category, (totals.get(f.category) ?? 0) + f.importance));
  const sum = Array.from(totals.values()).reduce((a, b) => a + b, 0);
  const tones: Record<string, "ai" | "pos" | "warn"> = {
    "Zone Quality":    "ai",
    "Market Context":  "ai",
    "Sector Context":  "ai",
    "Volatility":      "warn",
    "Volume":          "pos",
  };
  return Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([label, v]) => ({
      label,
      share: ((v / sum) * 100).toFixed(1),
      tone: tones[label] ?? "pos",
    }));
}
