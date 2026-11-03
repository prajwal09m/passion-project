// Investigation workspace — the centerpiece page.
// Composition: sticky context rail + evidence workspace + hypothesis panel;
// below them, the honest timeline and the evidence-linked final report.
import { Fragment, useEffect, useState } from 'react'
import {
  Action, api, EvidenceRef, FinalReport, formatTimelineTime, Hypothesis,
  InvestigationDetail, TimelineEvent, UploadedFile, useLoading,
} from './api'
import { EmptyState, ErrorState, Loading, Note, Pill, ResultRenderer, fmtInt, fmtNum, shortPath } from './ui'
import { ResearchLabPanel } from './ResearchLab'
import { TimelineFunnelChart } from './charts'
import { CausalPanel } from './CausalPanel'

function short(id: string): string { return id.slice(0, 8) }

function ClosurePanel({ id }: { id: string }) {
  const [c, setC] = useState<null | {
    hypotheses: { id: string; text: string; status: string }[];
    transitions: { hypothesis_id: string; hypothesis: string; from: string; to: string }[];
    experiment_ledger: { seq: number; title: string }[];
    experiments_executed: number; experiments_cap: number;
    tool_calls_used: number; tool_calls_max: number;
    verification: { seq: number; title: string }[];
    resolution: { seq: number; title: string }[];
  }>(null)
  useEffect(() => {
    let live = true
    api.closure(id).then((r) => { if (live) setC(r as never) }).catch(() => { if (live) setC(null) })
    return () => { live = false }
  }, [id])
  if (!c) return <EmptyState what="No closure records yet — they appear as the investigation runs." />
  const stage = (s: string) => s
  return (
    <div>
      <p className="faint" style={{ margin: '0 0 8px' }}>
        Experiments {c.experiments_executed}/{c.experiments_cap} (hypothesis bookkeeping excluded) ·
        tool calls {c.tool_calls_used}/{c.tool_calls_max}
      </p>
      {c.hypotheses.map((h) => (
        <div key={h.id} className="tl-item">
          <div className="tl-when">Stage: {stage(h.status)}<span className="tl-kind">{short(h.id)}</span></div>
          <div className="tl-title">{h.text}</div>
        </div>
      ))}
      {c.transitions.map((t, i) => (
        <div key={i} className="tl-item k-resolution">
          <div className="tl-when">Transition<span className="tl-kind">{short(t.hypothesis_id)}</span></div>
          <div className="tl-title">{t.from} → {t.to}: {t.hypothesis}</div>
        </div>
      ))}
      {c.verification.map((e) => (
        <div key={e.seq} className="tl-item k-verification">
          <div className="tl-when">Verification<span className="tl-kind">#{e.seq}</span></div>
          <div className="tl-title">{e.title}</div>
        </div>
      ))}
      {c.resolution.map((e) => (
        <div key={e.seq} className="tl-item k-resolution">
          <div className="tl-when">Resolution<span className="tl-kind">#{e.seq}</span></div>
          <div className="tl-title">{e.title}</div>
        </div>
      ))}
    </div>
  )
}

