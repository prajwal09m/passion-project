// Evidence-visualization layer — every chart is driven by backend-computed
// data (case_metrics / saved action results) and never generates sample data.
import type { CSSProperties, ReactNode } from 'react'
import type { BootPair, ReliabilityBin } from './api'

const W = 640
const PAD_L = 116
const PAD_R = 18
const PAD_T = 10
const PAD_B = 30

const SVG_STYLE: CSSProperties = { width: '100%', height: 'auto', display: 'block' }

export function shortName(arm: string): string {
  return arm.replace('LogisticRegression', 'LR').replace('LightGBM', 'LGBM')
}

function ChartFrame({ title, note, children, ariaLabel }: {
  title: string
  note?: string
  ariaLabel: string
  children?: ReactNode
}) {
  return (
    <div className="chart">
      <div className="ctitle">{title}</div>
      {children !== undefined && children !== null && (
        <figure role="img" aria-label={ariaLabel} style={{ margin: 0 }}>
          {children}
        </figure>
      )}
      {note && <div className="cnote">{note}</div>}
    </div>
  )
}

/** Horizontal bar chart of pooled AUC per arm on a 0.5–1.0 scale. */
export function PooledAucChart({ pooled, nRows }: {
  pooled: Record<string, number>
  nRows: number
}) {
  const arms = Object.entries(pooled).sort((a, b) => b[1] - a[1])
  if (!arms.length) return null
  const rowH = 30
  const height = arms.length * rowH + PAD_B + 10
  const plotW = W - PAD_L - PAD_R
  const x = (v: number) => PAD_L + plotW * (Math.min(Math.max(v, 0.5), 1) - 0.5) / 0.5
  const scale = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
  const aria = `Bar chart: pooled out-of-fold AUC by arm on ${nRows.toLocaleString()} rows. ` +
    arms.map(([a, v]) => `${a} = ${v.toFixed(3)}`).join('; ')
  const note = 'Scale runs from 0.5 (random ranking) to 1.0 (perfect ranking). ' +
    'Recomputed live from the frozen OOF artifact each time this page loads.'
  return (
    <ChartFrame
      title="Out-of-fold AUC by model arm (pooled across folds)"
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        {scale.map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={PAD_T} y2={height - PAD_B}
              className={v === 0.5 ? 'axis' : 'gridline'} />
            <text x={x(v)} y={height - 8} textAnchor="middle">{v.toFixed(1)}</text>
          </g>
        ))}
        {arms.map(([arm, auc], i) => {
          const y = i * rowH + 6
          return (
            <g key={arm}>
              <rect x={x(0.5)} y={y} width={Math.max(2, x(auc) - x(0.5))} height={17}
                className="bar" rx={1} />
              <text x={PAD_L - 8} y={y + 12} textAnchor="end" fontSize="10.5"
                fill="#9aa3af">{shortName(arm)}</text>
              <text x={x(auc) + 6} y={y + 12} fontSize="10.5" fill="#e8e5de">
                {auc.toFixed(3)}
              </text>
            </g>
          )
        })}
        <line x1={PAD_L} x2={W - PAD_R} y1={PAD_T} y2={PAD_T} className="axis" />
      </svg>
    </ChartFrame>
  )
}

/** Grouped per-fold AUC bars: one strip per fold, bars per arm. */
export function PerFoldAucChart({ perFold, foldSizes }: {
  perFold: Record<string, Record<string, number>>
  foldSizes: Record<string, number>
}) {
  const folds = Object.keys(perFold).sort()
  if (!folds.length) return null
  const armSet = new Set<string>()
  folds.forEach((f) => Object.keys(perFold[f]).forEach((a) => armSet.add(a)))
  const arms = Array.from(armSet).sort()
  const rowH = 36
  const height = folds.length * rowH + PAD_B + 10
  const plotW = W - PAD_L - PAD_R
  const x = (v: number) => PAD_L + plotW * (Math.min(Math.max(v, 0.5), 1) - 0.5) / 0.5
  const scale = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
  const barH = Math.max(3, Math.floor(22 / arms.length))
  const aria = 'Bar chart comparing per-fold AUC across model arms, one strip per fold. ' +
    folds.map((f) => 'fold ' + f + ': ' +
      arms.map((a) => (shortName(a) + '=' + (perFold[f]?.[a] ?? 0).toFixed(3))).join(', ')).join('; ')
  const note = 'Folds are chronological evaluation windows; a strong pooled AUC can hide weak folds and vice versa. '
    + 'Each strip carries the best arm value in the accent color.'
  return (
    <ChartFrame
      title="Per-fold out-of-fold AUC — cross-period comparison"
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        {scale.map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={PAD_T} y2={height - PAD_B}
              className={v === 0.5 ? 'axis' : 'gridline'} />
            <text x={x(v)} y={height - 6} textAnchor="middle">{v.toFixed(1)}</text>
          </g>
        ))}
        {folds.map((fold, i) => {
          const y = i * rowH + 6
          const values = arms.map((a) => perFold[fold]?.[a] ?? 0)
          const bestIdx = values.indexOf(Math.max(...values))
          return (
            <g key={fold}>
              {arms.map((arm, j) => {
                const v = perFold[fold]?.[arm]
                if (v == null) return null
                return (
                  <rect key={arm} x={x(0.5)} y={y + j * barH}
                    width={Math.max(2, x(v) - x(0.5))} height={barH - 1}
                    className="bar" />
                )
              })}
              {bestIdx >= 0 && values[bestIdx] > 0.5 && (
                <text x={x(values[bestIdx]) + 6} y={y + 13} fontSize="10" fill="#e2b25f">
                  best {values[bestIdx].toFixed(3)}
                </text>
              )}
              <text x={PAD_L - 8} y={y + 14} textAnchor="end" fontSize="10.5" fill="#9aa3af">
                fold {fold}{foldSizes[fold] ? ` · ${foldSizes[fold].toLocaleString()} rows` : ''}
              </text>
            </g>
          )
        })}
        <line x1={PAD_L} x2={W - PAD_R} y1={PAD_T} y2={PAD_T} className="axis" />
      </svg>
    </ChartFrame>
  )
}

