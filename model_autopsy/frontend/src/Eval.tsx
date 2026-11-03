// Independent Evaluation — Milestone 4 dashboard section.
// Benchmark projects, runs, scorecards with per-dimension drill-down,
// evidence tracing (conclusion -> hypothesis -> experiment -> numbers),
// and blind human review. Consistent with the ResearchLab look.
import { useState } from 'react'
import { api, useLoading } from './api'
import { EmptyState, ErrorState, Loading, Pill } from './ui'

interface EvalProject {
  id: string; family: string; name: string; task: string; brief: string
}

interface Manifest {
  run_id: string; eval_version: string; max_experiments?: number
  aggregate: { n: number; mean_overall: number; verdicts: Record<string, number> }
  results: { project: string; verdict: string; overall: number; elapsed_s: number }[]
}

interface Scorecard {
  project: string; verdict: string; overall: number | null; note: string
  false_positive: boolean
  dimensions: Record<string, number | null>; weights: Record<string, number>
  rubric_version?: string; notes?: Record<string, string>; unavailable?: string[]
}

interface RunRecord {
  project: string; investigation_id: string; elapsed_s: number
  report: {
    executive_summary: string
    confirmed_findings: { hypothesis_id: string; title: string }[]
    rejected_hypotheses: { hypothesis_id: string; title: string }[]
    inconclusive: { hypothesis_id: string; title: string }[]
    experiments: { experiment_id: string; tool: string; summary: string; numbers?: Record<string, unknown> }[]
    verification: { hypothesis_id?: string; verdict?: string; tool?: string; action_id?: string; result?: string; planned?: boolean; reason?: string; detail?: string }[]
    limitations: string[]
  }
  scorecard: Scorecard
  human_review: { review: null | { blind_verdict: string; revealed: boolean; post_reveal_assessment?: string } }
}

function VerdictPill({ v }: { v: string }) {
  const ok = v === 'correct' || v === 'correct-null'
  const warn = v === 'partial' || v === 'inconclusive'
  return <span className={'pill ' + (ok ? 'ok' : warn ? 'warn' : 'bad')}>{v}</span>
}