export default function Workspace({ id, onBack }: { id: string; onBack: () => void }) {
  const { data: invBasis, error, reload } = useLoading<InvestigationDetail>(() => api.getInvestigation(id), [id])
  const [events, setEvents] = useState<TimelineEvent[] | null>(null)
  const [timelineError, setTimelineError] = useState('')
  const [m16, setM16] = useState<{
    reservation: TimelineEvent[]; skeptic: TimelineEvent[];
    grounded: TimelineEvent[]; linker_notes: TimelineEvent[];
    status_justifications: { id: string; text: string; status: string; justification: string | null }[]
  } | null>(null)
  const [busy, setBusy] = useState('') // '' | 'ctx' | 'tool' | 'meta' | 'report' | 'auto' | ...
  const [actErr, setActErr] = useState('')
  const [actOk, setActOk] = useState('')
  const [lastToolOutput, setLastToolOutput] = useState<Action | null>(null)
  // Fresh detail state so budget/hypotheses/evidence update in place after
  // every action instead of showing stale numbers until a manual reload.
  const [liveInv, setLiveInv] = useState<InvestigationDetail | null>(null)

  async function refresh() {
    try {
      const [d, t] = await Promise.all([api.getInvestigation(id), api.timeline(id)])
      setLiveInv(d)
      setEvents(t.events)
      try {
        const m = await api.m16(id)
        setM16(m)
      } catch { setM16(null) }
      setTimelineError('')
      return d
    } catch (e) {
      setTimelineError(e instanceof Error ? e.message : String(e))
      return null
    }
  }

  useEffect(() => { refresh() }, [id])

  async function act(label: string, fn: () => Promise<unknown>) {
    setBusy(label); setActErr(''); setActOk('')
    try {
      await fn()
      await refresh()
    } catch (e) {
      setActErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy('')
    }
  }

  if (error && !invBasis) {
    return (
      <>
        <button className="ghost" onClick={onBack}>← back to workbench</button>
        <ErrorState error={error} onRetry={reload} />
      </>
    )
  }
  if (!invBasis) return <Loading what="Loading investigation" />

  // Prefer the live detail (updated in place after each action); fall back to
  // the value from the initial load/reload.
  const inv = (liveInv && liveInv.id === id) ? liveInv : invBasis

  const budgetPct = Math.min(100, Math.round((inv.tool_call_count / Math.max(1, inv.max_tool_calls)) * 100))
  const hot = inv.tool_call_count >= inv.max_tool_calls
  const isML = inv.mode === 'ml'
  const context = (inv.config?.context ?? null) as {
    workspace_root?: string; git?: unknown; path?: string; source?: string; filename?: string
  } | null
  const revisionPlans = (inv.config?.revision_plans ?? []) as {
    at: string; findings?: string[]; instructions?: string[]; review_tests?: string; applied?: unknown
  }[]

  async function runInlineTool(toolName: string, args: Record<string, unknown>) {
    await act('tool', async () => {
      const res = await api.runTool(id, toolName, args)
      const detail = await api.getInvestigation(id)
      const a = (detail.actions ?? []).find((x) => x.id === res.action_id)
      setLastToolOutput(a ?? null)
      setActOk(res.ok ? `Tool ${toolName} executed; its real output is now shown as evidence below.`
        : `Tool ${toolName} refused or failed: ${res.error ?? res.detail}`)
    })
  }

  return (
    <div>
      <div className="crumb"><button onClick={onBack}>← home</button></div>

      <div className="invhero">
        <div className="invhero-top">
          <div style={{ flex: '1 1 420px' }}>
            <div className="kicker">{isML ? 'ML model autopsy' : 'Software autopsy'} · {short(inv.id)} · created {inv.created_at?.slice(0, 19).replace('T', ' ')}</div>
            <h1>{inv.title}</h1>
            <p className="sub clamp2" style={{ margin: 0 }}>{inv.question}</p>
            {inv.question && inv.question.length > 140 && (
              <details className="qmore">
                <summary>Full investigation question</summary>
                <p className="fullq">{inv.question}</p>
              </details>
            )}
          </div>
        </div>
        <div className="verdictrow">
          <div className="verdict" role="status">
            <span title="Whether the workflow itself finished"><b>Execution</b> <Pill status={inv.status} /></span>
            {inv.scientific && (
              <span title="What the recorded evidence establishes — distinct from workflow completion">
                <b>Scientific</b> <Pill status={inv.scientific.status} /> {inv.scientific.explanation}
              </span>
            )}
          </div>
          <div className="budgetslim" role="img"
            aria-label={`Tool-call budget: ${inv.tool_call_count} of ${inv.max_tool_calls} used; iterations ${inv.iteration_count} of ${inv.max_iterations}.`}>
            <span className="b"><span className="track"><i style={{ width: `${budgetPct}%` }} /></span>{inv.tool_call_count}/{inv.max_tool_calls} calls</span>
            <span className="b">{inv.iteration_count}/{inv.max_iterations} iters</span>
          </div>
        </div>
        <StageSteps inv={inv} />
        {inv.scientific && inv.status === 'complete' && inv.scientific.status === 'inconclusive' && (
          <div style={{ marginTop: 10 }}>              <Note kind="warn">Diagnostic battery finished. No explanation has been established yet — this is not a pass. See hypotheses and what would test them below.</Note>
          </div>
        )}
      </div>

      <div className="wsgrid">
        {/* ---------- main column ---------- */}
        <div className="col-main">

          {actErr && <Note kind="bad">{actErr}</Note>}
          {actOk && <Note kind="ok">{actOk}</Note>}
          {!actErr && !hot && (
            <Note kind="accent">
              {inv.status === 'created'
                ? 'Step 1 — load the real context (repository or dataset), then run diagnostics or a Meta turn.'
                : isML ? 'Run diagnostics one at a time; every output becomes recorded evidence the hypotheses can cite.'
                  : 'Inspect diffs and run the fixed test command; register findings and revision bundles for human review.'}
            </Note>
          )}

          {lastToolOutput && (
            <section className="section" aria-label="Latest diagnostic output" id="latest-diagnostic">
              <div className="sechead"><h2>Latest diagnostic</h2><span className="count">recorded output</span></div>
              <EvidenceItem action={lastToolOutput} defaultOpen />
            </section>
          )}

          <section className="section" aria-label="Evidence workspace">
            <div className="sechead"><h2>Evidence</h2><span className="count">{inv.actions?.length ?? 0} recorded actions</span></div>
            {(inv.actions?.length ?? 0) > 0 ? (
              [...inv.actions].reverse().map((a, i) => (
                <EvidenceItem key={a.id} action={a} defaultOpen={i === 0} />
              ))
            ) : (
              <EmptyState what="No diagnostics have run yet."
                action="Load context, then run a Meta turn in Run controls." />
            )}
          </section>

          <section className="section" aria-label="Potential explanations" id="hypotheses">
            <div className="sechead"><h2>Hypotheses</h2><span className="count">{inv.hypotheses?.length ?? 0} proposed · suspicion, not proof</span></div>
            {inv.scientific && (inv.scientific.suspicious_feature || (inv.scientific.evidence_gaps?.length ?? 0) > 0) && (
              <div className="verdict" style={{ marginBottom: 12 }}>
                {inv.scientific.suspicious_feature && (
                  <span><b>Suspicion signal</b> {inv.scientific.suspicious_feature} (|r|={Number(inv.scientific.suspicious_max_abs_r).toFixed(3)})</span>
                )}
                {(inv.scientific.evidence_gaps?.length ?? 0) > 0 && (
                  <span><b>Evidence gaps</b> {(inv.scientific.evidence_gaps ?? []).join(' · ')}</span>
                )}
              </div>
            )}
            <EvidenceMap inv={inv} />
            <HypothesisBoard inv={inv} actions={inv.actions ?? []} busy={busy !== ''} onChanged={refresh} />
            <div className="actionsrow" style={{ marginTop: 10 }}>
              <button className="ghost" disabled={busy !== ''} title="Offline, deterministic: proposes up to 3 hypotheses from recorded diagnostics only. Never duplicates existing ones." onClick={() => act('interp', async () => {
                const r = await api.autoInterpret(inv.id)
                setActOk(r.hypotheses.created.length ? `Proposed ${r.hypotheses.created.length} candidate explanation(s) — suspicion only, not proof.` : 'No new candidate could be formulated from recorded evidence; see missing-evidence hints.')
              })}>{busy === 'interp' ? 'Interpreting…' : 'Propose explanations from evidence'}</button>
            </div>
            <ManualHypothesisForm inv={inv} disabled={busy !== ''} onSub={refresh} act={act} />
          </section>

          <section className="section" aria-label="Suggested experiments">
            <div className="sechead"><h2>What would test it</h2><span className="count">{inv.recommended_experiments?.length ?? 0} suggested</span></div>
            <SuggestedExperiments inv={inv} />
          </section>

          <section className="section" aria-label="Findings">
            <div className="sechead"><h2>Findings</h2><span className="count">{inv.latest_findings.length} recorded</span></div>
            {inv.latest_findings.length === 0 ? (
              <EmptyState what="No findings recorded yet."
                action="Findings are recorded from evidence; add one after a diagnostic runs." />
            ) : (
              inv.latest_findings.map((f, i) => (
                <div key={i} className="finding">
                  <b>{f.status}</b>
                  {f.summary}
                  {f.evidence_action_id && (
                    <span className="evref" style={{ marginLeft: 8 }}>evidence: action #{actionLabel(f.evidence_action_id, inv.actions ?? [])}</span>
                  )}
                </div>
              ))
            )}
            <FindingForm invId={inv.id} actions={inv.actions ?? []}
              disabled={busy !== ''} onDone={() => refresh()} act={act} />
          </section>

          {(revisionPlans.length) > 0 && !isML && (
            <section className="section" aria-label="Proposed revision plans">
              <h3>Proposed revision instructions — human review required</h3>
              {revisionPlans.map((p, i) => (
                <div key={i} className="hyp">
                  <div className="foot" style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <span className="pill">plan #{i}</span>
                    <span className="muted">{short(String(p.at))}</span>
                    {p.applied
                      ? <span className={'pill ok'}>applied manually · acknowledged by owner</span>
                      : <span className={'pill warn'}>proposed — NOT applied</span>}
                  </div>
                  <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
                    {(p.instructions ?? []).map((s, j) => <li key={j}>{s}</li>)}
                  </ul>
                  {p.review_tests && (
                    <p className="faint" style={{ margin: '6px 0 0' }}>suggested tests: {p.review_tests}</p>
                  )}
                  {!p.applied && (
                    <div style={{ marginTop: 8 }}>
                      <button className="ghost" disabled={busy !== ''}
                        onClick={() => act('apply' + i, async () => {
                          await api.markPlanApplied(inv.id, i)
                          setActOk(`Plan ${i} marked applied (manual acknowledgement recorded). No code was changed by this platform.`)
                        })}>
                        Acknowledge applied manually (owner action)
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </section>
          )}

          <details className="section hs-section" aria-label="Advanced record">
            <summary style={{ cursor: 'pointer' }}>
              <span className="sechead" style={{ display: 'inline-flex' }}><h2 style={{ fontSize: 16 }}>Advanced record</h2><span className="count">research lab · live discovery · closure</span></span>
            </summary>
            {isML && (
              <section aria-label="Research lab" style={{ marginTop: 12 }}>
                <h3>Research lab — autonomous cycle</h3>
                <ResearchLabPanel id={inv.id} />
              </section>
            )}
            <section aria-label="Live discovery (M16)" style={{ marginTop: 12 }}>
              <h3>Live discovery — reservation, skeptic, attribution</h3>
              {!m16 ? (
                <EmptyState what="No M16 records yet — they appear after a live turn runs." />
              ) : (m16.reservation.length === 0 && m16.skeptic.length === 0 && m16.grounded.length === 0) ? (
                <EmptyState what="No reservation, skeptic, or grounding records on this investigation." />
              ) : (
                <ul className="tl">
                  {m16.reservation.map((e) => (
                    <li key={'r' + e.seq} className="k-info"><span className="tlt"><b>Reserved probe</b> {e.title}</span><span className="tltime">#{e.seq}</span></li>
                  ))}
                  {m16.skeptic.map((e) => (
                    <li key={'s' + e.seq} className="k-warn"><span className="tlt"><b>Skeptic-lite</b> {e.title}</span><span className="tltime">#{e.seq}</span></li>
                  ))}
                  {m16.grounded.map((e) => (
                    <li key={'g' + e.seq} className="k-info"><span className="tlt"><b>Grounded facts</b> {e.title}</span><span className="tltime">#{e.seq}</span></li>
                  ))}
                  {m16.status_justifications.filter((h) => h.justification).map((h) => (
                    <li key={h.id} className="k-info"><span className="tlt"><b>Status: {h.status}</b> {h.text}</span>
                      <details><summary>justification</summary><div className="tl-detail">{h.justification}</div></details>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section aria-label="Scientific closure (M18)" style={{ marginTop: 12 }}>
              <h3>Scientific closure — hypotheses, transitions, verification, spend</h3>
              <ClosurePanel id={inv.id} />
            </section>
          </details>

          <section className="section hs-section" aria-label="Timeline">
            <div className="sechead"><h2>Timeline</h2><span className="count">{events?.length ?? 0} events on record</span></div>
            {timelineError && <Note kind="bad">{timelineError}</Note>}
            {events && events.length > 0 && (
              <>
                <details>
                  <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Flow summary chart</summary>
                  <TimelineFunnelChart items={events.map((e) => ({
                    seq: e.seq,
                    kind: e.kind,
                    label: `${formatTimelineTime(e.created_at)}  ${e.title}`,
                  }))} />
                </details>
                <TimelineGroups events={events} />
              </>
            )}
            {events && events.length === 0 && <EmptyState what="Timeline is empty." />}
          </section>

          <section className="section hs-section" aria-label="Final report" id="report">
            <div className="sechead"><h2>Final report</h2><span className="count">deterministic · evidence-linked</span></div>
            <ReportSection inv={inv} busy={busy !== ''} run={() => act('report', async () => {
              await api.generateReport(inv.id)
              setActOk('Final report generated deterministically from recorded evidence.')
            })} />
          </section>
        </div>

        {/* ---------- side rail ---------- */}
        <div className="siderail">
          <div className="hud" aria-label="Run controls">
            <h3>Run controls</h3>
            <div className="actionsrow">
              <button className="primary" disabled={busy !== ''}
                onClick={() => act('ctx', async () => {
                  await api.buildContext(id)
                  setActOk('Context loaded from the real workspace/dataset.')
                })}>
                {busy === 'ctx' ? 'Loading…' : 'Load context'}
              </button>

              <div style={{ width: '100%' }}>
                <div className="faint" style={{ fontSize: 12, margin: '2px 0 6px' }}>
                  Meta AI is the investigator — diagnostics run through Meta turns only.
                </div>
                <MetaPanel invId={inv.id} disabled={busy !== '' || hot} act={act} verifyMeta={() => act('meta', async () => {
                  const r = await api.metaTurn(id, 3)
                  if (r.status === 'ok') setActOk(`Meta turn completed: ${r.tool_calls?.length ?? 0} validated tool call(s); interpretation recorded on the timeline.`)
                  else if (r.status === 'meta_unavailable') setActErr('Meta unavailable: ' + (r.error ?? 'key not configured'))
                  else setActErr('Meta turn ended early: ' + r.status)
                })} />
              </div>
            </div>
            {(inv.actions?.length ?? 0) < 1 && (
              <p className="faint" style={{ marginTop: 8, fontSize: 12 }}>
                Load context, then run a Meta turn — Meta runs the diagnostics and interprets the results.
              </p>
            )}
          </div>

          <div className="railbox" aria-label="Scope">
            <h4>Scope</h4>
            <div className="railrow"><span>{isML ? 'Dataset' : 'Workspace'}</span><b title={String(context?.path ?? context?.source ?? context?.workspace_root ?? context?.filename ?? '')}>{context
              ? (String(context.path ?? context.source ?? context.workspace_root ?? context.filename ?? '')
                ? shortPath(String(context.path ?? context.source ?? context.workspace_root ?? context.filename))
                : 'loaded')
              : 'not loaded'}</b></div>
            <div className="railrow"><span>Mode</span><b>{inv.mode}</b></div>
            <div className="railrow"><span><a href="#report">Final report ↓</a></span></div>
          </div>

          <div className="railbox" aria-label="Hypotheses status">
            <h4>Hypotheses</h4>
            <div className="railrow"><span>supported</span><b>{(inv.hypotheses ?? []).filter((h) => h.status === 'supported').length}</b></div>
            <div className="railrow"><span>rejected</span><b>{(inv.hypotheses ?? []).filter((h) => h.status === 'rejected').length}</b></div>
            <div className="railrow"><span>open</span><b>{(inv.hypotheses ?? []).filter((h) => h.status !== 'supported' && h.status !== 'rejected').length}</b></div>
            <div className="railrow"><span><a href="#hypotheses">Open hypothesis board →</a></span></div>
          </div>
          <details className="railbox" aria-label="Causal diagnosis">
            <summary style={{ cursor: 'pointer' }}><h4 style={{ display: 'inline', margin: 0 }}>Causal diagnosis</h4></summary>
            <div style={{ marginTop: 8 }}><CausalPanel invId={inv.id} /></div>
          </details>

          <details className="railbox" aria-label="Mode legend">
            <summary style={{ cursor: 'pointer' }}><h4 style={{ display: 'inline', margin: 0 }}>How evidence is graded</h4></summary>
            <ul style={{ margin: '8px 0 0', paddingLeft: 16, fontSize: 12.5, color: 'var(--muted)', listStyle: 'disc' }}>
              <li><b style={{ color: 'var(--ok)' }}>confirmed</b> — directly from a recorded tool output</li>
              <li><b style={{ color: 'var(--warn)' }}>likely</b> — supported but not proven beyond recorded evidence</li>
              <li><b style={{ color: 'var(--accent)' }}>rejected / unresolved</b> — contradicted by, or still open to, evidence</li>
              <li>Meta's confidence is an <i>uncalibrated model self-report</i>, kept separate from measured metrics</li>
            </ul>
          </details>
        </div>
      </div>
    </div>
  )
}

/* ================= sub-components ================= */

function actionLabel(actionId: string, actions: Action[]): string {
  const a = actions.find((x) => x.id === actionId)
  return a ? `#${a.seq} ${a.tool_name}` : short(actionId)
}

/** One-line human digest of a recorded diagnostic — shown on the collapsed card. */
function actionDigest(action: Action): string {
  const r = (action.result ?? {}) as Record<string, unknown>
  const n = (k: string): number => (typeof r[k] === 'number' ? r[k] as number : NaN)
  if (action.status === 'failed') return action.error ? `failed — ${action.error.slice(0, 90)}` : 'failed'
  switch (action.tool_name) {
    case 'classification_metrics': {
      const auc = n('roc_auc')
      return isFinite(auc) ? `ROC AUC ${auc.toFixed(3)} · Brier ${fmtNum(n('brier'))}` : 'single class — AUC undefined'
    }
    case 'calibration_and_error_analysis': {
      const bins = (r.reliability_bins ?? []) as unknown[]
      return `Brier ${fmtNum(n('brier'))} · ${bins.length} reliability bins`
    }
    case 'grouped_auc_comparison': {
      const d = n('delta')
      return isFinite(d) ? `ΔAUC ${d >= 0 ? '+' : ''}${d.toFixed(4)}` : 'ΔAUC unavailable'
    }
    case 'feature_target_suspiciousness': {
      const rows = (r.top_correlations ?? []) as { feature: string; abs_r: number }[]
      return rows.length ? `top |r| ${Number(rows[0].abs_r).toFixed(3)} (${rows[0].feature})` : 'no correlations recorded'
    }
    case 'dataset_validation':
      return `${fmtInt(n('n_rows'))} rows · ${fmtInt(n('n_columns'))} columns`
    case 'time_split_validation':
      return r.date_min ? `${String(r.date_min).slice(0, 10)} → ${String(r.date_max).slice(0, 10)}` : 'no date columns'
    case 'script_static_inspection': {
      const f = (r.findings ?? r.warnings ?? r.issues ?? []) as unknown[]
      return `${f.length} finding${f.length === 1 ? '' : 's'}`
    }
    case 'run_tests':
      return r.passed === true ? `passed · exit ${Math.round(n('exit_code'))}` : `exit ${Math.round(n('exit_code'))}`
    case 'artifact_summary': {
      const pr = n('positive_rate')
      return isFinite(pr) ? `${fmtInt(n('n_rows'))} rows · ${(pr * 100).toFixed(1)}% positive` : `${fmtInt(n('n_rows'))} rows`
    }
    default: return resultDigest(r as Record<string, unknown>)
  }
}

function EvidenceItem({ action, defaultOpen }: { action: Action; defaultOpen?: boolean }) {
  const [raw, setRaw] = useState(false)
  return (
    <details className="diag card" open={defaultOpen} data-action-id={action.id}>
      <summary className="diaghead">
        <span className="toolname">{action.tool_name ?? action.kind}</span>
        <Pill status={action.status} />
        <span className="diagdigest">#{action.seq} · {actionDigest(action)}</span>
        <span className="chev">details</span>
      </summary>
      <div className="diagbody">
        {action.status === 'failed'
          ? <Note kind="bad">Execution failed — recorded honestly: {action.error}</Note>
          : <ResultRenderer action={action} />}
        {action.result && (
          <details className="raw" open={raw} onToggle={(e) => setRaw((e.target as HTMLDetailsElement).open)}>
            <summary>Raw result JSON (diagnostic view)</summary>
            <pre>{JSON.stringify(action.result, null, 2)}</pre>
          </details>
        )}
      </div>
    </details>
  )
}

function ManualToolPicker({ isML, disabled, contextReady, onRun, hot }: {
  isML: boolean
  disabled: boolean
  contextReady: boolean
  onRun: (tool: string, args: Record<string, unknown>) => void
  hot: boolean
}) {
  const ML = [
    { name: 'artifact_summary', label: 'Dataset summary', args: {} },
    { name: 'classification_metrics', label: 'AUC · precision · recall (LightGBM_C)', args: { score_column: 'LightGBM_C' } },
    { name: 'time_split_validation', label: 'Chronology validation', args: {} },
    { name: 'calibration_and_error_analysis', label: 'Calibration + per-fold AUC', args: {} },
    { name: 'grouped_auc_comparison', label: 'ΔAUC LR_A vs LGBM_A (bootstrap)', args: {} },
    { name: 'dataset_validation', label: 'Validate a custom CSV...', args: null },
    { name: 'script_static_inspection', label: 'Inspect training script (static, never executed)...', args: null },
  ]
  const SW = [
    { name: 'git_status_and_diff', label: 'Git status + diff', args: {} },
    { name: 'list_changed_files', label: 'List changed files', args: {} },
    { name: 'read_changed_file_head', label: 'Read a file head…', args: null },
    { name: 'run_tests', label: 'Run the fixed test suite', args: {} },
    { name: 'check_apply_approval', label: 'Check apply-approval gate', args: {} },
  ]
  const base = isML ? ML : SW
  const [customPath, setCustomPath] = useState('')
  const [fileHead, setFileHead] = useState('model_autopsy/README.md')
  const [scriptPath, setScriptPath] = useState('')
  const [pyFiles, setPyFiles] = useState<UploadedFile[]>([])
  useEffect(() => {
    api.uploads()
      .then((r) => setPyFiles((r.uploads ?? []).filter((f) => f.name.toLowerCase().endsWith('.py') && !f.is_duplicate)))
      .catch(() => setPyFiles([]))
  }, [])
  if (!contextReady) {
    return <Note kind="warn">Load context first — diagnostics resolve paths against the loaded workspace/dataset.</Note>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {hot && <Note kind="warn">Tool-call budget exhausted — 12/12 used. This is a recorded, honest stop.</Note>}
      {base.map((t) => (
        <div key={t.name} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {t.name === 'script_static_inspection' ? (
            <>
              {pyFiles.length > 0 && (
                <select aria-label='Choose an uploaded Python script' disabled={disabled}
                  value={pyFiles.some((f) => f.path === scriptPath) ? scriptPath : ''}
                  onChange={(e) => setScriptPath(e.target.value)}
                  style={{ flex: '1 1 220px', minWidth: 180, fontSize: 12 }}>
                  <option value="">Choose an uploaded .py…</option>
                  {pyFiles.map((f) => (
                    <option key={f.batch + '/' + f.name} value={f.path}>{f.name} ({f.batch})</option>
                  ))}
                </select>
              )}
              <input aria-label='Training script path (project-relative .py)' value={scriptPath} disabled={disabled} onChange={(e) => setScriptPath(e.target.value)} placeholder='...or paste a project-relative .py path' style={{ flex: '1 1 220px', minWidth: 180 }} />
            </>
          ) : null}
          {t.name === 'dataset_validation' || t.name === 'read_changed_file_head' ? (
            <input aria-label={t.name === 'dataset_validation' ? 'Custom CSV path (project-relative)' : 'File path (project-relative)'}
              value={t.name === 'dataset_validation' ? customPath : fileHead} disabled={disabled}
              onChange={(e) => (t.name === 'dataset_validation' ? setCustomPath(e.target.value) : setFileHead(e.target.value))}
              placeholder={isML ? 'study_files/outputs/study_v1/development/event_table.csv' : 'model_autopsy/README.md'}
              style={{ flex: '1 1 220px', minWidth: 180 }} />
          ) : null}
          {t.name === 'grouped_auc_comparison' ? (
            <span className="faint" style={{ fontSize: 11 }}>score pair A/B — default in the registry</span>
          ) : null}
          <button className="ghost" disabled={disabled || (t.args === null && (t.name === 'dataset_validation' ? !customPath.trim() : t.name === 'script_static_inspection' ? !scriptPath.trim() : !fileHead.trim()))} title={t.name === 'script_static_inspection' ? (scriptPath.trim() ? 'Parse this script statically (never executed)' : 'Enter a .py path to enable inspection') : undefined}
            onClick={() => onRun(t.name, t.args === null
              ? (t.name === 'dataset_validation' ? { predictions_path: customPath } : t.name === 'script_static_inspection' ? { script_path: scriptPath } : { file_path: fileHead })
              : (t.args as Record<string, unknown>))}>
            {t.label}
          </button>
        </div>
      ))}
      <p className="faint" style={{ fontSize: 11.5, margin: '2px 0 0' }}>
        Every argument is validated server-side before execution; paths outside the project root are refused.
      </p>
    </div>
  )
}

function MetaPanel({ invId, disabled, act, verifyMeta }: {
  invId: string
  disabled: boolean
  act: (label: string, fn: () => Promise<unknown>) => Promise<void>
  verifyMeta: () => Promise<unknown>
}) {
  const [status, setStatus] = useState<{ key_configured: boolean; model_id: string } | null>(null)
  useEffect(() => {
    api.metaStatus().then((s) => setStatus({ key_configured: s.key_configured, model_id: s.model_id }))
      .catch(() => setStatus(null))
  }, [])
  const keyMissing = status === null || !status.key_configured
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {keyMissing && (
        <Note kind="accent">
          MODEL_API_KEY not configured → manual mode. The investigation stays fully usable;
          Meta-specific stages are marked unavailable rather than simulated.
        </Note>
      )}
      {!keyMissing && (
        <p className="faint" style={{ fontSize: 12, margin: 0 }}>
          Live integration against {status?.model_id}: requests are bounded, tool calls are validated
          server-side and round-tripped. Pushing "Run" will spend API tokens.
        </p>
      )}
      <button className="primary" disabled={disabled}
        onClick={() => act('meta', verifyMeta)}>
        {disabled ? 'Running…' : 'Run bounded Meta turn (≤3 rounds)'}
      </button>
      <p className="faint" style={{ fontSize: 11.5, margin: 0 }}>
        Advertised function schemas are generated from the same registry the backend validates against.
        Failed calls and spent budgets are recorded honestly on the timeline.
      </p>
    </div>
  )
}

function EvidenceChipList({ refs, actions }: { refs: EvidenceRef[]; actions: Action[] }) {
  if (!refs?.length) return null
  return (
    <span className="hypchips">
      {refs.map((r, i) => {
        const a = actions.find((x) => x.id === r.action_id)
        return (
          <span key={i} className={'evchip' + (r.relation === 'supports' ? ' sup' : r.relation === 'contradicts' ? ' con' : '')}
            title={`${r.relation} — ${a ? `#${a.seq} ${a.tool_name}` : 'action ' + short(r.action_id)}`}>
            {r.relation === 'supports' ? '▲ ' : r.relation === 'contradicts' ? '▼ ' : ''}
            {a ? `#${a.seq} ${a.tool_name}` : short(r.action_id)}
          </span>
        )
      })}
    </span>
  )
}

function LinkEvidenceForm({ h, actions, onSub }: {
  h: Hypothesis
  actions: Action[]
  onSub: () => Promise<InvestigationDetail | null>
}) {
  const [actionId, setActionId] = useState(actions[0]?.id ?? '')
  const [relation, setRelation] = useState<'supports' | 'contradicts'>('supports')
  const [err, setErr] = useState('')
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
      <label>
        <span className="faint" style={{ fontSize: 11 }}>evidence action: </span>
        <select value={actionId} onChange={(e) => setActionId(e.target.value)}
          style={{ width: 210, fontSize: 12 }}>
          {actions.map((a) => (
            <option key={a.id} value={a.id}>#{a.seq} {a.tool_name}</option>
          ))}
        </select>
      </label>
      <label className="faint" style={{ fontSize: 11 }}>
        <select value={relation} onChange={(e) => setRelation(e.target.value as 'supports' | 'contradicts')}>
          <option value="supports">supports</option>
          <option value="contradicts">contradicts</option>
        </select>
      </label>
      <button className="ghost" style={{ padding: '4px 10px', fontSize: 12 }}
        onClick={async () => {
          if (!actionId || !actionId.trim()) return
          try { await api.linkEvidence(h.id, actionId, relation); setErr(''); await onSub() }
          catch (e) { setErr(String(e)) }
        }}>
        Link
      </button>
      {err && <span className="faint" style={{ fontSize: 11 }}>{err}</span>}
    </div>
  )
}

function StageSteps({ inv }: { inv: InvestigationDetail }) {
  const ranActions = (inv.actions ?? []).filter((a) => a.status === 'ran').length
  const hypos = inv.hypotheses ?? []
  const verdicts = hypos.filter((h) => h.status === 'supported' || h.status === 'rejected').length
  const findings = inv.latest_findings?.length ?? 0
  const ctx = inv.status !== 'created'
  const stages = [
    { label: 'Context', state: ctx ? 'done' : 'active' },
    { label: 'Diagnose', state: ranActions > 0 ? 'done' : ctx ? 'active' : 'todo' },
    { label: 'Hypothesize', state: hypos.length > 0 ? 'done' : ranActions > 0 ? 'active' : 'todo' },
    { label: 'Verify', state: verdicts > 0 || findings > 0 ? 'done' : hypos.length > 0 ? 'active' : 'todo' },
    { label: 'Report', state: inv.final_report ? 'done' : verdicts > 0 ? 'active' : 'todo' },
  ] as { label: string; state: 'done' | 'active' | 'todo' }[]
  return (
    <ol className="steps" aria-label="Investigation pipeline">
      {stages.map((s, i) => (
        <li key={s.label} className={'step ' + s.state} aria-current={s.state === 'active' ? 'step' : undefined}>
          <span className="dot">{s.state === 'done' ? '✓' : i + 1}</span>
          {s.label}
          {i < stages.length - 1 && <span className="bar" />}
        </li>
      ))}
    </ol>
  )
}

/** Actions that register hypotheses rather than produce diagnostic evidence —
 *  they must not appear in the diagnostics column of the evidence map. */
const NON_DIAGNOSTIC_TOOLS = new Set(['propose_hypothesis', 'propose_revision_instructions'])

/** Visual trace: which recorded diagnostics each hypothesis cites, and how. */
function EvidenceMap({ inv }: { inv: InvestigationDetail }) {
  const acts = (inv.actions ?? [])
    .filter((a) => a.status === 'ran' && !NON_DIAGNOSTIC_TOOLS.has(a.tool_name ?? ''))
    .slice(-8)
  const hypos = (inv.hypotheses ?? []).slice(0, 8)
  if (acts.length === 0 || hypos.length === 0) return null
  const rowH = 36
  const H = Math.max(acts.length, hypos.length) * rowH + 34
  const yA = (i: number) => 26 + i * rowH
  const yH = (i: number) => 26 + i * rowH
  const actIndex = new Map(acts.map((a, i) => [a.id, i]))
  const links: { a: number; h: number; rel: string }[] = []
  hypos.forEach((h, hi) => {
    for (const ref of h.evidence_refs ?? []) {
      const ai = actIndex.get(ref.action_id)
      if (ai !== undefined) links.push({ a: ai, h: hi, rel: ref.relation })
    }
  })
  const aria = hypos.map((h) => {
    const refs = (h.evidence_refs ?? [])
      .map((r) => {
        const a = acts.find((x) => x.id === r.action_id)
        return `${r.relation} #${a ? a.seq : '?'} ${a ? a.tool_name : 'unknown'}`
      })
    return `${h.text} — ${refs.length ? refs.join('; ') : 'no linked evidence'}`
  }).join('. ')
  return (
    <figure style={{ margin: '0 0 12px' }}>
      <figcaption className="faint" style={{ fontSize: 11.5, marginBottom: 4 }}>
        Evidence map — which diagnostics each hypothesis cites
      </figcaption>
      <div className="hypchips" style={{ marginBottom: 6 }} aria-hidden="true">
        <span className="evchip sup">▲ supports</span>
        <span className="evchip con">▼ contradicts</span>
        <span className="evchip">other relation</span>
      </div>
      <svg className="evmap" viewBox={`0 0 640 ${H}`} role="img" aria-label={aria}>
        {links.map((l, i) => {
          const x1 = 250, y1 = yA(l.a), x2 = 390, y2 = yH(l.h)
          const mx = (x1 + x2) / 2, my = (y1 + y2) / 2
          const glyph = l.rel === 'supports' ? '▲' : l.rel === 'contradicts' ? '▼' : '•'
          const linkCls = l.rel === 'supports' ? 'link-sup' : l.rel === 'contradicts' ? 'link-con' : 'link-neu'
          return (
            <g key={i}>
              <title>{`#${acts[l.a].seq} ${acts[l.a].tool_name ?? acts[l.a].kind} ${l.rel} hypothesis ${short(hypos[l.h].id)} (${hypos[l.h].status})`}</title>
              <line x1={x1} y1={y1} x2={x2} y2={y2} className={linkCls} strokeWidth={2.25} />
              <text x={mx} y={my - 5} textAnchor="middle" className={'linklab ' + linkCls}>{glyph}</text>
            </g>
          )
        })}
        {acts.map((a, i) => (
          <g key={a.id}>
            <title>{`#${a.seq} ${a.tool_name ?? a.kind}: ${actionDigest(a)}`}</title>
            <rect className="node" x={8} y={yA(i) - 13} width={242} height={26} rx={6} />
            <text className="nodelabel" x={20} y={yA(i) + 1}>#{a.seq} {(a.tool_name ?? a.kind ?? '').slice(0, 24)}</text>
            <text className="nodesub" x={20} y={yA(i) + 11}>diagnostic</text>
          </g>
        ))}
        {hypos.map((h, i) => (
          <g key={h.id}>
            <title>{`${h.text} — ${h.status}`}</title>
            <rect className="node" x={390} y={yH(i) - 13} width={242} height={26} rx={6} />
            <text className="nodelabel" x={402} y={yH(i) + 1}>{short(h.id)} · {h.text.slice(0, 30)}{h.text.length > 30 ? '…' : ''}</text>
            <text className="nodesub" x={402} y={yH(i) + 11}>{h.status}</text>
          </g>
        ))}
      </svg>
    </figure>
  )
}

/** Single home for hypotheses: status rail, evidence chips, expandable detail + controls. */
function HypothesisBoard({ inv, actions, busy, onChanged }: {
  inv: InvestigationDetail
  actions: Action[]
  busy: boolean
  onChanged: () => Promise<InvestigationDetail | null>
}) {
  const hypos = inv.hypotheses ?? []
  if (hypos.length === 0) {
    return <EmptyState what="No explanations proposed yet." action="Run diagnostics, then press “Propose explanations from evidence” — or add a manual hypothesis below. Lack of proposals is not a pass." />
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {hypos.map((h) => {
        const machine = h.source === 'machine' || (h.rationale ?? '').includes('[machine-generated]')
        const st = h.status === 'supported' ? 'supported'
          : h.status === 'rejected' ? 'contradicted' : 'unresolved'
        const sup = (h.evidence_refs ?? []).filter((e) => e.relation === 'supports').length
        const con = (h.evidence_refs ?? []).filter((e) => e.relation === 'contradicts').length
        const ran = actions.filter((a) => a.status === 'ran')
        return (
          <details key={h.id} className={'hypcard st-' + st}>
            <summary>
              <div className="hyphead">
                <span className="hid">{short(h.id)}</span>
                <span className="hclaim">{h.text}</span>
                <Pill status={h.status} />
              </div>
              <div className="hypchips">
                <span className="evchip">{machine ? 'machine · suspicion only' : `origin: ${h.source}`}</span>
                {h.confidence !== null && h.confidence !== undefined && (
                  <span className="evchip" title="Uncalibrated model self-report — not a statistical confidence interval">
                    conf {h.confidence}%*
                  </span>
                )}
                {sup > 0 && <span className="evchip sup">▲ {sup} supporting</span>}
                {con > 0 && <span className="evchip con">▼ {con} contradicting</span>}
                {(h.evidence_refs ?? []).length === 0 && <span className="evchip">no linked evidence</span>}
              </div>
            </summary>
            <div className="hypbody">
              {h.rationale && <p className="muted" style={{ margin: '0 0 6px', fontSize: 12.5 }}><b>Why proposed: </b>{h.rationale}</p>}
              {h.predicted_observation && <p className="muted" style={{ margin: '0 0 6px', fontSize: 12.5 }}><b>Test: </b>{h.predicted_observation}</p>}
              {h.confidence_note && <p className="faint" style={{ margin: '0 0 6px', fontSize: 12 }}><b>Confidence meaning: </b>{h.confidence_note}</p>}
              <EvidenceChipList refs={h.evidence_refs ?? []} actions={actions} />
              {!busy && h.status !== 'supported' && h.status !== 'rejected' && (
                <div className="actionsrow" style={{ marginTop: 8 }}>
                  <button className="ghost" onClick={async () => { await api.patchHypothesis(h.id, { status: 'supported' }); onChanged() }}>Mark supported</button>
                  <button className="ghost" onClick={async () => { await api.patchHypothesis(h.id, { status: 'rejected' }); onChanged() }}>Mark rejected</button>
                  {ran.length > 0 && <LinkEvidenceForm h={h} actions={ran} onSub={onChanged} />}
                </div>
              )}
            </div>
          </details>
        )
      })}
      <p className="faint" style={{ fontSize: 11.5, margin: 0 }}>
        <sup>*</sup> Any displayed percentage is what the model or operator recorded — it is NOT an
        interval or a probability. Trust only the linked evidence.
      </p>
    </div>
  )
}

function SuggestedExperiments({ inv }: { inv: InvestigationDetail }) {
  const recs = inv.recommended_experiments ?? []
  if (recs.length === 0) return <EmptyState what="No experiments suggested yet." action="Propose explanations first — experiments are derived from hypotheses and evidence gaps." />
  return (
    <div>
      {recs.slice(0, 5).map((e, i) => (
        <div key={i} className="hyp">
          <div className="statement">{e.title}</div>
          <p className="muted" style={{ margin: '4px 0', fontSize: 12.5 }}><b>What to test: </b>{e.what}</p>
          <p className="muted" style={{ margin: '4px 0', fontSize: 12.5 }}><b>Why: </b>{e.why}</p>
          <p className="faint" style={{ margin: '4px 0', fontSize: 12 }}>Supports if: {e.support_if} · Contradicts if: {e.contradict_if}</p>
          <p className="faint" style={{ margin: '4px 0', fontSize: 12 }}>Required: {Array.isArray(e.required_inputs) ? e.required_inputs.join('; ') : (e.required_inputs ?? 'recorded artifacts')}{e.tool ? ` · executable via: ${e.tool}${e.executable_now ? '' : ' (needs input)'}` : ' · manual verification needed'}</p>
        </div>
      ))}
    </div>
  )
}

function ManualHypothesisForm({ inv, disabled, onSub, act }: {
  inv: InvestigationDetail
  disabled: boolean
  onSub: () => Promise<InvestigationDetail | null>
  act: (label: string, fn: () => Promise<unknown>) => void
}) {
  const [text, setText] = useState('')
  const [rationale, setRationale] = useState('')
  const did = !text.trim() || disabled
  return (
    <details style={{ marginTop: 8 }}>
      <summary style={{ cursor: 'pointer', color: 'var(--accent)', fontSize: 13 }}>Add manual hypothesis</summary>
      <form onSubmit={(e) => { e.preventDefault(); if (!did) act('hyp', async () => {
        await api.addHypothesis(inv.id, text, 'manual', rationale || undefined)
        setText(''); setRationale(''); await onSub()
      }) }}>
        <div className="field" style={{ marginTop: 6 }}>
          <label htmlFor={'hytext-' + inv.id}>Falsifiable statement</label>
          <textarea id={'hytext-' + inv.id} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. If fold-4 degradation is real, unlearning fold-4 dates should drop pooled AUC below X." />
        </div>
        <div className="field" style={{ marginTop: 6 }}>
          <label htmlFor={'hyrat-' + inv.id}>Why plausible (optional)</label>
          <input id={'hyrat-' + inv.id} value={rationale} onChange={(e) => setRationale(e.target.value)} />
        </div>
        <button className="primary" style={{ marginTop: 6 }} disabled={did} type="submit" title={text.trim() ? 'Register this falsifiable statement' : 'Enter a hypothesis statement to enable registration'}>
          Register (origin: manual)
        </button>
        {!text.trim() && <p className="faint" style={{ fontSize: 11.5, margin: '4px 0 0' }} role="note">Enter a hypothesis statement to enable registration.</p>}
      </form>
    </details>
  )
}

function FindingForm({ invId, actions, disabled, onDone, act }: {
  invId: string
  actions: Action[]
  disabled: boolean
  onDone: () => Promise<InvestigationDetail | null> | void
  act: (label: string, fn: () => Promise<unknown>) => void
}) {
  const [summary, setSummary] = useState('')
  const [status, setStatus] = useState('confirmed')
  const [evidence, setEvidence] = useState('')
  const ran = actions.filter((a) => a.status === 'ran')
  const sub = () => act('finding', async () => {
    await api.addFinding(invId, summary, status, evidence || undefined)
    setSummary(''); setEvidence('')
    await onDone()
  })
  return (
    <details style={{ marginTop: 8 }}>
      <summary style={{ cursor: 'pointer', color: 'var(--accent)', fontSize: 13 }}>Record a finding</summary>
      <form onSubmit={(e) => { e.preventDefault(); if (!disabled && summary.trim()) sub() }}>
        <div className="row" style={{ marginTop: 6 }}>
          <div className="field">
            <label htmlFor={'fsum-' + invId}>Summary (evidence-backed statement)</label>
            <input id={'fsum-' + invId} value={summary} onChange={(e) => setSummary(e.target.value)} />
          </div>
          <div className="field" style={{ maxWidth: 150, flex: '0 0 150px' }}>
            <label htmlFor={'fst-' + invId}>Status</label>
            <select id={'fst-' + invId} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="confirmed">confirmed</option>
              <option value="likely">likely</option>
              <option value="rejected">rejected</option>
              <option value="unresolved">unresolved</option>
            </select>
          </div>
          <div className="field" style={{ maxWidth: 200 }}>
            <label htmlFor={'fev-' + invId}>Evidence action</label>
            <select id={'fev-' + invId} value={evidence} onChange={(e) => setEvidence(e.target.value)}>
              <option value="">— none (unverified) —</option>
              {ran.map((a) => <option key={a.id} value={a.id}>#{a.seq} {a.tool_name}</option>)}
            </select>
          </div>
        </div>
        <button className="primary" style={{ marginTop: 6 }} disabled={disabled || !summary.trim()} type="submit" title={summary.trim() ? 'Record this evidence-backed finding' : 'Enter a finding summary to enable recording'}>
          Record finding
        </button>
        {!summary.trim() && <p className="faint" style={{ fontSize: 11.5, margin: '4px 0 0' }} role="note">Enter a finding summary to enable recording.</p>}
        {ran.length === 0 && <p className="faint" style={{ fontSize: 11.5, margin: '4px 0 0' }} role="note">No recorded diagnostic to cite yet — run a diagnostic before linking evidence.</p>}
      </form>
    </details>
  )
}

function kindClass(kind: string): string {
  const k = kind.toLowerCase()
  if (/fail|reject|regress|error|denied/.test(k)) return 'k-bad'
  if (/complete|support|confirm|pass|^ok|verif|resolv/.test(k)) return 'k-ok'
  if (/warn|unresolv|missing|budget/.test(k)) return 'k-warn'
  return 'k-info'
}

/** Compact timeline: strictly-consecutive same-kind runs of 3+ collapse;
 *  per-event detail is always one click away, never inline. */
function TimelineGroups({ events }: { events: TimelineEvent[] }) {
  const groups: TimelineEvent[][] = []
  for (const e of events) {
    const last = groups[groups.length - 1]
    if (last && last[0].kind === e.kind) last.push(e)
    else groups.push([e])
  }
  return (
    <ul className="tl">
      {groups.map((g, gi) => g.length >= 3 ? (
        <li key={`${g[0].seq}-${gi}`} className={kindClass(g[0].kind)}>
          <span className="tlt"><b>{g.length} × {g[0].kind}</b> — {g[0].title.slice(0, 80)}</span>
          <span className="tltime">#{g[0].seq}–#{g[g.length - 1].seq}</span>
          <details>
            <summary>expand {g.length} events</summary>
            <ul className="tl">
              {g.map((e, ei) => <TimelineRow key={`${e.seq}-${ei}`} e={e} />)}
            </ul>
          </details>
        </li>
      ) : (
        <Fragment key={`${g[0].seq}-${gi}`}>{g.map((e, ei) => <TimelineRow key={`${e.seq}-${ei}`} e={e} />)}</Fragment>
      ))}
    </ul>
  )
}

function TimelineRow({ e }: { e: TimelineEvent }) {
  return (
    <li className={kindClass(e.kind)}>
      <span className="tlt">{e.title}</span>
      <span className="tltime">{formatTimelineTime(e.created_at)} · {e.kind} · #{e.seq}</span>
      {e.detail && (
        <details>
          <summary>detail</summary>
          <div className="tl-detail">{e.detail}</div>
        </details>
      )}
    </li>
  )
}

function ReportSection({ inv, busy, run }: {
  inv: InvestigationDetail
  busy: boolean
  run: () => void
}) {
  const r = inv.final_report as FinalReport | null
  const hasEvidence = inv.latest_findings.length > 0 || (inv.actions?.length ?? 0) > 0 || (inv.hypotheses?.length ?? 0) > 0
  if (!r) {
    if (inv.status === 'complete') return null
    return (
      <div>
        <EmptyState what="No final report yet."
          action={hasEvidence ? 'Generate one from the recorded evidence.' : 'Run diagnostics first; the report needs evidence.'} />
        {hasEvidence && (
          <button className="primary" disabled={busy} onClick={run}>
            {busy ? 'Generating…' : 'Generate final report'}
          </button>
        )}
      </div>
    )
  }
  return (
    <div className="report">
      <div className="actionsrow" style={{ marginBottom: 12 }}>
        <span title="Whether the workflow finished"><Pill status={r.execution_status ?? 'complete'} /></span>
        {r.scientific_assessment && <span title="What the evidence establishes"><Pill status={r.scientific_assessment.status} /></span>}
        <span className="faint">generated {String(r.generated_at).slice(0, 19).replace('T', ' ')} · deterministic from recorded evidence</span>
      </div>
      {r.scientific_assessment && <Note kind="accent">Scientific assessment: {r.scientific_assessment.status} — {r.scientific_assessment.explanation}</Note>}
      {r.main_interpretation && (
        <div className="section">
          <h3>Main interpretation — in plain language</h3>
          <p>{r.main_interpretation}</p>
        </div>
      )}
      {r.investigation_scope && (
        <div className="section">
          <h3>Investigation scope — what was examined</h3>
          <ScopeList label="Examined" items={r.investigation_scope.examined ?? []} empty="none recorded" />
          <ScopeList label="Stored but not examined" items={r.investigation_scope.stored_not_examined ?? []} empty="none" />
          <ScopeList label="Missing" items={r.investigation_scope.missing ?? []} empty="none recorded" />
        </div>
      )}
      {r.candidate_explanations && ((r.candidate_explanations.machine ?? []).length > 0 || (r.candidate_explanations.manual ?? []).length > 0) && (
        <div className="section">
          <h3>Candidate explanations</h3>
          {(r.candidate_explanations.machine ?? []).length > 0 && (
            <><h4>Machine-proposed (suspicion only)</h4><ul>{(r.candidate_explanations.machine ?? []).map((h) => <li key={h.hypothesis_id}>{h.text} <span className="faint">({h.status})</span></li>)}</ul></>
          )}
          {(r.candidate_explanations.manual ?? []).length > 0 && (
            <><h4>Manually registered</h4><ul>{(r.candidate_explanations.manual ?? []).map((h) => <li key={h.hypothesis_id}>{h.text} <span className="faint">({h.status})</span></li>)}</ul></>
          )}
        </div>
      )}

      <div className="section">
        <h3>Confirmed observations — tool-established facts</h3>
        {r.confirmed.length ? (
          <ul>{r.confirmed.map((c, i) => (
            <li key={i}>{c.summary}
              {c.evidence_action_id && <span className="evref" style={{ marginLeft: 6 }}>→ {short(c.evidence_action_id)}</span>}
            </li>
          ))}</ul>
        ) : <p className="muted">None recorded — nothing was directly established by tool output.</p>}
      </div>

      <div className="section">
        <h3>Supported / likely explanations</h3>
        {r.likely.length || r.supported_hypotheses.length ? (
          <ul>
            {r.likely.map((c, i) => <li key={'l' + i}>{c.summary}</li>)}
            {r.supported_hypotheses.map((h) => (
              <li key={h.hypothesis_id}>{h.text}
                {h.evidence_refs.length > 0 && (
                  <span className="evref" style={{ marginLeft: 6 }}>
                    evidence: {h.evidence_refs.map((e) => short(e.action_id)).join(', ')}
                  </span>
                )}
              </li>
            ))}
          </ul>
        ) : <p className="muted">No explanation currently rises to "supported" on the recorded evidence.</p>}
      </div>

      <div className="section">
        <h3>Rejected explanations</h3>
        {r.rejected.length ? (
          <ul>{r.rejected.map((x, i) => (
            <li key={i}>
              {x.summary ?? x.text}
              {x.evidence_refs?.map((e) => (
                <span key={e.action_id} className="evref" style={{ marginLeft: 6 }}>
                  {e.relation} → {short(e.action_id)}
                </span>
              ))}
            </li>
          ))}</ul>
        ) : <p className="muted">No hypothesis has been contradicted by recorded evidence.</p>}
      </div>

      <div className="section">
        <h3>Unresolved questions</h3>
        {r.unresolved.length ? (
          <ul>{r.unresolved.map((u) => (
            <li key={u.hypothesis_id}>{u.text} <span className="faint">({u.origin}, still {u.status})</span></li>
          ))}</ul>
        ) : <p className="muted">All registered hypotheses reached a verdict.</p>}
      </div>

      <div className="section">
        <h3>Limitations</h3>
        <ul>{r.limitations.map((l, i) => <li key={i} className="muted">{l}</li>)}</ul>
      </div>

      <div className="section">
        <h3>Recommended next experiments</h3>
        <ul>{r.recommended_next.map((n, i) => (
          <li key={i}>{n.action}{n.for && <span className="faint"> (for {short(n.for)})</span>}</li>
        ))}</ul>
      </div>

      <div className="section">
        <h3>Evidence ledger — every action on record</h3>
        <div className="tablewrap">
          <table>
            <thead><tr><th>#</th><th>Tool</th><th>Status</th><th>Key result figures</th></tr></thead>
            <tbody>
              {r.evidence_performed.map((e) => (
                <tr key={e.action_id}>
                  <td>{e.seq}</td>
                  <td><code className="inline">{e.tool}</code></td>
                  <td><Pill status={e.status} /></td>
                  <td>{e.error ? <span style={{ color: 'var(--bad)' }}>{e.error}</span>
                    : <span className="muted">{resultDigest(e.result_digest)}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <Note>{r.scope_note}</Note>
    </div>
  )
}

/** Drop duplicate scope entries where one path subsumes another
 *  (e.g. a relative path repeated as an absolute path for the same file). */
function dedupeScopePaths(list: string[]): string[] {
  const norm = (s: string) => s.replace(/\\/g, '/').toLowerCase()
  const out: string[] = []
  for (const s of list.map((x) => String(x).trim()).filter(Boolean)) {
    const n = norm(s)
    if (out.some((o) => norm(o) === n)) continue
    if (out.some((o) => { const on = norm(o); return on !== n && on.endsWith('/' + n) })) continue
    for (let i = out.length - 1; i >= 0; i--) {
      const on = norm(out[i])
      if (on !== n && n.endsWith('/' + on)) out.splice(i, 1)
    }
    out.push(s)
  }
  return out
}

function ScopeList({ label, items, empty }: { label: string; items: string[]; empty: string }) {
  const deduped = dedupeScopePaths(items)
  return (
    <div style={{ margin: '6px 0' }}>
      <span className="muted" style={{ fontSize: 12 }}>{label}: </span>
      {deduped.length === 0 ? (
        <span className="faint" style={{ fontSize: 12 }}>{empty}</span>
      ) : (
        <span className="hypchips">
          {deduped.map((s, i) => (
            <span key={i} className="pathshort" title={s} style={{ border: '1px solid var(--line)', borderRadius: 6, padding: '1px 7px' }}>
              {shortPath(s)}
            </span>
          ))}
        </span>
      )}
    </div>
  )
}

function resultDigest(d?: Record<string, unknown>): string {
  if (!d) return '—'
  const out: string[] = []
  for (const [k, v] of Object.entries(d)) {
    if (v == null || k.startsWith('_') || k === 'ok') continue
    const shown = typeof v === 'number'
      ? (Number.isInteger(v) ? v.toLocaleString() : fmtNum(v))
      : (() => { const s = String(v); return s.length > 40 && /[/\\]/.test(s) ? shortPath(s) : s.slice(0, 40) })()
    out.push(`${k}=${shown}`)
    if (out.length >= 4) break
  }
  return out.join(' · ') || '—'
}
