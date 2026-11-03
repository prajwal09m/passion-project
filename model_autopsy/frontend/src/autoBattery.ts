// Shared one-click diagnostic battery — used by the New Investigation page
// AND the workspace Run controls, so a pure page-user is never stranded
// on an empty workspace with only manual tool forms.
import { api } from './api'

export function columnNames(result: Record<string, unknown> | null | undefined): string[] {
  if (!result) return []
  const raw = (result as Record<string, unknown>).columns
  if (!Array.isArray(raw)) return []
  return raw.map((c) => typeof c === 'string' ? c : (c as { name?: unknown }).name)
    .filter((c): c is string => typeof c === 'string' && c.length > 0)
}

export function pickScoreColumn(cols: string[], fallback: string): string {
  if (cols.includes(fallback)) return fallback
  const candidates = ['score', 'prediction', 'pred', 'prob', 'proba',
    'probability', 'y_score', 'y_pred']
  return candidates.find((c) => cols.includes(c))
    ?? cols.find((c) => c !== 'label' && c !== 'fold' && c !== 'date')
    ?? fallback
}

export interface BatterySummary {
  confirmed: number; likely: number; rejected: number;
  unresolved: number; evidence: number
}

/** Run summary → metrics → calibration → validation → suspiciousness scan,
 *  then generate the report. Every tool failure is logged, never fatal. */
export async function runFullBattery(
  invId: string, pred: string, fallbackScore: string,
  push: (s: string) => void,
): Promise<BatterySummary | null> {
  // Learn the real columns first so the score column never has to be guessed.
  let sc = fallbackScore
  try {
    const s = await api.runTool(invId, 'artifact_summary', { predictions_path: pred })
    const cols = columnNames(s.result)
    push(`artifact_summary: ok (${cols.length} columns: ${cols.slice(0, 8).join(', ')})`)
    sc = pickScoreColumn(cols, fallbackScore)
    if (sc !== fallbackScore) push(`score column auto-detected: ${sc}`)
  } catch (e) {
    push(`artifact_summary: failed (${e instanceof Error ? e.message : String(e)}) — continuing with "${sc}"`)
  }
  const battery: [string, Record<string, unknown>][] = [
    ['classification_metrics', { predictions_path: pred, score_column: sc }],
    ['calibration_and_error_analysis', { predictions_path: pred, score_column: sc }],
    ['dataset_validation', { predictions_path: pred, score_columns: [sc] }],
    ['feature_target_suspiciousness', { feature_csv: pred, label_csv: pred }],
  ]
  for (const [tool, targs] of battery) {
    try {
      const r = await api.runTool(invId, tool, targs)
      if (r.ok) {
        const auc = r.result && typeof r.result.roc_auc === 'number'
          ? ` — AUC ${Number(r.result.roc_auc).toFixed(4)}` : ''
        push(`${tool}: ok${auc}`)
      } else {
        push(`${tool}: failed (${String(r.error ?? r.detail ?? 'unknown error')})`)
      }
    } catch (e) {
      push(`${tool}: failed (${e instanceof Error ? e.message : String(e)})`)
    }
  }
  try {
    const interp = await api.autoInterpret(invId)
    const n = interp.hypotheses.created.length
    push(n > 0 ? `Potential explanations proposed: ${n} candidate(s) — suspicion only, not proof (${interp.scientific.status})` : `No candidate explanation proposed: ${interp.hypotheses.note} (scientific: ${interp.scientific.status})`)
    for (const e of interp.experiments.slice(0, 3)) push(`Suggested experiment: ${e.title}`)
  } catch (e) {
    push(`Automatic interpretation unavailable (${e instanceof Error ? e.message : String(e)}) — hypotheses can still be added manually`)
  }
  try {
    const rep = await api.generateReport(invId)
    const r = rep.report
    const sci = (r as unknown as { scientific_assessment?: { status?: string } }).scientific_assessment?.status ?? 'inconclusive'
    push(`Diagnostic battery finished — scientific assessment: ${sci}. Lack of findings is not proof of safety.`)
    push(`Report generated: ${r.confirmed.length} confirmed · ${r.likely.length} likely · ${r.unresolved.length} unresolved · ${r.evidence_performed.length} evidence actions`)
    return {
      confirmed: r.confirmed.length, likely: r.likely.length,
      rejected: r.rejected.length, unresolved: r.unresolved.length,
      evidence: r.evidence_performed.length,
    }
  } catch (e) {
    push(`Report generation failed (${e instanceof Error ? e.message : String(e)}) — run it from the report section below`)
    return null
  }
}
