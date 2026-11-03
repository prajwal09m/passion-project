// New Investigation — the generalized, product-center entrance to Model Autopsy.
//
// Five explicit steps, independent of any case study:
//   1. Bring your model (upload artifacts from disk)
//   2. Understand the material (what can be established, what is unknown)
//   3. Configure the investigation (concern + task type)
//   4. Investigation begins (engine stages, inspectable)
//   5. Results (report structure: discovery vs verification vs confirmation)
//
// Unknowns are displayed as unknown — never invented. File types are only
// described, never executed; the backend tools read uploads read-only.
import { useEffect, useRef, useState } from 'react'
import { api, uploadArtifacts, type UploadedFile } from './api'
import { runFullBattery } from './autoBattery'
import { EmptyState, Loading, Note } from './ui'

type Go = (p: 'history' | 'eval' | 'cases' | 'projects' | 'new') => void

const ACCEPT = '.csv,.json,.jsonl,.parquet,.txt,.log,.md,.py,.yaml,.yml,.toml,.cfg,.ini,.zip'

const CONCERN_PRESETS: { label: string; text: string }[] = [
  { label: 'Good in training, poor on unseen data', text: 'The model performs well during training but poorly on unseen data. Check for overfitting, leakage, and distribution shift between splits.' },
  { label: 'Suspected data leakage', text: 'I suspect data leakage: some feature may carry information about the target that will not be available at prediction time.' },
  { label: 'Biased toward certain classes', text: 'Predictions appear biased toward certain classes. Examine label balance, threshold behavior, calibration, and subgroup performance.' },
  { label: 'Performance decayed over time', text: 'Model performance has deteriorated over time. Examine chronology, drift, and whether recent data differs from the training window.' },
  { label: 'Broad investigation — I don’t know what’s wrong', text: 'I don’t know what’s wrong. Investigate the model broadly: data quality, validation design, calibration, and competing failure hypotheses.' },
]

const TASK_TYPES = ['unknown', 'classification', 'regression', 'forecasting', 'ranking', 'clustering', 'other'] as const

const STAGES = [
  { n: '01', name: 'Artifact inspection', desc: 'load uploads read-only, record provenance' },
  { n: '02', name: 'Diagnostic experiments', desc: 'bounded tools run against real artifacts' },
  { n: '03', name: 'Hypothesis generation', desc: 'competing, falsifiable explanations' },
  { n: '04', name: 'Evidence collection', desc: 'every claim linked to recorded output' },
  { n: '05', name: 'Independent verification', desc: 'separate tool path reproduces findings' },
  { n: '06', name: 'Final conclusions', desc: 'auditable report with limitations' },
]

function missingEvidence(files: UploadedFile[]): { label: string; present: boolean; hint: string }[] {
  const names = files.map((f) => f.name.toLowerCase()).join('\n')
  const hasCsv = files.some((f) => /\.(csv|jsonl?|parquet)$/.test(f.name.toLowerCase()))
  const hasScores = /score|pred|prob|logit|oof|predict/.test(names)
  const hasLabels = /label|target|truth|actual|y_|ground/.test(names)
  const hasScript = files.some((f) => /\.py$/.test(f.name.toLowerCase()))
  const hasConfig = files.some((f) => /\.(yaml|yml|toml|cfg|ini|json)$/.test(f.name.toLowerCase()))
  const hasLogs = files.some((f) => /\.(log|txt|md)$/.test(f.name.toLowerCase()))
  return [
    { label: 'Predictions + ground truth', present: hasCsv && (hasScores || hasLabels), hint: hasCsv ? 'dataset-like file present — confirm it carries both score and label columns' : 'upload a predictions file (CSV/JSONL/Parquet with score + label columns)' },
    { label: 'Model / project bundle', present: files.some((f) => /\.zip$/.test(f.name.toLowerCase())), hint: 'a .zip bundle with model files or source helps, but is never executed' },
    { label: 'Training / evaluation scripts', present: hasScript, hint: 'scripts are read for provenance only — what was trained, how it was split' },
    { label: 'Configuration', present: hasConfig, hint: 'hyperparameters, thresholds, and environment notes disambiguate results' },
    { label: 'Logs & experiment records', present: hasLogs, hint: 'logs establish chronology: what ran, when, on which data' },
  ]
}

