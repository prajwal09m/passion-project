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
    default: return <GenericResult result={result} />
  }
}

function ClassificationMetrics({ result: r }: { result: Result }) {
  const rocAuc = num(r, 'roc_auc')
  const perSplit = r.per_split_auc as Record<string, number> | undefined
  const splits = perSplit ? Object.entries(perSplit) : []
  return (
    <>
      <KV items={[
        ['Rows n', num(r, 'n').toLocaleString()],
        ['ROC AUC', isFinite(rocAuc) ? rocAuc.toFixed(4) : 'n/a (single class present)'],
        ['Brier score', <span>{fmtNum(num(r, 'brier'))} <span className="faint">{str(r, 'brier_convention')}</span></span>],
        ['Precision @ thr', fmtNum(num(r, 'precision_at_threshold'))],
        ['Recall @ thr', fmtNum(num(r, 'recall_at_threshold'))],
        ['Threshold', fmtNum(num(r, 'threshold'), 2)],
        ['Score column', str(r, 'score_column')],
        ['Source', <code className="inline">{str(r, 'source')}</code>],
      ]} />
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
        ['Rows', num(r, 'n_rows').toLocaleString()],
        ['Date column', r.date_column ? String(r.date_column) : 'not present'],
        ['Valid dates', r.n_valid_dates != null ? num(r, 'n_valid_dates').toLocaleString() : '—'],
        ['Date range', r.date_min ? `${str(r, 'date_min')} → ${str(r, 'date_max')}` : '—'],
        ['Source', <code className="inline">{str(r, 'source')}</code>],
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
        ['Rows n', num(r, 'n').toLocaleString()],
        ['Replicates', num(r, 'n_boot').toLocaleString()],
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
      <KV items={[
        ['Features scanned', num(r, 'n_features').toLocaleString()],
        ['Source', <code className="inline">{str(r, 'source')}</code>],
      ]} />
      <div className="tablewrap">
        <table>
          <caption className="faint" style={{ captionSide: 'top', textAlign: 'left', fontSize: 11, padding: '4px 0' }}>
            Strongest |point-biserial| feature–label associations. ASSOCIATION ONLY — not proof of leakage.
          </caption>
          <thead><tr><th>Feature</th><th className="num">r</th><th className="num">|r|</th><th className="num">n</th></tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.feature}>
                <td><code className="inline">{row.feature}</code></td>
                <td className="num">{row.r.toFixed(4)}</td>
                <td className="num">{row.abs_r.toFixed(4)}</td>
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
  return (
    <>
      <KV items={[
        ['File', str(r, 'filename')],
        ['Rows', num(r, 'n_rows').toLocaleString()],
        ['Columns', num(r, 'n_columns').toLocaleString()],
        ['Duplicate rows', num(r, 'n_duplicate_rows').toLocaleString()],
      ]} />
      {!allPresent && <Note kind="warn">Some expected columns are absent — the notes below state exactly what is missing.</Note>}
      <div className="tablewrap">
        <table>
          <thead><tr><th>Column</th><th>Dtype</th><th className="num">Missing</th><th className="num">Unique</th></tr></thead>
          <tbody>
            {cols.map((c) => (
              <tr key={c.name}>
                <td><code className="inline">{c.name}</code></td><td>{c.dtype}</td>
                <td className="num">{c.n_missing.toLocaleString()}</td>
                <td className="num">{c.n_unique.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
  return (
    <>
      <KV items={[
        ['Exit code', String(num(r, 'exit_code'))],
        ['Passed', r.passed === true ? 'yes' : r.passed === false ? 'no' : '—'],
        ['Duration', `${num(r, 'seconds')}s`],
        ['Command', <code className="inline">{JSON.stringify(r.command)}</code>],
      ]} />
      <pre className="log">{str(r, 'tail') || str(r, 'summary_line')}</pre>
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
  return (
    <Note kind="accent">
      Structured hypothesis registered by the runtime investigator (origin: meta; any
      confidence in it is an uncalibrated model self-report, not a statistical result).
      {r.note ? <div className="faint" style={{ marginTop: 6 }}>{str(r, 'note')}</div> : null}
    </Note>
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
        ['Rows', num(r, 'n_rows').toLocaleString()],
        ['Positive share', isFinite(num(r, 'positive_rate')) ? (num(r, 'positive_rate') * 100).toFixed(2) + '%' : '—'],
        ['Folds', folds ? Object.keys(folds).join(', ') : '—'],
        ['Source', <code className="inline">{str(r, 'source') || str(r, 'oof_csv') || str(r, 'artifact')}</code>],
      ]} />
      {Object.keys(r).length === 0 && <Note>Summary recorded (see raw JSON below for fields).</Note>}
    </>
  )
}

function GenericResult({ result: r }: { result: Result }) {
  const entries = Object.entries(r)
    .filter(([k]) => !['ok'].includes(k))
    .slice(0, 12)
  return (
    <KV items={entries.map(([k, v]) => [
      k,
      typeof v === 'number' && isFinite(v) ? fmtNum(v)
        : typeof v === 'object' && v !== null ? <code className="inline">{JSON.stringify(v).slice(0, 120)}</code>
          : String(v),
    ])} />
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
