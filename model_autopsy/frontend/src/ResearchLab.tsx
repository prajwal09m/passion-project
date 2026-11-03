// Research Lab — autonomous investigation workspace (Milestone 3).
// 8 sections: overview / hypotheses / experiments / evidence /
// verification / model behavior / efficiency / forensic report.
import { useState } from 'react'
import { api, useLoading, type ResearchState } from './api'
import { EmptyState, ErrorState, Loading, Pill } from './ui'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      {children}
    </section>
  )
}

export function ResearchLabPanel({ id }: { id: string }) {
  const { data, error, reload } = useLoading<ResearchState>(() => api.researchState(id), [id])
  const [running, setRunning] = useState(false)
  const [failed, setFailed] = useState('')

  async function run() {
    setRunning(true)
    setFailed('')
    try {
      await api.researchRun(id)
      reload()
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading research state" />
  const stages = data.stages || {}
  const hyps = data.hypotheses || []
  const report = data.report

  return (
    <div>
      <div className="row">
        <button className="primary" disabled={running} onClick={run}>
          {running ? 'Running autonomous cycle…' : 'Run autonomous cycle (offline)'}
        </button>
        <button className="ghost" onClick={reload}>Refresh</button>
      </div>
      {failed && <p className="error">{failed}</p>}
      {Object.keys(stages).length === 0 && !report && (
        <EmptyState what="No autonomous run yet." action="Run the offline cycle: recon → hypotheses → experiments → review → report." />
      )}
      <Section title="1. Research overview">
        <p className="muted">Stages completed: {Object.keys(stages).join(', ') || '—'}</p>
        {report && <p>{report.executive_summary}</p>}
      </Section>
      <Section title="2. Hypothesis workspace">
        {hyps.length === 0 ? <p className="muted">No hypotheses yet.</p> : (
          <ul>
            {hyps.map((h) => (
              <li key={h.id}>
                <strong>{h.title}</strong> <Pill status={h.status} />{' '}
                <span className="muted">priority {h.priority} · {h.diagnostics.join(', ')}</span>
                <br /><span className="muted">{h.mechanism}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section title="3. Experiment laboratory">
        {report ? (
          <ul>
            {report.experiments.map((e) => (
              <li key={e.experiment_id}>{e.tool} — {e.summary} <Pill status={e.status} /></li>
            ))}
          </ul>
        ) : <p className="muted">No experiments yet.</p>}
      </Section>
      <Section title="4. Evidence explorer">
        <p className="muted">Evidence lives in durable records by experiment id; summaries carry references, not blobs.</p>
        {report && report.experiments.map((e) => (
          <p key={e.experiment_id} className="muted">{e.experiment_id.slice(0, 8)} · {e.tool} · {e.summary}</p>
        ))}
      </Section>
      <Section title="5. Verification workspace">
        {report && report.verification.length > 0 ? (
          <ul>
            {report.verification.map((v, i) => (
              <li key={i}>{v.hypothesis_id.slice(0, 8)} → <Pill status={v.verdict} /></li>
            ))}
          </ul>
        ) : <p className="muted">No independent reviews yet.</p>}
        {data.reviews.length > 0 && <p className="muted">{data.reviews.length} review(s) preserved with disagreements intact.</p>}
      </Section>
      <Section title="6. Model behavior">
        <p className="muted">Task-aware panels from the Projects view apply here; the autonomous cycle reports per-diagnostic numbers above.</p>
      </Section>
      <Section title="7. Efficiency">
        <p className="muted">Offline cycle: no provider tokens billed. Token trade-offs are measured in the Part-10 harness (chars proxy + live usage when present).</p>
      </Section>
      <Section title="8. Final forensic report">
        {report ? (
          <>
            <h4>Confirmed ({report.confirmed_findings.length})</h4>
            <ul>{report.confirmed_findings.map((f) => <li key={f.hypothesis_id}>{f.title}</li>)}</ul>
            <h4>Rejected ({report.rejected_hypotheses.length})</h4>
            <ul>{report.rejected_hypotheses.map((f) => <li key={f.hypothesis_id}>{f.title}</li>)}</ul>
            <h4>Limitations</h4>
            <ul>{report.limitations.map((l, i) => <li key={i} className="muted">{l}</li>)}</ul>
            <h4>Recommendations</h4>
            <ul>{report.recommendations.map((r, i) => <li key={i}>{r}</li>)}</ul>
          </>
        ) : <p className="muted">Run the cycle to produce the forensic report.</p>}
      </Section>
    </div>
  )
}
