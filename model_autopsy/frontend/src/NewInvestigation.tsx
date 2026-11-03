// New Investigation — the generalized, product-center entrance to Model Autopsy.
//
// Upload artifacts, pick the predictions file, start. The investigation
// runs broad by default: the workspace exposes hypotheses, evidence and
// verification for inspection — never an unexplained loading animation.
//
// Unknowns are displayed as unknown — never invented. File types are only
// described, never executed; the backend tools read uploads read-only.
import { useEffect, useRef, useState } from 'react'
import { api, uploadArtifacts, type UploadedFile } from './api'
import { EmptyState, Loading, Note } from './ui'

type Go = (p: 'history' | 'eval' | 'cases' | 'projects' | 'new') => void

const ACCEPT = '.csv,.json,.jsonl,.parquet,.txt,.log,.md,.py,.yaml,.yml,.toml,.cfg,.ini,.zip'

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
  const [creating, setCreating] = useState(false)
  const [createErr, setCreateErr] = useState('')
  const [createdId, setCreatedId] = useState<string | null>(null)
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
      if (included.length === 0) throw new Error('No files selected — tick at least one file above to include in the diagnostic.')
      const questionParts = [
        'Broad investigation: examine the uploaded material and surface competing, falsifiable failure hypotheses.',
        'Declared task type: unknown.',
        'Model type: unknown (do not assume).',
        `Included artifacts (${included.length}): ${included.slice(0, 8).map((f) => f.path).join('; ')}${included.length > 8 ? '…' : ''}`,
      ]
      const inv = await api.createInvestigation({
        mode: 'ml',
        title: 'Model investigation — uploaded artifacts',
        question: questionParts.join('\n'),
        predictions_path: predPath.trim() || undefined,
      })
      await api.buildContext(inv.id)
      setCreatedId(inv.id)
    } catch (e) {
      setCreateErr(e instanceof Error ? e.message : String(e))
    } finally {
      setCreating(false)
    }
  }

  return (
    <>
      <div className="casehead">
        <div className="kicker">General-purpose ML investigation platform</div>
        <h1>New Investigation</h1>
        <p className="verdict">
          Bring model artifacts, pick the predictions file, and start —
          you receive a rigorous, evidence-linked report. What cannot be established is shown
          as <b>unknown</b>, never invented.
        </p>
        <div className="actionsrow">
          <button className="ghost" onClick={() => onGo('cases')}>First, see the Demand Zone AI case study →</button>
          <button className="ghost" onClick={() => onGo('history')}>Review past investigations →</button>
        </div>
      </div>

      <section className="section" aria-label="Bring your model">
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

      <section className="section" aria-label="Start investigation">
        <div className="verdict">
          {predPath
            ? <><b>Will diagnose</b> <code className="inline">{predPath}</code>{' '}
                <span className="faint">change it with “use this file” above</span></>
            : <><span className="pill warn">no predictions file selected</span><span className="faint">auto diagnostics will be skipped</span></>}
        </div>
        <div className="actionsrow" style={{ marginTop: 12 }}>
          <button className="primary" disabled={creating} onClick={start}>
            {creating ? 'Creating…' : 'Start investigation'}
          </button>
          <span className="faint">Meta AI runs the diagnostics in the workspace — no offline battery. Budget: ≤3 iterations, ≤12 tool calls.</span>
        </div>
        {createErr && <Note kind="bad">{createErr}</Note>}
        {createdId && (
          <Note kind="ok">
            <>Investigation created and context loaded. Open the workspace and press “Run bounded Meta turn” — Meta is the investigator.{' '}</>
            <button className="link" onClick={() => onOpen(createdId)}>Open the workspace →</button>
          </Note>
        )}
      </section>
    </>
  )
}