/** ΔAUC (B − A) with bootstrap uncertainty whiskers and an honest design note. */
export function DeltaAucChart({ pairs }: { pairs: BootPair[] }) {
  if (!pairs.length) return null
  const rowH = 44
  const height = pairs.length * rowH + PAD_B + 12
  const deltas = pairs.flatMap((p) => [p.delta, p.ci_low, p.ci_high])
  const lo = Math.min(0, Math.min(...deltas))
  const hi = Math.max(0.0005, Math.max(...deltas))
  const span = hi - lo
  const x = (v: number) => PAD_L + (W - PAD_L - PAD_R) * ((v - lo) / span)
  const aria = 'Per-pair delta AUC point estimates with 95 percent bootstrap confidence intervals. ' +
    pairs.map((p) => shortName(p.score_b) + ' minus ' + shortName(p.score_a) +
      ': delta ' + p.delta.toFixed(3) + ', interval ' + p.ci_low.toFixed(3) +
      ' to ' + p.ci_high.toFixed(3) + '.').join(' ')
  const note = 'An interval entirely above zero supports B > A; an interval crossing zero is ' +
    'inconclusive at this sample size. Sampling unit, design and seed are recorded per pair ' +
    'so the result is reproducible.'
  return (
    <ChartFrame
      title="ΔAUC by arm pair (B − A) with bootstrap uncertainty"
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        {pairs.map((p, i) => {
          const y = i * rowH + 12
          const sig = p.ci_low > 0 || p.ci_high < 0
          const barLo = Math.min(x(p.delta), x(0))
          const barW = Math.max(2, Math.abs(x(p.delta) - x(0)))
          const warn = p.sampling_unit !== 'ticker'
          return (
            <g key={p.score_a + '|' + p.score_b}>
              <line x1={x(0)} x2={x(0)} y1={PAD_T} y2={height - PAD_B} className="gridline" />
              <line x1={x(p.ci_low)} x2={x(p.ci_high)} y1={y} y2={y} className="whisker" />
              <line x1={x(p.ci_low)} x2={x(p.ci_low)} y1={y - 4} y2={y + 4} className="whisker" />
              <line x1={x(p.ci_high)} x2={x(p.ci_high)} y1={y - 4} y2={y + 4} className="whisker" />
              <rect x={barLo} y={y - 3} width={barW} height={6} rx={1}
                className={sig ? 'bar' : 'bar alt'} />
              <text x={PAD_L - 8} y={y - 2} textAnchor="end" fontSize="10.5" fill="#9aa3af">
                {shortName(p.score_b)}
              </text>
              <text x={PAD_L - 8} y={y + 10} textAnchor="end" fontSize="9.5" fill="#6b7480">
                vs {shortName(p.score_a)}
              </text>
              <text x={PAD_L + 6} y={y - 2} fontSize="10" fill="#e8e5de">
                Δ {p.delta.toFixed(3)}   CI [{p.ci_low.toFixed(3)}, {p.ci_high.toFixed(3)}]
              </text>
              <text x={PAD_L + 6} y={y + 11} fontSize="9.5" fill="#6b7480">
                {p.n_boot} boots · {p.sampling_unit}-level resampling · {p.reproducibility}
              </text>
              {warn && (
                <text x={W - PAD_R} y={y - 2} textAnchor="end" fontSize="9.5" fill="#d9a047">
                  ⚠ row-level design
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </ChartFrame>
  )
}

/** Calibration reliability curve with background bars of observed positive rate. */
export function CalibrationChart({ bins, champion, brier, logLoss }: {
  bins: ReliabilityBin[]
  champion: string
  brier?: number
  logLoss?: number
}) {
  if (!bins.length) return null
  const height = 280
  const plotW = W - PAD_L - PAD_R
  const plotH = height - PAD_T - PAD_B
  const x = (v: number) => PAD_L + plotW * v
  const y = (v: number) => PAD_T + plotH * (1 - v)
  const pts = bins.map((b) =>
    `${x((b.bin_low + b.bin_high) / 2).toFixed(1)},${y(b.fraction_positive).toFixed(1)}`).join(' ')
  const aria = `Line chart: predicted versus observed positive rate for ${champion}. ` +
    bins.map((b) => `bin ${b.bin_low.toFixed(1)}-${b.bin_high.toFixed(1)} (n=${b.n}): ` +
      `mean score ${b.mean_score.toFixed(3)}, observed ${b.fraction_positive.toFixed(3)}.`).join(' ')
  let note = 'Dotted line = perfect calibration (predicted equals observed). Points above the ' +
    'dotted line are underconfident; below it, overconfident.'
  if (brier != null) {
    note += ` Brier ${brier.toFixed(4)}` +
      (logLoss != null ? ` · log-loss ${logLoss.toFixed(4)}` : '') + ' — lower is better.'
  }
  return (
    <ChartFrame
      title={`Calibration reliability — ${champion}`}
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={'y' + v}>
            <line x1={PAD_L} x2={W - PAD_R} y1={y(v)} y2={y(v)}
              className={v === 0 ? 'axis' : 'gridline'} />
            <text x={PAD_L - 8} y={y(v) + 3} textAnchor="end">{v.toFixed(2)}</text>
          </g>
        ))}
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={'x' + v}>
            <line x1={x(v)} x2={x(v)} y1={y(0)} y2={y(1)}
              className={v === 0 ? 'axis' : 'gridline'} />
            <text x={x(v)} y={y(0) + 15} textAnchor="middle">{v.toFixed(2)}</text>
          </g>
        ))}
        {bins.map((b, i) => {
          const bw = plotW / 10 - 5
          const cx = x((b.bin_low + b.bin_high) / 2)
          return (
            <rect key={'b' + i} x={cx - bw / 2} y={y(b.fraction_positive)} width={bw}
              height={Math.max(1, y(0) - y(b.fraction_positive))}
              className="bar" opacity={0.28} />
          )
        })}
        <line x1={x(0)} x2={x(1)} y1={y(0)} y2={y(1)} className="diag" />
        {bins.length > 1 && <polyline points={pts} className="curve" />}
        {bins.map((b, i) => (
          <circle key={'p' + i} cx={x((b.bin_low + b.bin_high) / 2)}
            cy={y(b.fraction_positive)} r="3" className="point" />
        ))}
        <text x={PAD_L} y={y(0) + 27} fontSize="9.5" fill="#6b7480">
          mean predicted score (per bin) →
        </text>
      </svg>
    </ChartFrame>
  )
}

