// Main pages: Overview, ML case study, History, Settings, new-investigation forms.
import { useEffect, useState, type ReactNode } from 'react'
import {
  api, CaseMetrics, CaseStudy, InvestigationSummary, SettingsPayload,
  useLoading,
} from './api'
import {
  EmptyState, ErrorState, KV, Loading, Note, Pill,
} from './ui'
import {
  CalibrationChart, DeltaAucChart, FoldSpanChart, LabelBalanceChart,
  PooledAucChart, PerFoldAucChart, shortName,
} from './charts'

/* ================================================================
   Overview — the landing page organized around next meaningful action
   ================================================================ */

export function Overview({ onOpen, onGo }: {
  onOpen: (id: string) => void
  onGo: (p: 'software' | 'ml' | 'history' | 'settings') => void
}) {
  const { data, error, reload } = useLoading<{ items: InvestigationSummary[] }>(
    () => api.listInvestigations())

  if (error) {
    return (
      <>
        <ErrorState error={error} onRetry={reload}
          hint="The backend must be running: py -m model_autopsy.backend" />
      </>
    )
  }
  if (!data) return <Loading what="Loading overview" />

  const items = data.items
  const real = items.filter((i) => !i.is_test_record)
  const testRecords = items.filter((i) => i.is_test_record)
  const active = real.filter((i) => !['complete', 'failed', 'stopped'].includes(i.status))
  const attention = real.filter((i) => i.status === 'blocked' || i.status === 'failed')
  const completed = real.filter((i) => i.status === 'complete')

  return (
    <>
      <div className="casehead">
        <div className="kicker">Forensic research workbench</div>
        <h1>Model Autopsy</h1>
        <p className="verdict">
          An AI-assisted investigation environment: a runtime investigator proposes falsifiable
          hypotheses, executes <i>bounded</i>, validated diagnostics against real artifacts,
          updates its conclusions from actual outputs, and issues a final report in which every
          claim traces to recorded evidence. Nothing here is simulated.
        </p>
        <div className="actionsrow" style={{ marginTop: 14 }}>
          <button className="primary" onClick={() => onGo('ml')}>Open ML case study</button>
          <button className="ghost" onClick={() => onGo('software')}>New software autopsy</button>
        </div>
      </div>

      <div className="readouts">
        <div className="readout"><div className="num">{real.length}</div><div className="lbl">Investigations on record</div></div>
        <div className="readout"><div className="num">{active.length}</div><div className="lbl">Active</div></div>
        <div className="readout"><div className="num">{completed.length}</div><div className="lbl">Complete</div></div>
        <div className="readout"><div className="num" style={{ color: attention.length ? 'var(--warn)' : undefined }}>{attention.length}</div><div className="lbl">Needs attention</div></div>
      </div>

      <section className="section" aria-label="Recent investigations">
        <h3>Investigations</h3>
        {real.length === 0
          ? (
            <EmptyState
              what="No validated investigations yet — the board renders only what is real."
              action="Start the Demand Zone AI case study or a software autopsy above." />
          )
          : (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Title</th><th>Mode</th><th>Status</th><th className="num">Tool calls</th><th>Latest finding</th><th>Report</th></tr>
                </thead>
                <tbody>
                  {real.slice(0, 8).map((i) => (
                    <RowLink key={i.id} onOpen={() => onOpen(i.id)}>
                      <td>{i.title}</td>
                      <td>{i.mode}</td>
                      <td><Pill status={i.status} /></td>
                      <td className="num">{i.tool_call_count}/{i.max_tool_calls}</td>
                      <td className="muted">{i.latest_findings.length
                        ? `${i.latest_findings[i.latest_findings.length - 1].status}: ${i.latest_findings[i.latest_findings.length - 1].summary.slice(0, 70)}${i.latest_findings[i.latest_findings.length - 1].summary.length > 70 ? '…' : ''}`
                        : '—'}</td>
                      <td>{i.has_final_report ? <span className="pill ok">report</span> : <span className="faint">—</span>}</td>
                    </RowLink>
                  ))}
                </tbody>
              </table>
              {real.length > 8 && (
                <p className="faint"><button className="link" onClick={() => onGo('history')}>See all {real.length} in history →</button></p>
              )}
            </div>
          )}
      </section>

      {testRecords.length > 0 && (
        <Note kind="warn">
          {testRecords.length} record(s) in the database were created by pre-isolation test runs
          (listed above are excluded from the counts here). They are preserved, not deleted —
          review them with <code className="inline">py -3 -m model_autopsy.backend.prune</code> (dry run)
          and remove with <code className="inline">--apply</code> only with explicit owner confirmation.
        </Note>
      )}

      <CaseStudyBanner onOpen={() => onGo('ml')} />

      <section className="section" aria-label="Boundaries">
        <h3>Operating boundaries</h3>
        <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)', fontSize: 13 }}>
          <li>The Demand Zone autonomous campaign supervisor (<code className="inline">autonomous_agent/</code>) is fully independent — no tool here can start, stop, or modify it.</li>
          <li>All tools are read-only against the research artifacts; no code-writing capability exists.</li>
          <li>Live Meta inference happens only when a key is configured; without one, manual mode works end to end.</li>
        </ul>
      </section>
    </>
  )
}

