// Investigation workspace — the centerpiece page.
// Composition: sticky context rail + evidence workspace + hypothesis panel;
// below them, the honest timeline and the evidence-linked final report.
import { useEffect, useState } from 'react'
import {
  Action, api, EvidenceRef, FinalReport, formatTimelineTime, Hypothesis,
  InvestigationDetail, TimelineEvent, useLoading,
} from './api'
import { EvidenceCard, EmptyState, ErrorState, KV, Loading, Note, Pill, ResultRenderer, fmtNum } from './ui'
import { TimelineFunnelChart } from './charts'

function short(id: string): string { return id.slice(0, 8) }

export default function Workspace({ id, onBack }: { id: string; onBack: () => void }) {
  const { data: invBasis, error, reload } = useLoading<InvestigationDetail>(() => api.getInvestigation(id), [id])
  const [events, setEvents] = useState<TimelineEvent[] | null>(null)
  const [timelineError, setTimelineError] = useState('')
  const [busy, setBusy] = useState('') // '' | 'ctx' | 'tool' | 'meta' | 'report' | ...
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

      <div className="workspace">
        {/* ---------- main column ---------- */}
        <div className="col-main">
          <header>
            <div className="kicker">{isML ? 'ML model autopsy' : 'Software autopsy'} · {short(inv.id)}</div>
            <h1>{inv.title}</h1>
            <p className="sub" style={{ marginBottom: 10 }}>{inv.question}</p>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'baseline' }}>
              <Pill status={inv.status} />
              <span className="faint">created {inv.created_at?.slice(0, 19).replace('T', ' ')}</span>
            </div>
          </header>

          <div className={'budgetbar' + (hot ? ' hot' : '')}>
            <div className="meter" role="img"
              aria-label={`Tool-call budget: ${inv.tool_call_count} of ${inv.max_tool_calls} used.`}>
              <div className="fill" style={{ width: `${budgetPct}%` }} />
            </div>
            <span className="nums">{inv.tool_call_count}/{inv.max_tool_calls} tool calls</span>
            <span className="nums">{inv.iteration_count}/{inv.max_iterations} iterations</span>
          </div>

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
              <h3>Latest diagnostic — real output, recorded</h3>
              <ResultCard action={lastToolOutput} />
            </section>
          )}

          <section className="section" aria-label="Evidence workspace">
            <h3>Evidence workspace — {inv.actions?.length ?? 0} recorded actions</h3>
            {(inv.actions?.length ?? 0) > 0 ? (
              [...inv.actions].reverse().slice(0, 8).map((a) => (
                <ResultCard key={a.id} action={a} />
              ))
            ) : (
              <EmptyState what="No diagnostics have run yet."
                action="Load context above, then run a diagnostic or a Meta turn." />
            )}
            {(inv.actions?.length ?? 0) > 8 && (
              <p className="faint">Showing the 8 most recent — the full record lives in the timeline and report evidence ledger.</p>
            )}
          </section>

          <section className="section" aria-label="Findings">
            <h3>Findings — confirmed / likely / rejected / unresolved</h3>
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

          <section className="section hs-section" aria-label="Timeline">
            <h3>Timeline — every event on record</h3>
            {timelineError && <Note kind="bad">{timelineError}</Note>}
            {events && events.length > 0 && (
              <>
                <TimelineFunnelChart items={events.map((e) => ({
                  seq: e.seq,
                  kind: e.kind,
                  label: `${formatTimelineTime(e.created_at)}  ${e.title}`,
                }))} />
                <div className="timeline">
                  {events.map((e) => (
                    <div key={e.seq} className={'tl-item k-' + e.kind.replace(':', '-')}>
                      <div className="tl-when">{formatTimelineTime(e.created_at)}
                        <span className="tl-kind">{e.kind} · #{e.seq}</span>
                      </div>
                      <div className="tl-title">{e.title}</div>
                      {e.detail && <div className="tl-detail">{e.detail}</div>}
                    </div>
                  ))}
                </div>
              </>
            )}
            {events && events.length === 0 && <EmptyState what="Timeline is empty." />}
          </section>

          <section className="section hs-section" aria-label="Final report">
            <ReportSection inv={inv} busy={busy !== ''} run={() => act('report', async () => {
              await api.generateReport(inv.id)
              setActOk('Final report generated deterministically from recorded evidence.')
            })} />
          </section>
        </div>

        {/* ---------- side rail ---------- */}
        <div className="col-side">
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

              <details style={{ width: '100%' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--accent)', fontSize: 13.5, margin: '4px 0 6px' }}>
                  Run diagnostic (manual)
                </summary>
                <ManualToolPicker isML={isML} disabled={busy !== '' || hot}
                  contextReady={inv.status !== 'created'} onRun={runInlineTool} hot={hot} />
              </details>

              <details style={{ width: '100%' }}>
                <summary style={{ cursor: 'pointer', color: 'var(--accent)', fontSize: 13.5, margin: '4px 0 6px' }}>
                  Run Meta turn (AI-assisted)
                </summary>
                <MetaPanel invId={inv.id} disabled={busy !== '' || hot} act={act} verifyMeta={() => act('meta', async () => {
                  const r = await api.metaTurn(id, 3)
                  if (r.status === 'ok') setActOk(`Meta turn completed: ${r.tool_calls?.length ?? 0} validated tool call(s); interpretation recorded on the timeline.`)
                  else if (r.status === 'meta_unavailable') setActErr('Meta unavailable: ' + (r.error ?? 'key not configured'))
                  else setActErr('Meta turn ended early: ' + r.status)
                })} />
              </details>
            </div>
            {(inv.actions?.length ?? 0) < 1 && (
              <p className="faint" style={{ marginTop: 8, fontSize: 12 }}>
                Diagnostics unlock after context loads; Meta turns are bounded by the same 12-call budget.
              </p>
            )}
          </div>

          <div className="hud" aria-label="Investigation context">
            <h3>Investigation context</h3>
            <KV items={[
              ['Mode', inv.mode],
              ['Status', <Pill status={inv.status} />],
              ['Objective', inv.question],
              [isML ? 'Dataset' : 'Workspace',
                context ? (String(context.path ?? context.source ?? context.workspace_root ?? context.filename ?? '')
                  ? <code className="inline">{String(context.path ?? context.source ?? context.workspace_root ?? context.filename)}</code>
                  : <span className="faint">context loaded — no file reference recorded</span>)
                  : <span className="faint">not loaded — use Load context</span>],
            ]} />
          </div>

          <div className="hud" aria-label="Hypotheses">
            <h3>Hypotheses ({inv.hypotheses?.length ?? 0})</h3>
            <HypothesisList inv={inv} actions={inv.actions ?? []} busy={busy !== ''} onChanged={refresh} />
            <ManualHypothesisForm inv={inv} disabled={busy !== ''} onSub={refresh} act={act} />
          </div>

          <div className="hud" aria-label="Mode legend">
            <h3>How evidence is graded</h3>
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12.5, color: 'var(--muted)', listStyle: 'disc' }}>
              <li><b style={{ color: 'var(--ok)' }}>confirmed</b> — directly from a recorded tool output</li>
              <li><b style={{ color: 'var(--warn)' }}>likely</b> — supported but not proven beyond recorded evidence</li>
              <li><b style={{ color: 'var(--accent)' }}>rejected / unresolved</b> — contradicted by, or still open to, evidence</li>
              <li>Meta's confidence is an <i>uncalibrated model self-report</i>, kept separate from measured metrics</li>
            </ul>
          </div>
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