/** Fold date-span strips on a common time axis. */
export function FoldSpanChart({ spans, dateColumn, nonOverlapping }: {
  spans: Record<string, [string, string]>
  dateColumn: string
  nonOverlapping: boolean | null
}) {
  const folds = Object.entries(spans)
  if (!folds.length) return null
  const rowH = 34
  const height = folds.length * rowH + PAD_B + 16
  const plotW = W - PAD_L - PAD_R
  const dates = folds.flatMap(([, pair]) => pair).sort()
  const tMin = new Date(dates[0]).getTime()
  const tMax = new Date(dates[dates.length - 1]).getTime()
  if (!isFinite(tMin) || !isFinite(tMax)) return null
  const x = (iso: string) =>
    PAD_L + plotW * ((new Date(iso).getTime() - tMin) / Math.max(1, tMax - tMin))
  const aria = `Fold chronology computed from column ${dateColumn}: ` +
    folds.map(([f, pair]) => `fold ${f} runs ${pair[0]} to ${pair[1]}`).join('; ')
  const note = nonOverlapping === true
    ? 'Adjacent fold date spans do not overlap in this prediction artifact. That is a necessary ' +
      'but NOT sufficient check — non-overlapping OOF dates do not prove the training procedure ' +
      'itself was leak-free.'
    : nonOverlapping === false
      ? `Fold date spans overlap in column ${dateColumn}. This is a genuine chronology finding worth investigating.`
      : 'Chronology could not be determined from the artifact; record this as a limitation.'
  return (
    <ChartFrame
      title={`Fold chronology — date spans from '${dateColumn}'`}
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        {folds.map(([fold, pair], i) => {
          const y = i * rowH + 8
          const x0 = x(pair[0])
          const x1 = x(pair[1])
          return (
            <g key={fold}>
              <rect x={x0} y={y} width={Math.max(2, x1 - x0)} height={16} className="bar" rx={1} />
              <text x={PAD_L - 8} y={y + 12} textAnchor="end" fontSize="10.5" fill="#9aa3af">
                fold {fold}
              </text>
              <text x={Math.max(PAD_L, x0) + 4} y={y + 12} fontSize="9.5" fill="#6b7480">
                {pair[0]}
              </text>
              <text x={Math.min(W - PAD_R, x1) - 4} y={y + 12} fontSize="9.5" textAnchor="end"
                fill="#6b7480">{pair[1]}</text>
            </g>
          )
        })}
        <text x={PAD_L} y={height - 4} fontSize="10" fill="#6b7480">{dates[0]}</text>
        <text x={W - PAD_R} y={height - 4} fontSize="10" textAnchor="end" fill="#6b7480">
          {dates[dates.length - 1]}
        </text>
        <line x1={PAD_L} x2={W - PAD_R} y1={PAD_T} y2={PAD_T} className="axis" />
      </svg>
    </ChartFrame>
  )
}

