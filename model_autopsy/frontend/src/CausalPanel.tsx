import { useEffect, useState } from 'react'

interface CausalData {
  budget: { tool_calls: [number, number] }
  coverage: { missing_measurements: string[]; per_hypothesis: { hypothesis_id: string; family: string; collected: string[]; missing: string[]; covered: boolean }[]; untested: string[]; failed_skipped: string[]; inapplicable_skipped: string[] }
  report_validation: { summaries: { seq: number; valid: boolean; errors: string[]; output_class?: string | null; repair_eligible?: boolean | null; consistency_passed?: boolean | null; consistency_failures?: string[] | null; consistency_warnings?: string[] | null }[]; repairs?: { seq: number; title: string; valid: boolean | null; continuation?: string | null; output_class?: string | null; consistency_passed?: boolean | null; consistency_failures?: string[] | null }[]; generation_status?: string | null; fallbacks: { seq: number; title: string; version: string }[] }
  hypotheses: { id: string; text: string; status: string; confidence: number | null; justification: string | null; evidence_refs: { action_id: string; tool: string; relation: string }[] }[]
  competition: { pairs: { a: string; b: string; relation: string }[] }
  evidence_graph: { counts: { hypotheses: number; experiments: number } }
  selection: { ranked: { tool: string; expected_value: string; reason: string }[]; explanation: string }
  diagnosis_grades: Record<string, { level: string; verdict: string; reason: string }>
  transitions: { hypothesis_id: string; at: string; from: string; to: string }[]
  confidence_trail: { hypothesis_id: string; confidence: number | null; status: string; justification: string | null }[]
  feedback: { seq: number; kind: string; title: string; payload: Record<string, unknown> }[]
  stopping: { seq: number; title: string; rationale: string }[]
}