export function NewInvestigationPage({ onOpen, onGo }: { onOpen: (id: string) => void; onGo: Go }) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loadingUploads, setLoadingUploads] = useState(true)
  const [uploadErr, setUploadErr] = useState('')
  const [uploading, setUploading] = useState(false)
  const [predPath, setPredPath] = useState('')
  const [excluded, setExcluded] = useState<Set<string>>(new Set())
  const [showAllFiles, setShowAllFiles] = useState(false)
  const [lastBatchSize, setLastBatchSize] = useState(0)
  const included = files.filter((f) => !excluded.has(f.path))
  // Show the 10 most recent files; a bulk upload bigger than that stays
  // fully visible so nothing the user just added is hidden from them.
  const batchWindow = Math.max(10, lastBatchSize)
  const visibleFiles = showAllFiles ? files : files.slice(0, batchWindow)
  function toggleInclude(path: string, on: boolean) {
    setExcluded((prev) => {
      const next = new Set(prev)
      if (on) next.delete(path); else next.add(path)
      return next
    })
    if (!on && predPath === path) setPredPath('')
  }
  const [title, setTitle] = useState('Model investigation — uploaded artifacts')
  const [taskType, setTaskType] = useState<(typeof TASK_TYPES)[number]>('unknown')
  const [modelType, setModelType] = useState('')
  const [concern, setConcern] = useState('')
  const [creating, setCreating] = useState(false)
  const [createErr, setCreateErr] = useState('')
  const [createdId, setCreatedId] = useState<string | null>(null)
  const [scoreCol, setScoreCol] = useState('score')
  const [autoRun, setAutoRun] = useState(true)
  const [autoLog, setAutoLog] = useState<string[]>([])
  const [reportSummary, setReportSummary] = useState<null | {
    confirmed: number; likely: number; rejected: number;
    unresolved: number; evidence: number
  }>(null)
  const fileRef = useRef<HTMLInputElement | null>(null)

  async function refreshUploads() {
    setLoadingUploads(true)
    try {
      const r = await api.uploads()
      setFiles(r.uploads)
      // Never auto-pick a predictions file from history: batches carry no
      // timestamps, so "first CSV in the list" is arbitrary and has caused
      // stale files (e.g. the untouched template) to be diagnosed by
      // surprise. Selection happens explicitly — via "use this file", or
      // automatically only for a CSV in the batch the user just uploaded.
    } catch {
      // uploads endpoint missing on old backends — stay usable
      setFiles([])
    } finally {
      setLoadingUploads(false)
    }
  }

  useEffect(() => { refreshUploads() }, [])

  async function onFilesChosen(list: FileList | null) {
    if (!list || list.length === 0) return
    setUploading(true); setUploadErr('')
    try {
      const r = await uploadArtifacts(Array.from(list))
      setFiles((prev) => [...r.files, ...prev])
      setLastBatchSize(r.files.length)
      setShowAllFiles(false)
      const csv = r.files.find((f) => /\.(csv|jsonl?|parquet)$/i.test(f.name))
      if (csv) setPredPath(csv.path)
    } catch (e) {
      setUploadErr(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const evidence = missingEvidence(included)

  function downloadPredictionsTemplate() {
    const rows = [
      'score,label',
      '0.92,1',
      '0.15,0',
      '0.81,1',
      '0.33,0',
      '0.67,1',
      '0.48,0',
      '0.74,1',
      '0.22,0',
    ]
    const blob = new Blob([rows.join('\n') + '\n'], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'predictions_template.csv'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  async function start() {
    setCreating(true); setCreateErr(''); setCreatedId(null)
    try {
      if (included.length === 0) throw new Error('No files selected — tick at least one file in Step 1 to include in the diagnostic.')
      const questionParts = [
        concern.trim() || 'Broad investigation: examine the uploaded material and surface competing, falsifiable failure hypotheses.',
        `Declared task type: ${taskType}.`,
        modelType.trim() ? `Declared model: ${modelType.trim()}.` : 'Model type: unknown (do not assume).',
        `Included artifacts (${included.length}): ${included.slice(0, 8).map((f) => f.path).join('; ')}${included.length > 8 ? '…' : ''}`,
      ]
      const inv = await api.createInvestigation({
        mode: 'ml',
        title: title.trim() || 'Model investigation — uploaded artifacts',
        question: questionParts.join('\n'),
        predictions_path: predPath.trim() || undefined,
      })
      await api.buildContext(inv.id)
      setCreatedId(inv.id)
      if (autoRun) {
        if (predPath.trim()) {
          await runBattery(inv.id, predPath.trim(), scoreCol.trim() || 'score')
        } else {
          setAutoLog([
            'No predictions file selected — investigation created without auto diagnostics.',
            'Scripts (.py) are read for provenance only and never executed, so they cannot produce predictions.',
            'Pick a predictions CSV in Step 1 ("use this file") and press Start again, or run tools manually in the workspace.',
          ])
        }
      }
    } catch (e) {
      setCreateErr(e instanceof Error ? e.message : String(e))
    } finally {
      setCreating(false)
    }
  }

  /** One-click full investigation: diagnostics battery + report, no extra clicks. */
  async function runBattery(invId: string, pred: string, fallbackScore: string) {
    setAutoLog([]); setReportSummary(null)
    const summary = await runFullBattery(invId, pred, fallbackScore,
      (s) => setAutoLog((l) => [...l, s]))
    setReportSummary(summary)
  }

  return (
    <>
      <div className="casehead">
        <div className="kicker">General-purpose ML investigation platform</div>
        <h1>New Investigation</h1>
        <p className="verdict">
          Bring model artifacts, describe what concerns you — or ask for a broad investigation —
          and receive a rigorous, evidence-linked report. What cannot be established is shown
          as <b>unknown</b>, never invented.
        </p>
        <div className="actionsrow">
          <button className="ghost" onClick={() => onGo('cases')}>First, see the Demand Zone AI case study →</button>
          <button className="ghost" onClick={() => onGo('history')}>Review past investigations →</button>
        </div>
      </div>

      {/* Step 1 */}
      <section className="section" aria-label="Step 1 — Bring your model">
        <h3>Step 1 · Bring your model</h3>
        <h2>Upload files from your computer</h2>
        <p className="sub">
          Diagnostics <b>read</b> files — never execute them. Actively analyzed: CSV / JSON / Parquet predictions &amp; datasets.
          Python scripts are statically inspected for provenance only. Configs, logs, notes and .zip bundles
          are stored as supporting material. The predictions file you select below is the primary diagnostic target.
        </p>
        <div className="actionsrow" style={{ marginBottom: 12 }}>
          <input ref={fileRef} type="file" multiple accept={ACCEPT} style={{ display: 'none' }}
            onChange={(e) => onFilesChosen(e.target.files)} aria-label="Choose model artifacts" />
          <button className="primary" disabled={uploading} onClick={() => fileRef.current?.click()}>
            {uploading ? 'Uploading…' : 'Upload model files'}
          </button>
          <button className="ghost" onClick={refreshUploads}>Refresh file list</button>
          <button className="ghost" onClick={downloadPredictionsTemplate}>
            Download predictions CSV template
          </button>
          <span className="faint">≤50 MB each · no predictions file yet? Download the template, add your scores + labels, upload it back.</span>
        </div>
        {uploadErr && <Note kind="bad">{uploadErr}</Note>}
        {loadingUploads ? <Loading what="Listing uploaded artifacts" /> : files.length === 0 ? (
          <EmptyState what="No artifacts uploaded yet."
            action="Choose files above — the investigation adapts to whatever evidence is available." />
        ) : (
          <>
          <div className="actionsrow" style={{ margin: '0 0 8px' }}>
            <span className="faint" style={{ fontSize: 12 }}>
              {included.length} of {files.length} file{files.length === 1 ? '' : 's'} will go into the diagnostic.
            </span>
            <button className="ghost" onClick={() => setExcluded(new Set())}>Select all</button>
            <button className="ghost" onClick={() => { setExcluded(new Set(files.map((f) => f.path))); setPredPath('') }}>Unselect all</button>
          </div>
          <div className="tablewrap">
            <table>
              <thead><tr><th>Include</th><th>File</th><th>Kind</th><th className="num">Bytes</th><th>Analysis</th><th>Use as predictions</th><th>Manage</th></tr></thead>
              <tbody>
                {visibleFiles.map((f) => (
                  <tr key={f.batch + '/' + f.name} style={excluded.has(f.path) ? { opacity: 0.45 } : undefined}>
                    <td>
                      <input type="checkbox" aria-label={`Include ${f.name} in the diagnostic`}
                        checked={!excluded.has(f.path)}
                        onChange={(e) => toggleInclude(f.path, e.target.checked)} />
                    </td>
                    <td><code className="inline">{f.name}</code><br /><span className="faint">{f.path}</span>{f.is_duplicate && <><br /><span className="pill warn" title={f.duplicate_of}>duplicate content</span></>}</td>
                    <td className="muted">{f.kind}</td>
                    <td className="num">{f.bytes.toLocaleString()}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{f.analysis_note ?? (f.kind.includes('script') || f.name.endsWith('.py') ? 'statically inspected, never executed' : '—')}</td>
                    <td>
                      {/\.(csv|jsonl?|parquet)$/i.test(f.name)
                        ? <button className={predPath === f.path ? 'ghost' : 'link'} disabled={predPath === f.path}
                            title={predPath === f.path ? 'This file is the primary diagnostic target' : 'Select as the primary diagnostic target (also includes the file)'}
                            onClick={() => { toggleInclude(f.path, true); setPredPath(f.path) }}>{predPath === f.path ? 'selected ✓ primary' : 'use this file'}</button>
                        : <span className="faint" title="Only CSV/JSON/Parquet can be the primary diagnostic target">—</span>}
                    </td>
                    <td>
                      <button className="link" title="Remove from selectable history (bytes retained for existing investigations)" onClick={async () => {
                        try { await api.removeUpload(f.batch, f.name); refreshUploads() } catch (e) { setUploadErr(e instanceof Error ? e.message : String(e)) }
                      }}>remove</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!showAllFiles && files.length > visibleFiles.length && (
            <p style={{ margin: '8px 0 0' }}>
              <button className="link" onClick={() => setShowAllFiles(true)}>
                Show all {files.length} files ({files.length - visibleFiles.length} older hidden)
              </button>
            </p>
          )}
          {showAllFiles && files.length > batchWindow && (
            <p style={{ margin: '8px 0 0' }}>
              <button className="link" onClick={() => setShowAllFiles(false)}>Show recent {batchWindow} only</button>
            </p>
          )}
          <p className="faint" style={{ fontSize: 12 }}>To replace a file, upload the new version, select it as primary with “use this file”, then remove the old entry. Removal hides it from this list; investigations that already reference it keep their evidence intact.</p>
          </>
        )}
      </section>

      {/* Step 2 */}
      <section className="section" aria-label="Step 2 — Understand the model">
        <h3>Step 2 · Understand the model</h3>
        <h2>What can be established from this material</h2>
        <p className="sub">
          A model file alone is rarely enough to diagnose behavior. The checklist below inspects your
          uploads and names the missing evidence that would sharpen the investigation.
        </p>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Property</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Model type</td><td>{modelType.trim() || <span className="faint">unknown — declare below, or leave unknown</span>}</td></tr>
              <tr><td>Task</td><td>{taskType === 'unknown' ? <span className="faint">unknown</span> : taskType}</td></tr>
              <tr><td>Framework</td><td><span className="faint">unknown — inferred from bundle / config when present</span></td></tr>
              <tr><td>Input features</td><td><span className="faint">unknown — established from dataset / predictions header</span></td></tr>
              <tr><td>Artifacts on hand</td><td className="num">{included.length} selected ({files.length} uploaded)</td></tr>
              <tr><td>Predictions source</td><td>{predPath ? <code className="inline">{predPath}</code> : <span className="faint">none selected — diagnostics needing scores will report the gap</span>}</td></tr>
            </tbody>
          </table>
        </div>
        <h3 style={{ marginTop: 18 }}>Missing-evidence checklist</h3>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Evidence</th><th>Status</th><th>Why it matters</th></tr></thead>
            <tbody>
              {evidence.map((e) => (
                <tr key={e.label}>
                  <td>{e.label}</td>
                  <td>{e.present ? <span className="pill ok">present?</span> : <span className="pill warn">missing</span>}</td>
                  <td className="muted">{e.hint}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Step 3 */}
      <section className="section" aria-label="Step 3 — Configure the investigation">
        <h3>Step 3 · Configure the investigation</h3>
        <h2>What concerns you?</h2>
        <p className="sub">Pick a preset or write your own. There is always a general option for when you don’t know what to look for.</p>
        <div className="actionsrow" style={{ marginBottom: 12 }}>
          {CONCERN_PRESETS.map((p) => (
            <button key={p.label} className="ghost" onClick={() => setConcern(p.text)}>{p.label}</button>
          ))}
        </div>
        <div className="row" style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div className="field" style={{ maxWidth: 320 }}>
            <label htmlFor="ni-title">Investigation title</label>
            <input id="ni-title" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field" style={{ maxWidth: 220 }}>
            <label htmlFor="ni-task">Task type</label>
            <select id="ni-task" value={taskType} onChange={(e) => setTaskType(e.target.value as typeof taskType)}>
              {TASK_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div className="field" style={{ maxWidth: 320 }}>
            <label htmlFor="ni-model">Model type (optional — unknown is fine)</label>
            <input id="ni-model" value={modelType} placeholder="e.g. gradient boosting, ResNet, BPE-LM…"
              onChange={(e) => setModelType(e.target.value)} />
          </div>
        </div>
        <div className="field" style={{ marginTop: 10 }}>
          <label htmlFor="ni-concern">Concern / question</label>
          <textarea id="ni-concern" value={concern} onChange={(e) => setConcern(e.target.value)}
            placeholder="e.g. My model performs well during training but poorly on unseen data — or leave blank for a broad investigation." />
        </div>
        <div className="row" style={{ display: 'flex', gap: 14, flexWrap: 'wrap', alignItems: 'flex-end', marginTop: 10 }}>
          <div className="field" style={{ maxWidth: 560, flex: 2 }}>
            <label htmlFor="ni-pred">Predictions path override (optional)</label>
            <input id="ni-pred" value={predPath} placeholder="blank = no score-based diagnostics"
              onChange={(e) => setPredPath(e.target.value)} />
          </div>
          <div className="field" style={{ maxWidth: 200 }}>
            <label htmlFor="ni-score">Score column</label>
            <input id="ni-score" value={scoreCol} placeholder="score"
              onChange={(e) => setScoreCol(e.target.value)} />
          </div>
        </div>
        <p className="faint" style={{ fontSize: 12 }}>
          The score column is auto-detected from the uploaded file when Step 4 runs — only change this if your scores live under an unusual column name.
        </p>
      </section>

      {/* Step 4 */}
      <section className="section" aria-label="Step 4 — Investigation begins">
        <h3>Step 4 · Investigation begins</h3>
        <h2>The engine becomes the centerpiece</h2>
        <p className="sub">
          Creating the investigation loads artifact context, then the workspace exposes each stage for
          inspection — never an unexplained loading animation.
        </p>
        <div className="tablewrap">
          <table>
            <thead><tr><th>#</th><th>Stage</th><th>What you inspect</th></tr></thead>
            <tbody>
              {STAGES.map((s) => (
                <tr key={s.n}><td className="num">{s.n}</td><td>{s.name}</td><td className="muted">{s.desc}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="field" style={{ marginTop: 12 }}>
          <label style={{ display: 'flex', gap: 8, alignItems: 'center', cursor: 'pointer' }}>
            <input type="checkbox" checked={autoRun} style={{ width: 'auto' }}
              onChange={(e) => setAutoRun(e.target.checked)} />
            Run the full investigation automatically — diagnostics battery + report, one click
          </label>
        </div>
        <div className="verdict">
          {predPath
            ? <><b>Will diagnose</b> <code className="inline">{predPath}</code>{' '}
                <span className="faint">change it with “use this file” in Step 1</span></>
            : <><span className="pill warn">no predictions file selected</span><span className="faint">auto diagnostics will be skipped</span></>}
        </div>
        <div className="actionsrow" style={{ marginTop: 12 }}>
          <button className="primary" disabled={creating} onClick={start}>
            {creating ? 'Running full investigation…' : autoRun ? 'Start — upload, diagnose, report' : 'Start investigation'}
          </button>
          <span className="faint">Budget: ≤3 iterations, ≤12 tool calls — tight by design.</span>
        </div>
        {createErr && <Note kind="bad">{createErr}</Note>}
        {autoLog.length > 0 && (
          <details style={{ marginTop: 8 }}>
            <summary className="faint" style={{ cursor: 'pointer', fontSize: 12 }}>Auto-investigation log ({autoLog.length})</summary>
            <ul className="tl" style={{ marginTop: 6 }}>
              {autoLog.map((line, i) => (
                <li key={i} className="k-info"><span className="tlt">{line}</span></li>
              ))}
            </ul>
          </details>
        )}
        {createdId && (
          <Note kind="ok">
            {reportSummary
              ? <>Diagnostic battery finished — report: {reportSummary.confirmed} confirmed · {reportSummary.likely} likely · {reportSummary.unresolved} unresolved · {reportSummary.evidence} evidence actions. Execution finished; check the workspace scientific assessment for what is actually established.{' '}</>
              : <>Investigation created and context loaded.{' '}</>}
            <button className="link" onClick={() => onOpen(createdId)}>Open the workspace →</button>
          </Note>
        )}
      </section>

      {/* Step 5 */}
      <section className="section" aria-label="Step 5 — Results">
        <h3>Step 5 · Results</h3>
        <h2>What a finished report contains</h2>
        <p className="sub">
          Discovery, evidence, verification, and confirmation are visually distinct throughout the report —
          supported findings never look like open questions.
        </p>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Section</th><th>Answers</th></tr></thead>
            <tbody>
              <tr><td>Executive summary</td><td className="muted">What was discovered, in plain language</td></tr>
              <tr><td>Findings</td><td className="muted">What problems were identified</td></tr>
              <tr><td>Hypotheses</td><td className="muted">Which explanations were supported, rejected, or remain unresolved</td></tr>
              <tr><td>Evidence</td><td className="muted">What actual experiments support each finding</td></tr>
              <tr><td>Verification</td><td className="muted">Which explanations were independently tested</td></tr>
              <tr><td>Recommendations</td><td className="muted">What to investigate or change next</td></tr>
              <tr><td>Reproducibility</td><td className="muted">Whether the investigation can be repeated</td></tr>
            </tbody>
          </table>
        </div>
        <Note>
          Benchmark evaluations of the investigator itself live on the <b>Evaluation</b> page — sealed
          ground truth, mechanism-level scoring. Your uploads and investigations are never mixed into
          those corpora; user history stays on the <b>History</b> page.
        </Note>

      </section>
    </>
  )
}