/** Compact sequence strip of the investigation timeline (first ~30 events). */
export function TimelineFunnelChart({ items }: {
  items: { seq: number; kind: string; label: string }[]
}) {
  if (!items.length) return null
  const shown = items.slice(0, 30)
  const height = shown.length * 20 + 34
  const aria = 'Sequence strip of the investigation record: ' +
    shown.map((it) => it.label).join('; ') +
    (items.length > 30 ? `. ${items.length - shown.length} more events follow in the timeline section.` : '')
  const note = 'Accent dots are tool results, hypotheses and reports; gray dots are bookkeeping. ' +
    'Read top to bottom in chronological order.'
  return (
    <ChartFrame
      title="Investigation record at a glance"
      ariaLabel={aria}
      note={note}>
      <svg viewBox={`0 0 ${W} ${height}`} style={SVG_STYLE}>
        <line x1={14} x2={14} y1={18} y2={height - 16} className="axis" />
        {shown.map((it, i) => {
          const y = 18 + i * 20
          const emphasis = /^(tool_result|hypothesis|finding|report|revision)$/.test(it.kind)
          return (
            <g key={it.seq}>
              <circle cx={14} cy={y} r={emphasis ? 4 : 3}
                fill={emphasis ? '#e2b25f' : '#6b7480'} />
              <text x={26} y={y + 4} fontSize="11" fill="#e8e5de">
                {it.label.length > 84 ? it.label.slice(0, 84) + '…' : it.label}
              </text>
            </g>
          )
        })}
      </svg>
    </ChartFrame>
  )
}

/** Label-balance bar: positive share of the prediction artifact. */
export function LabelBalanceChart({ counts, positiveShare, nRows }: {
  counts?: { negative_0: number; positive_1: number }
  positiveShare: number
  nRows: number
}) {
  if (nRows <= 0 || !counts) return null
  const title = `Label balance — ${counts.positive_1.toLocaleString()} positive / ` +
    `${counts.negative_0.toLocaleString()} negative of ${nRows.toLocaleString()} rows`
  const barW = Math.max(2, (W - PAD_L - PAD_R) * (counts.positive_1 / nRows))
  const aria = `${title} Positive share ${(positiveShare * 100).toFixed(1)} percent.`
  const note = 'Interpret AUC together with this base rate — the balance defines what 0.5 AUC ' +
    '(random ranking) means in practice for this dataset.'
  return (
    <ChartFrame title={title} ariaLabel={aria} note={note}>
      <svg viewBox={`0 0 ${W} 90`} style={SVG_STYLE}>
        <rect x={PAD_L} y={30} width={W - PAD_L - PAD_R} height={22} fill="#2a3140" rx={2} />
        <rect x={PAD_L} y={30} width={barW} height={22} className="bar" rx={1} />
        <text x={PAD_L - 8} y={44} textAnchor="end" fontSize="10.5" fill="#9aa3af">label</text>
        <text x={PAD_L + 6} y={46} fontSize="10" fill="#e8e5de">
          positive {(positiveShare * 100).toFixed(1)}%
        </text>
        <line x1={PAD_L} x2={W - PAD_R} y1={22} y2={22} className="axis" />
      </svg>
    </ChartFrame>
  )
}
