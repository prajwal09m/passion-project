// Integrated research workspace (M13): portfolio, verification,
// memory transfer, evaluation corpora, frameworks. Read-only except
// explicit user actions; paid proposals never execute without a
// human approval token, which this UI never mints on its own.
import { useState } from 'react'
import { api, useLoading } from './api'
import { EmptyState, ErrorState, Loading } from './ui'

type Project = {
  id: string; objectives: string; status: string;
  n_experiments: number; n_unresolved: number
}

export function LabPage() {
  const { data, error, reload } = useLoading<{ projects: Project[] }>(
    () => api.labProjects(), [])
  const [creating, setCreating] = useState(false)
  const [objectives, setObjectives] = useState('')
  const [failed, setFailed] = useState('')
  const [query, setQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  async function create() {
    if (!objectives.trim()) return
    setCreating(true)
    setFailed('')
    try {
      await api.labCreate(objectives.trim())
      setObjectives('')
      reload()
    } catch (e) {
      setFailed(e instanceof Error ? e.message : String(e))
    } finally {
      setCreating(false)
    }
  }

  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading research portfolio" />
  return (
    <div>
      <h2>Research Laboratory</h2>
      <p className="muted">
        Persistent portfolio · evidence-required conclusions · independent
        verification · transfer-guarded memory. Established findings and
        uncertain hypotheses are visually distinct throughout.
      </p>
      <div className="row">
        <input
          value={objectives}
          onChange={(e) => setObjectives(e.target.value)}
          placeholder="New project objectives…"
          aria-label="New project objectives"
        />
        <button className="primary" disabled={creating} onClick={create}>
          {creating ? 'Creating…' : 'Create project'}
        </button>
        <button className="ghost" onClick={reload}>Refresh</button>
      </div>
      {failed && <p className="error">{failed}</p>}
      <section className="card">
        <h3>1. Research overview — portfolio intelligence</h3>
        <LabPortfolio />
      </section>
      <section className="card">
        <h3>2. Investigations — searchable, filterable</h3>
        <div className="row" style={{ marginBottom: 10 }}>
          <input value={query} onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by project ID or objectives…" aria-label="Search lab projects"
            style={{ maxWidth: 340 }} />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
            aria-label="Filter by status" style={{ maxWidth: 200 }}>
            <option value="">all statuses</option>
            <option value="active">active</option>
            <option value="blocked">blocked</option>
            <option value="completed">completed</option>
          </select>
          <span className="muted">showing {data.projects.filter((p) =>
            (!statusFilter || p.status === statusFilter) &&
            (!query.trim() || (p.id + ' ' + (p.objectives ?? '')).toLowerCase().includes(query.trim().toLowerCase()))
            ).length} of {data.projects.length}</span>
        </div>
        {data.projects.length === 0 ? (
          <EmptyState
            what="No research projects yet."
            action="Create one above: objectives first, agenda and evidence accumulate durably." />
        ) : (
          <ul>
            {data.projects.filter((p) =>
              (!statusFilter || p.status === statusFilter) &&
              (!query.trim() || (p.id + ' ' + (p.objectives ?? '')).toLowerCase().includes(query.trim().toLowerCase()))
            ).map((p) => (
              <li key={p.id}>
                <strong className="muted">{p.objectives || p.id}</strong>{' '}
                <span className="faint">· {p.id} · {p.status} · {p.n_experiments} exp · {p.n_unresolved} open</span>
                <LabProjectRow id={p.id} />
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="card">
        <h3>3. Verification — independent reproduction</h3>
        <p className="muted">
          Findings reproduce only through an independent tool path with a
          content-hashed manifest. Missing reproduction is recorded as
          uncertainty, never as disproof. Run verification from the
          investigation workspace; grades appear in the final report.
        </p>
      </section>
      <section className="card">
        <h3>4. Research memory — validated knowledge &amp; transfer</h3>
        <LabMemory />
        <LabKnowledge />
      </section>
      <section className="card">
        <h3>5. Evaluation — four held-out corpora (evidence-required)</h3>
        <LabUnseen />
        <LabCorpusB />
        <LabCorpusC />
        <LabCorpusD />
      </section>
      <section className="card">
        <h3>9. Model performance — demand-zone breakthrough (measured)</h3>
        <LabModelPerformance />
      </section>
      <section className="card">
        <h3>10. Scientific resolution — terminal diagnoses</h3>
        <p className="muted">
          Investigations end with a specific diagnosis (13 classes) and
          one of six statuses: confirmed, strongly-supported, falsified,
          verified-null, partially-resolved, unresolved. Unresolved is
          never relabeled confirmed. Per-investigation diagnoses are
          recorded on the timeline by the autonomous loop.
        </p>
      </section>
      <section className="card">
        <h3>6. Frameworks — honest capability reporting</h3>
        <LabFrameworks />
      </section>
      <section className="card">
        <h3>7. Discovery intelligence — strategies, risk, robustness</h3>
        <LabStrategies />
        <LabStrategyPerf />
        <LabFlagshipM15 />
        <p className="muted">
          Novel mechanisms, perturbations, and robustness maps run in the
          investigation workspace against real artifacts; this portfolio
          view reports only stored cross-project state. Untested regions
          are never shown as safe.
        </p>
      </section>
      <section className="card">
        <h3>8. Live/offline parity — where discovery is lost</h3>
        <LabLiveAudit />
      </section>
    </div>
  )
}

function LabProjectRow({ id }: { id: string }) {
  const { data, error, reload } = useLoading<{
    id: string; objectives: string; status: string;
    agenda: { id: string; kind: string; status: string }[];
    experiments: { tool: string }[];
    unresolved: string[]; resource_usage: { tool_calls: number }
  }>(() => api.labProject(id), [id])
  if (error) return <p className="error">{id}: {error}</p>
  if (!data) return <p className="muted">{id}: loading…</p>
  return (
    <div className="card">
      <strong>{data.objectives || id}</strong>{' '}
      <span className="muted">{data.status} · {data.experiments.length} experiments ·{' '}
        {data.unresolved.length} unresolved</span>
      <div className="row">
        <button className="ghost" onClick={async () => { await api.labTick(id); reload() }}>
          Scheduler tick (offline only)
        </button>
        <button className="ghost" onClick={reload}>Refresh</button>
      </div>
      {data.agenda.length > 0 && (
        <p className="muted">
          Agenda: {data.agenda.map((a) => `${a.id} [${a.kind}/${a.status}]`).join(' · ')}
        </p>
      )}
    </div>
  )
}

function LabPortfolio() {
  const { data, error, reload } = useLoading<{
    promising: { id: string; why: string }[];
    blocked: { id: string; why: string }[];
    needs_review: { id: string; why: string }[];
    pausable: { id: string; why: string }[];
    note: string
  }>(() => api.labPortfolio(), [])
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading portfolio intelligence" />
  const cols: [string, { id: string; why: string }[]][] = [
    ['Promising', data.promising],
    ['Blocked', data.blocked],
    ['Needs review', data.needs_review],
    ['Pausable', data.pausable],
  ]
  return (
    <div>
      {cols.map(([label, rows]) => (
        <div key={label}>
          <strong>{label} ({rows.length})</strong>
          {rows.length === 0 ? (
            <p className="muted">None.</p>
          ) : (
            <ul>
              {rows.map((r) => (
                <li key={r.id} className="muted">
                  <strong>{r.id}</strong> — {r.why}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <p className="muted">{data.note}</p>
    </div>
  )
}

function LabMemory() {
  const { data, error, reload } = useLoading<{
    entries: { kind: string; content: string; project_id: string; scope: string }[]
  }>(() => api.labMemory(), [])
  if (error) return <ErrorState error={error} onRetry={reload} />
  if (!data) return <Loading what="Loading research memory" />
  return (
    <div>
      <strong>Validated knowledge</strong>
      {data.entries.length === 0 ? (
        <p className="muted">No entries yet. Findings stay pinned to their project until independently replicated.</p>
      ) : (
        <ul>
          {data.entries.slice(-8).map((e, i) => (
            <li key={i} className="muted">
              [{e.kind}/{e.scope}] {e.content} <span>({e.project_id})</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function LabKnowledge() {
  const { data } = useLoading<{
    candidates: { content: string; category: string; validation: string }[];
    strategy: { transfers_helped: number; transfers_misled: number }
  }>(() => api.labKnowledge('', ''), [])
  if (!data) return null
  return (
    <div>
      <strong>Transfer candidates (hypotheses, never facts)</strong>
      {data.candidates.length === 0 ? (
        <p className="muted">No transfer candidates for an unprofiled project. Open a project to surface guarded suggestions.</p>
      ) : (
        <ul>
          {data.candidates.slice(0, 5).map((c, i) => (
            <li key={i} className="muted">
              [{c.category}/{c.validation}] {c.content}
            </li>
          ))}
        </ul>
      )}
      <p className="muted">
        Transfer record: helped {data.strategy.transfers_helped} · misled {data.strategy.transfers_misled}.
        Nothing here rewrites scientific thresholds.
      </p>
    </div>
  )
}

function LabUnseen() {
  const { data } = useLoading<{
    scenarios: { id: string; task: string; brief: string }[]
  }>(() => api.labUnseen(), [])
  if (!data) return null
  return (
    <div>
      <strong>Corpus A — M10 unseen projects</strong>
      <ul>
        {data.scenarios.map((s) => (
          <li key={s.id} className="muted">
            <strong>{s.id}</strong> [{s.task}] — {s.brief}
          </li>
        ))}
      </ul>
    </div>
  )
}

function LabCorpusB() {
  const { data } = useLoading<{
    scenarios: { id: string; task: string; brief: string }[]
  }>(() => api.labCorpusB(), [])
  if (!data) return null
  return (
    <div>
      <strong>Corpus B — M13 second held-out corpus</strong>
      <ul>
        {data.scenarios.map((s) => (
          <li key={s.id} className="muted">
            <strong>{s.id}</strong> [{s.task}] — {s.brief}
          </li>
        ))}
      </ul>
      <p className="muted">Ground truth stays sealed; the evaluator grades evidence-required discovery only.</p>
    </div>
  )
}

function LabCorpusC() {
  const { data } = useLoading<{
    scenarios: { id: string; task: string; brief: string }[]
  }>(() => api.labCorpusC(), [])
  if (!data) return null
  return (
    <div>
      <strong>Corpus C — M14 third corpus (interaction, robustness, novel)</strong>
      <ul>
        {data.scenarios.map((s) => (
          <li key={s.id} className="muted">
            <strong>{s.id}</strong> [{s.task}] — {s.brief}
          </li>
        ))}
      </ul>
      <p className="muted">Novelty is reported separately from discovery; evidence is still required.</p>
    </div>
  )
}

function LabStrategies() {
  const { data } = useLoading<{
    policies: { name: string; version: string; description: string }[]
  }>(() => api.labStrategies(), [])
  if (!data) return null
  return (
    <div>
      <strong>Versioned research strategies (frozen baseline + contenders)</strong>
      <ul>
        {data.policies.map((p) => (
          <li key={p.name} className="muted">
            <strong>{p.name}</strong> [{p.version}] — {p.description}
          </li>
        ))}
      </ul>
    </div>
  )
}

function LabStrategyPerf() {
  const { data } = useLoading<{
    aggregate: { n: number; discovery_hits: number; resolved: number; wasted: number; verify_failures: number; note: string }
  }>(() => api.labStrategyPerf(), [])
  if (!data) return null
  return (
    <div>
      <strong>Strategy performance (held-out, no sealed labels)</strong>
      <p className="muted">
        {data.aggregate.n} recorded investigations · {data.aggregate.discovery_hits} hits ·{' '}
        {data.aggregate.resolved} resolved · {data.aggregate.wasted} wasted ·{' '}
        {data.aggregate.verify_failures} verify failures. {data.aggregate.note}
      </p>
    </div>
  )
}

function LabFlagshipM15() {
  const { data } = useLoading<{
    tracks: Record<string, { stop: string; ran: string[]; statuses: string[]; resolution: { class: string } | null }>; diagnostic: { name: string; status: string }
  }>(() => api.labFlagshipM15(), [])
  if (!data) return null
  return (
    <div>
      <strong>Flagship M15 — wrong-lead pivot + null track</strong>
      <ul>
        {Object.entries(data.tracks).map(([k, v]) => (
          <li key={k} className="muted">
            <strong>{k}</strong> — {v.resolution?.class ?? 'pending'} · {v.stop} · ran {v.ran.join(', ')}
          </li>
        ))}
      </ul>
      <p className="muted">Diagnostic {data.diagnostic.name}: {data.diagnostic.status}.</p>
    </div>
  )
}

function LabLiveAudit() {
  const { data } = useLoading<{
    stages: Record<string, { failure: string | null }>;
    opportunities: { opportunity: string; lost_at: string | null }[]
  }>(() => api.labLiveAudit(), [])
  if (!data) return <p className="muted">No saved live trace to audit.</p>
  const lost = data.opportunities.filter((o) => o.lost_at)
  return (
    <div>
      <p className="muted">
        Saved-trace audit: {data.opportunities.length} opportunities ·{' '}
        {lost.length} with a diagnosable loss stage. Model failures (no
        hypotheses, no linking) are distinct from infrastructure failures
        (no events, executions refused, no report).
      </p>
      {lost.length > 0 && (
        <ul>
          {lost.slice(0, 6).map((o, i) => (
            <li key={i} className="muted">
              {o.opportunity} — lost at {o.lost_at}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function LabCorpusD() {
  const { data } = useLoading<{
    scenarios: { id: string; task: string; brief: string }[]
  }>(() => api.labCorpusD(), [])
  if (!data) return null
  return (
    <div>
      <strong>Corpus D — M15 null, unidentifiable, combined, confounded</strong>
      <ul>
        {data.scenarios.map((s) => (
          <li key={s.id} className="muted">
            <strong>{s.id}</strong> [{s.task}] — {s.brief}
          </li>
        ))}
      </ul>
      <p className="muted">Correct outcomes include verified-null and inconclusive; resolution quality is graded, not just discovery.</p>
    </div>
  )
}

function LabModelPerformance() {
  const { data } = useLoading<{
    measured: boolean; baseline_test_auc?: number;
    test_delta?: { auc_base: number; auc_cand: number; delta: number; delta_ci95: number[]; n: number; significant: boolean };
    brier?: { base: number; cand: number }; candidate?: string; promotion?: string;
    failed_candidates?: Record<string, { delta: number; ci: number[] }>; reason?: string
  }>(() => api.labModelPerformance(), [])
  if (!data) return <p className="muted">Loading measured performance…</p>
  if (!data.measured) return <p className="muted">Not measured in this environment: {data.reason}</p>
  return (
    <div>
      <p className="muted">
        Baseline held-out AUC <strong>{data.baseline_test_auc}</strong> → candidate{' '}
        <strong>{data.test_delta?.auc_cand}</strong> (Δ {data.test_delta?.delta}{' '}
        [{data.test_delta?.delta_ci95.join(', ')}], n={data.test_delta?.n}).{' '}
        Brier {data.brier?.base} → {data.brier?.cand}.
      </p>
      <p className="muted">{data.candidate} — {data.promotion}</p>
      {data.failed_candidates && (
        <p className="muted">
          Failed on validation: {Object.entries(data.failed_candidates).map(([k, v]) => `${k} Δ${v.delta}`).join(' · ')}
        </p>
      )}
    </div>
  )
}

function LabFrameworks() {
  const { data } = useLoading<{
    frameworks: { framework: string; usable: boolean; reason: string }[]
  }>(() => api.frameworks(), [])
  if (!data) return null
  return (
    <ul>
      {data.frameworks.map((f) => (
        <li key={f.framework} className="muted">
          <strong>{f.framework}</strong> — {f.usable ? 'available' : `unavailable: ${f.reason}`}
        </li>
      ))}
    </ul>
  )
}
