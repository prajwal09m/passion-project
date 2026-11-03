// UI primitives + typed tool-result renderers. Renderers are driven by the
// ACTUAL saved action result payload (nothing hardcoded); raw JSON remains
// available in a clearly labeled diagnostic disclosure.
import { useState, Fragment, type ReactNode } from 'react'
import {
  Action, statusClass, EvidenceRef,
} from './api'
import { CalibrationChart, PooledAucChart } from './charts'

/* ---------- status primitives ---------- */

export function Pill({ status }: { status: string }) {
  return <span className={'pill ' + statusClass(status)}>{status}</span>
}

export function Loading({ what = 'Loading' }: { what?: string }) {
  return (
    <div className="statebuf" role="status">
      <h3>{what}…</h3>
      <div className="hint">Real backend call in flight — nothing cached or simulated.</div>
    </div>
  )
}

export function ErrorState({ error, onRetry, hint }: {
  error: string; onRetry?: () => void; hint?: string
}) {
  return (
    <div className="statebuf" role="alert">
      <h3>Something failed</h3>
      <div className="hint">{error}</div>
      {hint && <div className="hint faint">{hint}</div>}
      {onRetry && <div style={{ marginTop: 10 }}><button className="ghost" onClick={onRetry}>Retry</button></div>}
    </div>
  )
}

export function EmptyState({ what, action, onAction }: {
  what: string; action?: string; onAction?: () => void
}) {
  return (
    <div className="statebuf">
      <h3>{what}</h3>
      {action && (
        <div className="hint">
          {onAction ? <button className="link" onClick={onAction}>{action}</button> : action}
        </div>
      )}
    </div>
  )
}

/* ---------- notes ---------- */

export function Note({ kind = '', children }: { kind?: '' | 'warn' | 'bad' | 'ok' | 'accent'; children: ReactNode }) {
  return <div className={'note ' + kind}>{children}</div>
}

/* ---------- evidence wrapper ---------- */

export function EvidenceCard({ action, children, docket }: {
  action: Action
  children?: ReactNode
  docket?: string
}) {
  const [raw, setRaw] = useState(false)
  const failed = action.status === 'failed'
  return (
    <div className={'evidence'} data-action-id={action.id}>
      <header>
        <span className="toolname">{action.tool_name ?? action.kind}</span>
        <Pill status={action.status} />
        {docket && <span className="meta">{docket}</span>}
        <span className="why">action #{action.seq} · iteration {action.iteration}</span>
      </header>
      {failed ? (
        <div className="body">
          <Note kind="bad">Execution failed — recorded honestly: {action.error}</Note>
          {children}
        </div>
      ) : (
        <div className="body">{children}</div>
      )}
      {action.result && (
        <details className="raw" open={raw} onToggle={(e) => setRaw((e.target as HTMLDetailsElement).open)}>
          <summary>Raw result JSON (diagnostic view)</summary>
          <pre>{JSON.stringify(action.result, null, 2)}</pre>
        </details>
      )}
    </div>
  )
}

/* ---------- key/value + generic list helpers ---------- */

export function KV({ items }: { items: [string, ReactNode][] }) {
  return <dl className="kv">{items.map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}</dl>
}

export function fmtNum(v: unknown, digits = 4): string {
  if (typeof v !== 'number' || !isFinite(v)) return String(v)
  return v.toFixed(digits)
}

export function fmtInt(v: unknown): string {
  if (typeof v !== 'number' || !isFinite(v)) return '—'
  return Math.round(v).toLocaleString()
}

/** Shorten long filesystem paths for display; the full path stays in the title tooltip. */
export function shortPath(p: string): string {
  if (!p || p.length <= 48) return p
  const parts = p.split(/[/\\]/)
  const base = parts[parts.length - 1] || p
  return parts.length > 1 ? `…/${base}` : (p.length > 48 ? '…' + p.slice(-45) : p)
}