function ResultCard({ action }: { action: Action }) {
  return (
    <EvidenceCard
      action={action}
      docket={(action.result as Record<string, unknown> | null)?.source
        ? String((action.result as Record<string, unknown>).source) : undefined}>
      <ResultRenderer action={action} />
    </EvidenceCard>
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
    { name: 'dataset_validation', label: 'Validate a custom CSV…', args: null },
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
  if (!contextReady) {
    return <Note kind="warn">Load context first — diagnostics resolve paths against the loaded workspace/dataset.</Note>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {hot && <Note kind="warn">Tool-call budget exhausted — 12/12 used. This is a recorded, honest stop.</Note>}
      {base.map((t) => (
        <div key={t.name} style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
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
          <button className="ghost" disabled={disabled || (t.args === null && (t.name === 'dataset_validation' ? !customPath.trim() : !fileHead.trim()))}
            onClick={() => onRun(t.name, t.args === null
              ? (t.name === 'dataset_validation' ? { predictions_path: customPath } : { file_path: fileHead })
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

function HypothesisList({ inv, actions, busy, onChanged }: {
  inv: InvestigationDetail
  actions: Action[]
  busy: boolean
  onChanged: () => Promise<InvestigationDetail | null>
}) {
  const [openId, setOpenId] = useState<string | null>(null)
  const hypos = inv.hypotheses ?? []
  if (hypos.length === 0) {
    return (
      <EmptyState what="No hypotheses yet."
        action="Meta turns register them through a validated tool; or add your own below." />
    )
  }
  return (
    <div>
      {hypos.map((h) => (
        <div key={h.id} className={'hyp ' + (h.status === 'supported' ? 'supported'
          : h.status === 'rejected' ? 'rejected'
            : (h.status === 'testing' || h.status === 'investigating') ? 'testing' : '')}>
          <div className="statement">{h.text}</div>
          <div className="foot">
            <span className="origin">{h.source === 'meta' ? 'origin: meta' : 'origin: manual'}</span>
            <Pill status={h.status} />
            {h.confidence !== null && (
              <span title="Uncalibrated model self-report — not a statistical confidence interval">
                conf {h.confidence}%<sup>*</sup>
              </span>
            )}
            <EvidenceChipList refs={h.evidence_refs ?? []} actions={actions} />
            <button className="link" onClick={() => setOpenId(openId === h.id ? null : h.id)}>
              {openId === h.id ? 'hide controls' : 'manage'}
            </button>
          </div>
          {h.rationale && <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>{h.rationale}</div>}
          {h.predicted_observation && (
            <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>
              <b>predicted observation:</b> {h.predicted_observation}
            </div>
          )}
          {h.confidence_note && (
            <div className="faint" style={{ fontSize: 12, marginTop: 4 }}>
              <b>confidence meaning:</b> {h.confidence_note}
            </div>
          )}
          {openId === h.id && (
            <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {!busy && h.status !== 'rejected' && h.status !== 'supported' ? (
                <div className="actionsrow">
                  <button className="ghost" onClick={async () => {
                    await api.patchHypothesis(h.id, { status: 'supported' }); onChanged()
                  }}>Mark supported</button>
                  <button className="ghost" onClick={async () => {
                    await api.patchHypothesis(h.id, { status: 'rejected' }); onChanged()
                  }}>Mark rejected</button>
                  {actions.some((a) => a.status === 'ran') && (
                    <LinkEvidenceForm h={h} actions={actions.filter((a) => a.status === 'ran')}
                      onSub={onChanged} />
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      ))}
      <p className="faint" style={{ fontSize: 11.5, marginTop: 4 }}>
        <sup>*</sup> Any displayed percentage is what the model or operator recorded — it is NOT an
        interval or a probability. Trust only the linked evidence.
      </p>
    </div>
  )
}

function EvidenceChipList({ refs, actions }: { refs: EvidenceRef[]; actions: Action[] }) {
  if (!refs?.length) return null
  return (
    <span className="evref" style={{ fontSize: 11 }}>
      {refs.map((r, i) => {
        const a = actions.find((x) => x.id === r.action_id)
        return (
          <span key={i} style={{ marginRight: 6 }}>
            {r.relation === 'supports' ? '▲' : '▼'} {a ? `#${a.seq} ${a.tool_name}` : short(r.action_id)}
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
        <button className="primary" style={{ marginTop: 6 }} disabled={did} type="submit">
          Register (origin: manual)
        </button>
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
        <button className="primary" style={{ marginTop: 6 }} disabled={disabled || !summary.trim()} type="submit">
          Record finding
        </button>
      </form>
    </details>
  )
}

function ReportSection({ inv, busy, run }: {
  inv: InvestigationDetail
  busy: boolean
  run: () => void
}) {
  const r = inv.final_report as FinalReport | null
  if (!r) {
    if (inv.status === 'complete') return null
    return (
      <div>
        <EmptyState what="No final report yet."
          action={inv.latest_findings.length ? 'Generate one from the recorded evidence.' : 'Run diagnostics first; the report needs evidence.'} />
        {inv.latest_findings.length > 0 && (
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
        <Pill status="complete" />
        <span className="faint">generated {String(r.generated_at).slice(0, 19).replace('T', ' ')} · deterministic from recorded evidence</span>
      </div>

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

function resultDigest(d?: Record<string, unknown>): string {
  if (!d) return '—'
  const out: string[] = []
  for (const [k, v] of Object.entries(d)) {
    if (v == null) continue
    out.push(`${k}=${typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString() : fmtNum(v)) : String(v).slice(0, 40)}`)
    if (out.length >= 4) break
  }
  return out.join(' · ') || '—'
}
