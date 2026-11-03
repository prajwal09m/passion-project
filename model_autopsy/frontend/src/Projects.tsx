// Universal project overview — spec-driven, no finance-specific copy.
// Demand Zone keeps its dedicated Case Study page; this page reflects
// whatever project the backend registry holds.
import { useState } from 'react'
import { api, useLoading, type ProjectDetail } from './api'

const TASK_FOCUS: Record<string, { metrics: string; panels: string[] }> = {
  classification: {
    metrics: 'Accuracy, precision/recall, ROC-AUC, calibration, confusion patterns',
    panels: ['Model diagnostics: thresholded metrics + reliability', 'Data & validation: label balance, splits, leakage checks'],
  },
  regression: {
    metrics: 'MAE, MSE, RMSE, R-squared, residual distribution, outliers, bias',
    panels: ['Model diagnostics: error distribution + heteroscedasticity', 'Data & validation: target coverage, split overlap'],
  },
  forecasting: {
    metrics: 'Error by horizon, drift, residual autocorrelation, maturity effects',
    panels: ['Model diagnostics: horizon curve + drift', 'Data & validation: chronology, split overlap, seasonality notes'],
  },
  ranking: {
    metrics: 'NDCG, MAP, precision/recall at K, position effects',
    panels: ['Model diagnostics: ranking quality by cutoff', 'Data & validation: candidate coverage'],
  },
  clustering: {
    metrics: 'Silhouette, stability, separation, size balance',
    panels: ['Model diagnostics: cluster profile', 'Data & validation: feature coverage'],
  },
  other: {
    metrics: 'Project-defined evaluation methodology',
    panels: ['Model diagnostics: per evaluation methodology', 'Data & validation: schema + quality'],
  },
}

function ProjectCard({ id, onOpen }: { id: string; onOpen: (inv: string) => void }) {
  const { data, error } = useLoading<ProjectDetail>(() => api.project(id), [id])
  const [starting, setStarting] = useState(false)
  const [failed, setFailed] = useState('')
  if (error) return <p className="error">Failed to load {id}: {error}</p>
  if (!data) return <p className="muted">Loading {id}…</p>
  const spec = data.spec
  const focus = TASK_FOCUS[spec.task_type] ?? TASK_FOCUS.other
  const model = spec.model as Record<string, string>
  const dataset = spec.dataset as Record<string, unknown>

  async function start() {
    setStarting(true)
    setFailed('')
    try {
      const inv = await api.createInvestigation({
        mode: 'ml',
        title: `${spec.name} investigation`,
        question: spec.objective || spec.description || `Investigate ${spec.name}`,
        project_id: spec.project_id,
      })
      onOpen(inv.id)
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e))
    } finally {
      setStarting(false)
    }
  }

  return (
    <section className="card">
      <h3>{spec.name}</h3>
      <p className="muted">{spec.description}</p>
      <dl className="facts">
        <dt>Domain</dt><dd>{spec.domain}</dd>
        <dt>Task</dt><dd>{spec.task_type}</dd>
        <dt>Model</dt><dd>{String(model?.name ?? '—')} [{String(model?.framework ?? '?')}]</dd>
        <dt>Target</dt><dd>{spec.target_definition || '—'}</dd>
        <dt>Evaluation</dt><dd>{spec.evaluation_methodology || '—'}</dd>
        <dt>Dataset</dt><dd>{String(dataset?.location ?? '—')}{dataset?.n_rows ? ` (${Number(dataset.n_rows).toLocaleString()} rows)` : ''}</dd>
      </dl>
      <h4>Diagnostic focus for this task</h4>
      <p className="muted">{focus.metrics}</p>
      <ul>{focus.panels.map((p) => <li key={p}>{p}</li>)}</ul>
      <h4>Capabilities exposed</h4>
      <p>{data.capabilities.length ? data.capabilities.join(', ') : 'none declared'}</p>
      <h4>Investigator brief</h4>
      <pre className="brief">{data.investigator_brief}</pre>
      {spec.known_limitations.length > 0 && (
        <><h4>Known limitations</h4>
        <ul>{spec.known_limitations.map((l) => <li key={l}>{l}</li>)}</ul></>
      )}
      <div className="row">
        <button onClick={start} disabled={starting}>
          {starting ? 'Starting…' : 'Start investigation with this project'}
        </button>
      </div>
      {failed && <p className="error">{failed}</p>}
    </section>
  )
}

export function ProjectsPage({ onOpen }: { onOpen: (id: string) => void }) {
  const { data, error } = useLoading(() => api.projects(), [])
  const [sel, setSel] = useState<string | null>(null)
  if (error) return <p className="error">Failed to load projects: {error}</p>
  if (!data) return <p className="muted">Loading projects…</p>
  const current = sel ?? data.projects[0]?.project_id ?? null
  return (
    <div>
      <h2>Projects</h2>
      <p className="muted">
        Every project is investigated through the same engine. Select a project to see
        its identity, task-specific diagnostic focus, and exposed capabilities —
        no hardcoded assumptions about industry, model, or metrics.
      </p>
      <div className="row">
        {data.projects.map((p) => (
          <button key={p.project_id}
            className={p.project_id === current ? 'active' : ''}
            onClick={() => setSel(p.project_id)}>
            {p.name} <span className="muted">· {p.task_type}</span>
          </button>
        ))}
      </div>
      {current && <ProjectCard key={current} id={current} onOpen={onOpen} />}
    </div>
  )
}