export function CausalPanel({ invId }: { invId: string }) {
  const [data, setData] = useState<CausalData | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    let live = true
    fetch(`/api/investigations/${invId}/causal`)
      .then((r) => { if (!r.ok) throw new Error(`causal ${r.status}`); return r.json() })
      .then((j) => { if (live) setData(j) })
      .catch((e) => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [invId])
  if (err) return <p className="muted">Causal view unavailable: {err}</p>
  if (!data) return <p className="muted">Loading causal view…</p>
  return (
    <section className="section" aria-label="Causal diagnosis">
      <h3>Causal diagnosis — competing explanations</h3>
      <p className="muted">{data.selection.explanation}</p>
      <div className="tablewrap"><table>
        <caption>Hypothesis competition (qualitative — no fabricated scores)</caption>
        <thead><tr><th>A</th><th>B</th><th>Relation</th></tr></thead>
        <tbody>{data.competition.pairs.map((p, i) => (
          <tr key={i}><td className="mono">{p.a.slice(0, 8)}</td><td className="mono">{p.b.slice(0, 8)}</td><td>{p.relation}</td></tr>
        ))}{data.competition.pairs.length === 0 && <tr><td colSpan={3}>Need 2+ hypotheses for competition analysis.</td></tr>}</tbody>
      </table></div>
      <div className="tablewrap"><table>
        <caption>Selection rationale (predicted value vs alternatives)</caption>
        <thead><tr><th>Tool</th><th>Expected</th><th>Why</th></tr></thead>
        <tbody>{data.selection.ranked.slice(0, 6).map((r) => (
          <tr key={r.tool}><td className="mono">{r.tool}</td><td>{r.expected_value}</td><td>{r.reason}</td></tr>
        ))}</tbody>
      </table></div>
      <div className="tablewrap"><table>
        <caption>Diagnosis grades (anomaly → established)</caption>
        <thead><tr><th>Hypothesis</th><th>Level</th><th>Verdict</th><th>Reason</th></tr></thead>
        <tbody>{Object.entries(data.diagnosis_grades).map(([hid, g]) => (
          <tr key={hid}><td className="mono">{hid.slice(0, 8)}</td><td>{g.level}</td><td>{g.verdict}</td><td>{g.reason}</td></tr>
        ))}</tbody>
      </table></div>
      <p className="muted">Evidence graph: {data.evidence_graph.counts.hypotheses} hypotheses · {data.evidence_graph.counts.experiments} experiments. Every conclusion traces to recorded action ids.</p>
      <div className="tablewrap"><table>
        <caption>Feedback loop — evidence → update → selection → execution</caption>
        <thead><tr><th>#</th><th>Stage</th><th>What happened</th></tr></thead>
        <tbody>{(data.feedback ?? []).map((f, i) => (
          <tr key={i}><td className="num">{f.seq}</td><td className="mono">{f.kind}</td><td>{f.title}</td></tr>
        ))}{(data.feedback ?? []).length === 0 && <tr><td colSpan={3}>No loop events yet — brief, links, and adherence appear as the investigation runs.</td></tr>}</tbody>
      </table></div>
      <div className="tablewrap"><table>
        <caption>Status transitions + confidence (auditable history)</caption>
        <thead><tr><th>Hypothesis</th><th>From → To</th><th>Confidence</th><th>Justification</th></tr></thead>
        <tbody>{(data.confidence_trail ?? []).map((c) => (
          <tr key={c.hypothesis_id}><td className="mono">{c.hypothesis_id.slice(0, 8)}</td>
            <td>{(data.transitions ?? []).filter((t) => t.hypothesis_id === c.hypothesis_id.slice(0, 8)).map((t) => `${t.from}→${t.to}`).join(', ') || c.status}</td>
            <td className="num">{c.confidence ?? '—'}</td><td>{c.justification ?? '—'}</td></tr>
        ))}</tbody>
      </table></div>
      {(data.stopping ?? []).length > 0 && (
        <p className="muted">Stopping: {(data.stopping ?? []).map((s) => s.rationale).join(' ')}</p>
      )}
      <div className="tablewrap"><table>
        <caption>Diagnostic coverage — what each hypothesis still needs</caption>
        <thead><tr><th>Hypothesis</th><th>Family</th><th>Collected</th><th>Missing</th><th>Evidence for / against</th></tr></thead>
        <tbody>{(data.coverage?.per_hypothesis ?? []).map((c) => {
          const h = (data.hypotheses ?? []).find((x) => x.id === c.hypothesis_id)
          const refs = h?.evidence_refs ?? []
          const sup = refs.filter((r) => r.relation === 'supports').length
          const con = refs.filter((r) => r.relation === 'contradicts').length
          return (
            <tr key={c.hypothesis_id}><td className="mono">{c.hypothesis_id.slice(0, 8)}</td><td>{c.family}</td>
              <td className="mono">{c.collected.join(', ') || '—'}</td><td className="mono">{c.missing.join(', ') || 'none'}</td>
              <td className="num">{sup} for / {con} against</td></tr>
          )
        })}{(data.coverage?.per_hypothesis ?? []).length === 0 && <tr><td colSpan={5}>No open hypotheses — nothing left to measure.</td></tr>}</tbody>
      </table></div>
      {(data.coverage?.missing_measurements ?? []).length > 0 && (
        <p className="muted">Unresolved measurements: {(data.coverage?.missing_measurements ?? []).join(', ')}. Untested hypotheses: {((data.coverage?.untested ?? []).map((u) => u.slice(0, 8)).join(', ') || 'none')}.</p>
      )}
      <div className="tablewrap"><table>
        <caption>Report validation — structural checks on the final summary</caption>
        <thead><tr><th>#</th><th>Valid</th><th>Output class</th><th>Errors</th></tr></thead>
        <tbody>{(data.report_validation?.summaries ?? []).map((s) => (
          <tr key={s.seq}><td className="num">{s.seq}</td><td>{s.valid ? 'valid' : 'INVALID'}</td><td className="mono">{s.output_class ?? '—'}</td><td>{(s.errors ?? []).join('; ') || '—'}</td></tr>
        ))}{(data.report_validation?.summaries ?? []).length === 0 && <tr><td colSpan={4}>No structured summary submitted yet.</td></tr>}</tbody>
      </table></div>
      {data.report_validation?.generation_status != null && data.report_validation.generation_status !== 'none_yet' && (
        <p className="muted">Report generation: <span className="mono">{data.report_validation.generation_status === 'model_native' ? 'model-native' : data.report_validation.generation_status === 'model_repaired' ? 'model-repaired (bounded repair)' : 'deterministic fallback (records only)'}</span> — the scientific findings above stand on recorded evidence either way.</p>
      )}
      {(data.report_validation?.summaries ?? []).filter((s) => s.valid && s.consistency_passed === false).length > 0 && (
        <p className="muted">Native-report consistency advisory: {(data.report_validation?.summaries ?? []).filter((s) => s.valid && s.consistency_passed === false).map((s) => `#${s.seq}: ${(s.consistency_failures ?? []).join('; ').slice(0, 200)}`).join(' · ')} — recorded against the final investigation state, not enforced; the findings above stand on recorded evidence either way.</p>
      )}
      {(data.report_validation?.repairs ?? []).length > 0 && (
        <p className="muted">Repair attempts: {(data.report_validation?.repairs ?? []).map((r) => `#${r.seq} ${r.valid == null ? 'not attempted' : r.valid ? `valid (${r.continuation ?? '?'})` : 'rejected'}${r.consistency_passed === false ? ` — consistency: ${(r.consistency_failures ?? []).join('; ').slice(0, 200)}` : ''}`).join(' · ')}</p>
      )}
      {(data.report_validation?.fallbacks ?? []).length > 0 && (
        <p className="muted">Deterministic fallback used ({(data.report_validation?.fallbacks ?? []).map((f) => f.version).join(', ')}): composed from recorded evidence only — the invalid model summary was preserved, not repaired away. A fallback is a reproducible record, not a valid model summary.</p>
      )}
    </section>
  )
}