function RowLink({ children, onOpen }: { children: ReactNode; onOpen: () => void }) {
  return (
    <tr className="clickable" tabIndex={0} role="link"
      onClick={onOpen}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen() } }}
      aria-label="Open investigation">
      {children}
    </tr>
  )
}

/** Compact case-study teaser on the overview, fed by the REAL metrics endpoint. */
function CaseStudyBanner({ onOpen }: { onOpen: () => void }) {
  const { data: m, error, reload } = useLoading<CaseMetrics>(() => api.caseMetrics(200))
  return (
    <section className="hs-section" aria-label="Case study">
      <h3>Opening case study</h3>
      {error
        ? <Note kind="warn">Case-study metrics unavailable: {error} <button className="link" onClick={reload}>retry</button></Note>
        : !m ? <Loading what="Recomputing case-study metrics" /> : (
          <div className="hud">
            <div className="hud grid2" style={{ border: 'none', padding: 0, marginBottom: 0, background: 'transparent' }}>
              <div>
                <h2 style={{ marginBottom: 4 }}>Demand Zone AI — frozen v1.0.2 champion</h2>
                <p className="muted" style={{ marginTop: 0 }}>
                  {m.n_rows.toLocaleString()} out-of-fold rows · folds {(Object.keys(m.per_fold_auc)).join(', ')} ·
                  {' '}ΔAUC intervals recomputed live by {m.delta_auc_pairs[0]?.n_boot ?? 200}+ bootstrap replicates
                  ({m.cluster_column_used ? 'ticker-clustered' : 'row-level'} resampling).
                </p>
                <p className="faint" style={{ fontSize: 12.5 }}>
                  Champion arms pooled AUC: {Object.entries(m.pooled_auc).slice(0, 4)
                    .map(([a, v]) => `${shortName(a)} ${v.toFixed(3)}`).join(' · ')}
                </p>
                <button className="primary" onClick={onOpen}>Enter the case study</button>
              </div>
              <div>
                <div className="readout" style={{ border: 'none', padding: 0 }}>
                  <div className="lbl">Why it's interesting</div>
                  <p className="muted" style={{ fontSize: 13 }}>
                    The archived narrative claims a 0.97 → 0.676 AUC drop after de-leaking. The
                    leaked-feature dataset is <b>not preserved in this repository</b>, so that claim
                    cannot be recomputed here. What IS recomputable: the frozen champion's real fold
                    chronology, calibration, and arm deltas — precisely what the case study examines.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
    </section>
  )
}

/* ================================================================
   ML case study page
   ================================================================ */

export function MLPage({ onOpen }: { onOpen: (id: string) => void }) {
  const { data: cs, error: csErr, reload: reloadCs } = useLoading<CaseStudy>(() => api.caseStudy())
  const { data: m, error: mErr, reload: reloadM } = useLoading<CaseMetrics>(() => api.caseMetrics(200))
  const { data: list, reload: reloadList } = useLoading<{ items: InvestigationSummary[] }>(() => api.listInvestigations('ml'))
  const [starting, setStarting] = useState(false)
  const [startErr, setStartErr] = useState('')

  async function startCaseStudy() {
    setStarting(true); setStartErr('')
    try {
      // Reopen the latest investigation this glue produced; only create a new
      // one when none exists, so repeated clicks never clone the case study.
      const CASE_TITLE = 'Demand Zone AI — error-cluster investigation'
      const { items } = await api.listInvestigations('ml')
      const existing = items.find((i) => i.title === CASE_TITLE)
      if (existing) { onOpen(existing.id); return }
      const inv = await api.createInvestigation({
        mode: 'ml',
        title: CASE_TITLE,
        question: 'Where does the frozen champion fail? Compare model arms on the real OOF artifact and investigate chronology, calibration, and arm deltas.',
      })
      await api.buildContext(inv.id)
      onOpen(inv.id)
      reloadList()
    } catch (e) {
      setStartErr(e instanceof Error ? e.message : String(e))
    } finally {
      setStarting(false)
    }
  }

  return (
    <>
      <div className="casehead">
        <div className="kicker">Case study 1 · recomputable evidence</div>
        <h1>{cs?.name ?? 'Demand Zone AI'}</h1>
        <p className="verdict">
          The frozen v1.0.2 protocol artifacts are the real, independently recomputable evidence.
          The archived 0.97 → 0.676 suspicious-AUC narrative is a <b>stored historical claim</b> over
          a dataset that is not preserved in this repository — it is presented as recorded history,
          never recomputed as if it were current evidence.
        </p>
        <div className="actionsrow" style={{ marginTop: 14 }}>
          <button className="primary" onClick={startCaseStudy} disabled={starting}>
            {starting ? 'Preparing real context…' : 'Start / reopen the case-study investigation'}
          </button>
          {(list?.items.length ?? 0) > 0 && (
            <span className="faint">{list?.items.length} prior ML investigation(s) in history</span>
          )}
        </div>
        {startErr && <Note kind="bad">{startErr}</Note>}
      </div>

      {csErr && <ErrorState error={csErr} onRetry={reloadCs} hint="Backend not reachable?" />}
      {!cs && !csErr && <Loading what="Loading case-study artifacts" />}

      {cs && (
        <section className="section" aria-label="Artifact provenance">
          <h3>Artifact provenance — read-only inputs</h3>
          {cs.error
            ? <Note kind="bad">Artifact problem: {cs.error}</Note>
            : (
              <KV items={[
                ['OOF predictions', <code className="inline">{cs.artifacts.oof_csv}</code>],
                ['Event table', <code className="inline">{cs.artifacts.event_csv}</code>],
                ['Model binaries', <code className="inline">{cs.artifacts.models_dir}</code>],
                ['Registered arms', cs.model_cols.length],
                ['Artifact summary',
                  cs.summary
                    ? `${Number(cs.summary.n_rows).toLocaleString()} rows · folds ${JSON.stringify(cs.summary.folds_present)} · positive-share ${(Number(cs.summary.positive_rate) * 100).toFixed(1)}%`
                    : 'unavailable'],
              ]} />
            )}
        </section>
      )}

      {mErr
        ? <Note kind="warn">Live metrics unavailable: {mErr} <button className="link" onClick={reloadM}>retry</button></Note>
        : !m ? <Loading what="Recomputing AUC / calibration / ΔAUC from the frozen artifact" /> : (
          <>
            <section className="section" aria-label="Arm comparison">
              <h3>Model-arm comparison</h3>
              <PooledAucChart pooled={m.pooled_auc} nRows={m.n_rows} />
              <div className="tablewrap">
                <table>
                  <caption className="faint" style={{ captionSide: 'top', textAlign: 'left', fontSize: 11, padding: '4px 0' }}>
                    Text alternative for the chart above — same numbers, both from the live recomputation.
                  </caption>
                  <thead><tr><th>Arm</th><th className="num">Pooled OOF AUC</th></tr></thead>
                  <tbody>
                    {Object.entries(m.pooled_auc).sort((a, b) => b[1] - a[1]).map(([arm, v]) => (
                      <tr key={arm}><td>{shortName(arm)}</td><td className="num">{v.toFixed(4)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="section" aria-label="Fold comparison">
              <h3>Per-fold comparison (2023 / 2024 / 2025 windows)</h3>
              <PerFoldAucChart perFold={m.per_fold_auc} foldSizes={m.fold_sizes} />
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr>
                      <th>Fold</th><th className="num">Rows</th>
                      {Object.keys(m.per_fold_auc).length > 0 &&
                        Object.keys(m.per_fold_auc[Object.keys(m.per_fold_auc)[0]] ?? {}).map((a) => (
                          <th key={a} className="num">{shortName(a)}</th>))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(m.per_fold_auc).sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([fold, scores]) => (
                      <tr key={fold}>
                        <td>{fold}</td>
                        <td className="num">{m.fold_sizes[fold]?.toLocaleString() ?? '—'}</td>
                        {Object.keys(m.per_fold_auc[Object.keys(m.per_fold_auc)[0]] ?? {}).map((a) => (
                          <td key={a} className="num">{scores[a] != null ? scores[a].toFixed(4) : 'n/a'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="section" aria-label="Delta AUC">
              <h3>ΔAUC with uncertainty (cluster-aware bootstrap)</h3>
              <DeltaAucChart pairs={m.delta_auc_pairs} />
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr><th>Pair (B − A)</th><th className="num">Δ</th><th className="num">95% CI</th>
                      <th className="num">Replicates</th><th>Design</th></tr>
                  </thead>
                  <tbody>
                    {m.delta_auc_pairs.map((p) => (
                      <tr key={p.score_a + p.score_b}>
                        <td>{shortName(p.score_b)} − {shortName(p.score_a)}</td>
                        <td className="num">{p.delta.toFixed(4)}</td>
                        <td className="num">[{p.ci_low.toFixed(3)}, {p.ci_high.toFixed(3)}]</td>
                        <td className="num">{p.n_boot}</td>
                        <td className="faint">{p.sampling_unit === 'ticker'
                          ? 'ticker-cluster (events of one ticker dependent)'
                          : 'row-level (limitation: ignores within-ticker dependence)'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Note kind="warn">
                Bootstrap assumptions: resampling treats each sampling unit as exchangeable within
                the pooled OOF rows; seed is fixed (42) for reproducibility. A ΔAUC interval that
                crosses zero supports no ranking claim at this sample size — report it as such.
              </Note>
            </section>

            {m.calibration && m.calibration.reliability_bins.length > 0 && (
              <section className="section" aria-label="Calibration">
                <h3>Calibration of the champion arm</h3>
                <CalibrationEmbed m={m} />
              </section>
            )}

            {m.chronology && Object.keys(m.chronology.fold_date_spans).length > 0 && (
              <section className="section" aria-label="Chronology">
                <h3>Fold chronology</h3>
                <FoldSpanChart spans={m.chronology.fold_date_spans}
                  dateColumn={m.chronology.date_column}
                  nonOverlapping={m.chronology.non_overlapping_adjacent_folds} />
              </section>
            )}

            {m.label_balance && (
              <section className="section" aria-label="Label balance">
                <h3>Label balance</h3>
                <LabelBalanceChart counts={m.label_balance.counts}
                  positiveShare={m.label_balance.positive_share}
                  nRows={m.label_balance.n_rows} />
              </section>
            )}

            <Note kind="accent">{m.historical_claim_note}</Note>
            <Note>
              Source of every figure on this page: <code className="inline">{m.source}</code> —
              recomputed live on request ({m.recomputed_live ? 'verified' : 'unverified'}) via
              <code className="inline"> /api/case-study/demand-zone/metrics</code>.
            </Note>
          </>
        )}
    </>
  )
}

function CalibrationEmbed({ m }: { m: CaseMetrics }) {
  const cal = m.calibration!
  return (
    <>
      <CalibrationChart bins={cal.reliability_bins} champion={cal.arm}
        brier={cal.brier} logLoss={cal.log_loss} />
      <div className="tablewrap">
        <table>
          <thead>
            <tr><th>Bin</th><th className="num">n</th><th className="num">Mean score</th><th className="num">Observed +</th></tr>
          </thead>
          <tbody>
            {cal.reliability_bins.map((b, i) => (
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

/* ================================================================
   New investigation form (software) — the Software Autopsy page
   ================================================================ */

export function SoftwarePage({ onOpen }: { onOpen: (id: string) => void }) {
  return <NewForm mode="software" onOpen={onOpen} />
}

function NewForm({ mode, onOpen }: { mode: 'software' | 'ml'; onOpen: (id: string) => void }) {
  const [title, setTitle] = useState(mode === 'software'
    ? 'Software autopsy — review the working tree'
    : 'Demand Zone AI — suspicious evaluation investigation')
  const [question, setQuestion] = useState('')
  const [root, setRoot] = useState('.')
  const [predictions, setPredictions] = useState('')
  const [created, setCreated] = useState<InvestigationSummary | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const steps = mode === 'software'
    ? ['Repository context →', 'Findings →', 'Hypotheses →', 'Proposed instructions →', 'Human review →', 'Tests →', 'Verdict']
    : ['Context →', 'Hypotheses →', 'Diagnostics →', 'Evidence →', 'Verdict']

  async function submit() {
    setBusy(true); setErr(''); setCreated(null)
    try {
      const inv = await api.createInvestigation({
        mode, title, question,
        workspace_root: mode === 'software' ? root : undefined,
        predictions_path: mode === 'ml' && predictions.trim() ? predictions : undefined,
      })
      await api.buildContext(inv.id)
      setCreated(inv)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="casehead">
        <div className="kicker">{mode === 'software' ? 'Software autopsy' : 'ML autopsy'} · bounded evidence workflow</div>
        <h1>{mode === 'software' ? 'Software Autopsy' : 'ML Model Autopsy'}</h1>
        <ol style={{ display: 'flex', gap: 10, listStyle: 'none', margin: '10px 0 0', padding: 0, flexWrap: 'wrap' }}>
          {steps.map((s, i) => <li key={i} className="faint" style={{ fontSize: 12.5 }}>{s}</li>)}
        </ol>
        <p className="verdict" style={{ marginTop: 10 }}>
          {mode === 'software'
            ? 'Read-only repository inspection; every revision is a PROPOSAL for human review. The platform never applies changes by itself and never grants the model a shell.'
            : 'Real diagnostics against a real prediction artifact. Every metric is computed on load; every conclusion must cite recorded evidence.'}
        </p>
      </div>

      <form className="hud" onSubmit={(e) => { e.preventDefault(); if (!busy && question.trim()) submit() }}>
        <h3>New {mode} investigation</h3>
        <div className="row">
          <div className="field">
            <label htmlFor={'title-' + mode}>Title</label>
            <input id={'title-' + mode} value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>
          {mode === 'software' && (
            <div className="field" style={{ maxWidth: 260 }}>
              <label htmlFor={'root-' + mode}>Workspace root (read-only)</label>
              <input id={'root-' + mode} value={root} onChange={(e) => setRoot(e.target.value)} placeholder="." />
            </div>
          )}
          {mode === 'ml' && (
            <div className="field" style={{ maxWidth: 320 }}>
              <label htmlFor={'pred-' + mode}>Predictions CSV override (optional)</label>
              <input id={'pred-' + mode} value={predictions} onChange={(e) => setPredictions(e.target.value)}
                placeholder="blank = frozen case-study artifact" />
            </div>
          )}
        </div>
        <div className="field" style={{ marginTop: 10 }}>
          <label htmlFor={'q-' + mode}>Investigation objective</label>
          <textarea id={'q-' + mode} value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder={mode === 'software'
              ? 'e.g. Audit the staged diff for correctness and register defects with file/line references.'
              : 'e.g. Why does the frozen champion validate as it does? Test chronology, calibration and arm deltas.'}
            required />
        </div>
        <div className="actionsrow" style={{ marginTop: 12 }}>
          <button className="primary" type="submit" disabled={busy || !question.trim()}>
            {busy ? 'Creating + loading real context…' : 'Create investigation'}
          </button>
          <span className="faint" style={{ fontSize: 12 }}>
            Budget: ≤3 iterations, ≤12 tool calls — tight by design so conclusions stay evidence-first.
          </span>
        </div>
      </form>

      {err && <Note kind="bad">{err}</Note>}
      {created && (
        <div className="hud">
          <h3>Created — context loaded from the real source</h3>
          <KV items={[
            ['Status', <Pill status={created.status} />],
            ['ID', <code className="inline">{created.id}</code>],
          ]} />
          <div className="actionsrow" style={{ marginTop: 10 }}>
            <button className="primary" onClick={() => onOpen(created.id)}>Open workspace →</button>
          </div>
        </div>
      )}
    </>
  )
}

/* ================================================================
   History — filterable, keyboard-accessible records
   ================================================================ */

export function HistoryPage({ onOpen }: { onOpen: (id: string) => void }) {
  const [mode, setMode] = useState('')
  const [status, setStatus] = useState('')
  const { data, error, reload } = useLoading<{ items: InvestigationSummary[] }>(
    () => api.listInvestigations(mode || undefined, status || undefined),
    [mode, status])

  return (
    <>
      <h1>Investigation history</h1>
      <p className="sub">Every recorded investigation with its budget usage and evidence state. Click a row (or focus it and press Enter) to open the workspace.</p>

      <form className="hud" style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div className="field" style={{ maxWidth: 160 }}>
          <label htmlFor="hist-mode">Mode</label>
          <select id="hist-mode" value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="">all</option><option value="software">software</option><option value="ml">ml</option>
          </select>
        </div>
        <div className="field" style={{ maxWidth: 190 }}>
          <label htmlFor="hist-status">Status</label>
          <select id="hist-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">all</option>
            <option value="created">created</option>
            <option value="context_ready">context ready</option>
            <option value="hypotheses_proposed">hypotheses proposed</option>
            <option value="investigating">investigating</option>
            <option value="finalizing">finalizing</option>
            <option value="complete">complete</option>
            <option value="blocked">blocked</option>
            <option value="failed">failed</option>
            <option value="stopped">stopped</option>
          </select>
        </div>
      </form>

      {error && <ErrorState error={error} onRetry={reload} />}
      {!data && !error ? <Loading what="Loading history" /> : null}
      {data && (data.items.length === 0
        ? <EmptyState what="No investigations match these filters."
          action="Clear the filters, or create a new investigation." />
        : (
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th><th>Title</th><th>Mode</th><th>Status</th>
                  <th>Created</th><th className="num">Tool calls</th><th className="num">Iterations</th><th>Report</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((i) => (
                  <RowLink key={i.id} onOpen={() => onOpen(i.id)}>
                    <td className="faint">{i.id.slice(0, 8)}</td>
                    <td>{i.title}{i.is_test_record
                      ? <span className="pill warn" title="Legacy record created by automated tests against the live app database. It stays on record until the owner runs the documented prune procedure.">test</span>
                      : null}</td>
                    <td>{i.mode}</td>
                    <td><Pill status={i.status} /></td>
                    <td>{i.created_at?.slice(0, 10)}</td>
                    <td className="num">{i.tool_call_count}/{i.max_tool_calls}</td>
                    <td className="num">{i.iteration_count}/{i.max_iterations}</td>
                    <td>{i.has_final_report ? <span className="pill ok">report</span> : <span className="faint">—</span>}</td>
                  </RowLink>
                ))}
              </tbody>
            </table>
          </div>
        ))}
    </>
  )
}

/* ================================================================
   Settings — honest integration states only
   ================================================================ */

export function SettingsPage() {
  const { data: s, error, reload } = useLoading<SettingsPayload>(() => api.settings())
  const [testing, setTesting] = useState(false)
  const [testNote, setTestNote] = useState('')

  async function test() {
    setTesting(true); setTestNote('')
    try {
      const r = await api.testConnection() as Record<string, unknown>
      setTestNote(r.ok
        ? `Live connection verified at ${new Date().toLocaleTimeString()}. This test ran a real /models request against ${String(r.base_url)}. It is NOT evidence that a full tool-calling investigation works — the first live Meta turn is the real verification.`
        : `Connection failed: ${String(r.detail ?? r.error)}`)
    } catch (e) {
      setTestNote('Connection failed: ' + String(e))
    } finally {
      setTesting(false)
      reload()
    }
  }

  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!s) return <Loading what="Loading settings" />

  const lt = s.meta.last_test
  const liveVerified = lt?.ok === true
  const failed = lt && !liveVerified

  return (
    <>
      <h1>Settings & integrations</h1>
      <p className="sub">Non-secret configuration. Credentials live only in backend environment variables — never in this UI, never in logs.</p>

      <section className="section" aria-label="Meta Model API">
        <h3>Meta Model API (runtime investigator)</h3>
        {!s.meta.key_configured
          ? <Note kind="accent">MODEL_API_KEY not configured → the app runs in <b>manual mode</b>. Investigations, diagnostics, and reports work end to end; Meta-specific stages display honestly as unavailable, never simulated. Set the key in <code className="inline">model_autopsy/.env</code> and restart the backend.</Note>
          : <Note kind="ok">MODEL_API_KEY is configured (value hidden by design). Meta turns become available in each investigation's Run controls; each turn is bounded and validated.</Note>}
        <KV items={[
          ['Base URL', <code className="inline">{s.meta.base_url}</code>],
          ['Model ID', <code className="inline">{s.meta.model_id}</code>],
          ['Verification status',
            lt === null || lt === undefined
              ? <span className="faint">never tested</span>
              : liveVerified ? <span className="pill ok">live-verified</span>
                : <span className="pill warn">last test failed</span>],
          ['Last test', lt?.at ? String(lt.at).replace('T', ' ').slice(0, 19) + 'Z' : <span className="faint">never</span>],
        ]} />
        {failed && <Note kind="warn">{'Last recorded test: ' + String(lt?.detail ?? 'no detail recorded')}</Note>}
        {liveVerified && (
          <Note kind="accent">
            A <b>/models</b> connectivity check is necessary but NOT sufficient: full live verification
            means one bounded Meta-driven investigation with a real tool round-trip (2C). Until that
            runs, treat this integration as <b>verified-for-connectivity only</b>.
          </Note>
        )}
        <div className="actionsrow" style={{ marginTop: 10 }}>
          <button className="ghost" onClick={test} disabled={testing || !s.meta.key_configured}>
            {testing ? 'Testing…' : 'Run live connection test'}
          </button>
          {!s.meta.key_configured && <span className="faint">configure MODEL_API_KEY first</span>}
        </div>
        {testNote && <Note>{testNote}</Note>}
      </section>

      <section className="section" aria-label="Safety limits">
        <h3>Investigation safety</h3>
        <KV items={[
          ['Iteration cap (absolute)', s.safety.absolute_max_iterations],
          ['Tool-call cap (absolute)', s.safety.absolute_max_tool_calls],
          ['Hypothesis cap', s.safety.max_hypotheses_per_investigation ?? 12],
          ['Workspace roots', s.safety.workspace_roots.map((r) => <code key={r} className="inline" style={{ marginRight: 6 }}>{r}</code>)],
          ['Write tools', s.safety.write_tools],
        ]} />
        <Note>{s.safety.campaign_isolation}</Note>
      </section>

      <section className="section" aria-label="Coding-agent boundary">
        <h3>Coding-agent integration</h3>
        <p className="muted">
          Manual authoring integration is deliberately deferred: software investigations already
          support the Git-based review → findings → proposals → human-application loop. Connecting
          a coding agent later is a separate integration; applying any change remains a
          human-controlled action outside the investigation engine.
        </p>
      </section>
    </>
  )
}
