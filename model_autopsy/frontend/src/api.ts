// Typed API client for the Model Autopsy backend (FastAPI at the /api proxy).
import { useEffect, useState, useRef } from 'react'

const BASE = ''

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = `${detail}: ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail).slice(0, 300)}`
    } catch { /* keep status line */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

/* ---------- shared types ---------- */

export interface EvidenceRef {
  action_id: string
  tool?: string | null
  relation: string
  action_status?: string
}

export interface Revision {
  at: string
  from: string
  to: string
}

export interface Hypothesis {
  id: string
  text: string
  status: string
  confidence: number | null
  source: string
  rationale?: string | null
  predicted_observation?: string | null
  confidence_note?: string | null
  evidence_refs?: EvidenceRef[] | null
  revisions?: Revision[] | null
  created_at?: string
}

export interface Action {
  id: string
  seq: number
  kind: string
  tool_name: string | null
  status: string
  arguments: Record<string, unknown>
  result: Record<string, unknown> | null
  error: string | null
  iteration: number
}

export interface TimelineEvent {
  seq: number
  kind: string
  title: string
  detail: string | null
  payload: Record<string, unknown>
  created_at: string
}

export interface InvestigationSummary {
  id: string
  mode: 'software' | 'ml'
  title: string
  status: string
  scientific_status?: string | null
  iteration_count: number
  max_iterations: number
  tool_call_count: number
  max_tool_calls: number
  created_at: string
  latest_findings: Finding[]
  tags?: string[]
  is_test_record?: boolean
  has_final_report: boolean
  question?: string
  config?: Record<string, unknown>
}

export interface Finding {
  status: string
  summary: string
  evidence_action_id?: string | null
}

export interface InvestigationDetail extends InvestigationSummary {
  final_report: FinalReport | null
  hypotheses: Hypothesis[]
  actions: Action[]
  scientific?: ScientificAssessment | null
  recommended_experiments?: ExperimentRec[] | null
}

export interface FinalReport {
  investigation_id: string
  mode: string
  question: string
  generated_at: string
  execution_status?: string
  scientific_assessment?: ScientificAssessment
  main_interpretation?: string
  investigation_scope?: { uploaded?: string[]; examined?: string[]; used_by_diagnostics?: string[]; stored_not_examined?: string[]; missing?: string[] }
  candidate_explanations?: { machine?: { hypothesis_id: string; text: string; status: string }[]; manual?: { hypothesis_id: string; text: string; status: string }[] }
  recommended_experiments?: ExperimentRec[]
  diagnostics_not_run?: string[]
  reproducibility?: Record<string, unknown>
  confirmed: { summary: string; evidence_action_id?: string | null }[]
  likely: { summary: string; evidence_action_id?: string | null }[]
  rejected: ({ summary?: string; hypothesis_id?: string; text?: string; evidence_action_id?: string | null; evidence_refs?: EvidenceRef[] })[]
  unresolved: { hypothesis_id: string; text: string; status: string; origin: string; confidence_is_model_note: boolean }[]
  supported_hypotheses: { hypothesis_id: string; text: string; evidence_refs: EvidenceRef[] }[]
  evidence_performed: { action_id: string; seq: number; tool: string | null; status: string; result_digest?: Record<string, unknown>; error?: string }[]
  limitations: string[]
  recommended_next: { for: string | null; action: string; status: string }[]
  budget: { tool_calls: number[]; iterations: number[] }
  scope_note: string
}

/* ---------- case study ---------- */

export interface CaseStudy {
  name: string
  artifacts: Record<string, string>
  model_cols: string[]
  summary: Record<string, unknown> | null
  error: string | null
  docs: Record<string, string>
  suggest_investigation: { mode?: string; title?: string; question?: string }
}

export interface BootPair {
  score_a: string
  score_b: string
  auc_a: number
  auc_b: number
  delta: number
  ci_low: number
  ci_high: number
  n_boot: number
  design: string
  sampling_unit: string
  reproducibility: string
}

export interface ReliabilityBin {
  bin_low: number
  bin_high: number
  n: number
  mean_score: number
  fraction_positive: number
}

export interface CaseMetrics {
  ok: boolean
  source: string
  n_rows: number
  cluster_column_used: string | null
  pooled_auc: Record<string, number>
  per_fold_auc: Record<string, Record<string, number>>
  fold_sizes: Record<string, number>
  delta_auc_pairs: BootPair[]
  calibration: {
    arm: string
    reliability_bins: ReliabilityBin[]
    brier: number
    log_loss: number
    brier_note: string
  } | null
  label_balance: {
    counts: { negative_0: number; positive_1: number }
    positive_share: number
    n_rows: number
  } | null
  chronology: {
    date_column: string
    fold_date_spans: Record<string, [string, string]>
    non_overlapping_adjacent_folds: boolean
    oscope_note: string
  } | null
  recomputed_live: boolean
  historical_claim_note: string
}

/* ---------- universal projects ---------- */

export interface ProjectListItem {
  project_id: string
  name: string
  domain: string
  task_type: string
}

export interface ProjectDetail {
  spec: {
    project_id: string
    name: string
    description: string
    domain: string
    objective: string
    task_type: string
    target_definition: string
    evaluation_methodology: string
    known_limitations: string[]
    model: Record<string, unknown>
    dataset: Record<string, unknown>
  }
  capabilities: string[]
  investigator_brief: string
}

export interface ResearchHypothesis {
  id: string
  title: string
  mechanism: string
  status: string
  priority: string
  support_criteria: string
  refute_criteria: string
  diagnostics: string[]
  evidence_motivating: unknown[]
  history: { from: string | null; to: string; note: string }[]
}

export interface ResearchReport {
  executive_summary: string
  confirmed_findings: { hypothesis_id: string; title: string }[]
  rejected_hypotheses: { hypothesis_id: string; title: string }[]
  inconclusive: { hypothesis_id: string; title: string }[]
  open_hypotheses: { hypothesis_id: string; title: string; status: string }[]
  experiments: { experiment_id: string; tool: string; status: string; summary: string }[]
  verification: { hypothesis_id: string; verdict: string }[]
  limitations: string[]
  recommendations: string[]
}

export interface ResearchState {
  investigation_id: string
  stages: Record<string, unknown>
  hypotheses: ResearchHypothesis[]
  reviews: { hypothesis_id: string; verdict: string }[]
  taxonomy: Record<string, unknown>
  report: ResearchReport | null
}

export interface FrameworkInfo {
  framework: string
  usable: boolean
  reason: string
  capabilities: string[]
}

/* ---------- settings + contract ---------- */

export interface ToolParam {
  type: string
  required?: boolean
  min_length?: number
  max_length?: number
  minimum?: number | null
  maximum?: number | null
  pattern?: string
  description?: string
  min_items?: number
  max_items?: number
  item_type?: string
}

export interface SettingsPayload {
  meta: {
    key_configured: boolean
    base_url: string
    model_id: string
    last_test: { ok?: boolean; at?: string; detail?: string | number; verified?: string } | null
  }
  safety: {
    absolute_max_iterations: number
    absolute_max_tool_calls: number
    max_hypotheses_per_investigation?: number
    workspace_roots: string[]
    write_tools: string
    campaign_isolation: string
  }
}

/* ---------- client ---------- */

export interface UploadedFile {
  batch: string; name: string; path: string; bytes: number; kind: string;
  sha256?: string; is_duplicate?: boolean; duplicate_of?: string;
  analyzed?: boolean; analysis_note?: string
}

export interface ScientificAssessment {
  execution_status?: string; status: string; explanation: string; guidance?: string;
  evidence_gaps?: string[]; scope_gaps?: string[];
  suspicious_max_abs_r?: number | null; suspicious_feature?: string | null
}

export interface ExperimentRec {
  hypothesis_id: string; title: string; what: string; why: string;
  evidence?: { action_id?: string; tool?: string }[];
  required_inputs?: string[] | string; measures?: string;
  support_if?: string; contradict_if?: string;
  executable_now?: boolean; tool?: string; missing?: string[] | string; priority?: number
}

export async function uploadArtifacts(files: File[]): Promise<{ ok: boolean; batch: string; files: UploadedFile[] }> {
  const form = new FormData()
  for (const f of files) form.append('files', f, f.name)
  const res = await fetch('/api/uploads', { method: 'POST', body: form })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = `${detail}: ${typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail).slice(0, 300)}`
    } catch { /* keep status */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  health: () => call<{ ok: boolean }>('/api/health'),

  uploads: () => call<{ uploads: UploadedFile[] }>('/api/uploads'),

  removeUpload: (batch: string, name: string, purge = false) =>
    call<{ ok: boolean; removed?: string; purged?: boolean; note?: string }>(`/api/uploads/${encodeURIComponent(batch)}/${encodeURIComponent(name)}${purge ? '?purge=true' : ''}`, { method: 'DELETE' }),

  autoInterpret: (id: string) =>
    call<{ ok: boolean; hypotheses: { created: { id: string; text: string }[]; skipped: string[]; note: string }; scientific: ScientificAssessment; experiments: ExperimentRec[] }>(`/api/investigations/${id}/auto-interpret`, { method: 'POST' }),

  scientific: (id: string) =>
    call<{ execution_status: string; scientific: ScientificAssessment; experiments: ExperimentRec[] }>(`/api/investigations/${id}/scientific`),

  listInvestigations: (mode?: string, status?: string) => {
    const p = new URLSearchParams()
    if (mode) p.set('mode', mode)
    if (status) p.set('status', status)
    const qs = p.toString()
    return call<{ items: InvestigationSummary[] }>(
      `/api/investigations${qs ? `?${qs}` : ''}`)
  },

  createInvestigation: (body: {
    mode: string; title: string; question: string;
    max_iterations?: number; workspace_root?: string; predictions_path?: string;
    project_id?: string
  }) =>
    call<InvestigationSummary>('/api/investigations', {
      method: 'POST', body: JSON.stringify(body) }),

  getInvestigation: (id: string) =>
    call<InvestigationDetail>(`/api/investigations/${id}`),

  timeline: (id: string) =>
    call<{ events: TimelineEvent[] }>(`/api/investigations/${id}/timeline`),

  m16: (id: string) =>
    call<{ investigation_id: string; reservation: TimelineEvent[]; skeptic: TimelineEvent[]; grounded: TimelineEvent[]; linker_notes: TimelineEvent[]; status_justifications: { id: string; text: string; status: string; justification: string | null; evidence_refs: EvidenceRef[] | null }[] }>(`/api/investigations/${id}/m16`),

  closure: (id: string) =>
    call<{ investigation_id: string; hypotheses: { id: string; text: string; status: string; evidence_refs: EvidenceRef[] | null; revisions: { from: string; to: string; at?: string }[] | null; justification: string | null }[]; transitions: { hypothesis_id: string; hypothesis: string; from: string; to: string; at?: string; evidence_action_id?: string }[]; experiment_ledger: TimelineEvent[]; experiments_executed: number; experiments_cap: number; tool_calls_used: number; tool_calls_max: number; reservation: TimelineEvent[]; skeptic: TimelineEvent[]; verification: TimelineEvent[]; resolution: TimelineEvent[] }>(`/api/investigations/${id}/closure`),

  buildContext: (id: string) =>
    call<{ ok: boolean; status: string }>(
      `/api/investigations/${id}/context`, { method: 'POST' }),

  runTool: (id: string, tool_name: string, args: Record<string, unknown> = {}) =>
    call<{ ok: boolean; result?: Record<string, unknown>; error?: string; detail?: string; action_id?: string }>(
      `/api/investigations/${id}/tool`, {
        method: 'POST',
        body: JSON.stringify({ tool_name, arguments: args }),
      }),

  metaTurn: (id: string, max_rounds = 3) =>
    call<{ status: string; message_text?: string; error?: string; tool_calls?: { call_id: string; name: string; outcome: Record<string, unknown> }[] }>(
      `/api/investigations/${id}/meta-turn`, {
        method: 'POST', body: JSON.stringify({ max_rounds }) }),

  addHypothesis: (id: string, text: string, source = 'manual', rationale?: string) =>
    call<Hypothesis>(`/api/investigations/${id}/hypotheses`, {
      method: 'POST', body: JSON.stringify({ text, source, rationale }) }),

  patchHypothesis: (id: string, body: { status?: string; confidence?: number | null; rationale?: string | null }) =>
    call<Hypothesis>(`/api/hypotheses/${id}`, {
      method: 'PATCH', body: JSON.stringify(body) }),

  linkEvidence: (hypothesisId: string, actionId: string, relation: 'supports' | 'contradicts') =>
    call<{ id: string }>(`/api/hypotheses/${hypothesisId}/evidence`, {
      method: 'POST', body: JSON.stringify({ action_id: actionId, relation }) }),

  addFinding: (id: string, summary: string, status: string, evidenceActionId?: string) =>
    call<unknown>(`/api/investigations/${id}/findings`, {
      method: 'POST',
      body: JSON.stringify({ summary, status, evidence_action_id: evidenceActionId || undefined }) }),

  generateReport: (id: string) =>
    call<{ ok: boolean; report: FinalReport }>(`/api/investigations/${id}/report`, {
      method: 'POST' }),

  markPlanApplied: (id: string, planIndex: number) =>
    call<{ ok: boolean }>(`/api/investigations/${id}/revision-plan/${planIndex}/applied`, {
      method: 'POST' }),

  researchRun: (id: string) =>
    call<{ ok: boolean; report: ResearchReport }>(`/api/investigations/${id}/research/run`, {
      method: 'POST' }),

  researchState: (id: string) =>
    call<ResearchState>(`/api/investigations/${id}/research`),

  projects: () =>
    call<{ projects: ProjectListItem[] }>('/api/projects'),

  project: (id: string) =>
    call<ProjectDetail>(`/api/projects/${id}`),

  frameworks: () =>
    call<{ frameworks: FrameworkInfo[] }>('/api/model-frameworks'),

  caseStudy: () => call<CaseStudy>('/api/case-study/demand-zone'),

  caseMetrics: (nBoot = 500) =>
    call<CaseMetrics>(`/api/case-study/demand-zone/metrics?n_boot=${nBoot}`),

  metaStatus: () =>
    call<{ key_configured: boolean; base_url: string; model_id: string }>(
      '/api/meta/status'),

  testConnection: () => call<Record<string, unknown>>('/api/meta/test-connection', { method: 'POST' }),

  settings: () => call<SettingsPayload>('/api/settings'),

  toolContract: (mode?: string) => {
    const qs = mode ? `?mode=${mode}` : ''
    return call<Record<string, { mode: string; description: string; parameters: Record<string, ToolParam> }>>(
      `/api/tool-contract${qs}`)
  },

  evalProjects: () =>
    call<{ projects: { id: string; family: string; name: string; task: string; brief: string }[] }>('/api/eval/projects'),

  evalAudit: () =>
    call<{ ok: boolean; violations: unknown[]; files_scanned: number; tokens_checked: number }>('/api/eval/separation-audit'),

  evalRunAll: (project?: string, max_experiments = 4) =>
    call<{ ok: boolean; run_id: string; manifest: unknown }>('/api/eval/runs', {
      method: 'POST', body: JSON.stringify({ project, max_experiments }) }),

  evalRuns: () =>
    call<{ runs: { run_id: string; eval_version: string; max_experiments: number; aggregate: { n: number; mean_overall: number; verdicts: Record<string, number> }; results: { project: string; verdict: string; overall: number; elapsed_s: number }[] }[] }>('/api/eval/runs'),

  evalRun: (runId: string) =>
    call<{ run_id: string; eval_version: string; max_experiments?: number; aggregate: { n: number; mean_overall: number; verdicts: Record<string, number> }; results: { project: string; verdict: string; overall: number; elapsed_s: number }[] }>(`/api/eval/runs/${runId}`),

  evalResult: (runId: string, project: string) =>
    call<{
      project: string; investigation_id: string; elapsed_s: number;
      report: {
        executive_summary: string;
        confirmed_findings: { hypothesis_id: string; title: string }[];
        rejected_hypotheses: { hypothesis_id: string; title: string }[];
        inconclusive: { hypothesis_id: string; title: string }[];
        experiments: { experiment_id: string; tool: string; summary: string; numbers?: Record<string, unknown> }[];
        verification: { hypothesis_id: string; verdict: string }[];
        limitations: string[]
      };
      scorecard: {
        project: string; verdict: string; overall: number; note: string; false_positive: boolean;
        dimensions: Record<string, number>; weights: Record<string, number>
      };
      human_review: { review: null | { blind_verdict: string; revealed: boolean; post_reveal_assessment?: string } }
    }>(`/api/eval/runs/${runId}/${project}`),

  evalBlind: (runId: string, project: string, reviewer: string, verdict: string, notes: string) =>
    call<unknown>(`/api/eval/runs/${runId}/${project}/review/blind`, {
      method: 'POST', body: JSON.stringify({ reviewer, verdict, notes }) }),

  evalReveal: (runId: string, project: string, assessment: string) =>
    call<unknown>(`/api/eval/runs/${runId}/${project}/review/reveal`, {
      method: 'POST', body: JSON.stringify({ assessment }) }),

  liveRuns: () =>
    call<{ runs: { run_id: string; status: string; eval_project: string; model: string; budget: unknown }[]; note: string }>('/api/live/runs'),

  labProjects: () =>
    call<{ projects: { id: string; objectives: string; status: string; n_experiments: number; n_unresolved: number }[] }>('/api/lab/projects'),

  labCreate: (objectives: string) =>
    call<{ id: string }>('/api/lab/projects', {
      method: 'POST', body: JSON.stringify({ objectives }) }),

  labProject: (id: string) =>
    call<{
      id: string; objectives: string; status: string;
      agenda: { id: string; kind: string; status: string }[];
      experiments: { tool: string }[]; unresolved: string[];
      resource_usage: { tool_calls: number }
    }>(`/api/lab/projects/${id}`),

  labTick: (id: string) =>
    call<{ acted: unknown[]; deferred: unknown[]; budget_left: number }>(`/api/lab/projects/${id}/tick`, {
      method: 'POST', body: JSON.stringify({}) }),

  labMemory: () =>
    call<{ entries: { kind: string; content: string; project_id: string; scope: string }[] }>('/api/lab/memory'),

  labUnseen: () =>
    call<{ scenarios: { id: string; task: string; brief: string }[] }>('/api/lab/m10'),

  labPortfolio: () =>
    call<{ promising: { id: string; why: string }[]; blocked: { id: string; why: string }[]; needs_review: { id: string; why: string }[]; pausable: { id: string; why: string }[]; note: string }>('/api/lab/portfolio'),

  labKnowledge: (columns = '', task = '') =>
    call<{ candidates: { content: string; category: string; source_project: string; validation: string; treat_as: string }[]; strategy: { transfers_helped: number; transfers_misled: number } }>(`/api/lab/knowledge?columns=${encodeURIComponent(columns)}&task=${encodeURIComponent(task)}`),

  labCorpusB: () =>
    call<{ scenarios: { id: string; task: string; brief: string }[] }>('/api/lab/corpus-b'),

  labCorpusC: () =>
    call<{ scenarios: { id: string; task: string; brief: string }[] }>('/api/lab/corpus-c'),

  labCorpusD: () =>
    call<{ scenarios: { id: string; task: string; brief: string }[] }>('/api/lab/corpus-d'),

  labModelPerformance: () =>
    call<{ measured: boolean; baseline_test_auc?: number; test_delta?: { auc_base: number; auc_cand: number; delta: number; delta_ci95: number[]; n: number; significant: boolean }; brier?: { base: number; cand: number }; subgroups?: Record<string, { n: number; auc: number | null }>; candidate?: string; promotion?: string; failed_candidates?: Record<string, { delta: number; ci: number[] }>; reason?: string }>('/api/lab/model-performance'),

  labStrategies: () =>
    call<{ policies: { name: string; version: string; description: string }[] }>('/api/lab/strategies'),

  labLiveAudit: () =>
    call<{ stages: Record<string, { failure: string | null }>; opportunities: { opportunity: string; lost_at: string | null }[] }>('/api/lab/live-audit'),

  labStrategyPerf: () =>
    call<{ aggregate: { n: number; discovery_hits: number; resolved: number; wasted: number; verify_failures: number; note: string } }>('/api/lab/strategy-performance'),

  labEvalD: () =>
    call<{ scenarios: { id: string; task: string; brief: string; artifact: string }[] }>('/api/lab/eval-d'),

  labFlagshipM15: () =>
    call<{ tracks: Record<string, { stop: string; ran: string[]; statuses: string[]; resolution: { class: string; why: string } | null }>; diagnostic: { name: string; status: string; fp: number; fn: number } }>('/api/lab/flagship-m15'),

  liveRun: (runId: string) =>
    call<{ run_id: string; status: string; eval_project: string; budget: { cost_usd: { spent: number; cap: number }; tokens: { total: number; cap: number }; attempts: number[]; rounds: number[] } | null; artifacts: Record<string, string>; required_evidence_present: Record<string, boolean> }>(`/api/live/runs/${runId}`),
}

/* ---------- small date formatting used by the timeline ---------- */

export function formatTimelineTime(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toISOString().slice(11, 19) + 'Z'
}

/* ---------- status styling ---------- */

export function statusClass(status: string): string {
  switch (status) {
    case 'complete': case 'ran': case 'supported': case 'confirmed': case 'ok': case 'context_ready':
      return 'ok'
    case 'failed': case 'rejected': case 'cancelled': case 'stopped':
      return 'bad'
    case 'investigating': case 'revising': case 'finalizing': case 'testing': case 'likely':
      return 'accent'
    case 'blocked': case 'created': case 'context_ready_fail': case 'unavailable':
      return 'warn'
    default:
      return ''
  }
}

/** Simple fetch-on-mount hook with graceful failure. */
export function useLoading<K>(fn: () => Promise<K>, deps: unknown[] = []):
  { data: K | null; error: string; reload: () => void } {
  const [data, setData] = useState<K | null>(null)
  const [error, setError] = useState('')
  const [tick, setTick] = useState(0)
  const fRef = useRef(fn)
  fRef.current = fn
  useEffect(() => {
    let alive = true
    setData(null)
    setError('')
    fRef.current()
      .then((d) => { if (alive) setData(d) })
      .catch((e: unknown) => { if (alive) setError(e instanceof Error ? e.message : String(e)) })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])
  return { data, error, reload: () => setTick((t) => t + 1) }
}
