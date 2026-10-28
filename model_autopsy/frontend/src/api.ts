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
}

export interface FinalReport {
  investigation_id: string
  mode: string
  question: string
  generated_at: string
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

export const api = {
  health: () => call<{ ok: boolean }>('/api/health'),

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
    max_iterations?: number; workspace_root?: string; predictions_path?: string
  }) =>
    call<InvestigationSummary>('/api/investigations', {
      method: 'POST', body: JSON.stringify(body) }),

  getInvestigation: (id: string) =>
    call<InvestigationDetail>(`/api/investigations/${id}`),

  timeline: (id: string) =>
    call<{ events: TimelineEvent[] }>(`/api/investigations/${id}/timeline`),

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