export function EvalPage() {
  const { data: projData, error: projErr } = useLoading<{ projects: EvalProject[] }>(() => api.evalProjects(), [])
  const { data: runsData, error: runsErr, reload: reloadRuns } = useLoading<{ runs: Manifest[] }>(() => api.evalRuns(), [])
  const [running, setRunning] = useState(false)
  const [runErr, setRunErr] = useState('')
  const [selRun, setSelRun] = useState<string | null>(null)
  const [selProj, setSelProj] = useState<string | null>(null)

  async function runAll() {
    setRunning(true); setRunErr('')
    try {
      const r = await api.evalRunAll()
      setSelRun(r.run_id); setSelProj(null); reloadRuns()
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div>
      <h2>Independent Evaluation — investigator benchmark</h2>
      <p className="muted">
        This page grades the <b>investigator itself</b> on unfamiliar projects with concealed failure
        mechanisms (ground truth sealed, mechanism-level scoring). It is not your investigation history —
        user uploads and case-study runs live under <b>History</b> and <b>New Investigation</b>.
        Verdicts: correct / partial / incorrect / unsupported / inconclusive / correct-null.
      </p>
      <div className="row">
        <button className="primary" disabled={running} onClick={runAll}>
          {running ? 'Running offline evaluation…' : 'Run full evaluation (offline)'}
        </button>
        <button className="ghost" onClick={reloadRuns}>Refresh</button>
      </div>
      {runErr && <p className="error">{runErr}</p>}
      {runsErr && <ErrorState error={runsErr} onRetry={reloadRuns} />}

      <section className="card">
        <h3>Benchmark projects ({projData?.projects.length ?? '…'})</h3>
        {projErr && <ErrorState error={projErr} />}
        <ul>
          {(projData?.projects ?? []).map((p) => (
            <li key={p.id}>
              <strong>{p.name}</strong> <span className="muted">· {p.family} · {p.task}</span>
              <br /><span className="muted">{p.brief}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Evaluation runs</h3>
        {(runsData?.runs.length ?? 0) === 0 && <EmptyState what="No evaluation runs yet." action="Run the full offline evaluation above." />}
        <ul>
          {(runsData?.runs ?? []).map((m) => (
            <li key={m.run_id}>
              <button className="link" onClick={() => { setSelRun(m.run_id); setSelProj(null) }}>
                {m.run_id}
              </button>{' '}
              <span className="muted">
                {m.eval_version} · n={m.aggregate.n} · mean={m.aggregate.mean_overall} ·{' '}
                {Object.entries(m.aggregate.verdicts).map(([k, v]) => `${k}:${v}`).join(' ')}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {selRun && <RunDetail runId={selRun} selProj={selProj} onSelect={setSelProj} />}

      <LivePilotSection />
    </div>
  )
}

function LivePilotSection() {
  const { data, error, reload } = useLoading<{ runs: { run_id: string; status: string; eval_project: string; model: string }[]; note: string }>(() => api.liveRuns(), [])
  const [open, setOpen] = useState<string | null>(null)
  return (
    <section className="card">
      <h3>Live Meta pilot (read-only)</h3>
      <p className="muted">Live investigations are CLI-launched only — the dashboard never spends. {data?.note ?? ''}</p>
      {error && <ErrorState error={error} onRetry={reload} />}
      {(data?.runs.length ?? 0) === 0 && <EmptyState what="No live pilot runs preserved yet." action="Live pilots are created by the authorized CLI, not from this UI." />}
      <ul>
        {(data?.runs ?? []).map((r) => (
          <li key={r.run_id}>
            <button className="link" onClick={() => setOpen(open === r.run_id ? null : r.run_id)}>{r.run_id}</button>{' '}
            <Pill status={r.status} /> <span className="muted">{r.eval_project} · {r.model}</span>
            {open === r.run_id && <LiveRunDetail runId={r.run_id} />}
          </li>
        ))}
      </ul>
    </section>
  )
}

function LiveRunDetail({ runId }: { runId: string }) {
  const { data, error } = useLoading<{ status: string; eval_project: string; budget: { cost_usd: { spent: number; cap: number }; tokens: { total: number; cap: number }; attempts: number[]; rounds: number[] } | null; artifacts: Record<string, string>; required_evidence_present: Record<string, boolean> }>(() => api.liveRun(runId), [runId])
  if (error) return <ErrorState error={error} />
  if (!data) return <Loading what="Loading live run" />
  return (
    <div style={{ marginTop: 8 }}>
      <p>Status <Pill status={data.status} /> · project {data.eval_project}</p>
      {data.budget && (
        <p className="muted">Cost ${data.budget.cost_usd.spent} / ${data.budget.cost_usd.cap} · tokens {data.budget.tokens.total} / {data.budget.tokens.cap} · attempts {data.budget.attempts[0]} · rounds {data.budget.rounds[0]}</p>
      )}
      <p className="muted">Artifacts: {Object.keys(data.artifacts).join(', ')}</p>
      <p className="muted">Evidence present: {Object.entries(data.required_evidence_present).map(([k, v]) => `${k}:${v}`).join(' ')}</p>
    </div>
  )
}

function RunDetail({ runId, selProj, onSelect }: { runId: string; selProj: string | null; onSelect: (p: string | null) => void }) {
  const { data, error, reload } = useLoading<Manifest>(() => api.evalRun(runId), [runId])
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading run" />
  return (
    <section className="card">
      <h3>Run {data.run_id}</h3>
      <ul>
        {data.results.map((r) => (
          <li key={r.project}>
            <button className="link" onClick={() => onSelect(r.project)}>{r.project}</button>{' '}
            <VerdictPill v={r.verdict} />{' '}
            <span className="muted">overall {r.overall} · {r.elapsed_s}s</span>
          </li>
        ))}
      </ul>
      {selProj && <ProjectDrill runId={runId} project={selProj} />}
    </section>
  )
}

function ProjectDrill({ runId, project }: { runId: string; project: string }) {
  const { data, error, reload } = useLoading<RunRecord>(() => api.evalResult(runId, project), [runId, project])
  const [reviewer, setReviewer] = useState('')
  const [notes, setNotes] = useState('')
  const [msg, setMsg] = useState('')
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading investigation" />
  const sc = data.scorecard
  const rev = data.human_review.review

  async function blind(v: string) {
    setMsg('')
    try {
      await api.evalBlind(runId, project, reviewer || 'anonymous', v, notes)
      setMsg('Blind verdict recorded.')
      reload()
    } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
  }
  async function reveal() {
    setMsg('')
    try {
      await api.evalReveal(runId, project, notes)
      setMsg('Revealed; assessment recorded.')
      reload()
    } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <div style={{ marginTop: 12 }}>
      <h4>{project} <VerdictPill v={sc.verdict} /> <span className="muted">overall {sc.overall ?? 'insufficient data'}</span></h4>
      <p className="muted">rubric {sc.rubric_version ?? 'v2'}{sc.false_positive ? ' · FALSE POSITIVE flagged' : ''}</p>
      <p className="muted">{sc.note}</p>
      <h4>Dimensions (weights in parentheses)</h4>
      <ul>
        {Object.entries(sc.dimensions).map(([k, v]) => (
          <li key={k}>{k}: <strong>{v ?? 'unavailable'}</strong> <span className="muted">(w={sc.weights[k] ?? '—'}){sc.notes?.[k] ? ` — ${sc.notes[k]}` : ''}</span></li>
        ))}
      </ul>
      {(sc.unavailable?.length ?? 0) > 0 && <p className="muted">Unavailable (not measured, not zero): {sc.unavailable!.join(', ')}</p>}
      {sc.dimensions['discovery'] != null && Number(sc.dimensions['discovery']) > 0 && (sc.dimensions['confirmation'] == null || Number(sc.dimensions['confirmation']) < 1) && (
        <p className="muted">Discovery without confirmation: the mechanism was identified but not confirmed — discovery credit is not confirmation. See verification trail below.</p>
      )}
      <h4>Verification trail (executed vs planned)</h4>
      {(data.report.verification?.length ?? 0) === 0 && <p className="muted">No verification recorded.</p>}
      <ul>
        {(data.report.verification ?? []).map((vf, i) => (
          <li key={i}>
            {vf.action_id ? `executed: ${vf.tool ?? '?'} → ${vf.result ?? 'recorded'}` : vf.planned ? `planned but unexecuted: ${vf.tool ?? '?'}` : `not executed: ${vf.reason ?? 'no reason recorded'}`}
            {vf.detail && <span className="muted"> — {vf.detail}</span>}
          </li>
        ))}
      </ul>
      <h4>Evidence trail (conclusion → experiment → numbers)</h4>
      <p className="muted">{data.report.executive_summary}</p>
      <ul>
        {data.report.confirmed_findings.map((f) => <li key={f.hypothesis_id}>confirmed: {f.title}</li>)}
        {data.report.experiments.map((e) => (
          <li key={e.experiment_id}>
            [{e.tool}] {e.summary}
            {e.numbers && (
              <span className="muted"> · {Object.entries(e.numbers).slice(0, 4).map(([k, v]) =>
                `${k}=${typeof v === 'number' ? (Number.isInteger(v) ? v.toLocaleString() : v.toFixed(4)) : String(v).slice(0, 40)}`).join(' · ')}</span>
            )}
          </li>
        ))}
      </ul>
      <h4>Human review {rev ? <Pill status={rev.revealed ? 'complete' : 'investigating'} /> : <span className="muted">(none recorded)</span>}</h4>
      {!rev && (
        <div className="row">
          <input placeholder="reviewer id" value={reviewer} onChange={(e) => setReviewer(e.target.value)} />
          <input placeholder="blind notes (ground truth hidden)" value={notes} onChange={(e) => setNotes(e.target.value)} style={{ minWidth: 260 }} />
          {['defensible', 'questionable', 'not_defensible', 'cannot_tell'].map((v) => (
            <button key={v} className="ghost" onClick={() => blind(v)}>Blind: {v}</button>
          ))}
        </div>
      )}
      {rev && !rev.revealed && (
        <div className="row">
          <input placeholder="post-reveal assessment" value={notes} onChange={(e) => setNotes(e.target.value)} style={{ minWidth: 260 }} />
          <button className="primary" onClick={reveal}>Reveal ground truth + record assessment</button>
        </div>
      )}
      {rev?.revealed && <p className="muted">Blind: {rev.blind_verdict} · Post-reveal: {rev.post_reveal_assessment}</p>}
      {msg && <p className="muted">{msg}</p>}
    </div>
  )
}