export function PathVal({ path }: { path: string }) {
  return <code className="inline" title={path}>{shortPath(path)}</code>
}

export function looksLikePath(v: string): boolean {
  return v.length > 40 && (/[/\\]/.test(v)) && !/\s{2,}/.test(v)
}

/** Scale bar for a metric with a known reference range. Never implies good/bad —
 *  the label carries the reference (e.g. “0.5 = random ranking”). */
export function MBar({ label, value, min, max, display, invert }: {
  label: string; value: number; min: number; max: number; display: string; invert?: boolean
}) {
  const t = Math.min(Math.max((value - min) / (max - min), 0), 1)
  return (
    <div className="mbar" role="img"
      aria-label={`${label}: ${display} (scale ${min} to ${max})`}>
      <span className="mlabel">{label}</span>
      <span className="mtrack"><span className={'mfill' + (invert ? ' warn' : '')} style={{ width: `${(t * 100).toFixed(1)}%` }} /></span>
      <span className="mval">{display}</span>
    </div>
  )
}

/* ---------- typed renderers ---------- */

type Result = Record<string, unknown>

const num = (r: Result, k: string): number => (typeof r[k] === 'number' ? r[k] as number : NaN)
const str = (r: Result, k: string): string => (r[k] == null ? '' : String(r[k]))

/** Dispatch on the tool name that PRODUCED the result, not on guessed shapes. */
export function ResultRenderer({ action }: { action: Action }) {
  if (!action.result && action.status !== 'failed') return null
  const result: Result = action.result ?? {}
  switch (action.tool_name) {
    case 'classification_metrics': return <ClassificationMetrics result={result} />
    case 'calibration_and_error_analysis': return <CalibrationAnalysis result={result} />
    case 'time_split_validation': return <TimeSplit result={result} />
    case 'grouped_auc_comparison': return <GroupedAuc result={result} />
    case 'feature_target_suspiciousness': return <Suspiciousness result={result} />
    case 'dataset_validation': return <DatasetValidation result={result} />
    case 'git_status_and_diff': return <GitStatusDiff result={result} />
    case 'list_changed_files': return <ChangedFiles result={result} />
    case 'read_changed_file_head': return <FileHead result={result} />
    case 'run_tests': return <RunTests result={result} />
    case 'compare_test_results': return <CompareResults result={result} />
    case 'check_apply_approval': return <ApplyApproval result={result} />
    case 'propose_hypothesis': return <ProposeHypothesis result={result} />
    case 'propose_revision_instructions': return <ProposeRevision result={result} />
    case 'artifact_summary': return <ArtifactSummary result={result} />
    case 'script_static_inspection': return <ScriptInspection result={result} />
    default: return <GenericResult result={result} />
  }
}

function ClassificationMetrics({ result: r }: { result: Result }) {
  const rocAuc = num(r, 'roc_auc')
  const brier = num(r, 'brier')
  const prec = num(r, 'precision_at_threshold')
  const rec = num(r, 'recall_at_threshold')
  const perSplit = r.per_split_auc as Record<string, number> | undefined
  const splits = perSplit ? Object.entries(perSplit) : []
  return (
    <>
      <div className="faint" style={{ fontSize: 11.5, marginBottom: 6 }}>
        {fmtInt(num(r, 'n'))} rows · threshold {fmtNum(num(r, 'threshold'), 2)} · score column <code className="inline">{str(r, 'score_column')}</code> · source <PathVal path={str(r, 'source')} />
      </div>
      {isFinite(rocAuc) && (
        <MBar label="ROC AUC (0.5 = random)" value={rocAuc} min={0.5} max={1} display={rocAuc.toFixed(4)} />
      )}
      {!isFinite(rocAuc) && <Note>n/a — single class present, AUC undefined.</Note>}
      {isFinite(brier) && (
        <MBar label="Brier (0 = perfect, lower better)" value={brier} min={0} max={1} display={`${brier.toFixed(4)} ${str(r, 'brier_convention')}`} invert />
      )}
      {isFinite(prec) && (
        <MBar label="Precision @ threshold" value={prec} min={0} max={1} display={prec.toFixed(4)} />
      )}
      {isFinite(rec) && (
        <MBar label="Recall @ threshold" value={rec} min={0} max={1} display={rec.toFixed(4)} />
      )}
      {splits.length > 0 && (
        <div className="tablewrap" style={{ marginTop: 10 }}>
          <table>
            <caption className="faint" style={{ captionSide: 'top', textAlign: 'left', fontSize: 11, padding: '4px 0' }}>
              Per-{String(r.split_by ?? 'split')} AUC (same score column); each group recomputed separately.
            </caption>
            <thead><tr><th>Group</th><th className="num">AUC</th></tr></thead>
            <tbody>
              {splits.map(([g, v]) => (
                <tr key={g}><td>{g}</td><td className="num">{v.toFixed(4)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function CalibrationAnalysis({ result: r }: { result: Result }) {
  const bins = (r.reliability_bins ?? []) as { bin_low: number; bin_high: number; n: number; mean_score: number; fraction_positive: number }[]
  const perFold = r.per_fold_auc as Record<string, number> | undefined
  return (
    <>
      <KV items={[
        ['Champion arm', str(r, 'score_column')],
        ['Brier score', fmtNum(num(r, 'brier'))],
        ['Source', <code className="inline">{str(r, 'source')}</code>],
      ]} />
      {bins.length > 0 && (
        <CalibrationChart bins={bins} champion={str(r, 'score_column')} brier={num(r, 'brier')} />
      )}
      {perFold && Object.keys(perFold).length > 0 && (
        <PooledAucChart pooled={perFold} nRows={bins.reduce((s, b) => s + b.n, 0)} />
      )}
      <details>
        <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Reliability bins table ({bins.length} bins — also shown in the chart above)</summary>
        <div className="tablewrap">
          <table>
            <thead>
              <tr><th>Bin</th><th className="num">n</th><th className="num">Mean score</th><th className="num">Observed +</th></tr>
            </thead>
            <tbody>
              {bins.map((b, i) => (
                <tr key={i}>
                  <td>{b.bin_low.toFixed(1)}–{b.bin_high.toFixed(1)}</td>
                  <td className="num">{b.n.toLocaleString()}</td>
                  <td className="num">{b.mean_score.toFixed(3)}</td>
                  <td className="num">{b.fraction_positive.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  )
}

function TimeSplit({ result: r }: { result: Result }) {
  const spans = r.fold_date_spans as Record<string, [string, string]> | undefined
  const sizes = r.fold_sizes as Record<string, number> | undefined
  const spanEntries = spans ? Object.entries(spans) : []
  const nonOverlapping = spanEntries.length > 1 ? checkNonOverlap(spanEntries) : null
  return (
    <>
      <KV items={[
        ['Rows', fmtInt(num(r, 'n_rows'))],
        ['Date column', r.date_column ? String(r.date_column) : 'not present'],
        ['Valid dates', r.n_valid_dates != null ? fmtInt(num(r, 'n_valid_dates')) : '—'],
        ['Date range', r.date_min ? `${str(r, 'date_min')} → ${str(r, 'date_max')}` : '—'],
        ['Source', <PathVal path={str(r, 'source')} />],
      ]} />
      {spans && spanEntries.length > 0 && (
        <div className="tablewrap" style={{ marginTop: 10 }}>
          <table>
            <caption className="faint" style={{ captionSide: 'top', textAlign: 'left', fontSize: 11, padding: '4px 0' }}>
              Fold date spans{nonOverlapping === false && ' — ⚠ OVERLAP between adjacent folds'}.
              Non-overlapping OOF dates alone do NOT prove the training procedure was leak-free.
            </caption>
            <thead><tr><th>Fold</th><th>From</th><th>To</th><th className="num">Rows</th></tr></thead>
            <tbody>
              {spanEntries.map(([f, [a, b]]) => (
                <tr key={f}>
                  <td>{f}</td><td>{a}</td><td>{b}</td>
                  <td className="num">{sizes?.[f]?.toLocaleString() ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {!spans && <Note kind="warn">No fold/date columns found — chronological validation unavailable for this artifact.</Note>}
    </>
  )
}

function checkNonOverlap(entries: [string, [string, string]][]): boolean {
  const sorted = [...entries].sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }))
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i][1][0] <= sorted[i - 1][1][1]) return false
  }
  return true
}

function GroupedAuc({ result: r }: { result: Result }) {
  const ci = r.bootstrap_ci as [number, number] | undefined
  return (
    <>
      <KV items={[
        ['Score A', str(r, 'score_a')],
        ['Score B', str(r, 'score_b')],
        ['AUC A', fmtNum(num(r, 'auc_a'))],
        ['AUC B', fmtNum(num(r, 'auc_b'))],
        ['Δ (B − A)', fmtNum(num(r, 'delta'))],
        ['Bootstrap 95% CI', ci ? `[${ci[0].toFixed(4)}, ${ci[1].toFixed(4)}] — row-level resampling, seed 42` : '—'],
        ['Rows n', fmtInt(num(r, 'n'))],
        ['Replicates', fmtInt(num(r, 'n_boot'))],
        ['Source', <code className="inline">{str(r, 'source')}</code>],
      ]} />
      <Note kind="warn">
        This bootstrap resamples rows independently. Demand-zone events cluster by ticker, so the
        case-study ΔAUC chart uses ticker-cluster resampling where available; treat this row-level
        interval as a cross-sectional approximation.
      </Note>
    </>
  )
}

function Suspiciousness({ result: r }: { result: Result }) {
  const rows = (r.top_correlations ?? []) as { feature: string; r: number; abs_r: number; n: number }[]
  return (
    <>
      <div className="faint" style={{ fontSize: 11.5, marginBottom: 6 }}>
        {fmtInt(num(r, 'n_features'))} features scanned · <PathVal path={str(r, 'source')} />
      </div>
      <div className="tablewrap">
        <table>
          <caption className="faint" style={{ captionSide: 'top', textAlign: 'left', fontSize: 11, padding: '4px 0' }}>
            Strongest |point-biserial| feature–label associations. ASSOCIATION ONLY — not proof of leakage.
          </caption>
          <thead><tr><th>Feature</th><th className="num">r</th><th style={{ minWidth: 130 }}>strength</th><th className="num">n</th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.feature}>
                <td><code className="inline">{row.feature}</code></td>
                <td className="num">{row.r.toFixed(4)}</td>
                <td>
                  <span className="mtrack" style={{ display: 'block', height: 6, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                    <span style={{ display: 'block', height: '100%', width: `${(Math.min(Math.abs(row.abs_r), 1) * 100).toFixed(1)}%`, background: 'linear-gradient(90deg, var(--cyan), var(--violet))', borderRadius: 99 }} />
                  </span>
                </td>
                <td className="num">{row.n.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note kind="warn">{str(r, 'caveat')}</Note>
    </>
  )
}

function DatasetValidation({ result: r }: { result: Result }) {
  const cols = (r.columns ?? []) as { name: string; dtype: string; n_missing: number; n_unique: number }[]
  const checks = (r.checks ?? {}) as Record<string, Record<string, unknown>>
  const allPresent = Object.values(checks).every((c) => c.present !== false)
  const shown = cols.slice(0, 8)
  const hidden = cols.slice(8)
  const colTable = (list: typeof cols) => (
    <div className="tablewrap">
      <table>
        <thead><tr><th>Column</th><th>Dtype</th><th className="num">Missing</th><th className="num">Unique</th></tr></thead>
        <tbody>
          {list.map((c) => (
            <tr key={c.name}>
              <td><code className="inline">{c.name}</code></td><td>{c.dtype}</td>
              <td className="num">{c.n_missing.toLocaleString()}</td>
              <td className="num">{c.n_unique.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
  return (
    <>
      <div className="faint" style={{ fontSize: 11.5, marginBottom: 6 }}>
        <PathVal path={str(r, 'filename')} /> · {fmtInt(num(r, 'n_rows'))} rows · {fmtInt(num(r, 'n_columns'))} columns · {fmtInt(num(r, 'n_duplicate_rows'))} duplicate rows
      </div>
      {!allPresent && <Note kind="warn">Some expected columns are absent — the notes below state exactly what is missing.</Note>}
      {colTable(shown)}
      {hidden.length > 0 && (
        <details>
          <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Show {hidden.length} more columns</summary>
          {colTable(hidden)}
        </details>
      )}
      <div style={{ marginTop: 10 }}>
        {Object.entries(checks).map(([k, v]) => (
          <div key={k} className="finding">
            <b>{v.present === false ? 'missing' : 'ok'}</b>{k}
            {v.note ? <span className="muted"> — {String(v.note)}</span> : null}
            {typeof v.n_folds === 'number' ? <span className="muted"> · {v.n_folds} folds</span> : null}
            {typeof v.min === 'string' && typeof v.max === 'string' ? <span className="muted"> · {v.min.slice(0, 10)} → {v.max.slice(0, 10)}</span> : null}
          </div>
        ))}
      </div>
    </>
  )
}

function GitStatusDiff({ result: r }: { result: Result }) {
  return (
    <>
      {r.ok === false
        ? <Note kind="bad">{str(r, 'error')}</Note>
        : (
          <>
            <KV items={[['Workspace', <code className="inline">{str(r, 'workspace')}</code>]]} />
            <pre className="log">{str(r, 'status') || '(clean working tree)'}</pre>
            {str(r, 'diff_stat') && <pre className="log">{str(r, 'diff_stat')}</pre>}
            {str(r, 'diff_head')
              ? (
                <>
                  <pre className="diff">{str(r, 'diff_head')}</pre>
                  {r.diff_head_truncated && <Note kind="warn">Diff truncated at the character cap — use read_changed_file_head for full files.</Note>}
                </>
              )
              : <Note kind="ok">No diff body (clean tree or range had no changes).</Note>}
          </>
        )}
    </>
  )
}

function ChangedFiles({ result: r }: { result: Result }) {
  const files = (r.changed_files ?? []) as string[]
  return r.ok === false
    ? <Note kind="bad">{str(r, 'error')}</Note>
    : files.length
      ? (
        <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
          {files.map((f) => <li key={f}><code className="inline">{f}</code></li>)}
        </ul>
      )
      : <Note kind="ok">No changed files detected.</Note>
}

function FileHead({ result: r }: { result: Result }) {
  const lines = (r.head ?? []) as string[]
  return (
    <>
      <KV items={[['File', <code className="inline">{str(r, 'file')}</code>]]} />
      <pre className="log">{lines.join('\n')}</pre>
    </>
  )
}

function RunTests({ result: r }: { result: Result }) {
  const tail = str(r, 'tail') || str(r, 'summary_line')
  return (
    <>
      <KV items={[
        ['Exit code', String(Math.round(num(r, 'exit_code')))],
        ['Passed', r.passed === true ? 'yes' : r.passed === false ? 'no' : '—'],
        ['Duration', `${num(r, 'seconds')}s`],
        ['Command', <code className="inline">{JSON.stringify(r.command)}</code>],
      ]} />
      <details>
        <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Test output tail</summary>
        <pre className="log">{tail}</pre>
      </details>
    </>
  )
}

function CompareResults({ result: r }: { result: Result }) {
  const reg = r.regression === true
  return <Note kind={reg ? 'bad' : 'ok'}>
    {reg ? 'REGRESSION: tests passed before the change and failed after it.' :
      `No regression by exit-code comparison (before ${String(r.before_exit)} → after ${String(r.after_exit)}).`}
  </Note>
}

function ApplyApproval({ result: r }: { result: Result }) {
  return <Note kind={r.apply_allowed ? 'warn' : 'ok'}>
    {r.apply_allowed
      ? 'Apply flag granted by the OWNER. Application is still a manual, human action outside this platform.'
      : 'Apply not authorized — a code-writing capability does not exist here. Reason: ' + str(r, 'reason')}
  </Note>
}

function ProposeHypothesis({ result: r }: { result: Result }) {
  const text = str(r, 'text')
  const hid = str(r, 'hypothesis_id')
  return (
    <>
      {text ? (
        <p style={{ margin: '0 0 6px', fontWeight: 600 }}>{text}</p>
      ) : (
        <Note kind="warn">No hypothesis text recorded in this result — see the Hypotheses panel and the raw JSON below.</Note>
      )}
      {hid && (
        <p className="faint" style={{ margin: '0 0 6px', fontSize: 12 }}>
          hypothesis {hid.slice(0, 8)} — status, evidence and verdict live in the Hypotheses panel
        </p>
      )}
      <Note kind="accent">
        Registered by the runtime investigator (origin: meta); any confidence in it is an
        uncalibrated model self-report, not a statistical result.
        {r.note ? <div className="faint" style={{ marginTop: 6 }}>{str(r, 'note')}</div> : null}
      </Note>
    </>
  )
}

function ProposeRevision({ result: r }: { result: Result }) {
  return (
    <Note kind="accent">
      Revision instruction bundle PROPOSED for human review (plan #{String(r.plan_index)}).
      Nothing is applied by this platform — applying changes is always manual.
    </Note>
  )
}

function ArtifactSummary({ result: r }: { result: Result }) {
  const folds = r.folds_present as Record<string, number> | Record<string, unknown> | undefined
  return (
    <>
      <KV items={[
        ['Rows', fmtInt(num(r, 'n_rows'))],
        ['Positive share', isFinite(num(r, 'positive_rate')) ? (num(r, 'positive_rate') * 100).toFixed(2) + '%' : '—'],
        ['Folds', folds ? Object.keys(folds).join(', ') : '—'],
        ['Source', <code className="inline">{str(r, 'source') || str(r, 'oof_csv') || str(r, 'artifact')}</code>],
      ]} />
      {Object.keys(r).length === 0 && <Note>Summary recorded (see raw JSON below for fields).</Note>}
    </>
  )
}

const HIDDEN_KEYS = new Set(['ok', '_dedup', '_truncated_note', '_note'])

function fmtSmart(v: unknown): ReactNode {
  if (typeof v === 'number' && isFinite(v)) return Number.isInteger(v) ? fmtInt(v) : fmtNum(v)
  if (typeof v === 'string') return looksLikePath(v) ? <PathVal path={v} /> : v
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  if (Array.isArray(v) && v.every((x) => typeof x === 'string' || typeof x === 'number')) {
    const items = v.map(String)
    return <span>{items.slice(0, 8).join(', ')}{items.length > 8 ? ` (+${items.length - 8} more)` : ''}</span>
  }
  if (typeof v === 'object' && v !== null) {
    const s = JSON.stringify(v)
    return s.length > 160 ? (
      <details>
        <summary className="faint" style={{ cursor: 'pointer', fontSize: 11.5 }}>structured value ({Array.isArray(v) ? `${v.length} items` : `${Object.keys(v).length} keys`})</summary>
        <code className="inline" style={{ whiteSpace: 'pre-wrap' }}>{s.slice(0, 1200)}{s.length > 1200 ? '…' : ''}</code>
      </details>
    ) : <code className="inline">{s}</code>
  }
  return String(v)
}

function ScriptInspection({ result: r }: { result: Result }) {
  const findings = (r.findings ?? r.warnings ?? r.issues ?? []) as {
    severity?: string; category?: string; line?: number; message?: string; detail?: string
  }[]
  const order = (r.fit_split_order ?? r.execution_order ?? []) as string[]
  const script = str(r, 'script_path') || str(r, 'script') || str(r, 'file')
  const high = findings.filter((f) => (f.severity ?? '').toLowerCase() === 'high').length
  return (
    <>
      {script && <div className="faint" style={{ fontSize: 11.5, marginBottom: 6 }}><PathVal path={script} /></div>}
      {order.length > 0 && (
        <div className="codeflow" role="img" aria-label={`Execution order: ${order.join(', then ')}`}>
          {order.map((s, i) => (
            <Fragment key={i}>
              {i > 0 && <span className="cfarrow">→</span>}
              <span className={'cfstep' + (/fit/i.test(s) ? ' bad' : '')}><b>{s}</b></span>
            </Fragment>
          ))}
        </div>
      )}
      {findings.length === 0 && <Note kind="ok">No structural findings — nothing suspicious in the static parse.</Note>}
      {findings.length > 0 && (
        <>
          <div className="faint" style={{ fontSize: 11.5, margin: '4px 0' }}>
            {findings.length} finding{findings.length === 1 ? '' : 's'}{high > 0 ? ` · ${high} high-severity` : ''}
          </div>
          <ul className="warnlist">
            {findings.slice(0, 6).map((f, i) => (
              <li key={i}>
                <span className={`wl-tag ${((f.severity ?? 'info').toLowerCase() === 'high') ? 'high' : ((f.severity ?? '').toLowerCase() === 'medium' ? 'medium' : 'info')}`}>
                  {f.severity ?? 'info'}
                </span>
                <span>{f.line != null ? <span className="faint">L{f.line} · </span> : null}{f.message ?? f.detail ?? JSON.stringify(f)}</span>
              </li>
            ))}
          </ul>
          {findings.length > 6 && (
            <details>
              <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Show {findings.length - 6} more findings</summary>
              <ul className="warnlist">
                {findings.slice(6).map((f, i) => (
                  <li key={i}>
                    <span className={`wl-tag ${((f.severity ?? 'info').toLowerCase() === 'high') ? 'high' : ((f.severity ?? '').toLowerCase() === 'medium' ? 'medium' : 'info')}`}>
                      {f.severity ?? 'info'}
                    </span>
                    <span>{f.line != null ? <span className="faint">L{f.line} · </span> : null}{f.message ?? f.detail ?? JSON.stringify(f)}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </>
  )
}

function GenericResult({ result: r }: { result: Result }) {
  const entries = Object.entries(r).filter(([k]) => !HIDDEN_KEYS.has(k))
  const shown = entries.slice(0, 10)
  const rest = entries.slice(10)
  const note = typeof r._truncated_note === 'string' ? r._truncated_note : null
  return (
    <>
      <KV items={shown.map(([k, v]) => [k, fmtSmart(v)])} />
      {rest.length > 0 && (
        <details>
          <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Show {rest.length} more fields</summary>
          <KV items={rest.map(([k, v]) => [k, fmtSmart(v)])} />
        </details>
      )}
      {note && <div className="faint" style={{ fontSize: 11.5, marginTop: 4 }}>{note}</div>}
    </>
  )
}

/* ---------- hypothesis evidence refs ---------- */

export function EvidenceRefs({ refs, hydrate }: {
  refs?: EvidenceRef[] | null
  hydrate?: (id: string) => { label: string; failed?: boolean } | undefined
}) {
  if (!refs || refs.length === 0) return null
  return (
    <div className="hyp-foot" style={{ gap: 8 }}>
      {refs.map((r, i) => {
        const info = hydrate?.(r.action_id)
        return (
          <span key={i} className={'evlink'} title={r.relation}>
            {r.relation === 'supports' ? '▲ ' : r.relation === 'contradicts' ? '▼ ' : ''}→
            {info ? info.label : '#' + String(r.action_id).slice(0, 6)}
          </span>
        )
      })}
    </div>
  )
}
