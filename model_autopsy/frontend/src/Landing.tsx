/* Landing — the cinematic entry experience.
 *
 * Full-bleed scroll narrative: fullscreen hero with the animated neural
 * centerpiece, a real-data metric band, the investigation loop, the
 * problem/process editorial, and the ground band with live investigations
 * and the real case study. Everything below the hero is driven by ACTUAL
 * API data (investigation counts, pooled AUCs, calibration bins, per-fold
 * AUCs). The single conceptual panel is explicitly labeled as such.
 */
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, CaseMetrics, InvestigationSummary, useLoading } from './api'
import { initNeuralScene } from './NeuralScene'

type Go = (p: 'software' | 'ml' | 'history' | 'settings') => void

const LINKS: { key: 'software' | 'ml' | 'history' | 'settings'; label: string }[] = [
  { key: 'ml', label: 'Case Study' },
  { key: 'software', label: 'Software' },
  { key: 'history', label: 'History' },
  { key: 'settings', label: 'Settings' },
]

export default function Landing({ onOpen, onGo }: { onOpen: (id: string) => void; onGo: Go }) {
  return (
    <div className="landing">
      <LandingNav onGo={onGo} />
      <Hero onGo={onGo} />
      <Landbar />
      <ProblemProcess />
      <GroundBand onOpen={onOpen} onGo={onGo} />
      <Footnote />
    </div>
  )
}

/* ================================================================
   scroll reveal
   ================================================================ */
function Reveal({ children, className = '', delay = 0, as: Tag = 'div' }: {
  children: ReactNode; className?: string; delay?: 0 | 1 | 2 | 3; as?: 'div' | 'section' | 'span'
}) {
  const ref = useRef<HTMLElement | null>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) { el.classList.add('in'); io.disconnect() }
      }
    }, { threshold: 0.18 })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <Tag ref={ref as never}
      className={`rv${delay ? ` rv-d${delay}` : ''} ${className}`}>
      {children}
    </Tag>
  )
}

/* ================================================================
   nav
   ================================================================ */
function LandingNav({ onGo }: { onGo: Go }) {
  const [solid, setSolid] = useState(false)
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <header className={`topnav${solid ? '' : ' transparent'}`}>
      <button className="brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
        <span className="mark" aria-hidden>∿</span>
        Model Autopsy
      </button>
      <nav className="pagestabs" aria-label="Primary">
        {LINKS.map((l) => (
          <button key={l.key} onClick={() => onGo(l.key)}>{l.label}</button>
        ))}
      </nav>
      <ManualModeChip />
    </header>
  )
}

function ManualModeChip() {
  const { data } = useLoading<{ key_configured: boolean }>(() => api.metaStatus())
  const configured = data?.key_configured
  return (
    <span className={`modechip${configured ? ' live' : ''}`}
      title={configured
        ? 'MODEL_API_KEY configured — Meta-assisted turns available'
        : 'MODEL_API_KEY not configured — the app runs in manual mode; every diagnostic still works end to end'}>
      <span className="dot" aria-hidden />
      {configured ? 'Meta assists' : 'Manual Mode'}
    </span>
  )
}

/* ================================================================
   hero
   ================================================================ */
function Hero({ onGo }: { onGo: Go }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [webgl, setWebgl] = useState(true)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const handles = initNeuralScene(canvas)
    if (!handles) { setWebgl(false); return }
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const maxScan = window.innerHeight + 200
        handles.setScrollProgress(Math.min(1, window.scrollY / maxScan))
      })
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(raf); handles.dispose() }
  }, [])

  return (
    <section className="hero">
      <div className="grid-bg" aria-hidden />
      <div className="nebula-bg" aria-hidden />

      <div className="hero-stage" aria-hidden>
        {webgl
          ? <canvas ref={canvasRef} style={{ width: 'min(72vw, 900px)', height: 'min(78vh, 760px)' }} />
          : <div style={{
              position: 'absolute', right: '2%', top: '50%', transform: 'translateY(-50%)',
              width: 'min(46vw, 640px)', height: 'min(46vw, 640px)',
              background:
                'radial-gradient(circle at 50% 50%, rgba(139,124,246,0.3), transparent 58%),' +
                'radial-gradient(circle at 38% 42%, rgba(56,217,232,0.2), transparent 52%)',
            }} />}
        <HeroAnnotations />
      </div>

      <div className="hero-copy">
        <div className="hero-kicker">AI Model Forensics</div>
        <h1>
          When performance<br />
          hides the <span className="truth">truth</span>
        </h1>
        <p className="hero-sub">
          Model Autopsy investigates what metrics miss — hidden leakage, poor calibration,
          silent distribution shift — with bounded diagnostics run on <b>real artifacts</b>,
          hypotheses linked to evidence, and a <b>final report you can audit</b>.
        </p>
        <div className="hero-ctas">
          <button className="cta-primary" onClick={() => onGo('ml')}>
            Explore the Case Study <span className="arrow" aria-hidden>→</span>
          </button>
          <button className="cta-ghost" onClick={() => {
            document.getElementById('ground')?.scrollIntoView({ behavior: 'smooth' })
          }}>
            <span className="play" aria-hidden>▶</span>
            See live investigations
          </button>
        </div>
      </div>

      <div className="scrollcue" aria-hidden>
        <span>Scroll to explore</span>
        <div className="scrollpill"><i /></div>
      </div>
    </section>
  )
}

/* annotation callouts pinned over the neural structure */
function HeroAnnotations() {
  const items = [
    { top: '16%', left: '44%', label: 'Data Drift', sub: 'distribution shift detected',
      color: 'var(--accent-3)', lx: '24%', ly: '150%' },
    { top: '8%', left: '62%', label: 'Calibration', sub: 'under-confident buckets',
      color: 'var(--accent)', lx: '40%', ly: '120%' },
    { top: '56%', left: '60%', label: 'Feature Leakage', sub: 'suspicious correlation',
      color: 'var(--accent-2)', lx: '46%', ly: '120%' },
  ]
  return (
    <>
      {items.map((a) => (
        <div key={a.label} className="hero-annotation" style={{ top: a.top, left: a.left }}>
          <div className="pt"><span className="dot" style={{ background: a.color, color: a.color }} />{a.label}</div>
          <p className="sub">{a.sub}</p>
        </div>
      ))}
    </>
  )
}

/* ================================================================
   metric band — REAL investigation counts + REAL pooled AUCs
   ================================================================ */
function Landbar() {
  const { data: inv } = useLoading<{ items: InvestigationSummary[] }>(() => api.listInvestigations())
  const { data: m } = useLoading<CaseMetrics>(() => api.caseMetrics(200))

  const items = inv?.items ?? []
  const real = items.filter((i) => !i.is_test_record)
  const active = real.filter((i) => !['complete', 'failed', 'stopped'].includes(i.status))
  const completed = real.filter((i) => i.status === 'complete')
  const pooled = m?.pooled_auc ?? null

  return (
    <section className="landbar">
      <Reveal className="col">
        <h4><span className="live">●</span> Live System</h4>
        <div className="statrow">
          <div className="stat">
            <div className="n">{real.length}</div>
            <div className="l"><b>{real.length === 1 ? 'investigation' : 'investigations'}</b> real data, test records excluded</div>
          </div>
          <div className="stat">
            <div className="n">{active.length}</div>
            <div className="l"><b>{active.length === 1 ? 'is' : 'are'} active</b> in progress now</div>
          </div>
          <div className="stat">
            <div className="n">{completed.length}</div>
            <div className="l"><b>{completed.length === 1 ? 'complete' : 'complete'}</b> with reports on record</div>
          </div>
        </div>
      </Reveal>

      <Reveal className="col" delay={1}>
        <h4><span className="spark">◫</span> Real Case Study Metrics</h4>
        {pooled ? (
          <div className="aucrow">
            {(['LogisticRegression_A', 'LightGBM_A', 'LogisticRegression_B', 'LightGBM_B'] as const)
              .filter((k) => k in pooled)
              .map((k) => (
                <div className="auc" key={k}>
                  <div className="a">{pooled[k].toFixed(3)}</div>
                  <div className="t">{shortArm(k)}</div>
                </div>
              ))}
          </div>
        ) : (
          <div className="faint" style={{ fontSize: 12.5, paddingTop: 8 }}>computing from the frozen artifact…</div>
        )}
        <div className="aucsrc">pooled AUC recomputed live from the actual OOF artifact</div>
      </Reveal>

      <Reveal className="col loopcol" delay={2}>
        <h4><span className="loop">⟲</span> The Investigation Loop</h4>
        <div className="loopflow">
          {[
            { n: '01', nm: 'Context', ds: 'load data & environment' },
            { n: '02', nm: 'Diagnose', ds: 'run tools & collect evidence' },
            { n: '03', nm: 'Hypothesize', ds: 'test and validate with data' },
            { n: '04', nm: 'Report', ds: 'document findings with sources' },
          ].map((s) => (
            <div className="loopnode" key={s.n}>
              <div className="ic">{s.n}</div>
              <div>
                <div className="nm">{s.nm}</div>
                <div className="ds">{s.ds}</div>
              </div>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  )
}

function shortArm(k: string): string {
  if (k.startsWith('LogisticRegression_')) return 'LR ' + k.slice(-1)
  if (k.startsWith('LightGBM_')) return 'LGBM ' + k.slice(-1)
  return k
}

/* ================================================================
   problem / process — animated diagnostic deck (real + 1 labeled concept)
   ================================================================ */
function ProblemProcess() {
  const { data: m } = useLoading<CaseMetrics>(() => api.caseMetrics(200))
  return (
    <section className="landsection">
      <div className="probgrid">
        <Reveal>
          <div className="kicker-sm">The Problem</div>
          <h2 className="probh">Models can look good<br />while still <em>failing.</em></h2>
          <p className="probp">
            Hidden leakage. Poor calibration. Distribution shift. The real issues aren't
            always visible in headline metrics — so our real issues aren't always visible
            in your metrics, either.
          </p>
          <button className="landlink" onClick={() => {
            document.getElementById('ground')?.scrollIntoView({ behavior: 'smooth' })
          }}>
            See real examples <span className="arrow" aria-hidden>→</span>
          </button>
        </Reveal>

        <Reveal className="paneldeck" delay={1}>
          <DiagPanel title="Calibration" icon="◫"
            className="deck-a" render={(cv) => drawCalibration(cv, m ?? undefined)}>
            <p className="concept">predicted vs observed — computed from the real artifact</p>
          </DiagPanel>
          <DiagPanel title="Distribution Shift" icon="⇋"
            className="deck-b" render={(cv) => drawFoldAuc(cv, m ?? undefined)}>
            <p className="concept">per-fold AUC — computed from the real artifact</p>
          </DiagPanel>
          <DiagPanel title="Feature Leakage" icon="∿"
            className="deck-c" render={drawLeakConcept} concept>
            <p className="concept">conceptual illustration — not a measured result</p>
          </DiagPanel>
        </Reveal>

        <Reveal className="probright" delay={2}>
          <div className="kicker-sm violet">The Process</div>
          <h2 className="probh">From evidence<br />to answers.</h2>
          <ul className="processlist">
            <li>Run automated diagnostics on the real artifacts and record every output.</li>
            <li>Form competing, falsifiable hypotheses.</li>
            <li>Link every conclusion to the exact evidence that supports it.</li>
          </ul>
          <button className="landlink" onClick={() => {
            document.getElementById('ground')?.scrollIntoView({ behavior: 'smooth' })
          }}>
            Learn how it works <span className="arrow" aria-hidden>→</span>
          </button>
        </Reveal>
      </div>
    </section>
  )
}

function DiagPanel({ title, icon, render, className = '', children, concept = false, virusless = false }: {
  title: string; icon: string; render?: (cv: HTMLCanvasElement) => void
  className?: string; children?: ReactNode; concept?: boolean; virusless?: boolean
}) {
  const ref = useRef<HTMLCanvasElement | null>(null)
  useEffect(() => {
    const draw = () => {
      const cv = ref.current
      if (!cv) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = cv.clientWidth, h = cv.clientHeight
      cv.width = w * dpr; cv.height = h * dpr
      const g = cv.getContext('2d')
      if (!g) return
      g.setTransform(dpr, 0, 0, dpr, 0, 0)
      g.clearRect(0, 0, w, h)
      if (concept) drawLeakAnimation(g, w, h)
      else render?.(cv)
    }
    draw()
    const ro = new ResizeObserver(draw)
    if (ref.current) ro.observe(ref.current)
    return () => ro.disconnect()
  }, [concept, render])

  return (
    <div className={`diagpanel ${className}`}>
      <div className="ph">
        <span className="ic" aria-hidden>{icon}</span>
        <b style={{ fontWeight: 600 }}>{title}</b>
        <span className="pl" aria-hidden>⋮</span>
        {virusless ? <HintBadge kind="warn" text="Conceptual" /> : null}
      </div>
      <canvas ref={ref} style={{ width: 240, height: 132 }} />
      {children}
    </div>
  )
}

function HintBadge({ kind, text }: { kind: 'warn' | 'ok'; text: string }) {
  return (
    <span className={`pill ${kind}`} style={{ marginLeft: 'auto', fontSize: 9, padding: '1px 7px' }}>{text}</span>
  )
}

/* ---- concept drift panel canvas ---- */
function drawCalibration(cv: HTMLCanvasElement, m: CaseMetrics | undefined) {
  const w = cv.clientWidth, h = cv.clientHeight
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  cv.width = w * dpr; cv.height = h * dpr
  const g = cv.getContext('2d')
  if (!g) return
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  const pad = 14
  const ax = pad, ay = pad, aw = w - 2 * pad, ah = h - 2 * pad

  // gridlines
  g.strokeStyle = 'rgba(29,36,64,0.9)'
  g.lineWidth = 1
  for (let i = 0; i <= 4; i++) {
    const y = ay + (ah * i) / 4
    g.beginPath(); g.moveTo(ax, y); g.lineTo(ax + aw, y); g.stroke()
  }
  // perfect-diagonal reference
  g.strokeStyle = 'rgba(141,149,178,0.4)'
  g.setLineDash([4, 3])
  g.beginPath(); g.moveTo(ax, ay + ah); g.lineTo(ax + aw, ay); g.stroke()
  g.setLineDash([])

  // real calibration bins
  const bins = m?.calibration?.reliability_bins
  if (bins && bins.length > 1) {
    const xs = bins.map((b) => b.mean_score)
    const ys = bins.map((b) => b.fraction_positive)
    const x0 = Math.min(...xs), x1 = Math.max(...xs)
    const y0 = Math.min(...ys), y1 = Math.max(...ys)
    const sx = (x: number) => ax + ((x - x0) / Math.max(1e-6, x1 - x0)) * aw
    const sy = (y: number) => ay + ah - ((y - y0) / Math.max(1e-6, y1 - y0)) * ah
    // under envelope
    g.strokeStyle = 'rgba(139,124,246,0.35)'; g.lineWidth = 3
    g.beginPath()
    bins.forEach((_, i) => (i === 0 ? g.moveTo(sx(xs[0]), sy(ys[0])) : g.lineTo(sx(xs[i]), sy(ys[i]))))
    g.stroke()
    // crisp line
    g.strokeStyle = 'rgba(56,217,232,0.95)'; g.lineWidth = 1.4
    g.beginPath()
    bins.forEach((_, i) => (i === 0 ? g.moveTo(sx(xs[0]), sy(ys[0])) : g.lineTo(sx(xs[i]), sy(ys[i]))))
    g.stroke()
    for (const [i] of bins.entries()) {
      g.beginPath(); g.arc(sx(xs[i]), sy(ys[i]), 2.4, 0, Math.PI * 2)
      g.fillStyle = 'rgba(56,217,232,1)'; g.fill()
    }
  } else {
    g.fillStyle = 'rgba(93,102,132,0.9)'
    g.font = '10px "IBM Plex Mono", monospace'
    g.fillText('calibration bins unavailable', ax + 8, ay + ah / 2)
  }
}

function drawFoldAuc(cv: HTMLCanvasElement, m: CaseMetrics | undefined) {
  const w = cv.clientWidth, h = cv.clientHeight
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  cv.width = w * dpr; cv.height = h * dpr
  const g = cv.getContext('2d')
  if (!g) return
  g.setTransform(dpr, 0, 0, dpr, 0, 0)
  const pad = 14
  const ax = pad, ay = pad, aw = w - 2 * pad, ah = h - 2 * pad

  const perFold = m?.per_fold_auc
  const folds = perFold ? Object.keys(perFold).sort() : []
  for (let i = 0; i <= 4; i++) {
    const y = ay + (ah * i) / 4
    g.strokeStyle = 'rgba(29,36,64,0.9)'; g.lineWidth = 1
    g.beginPath(); g.moveTo(ax, y); g.lineTo(ax + aw, y); g.stroke()
  }
  if (folds.length > 0) {
    const champion = 'LightGBM_B' in (perFold?.[folds[0]] ?? {}) ? 'LightGBM_B' : ('LightGBM_A' in (perFold?.[folds[0]] ?? {}) ? 'LightGBM_A' : Object.keys(perFold?.[folds[0]] ?? {})[0])
    const vals = folds.map((f) => perFold?.[f]?.[champion]).filter((v): v is number => v != null)
    if (vals.length > 1) {
      const lo = Math.min(...vals) - 0.02, hi = Math.max(...vals) + 0.02
      const sx = (i: number) => ax + (aw * i) / (vals.length - 1)
      const sy = (v: number) => ay + ah - ((v - lo) / Math.max(1e-6, hi - lo)) * ah
      // area
      g.beginPath()
      vals.forEach((v, i) => (i === 0 ? g.moveTo(sx(0), sy(v)) : g.lineTo(sx(i), sy(v))))
      g.lineTo(sx(vals.length - 1), ay + ah); g.lineTo(sx(0), ay + ah)
      g.closePath()
      g.fillStyle = 'rgba(139,124,246,0.18)'; g.fill()
      // line
      g.strokeStyle = 'rgba(139,124,246,0.95)'; g.lineWidth = 1.5
      g.beginPath()
      vals.forEach((v, i) => (i === 0 ? g.moveTo(sx(0), sy(v)) : g.lineTo(sx(i), sy(v))))
      g.stroke()
      vals.forEach((v, i) => {
        g.beginPath(); g.arc(sx(i), sy(v), 2.6, 0, Math.PI * 2)
        g.fillStyle = '#8b7cf6'; g.fill()
      })
      g.fillStyle = 'rgba(93,102,132,0.95)'
      g.font = '9px "IBM Plex Mono", monospace'
      folds.forEach((f, i) => g.fillText(f.replace('20', '').slice(0, 3), sx(i) - 4, ay + ah + 0))
    }
  }
}

function drawLeakConcept(cv: HTMLCanvasElement) {
  // handled by animated loop wrapper (concept)
}

function drawLeakAnimation(g: CanvasRenderingContext2D, w: number, h: number) {
  const t = performance.now() / 1000
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const tt = reduced ? 2.0 : t
  // scatter cloud with wave motion
  for (let i = 0; i < 46; i++) {
    const px = 14 + ((i * 37) % (w - 28))
    const py = h / 2 + Math.sin(i * 1.7 + tt * (0.9 + (i % 5) * 0.12)) * (10 + (i % 7) * 3.2)
    const r = 1.2 + (i % 3) * 0.7
    g.beginPath()
    g.arc(px, py, r, 0, Math.PI * 2)
    g.fillStyle = i % 4 === 0
      ? 'rgba(255,92,135,0.9)'
      : i % 3 === 0 ? 'rgba(139,124,246,0.75)' : 'rgba(56,217,232,0.6)'
    g.fill()
  }
  // connecting glow line
  g.strokeStyle = 'rgba(255,92,135,0.4)'
  g.lineWidth = 1
  g.beginPath()
  for (let x = 0; x < w; x += 4) {
    const y = h / 2 + Math.sin(x * 0.06 + tt * 1.4) * 12 + Math.sin(x * 0.021 - tt * 0.7) * 7
    if (x === 0) g.moveTo(x, y)
    else g.lineTo(x, y)
  }
  g.stroke()
}

/* ================================================================
   ground band — live investigations + case study (REAL data)
   ================================================================ */
function GroundBand({ onOpen, onGo }: { onOpen: (id: string) => void; onGo: Go }) {
  const { data: inv } = useLoading<{ items: InvestigationSummary[] }>(() => api.listInvestigations())
  const { data: m, error: mErr } = useLoading<CaseMetrics>(() => api.caseMetrics(200))
  const items = inv?.items ?? []
  const real = items.filter((i) => !i.is_test_record)
  const testCount = items.filter((i) => i.is_test_record).length

  return (
    <section className="landsection groundband" id="ground">
      <Reveal className="landhead">
        <div className="kicker-sm violet">The Workbench</div>
        <h2><em>Real</em> investigations, <em>real</em> evidence,<br /><em>real</em> reports.</h2>
        <p>
          Every number below comes from the running system or the frozen Demand Zone
          artifact — nothing here is decorative or simulated.
        </p>
      </Reveal>

      <div className="groundcols">
        <Reveal>
          <div className="hud">
            <h3>Investigations on record</h3>
            {real.length === 0
              ? <p className="faint" style={{ fontSize: 13 }}>None yet — create the first investigation to populate this view.</p>
              : (
                <div className="tablewrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Title</th><th>Mode</th><th>Status</th><th className="num">Tool calls</th>
                      </tr>
                    </thead>
                    <tbody>
                      {real.slice(0, 6).map((i) => (
                        <tr className="clickable" role="link" tabIndex={0} key={i.id}
                          onClick={() => onOpen(i.id)}
                          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onOpen(i.id) } }}
                          aria-label={`Open investigation ${i.title}`}>
                          <td>{i.title}</td>
                          <td>{i.mode}</td>
                          <td><span className={`pill ${statusTone(i.status)}`}>{i.status.replace('_', ' ')}</span></td>
                          <td className="num">{i.tool_call_count}/{i.max_tool_calls}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            {testCount > 0 && (
              <p className="faint" style={{ fontSize: 11, marginTop: 10 }}>
                {testCount} legacy test-generated record{testCount === 1 ? '' : 's'} exist and are excluded here
                (review via <code className="inline">model_autopsy.backend.prune</code>).
              </p>
            )}
          </div>
          <button className="cta-ghost" onClick={() => onGo('history')}>
            Open full history <span aria-hidden>→</span>
          </button>
        </Reveal>

        <Reveal delay={1}>
          <div className="hud">
            <h3>Demand Zone AI — frozen v1.0.2 champion</h3>
            {mErr
              ? <p className="faint" style={{ fontSize: 12.5 }}>Case metrics unavailable: {mErr}</p>
              : !m ? <p className="faint" style={{ fontSize: 12.5 }}>Recomputing case-study metrics…</p>
              : (
                <>
                  <dl className="kv num" style={{ marginBottom: 14 }}>
                    <dt>OOF rows</dt><dd>{m.n_rows.toLocaleString()}</dd>
                    <dt>Cluster column</dt><dd>{m.cluster_column_used ?? 'none'}</dd>
                    <dt>ΔAUC replicates</dt><dd>{m.delta_auc_pairs[0]?.n_boot ?? '—'}</dd>
                    <dt>Bootstrap unit</dt><dd style={{ fontSize: 12 }}>{m.delta_auc_pairs[0]?.sampling_unit ?? '—'}</dd>
                  </dl>
                  {m.delta_auc_pairs[0] && (
                    <p style={{ fontSize: 12.5, color: 'var(--muted)', margin: '0 0 14px' }}>
                      Largest arm delta: <b style={{ color: 'var(--accent-2)' }}>
                        {shortNameArm(m.delta_auc_pairs[0].score_a)}→{shortNameArm(m.delta_auc_pairs[0].score_b)}
                      </b>{' '}
                      {m.delta_auc_pairs[0].delta >= 0 ? '+' : ''}{m.delta_auc_pairs[0].delta.toFixed(3)}{' '}
                      <span className="faint">({m.delta_auc_pairs[0].ci_low.toFixed(3)} … {m.delta_auc_pairs[0].ci_high.toFixed(3)})</span>
                    </p>
                  )}
                  <p className="faint" style={{ fontSize: 11.5, lineHeight: 1.55 }}>
                    The archived 0.97→0.676 narrative cannot be recomputed here — the leaked-feature
                    dataset is not preserved. Everything shown is currently reproducible from the artifact.
                  </p>
                </>
              )}
            <button className="cta-primary" style={{ marginTop: 14 }} onClick={() => onGo('ml')}>
              Open the case study <span className="arrow" aria-hidden>→</span>
            </button>
          </div>
        </Reveal>
      </div>
      <Footnote />
    </section>
  )
}

function shortNameArm(k: string): string {
  if (k.startsWith('LogisticRegression_')) return 'LR_' + k.slice(-1)
  if (k.startsWith('LightGBM_')) return 'LGBM_' + k.slice(-1)
  return k
}

function statusTone(status: string): string {
  switch (status) {
    case 'context_ready': case 'hypotheses_proposed': case 'investigating': case 'finalizing': return 'accent'
    case 'failed': case 'stopped': case 'blocked': return 'bad'
    case 'complete': return 'ok'
    default: return ''
  }
}

/* ================================================================
   footnote
   ================================================================ */
function Footnote() {
  return (
    <footer className="footnote">
      <span><b>Isolation</b> — the autonomous campaign supervisor is fully independent; no tool here can start, stop, or modify it.</span>
      <span><b>Evidence</b> — all tools are read-only; the platform applies no code changes.</span>
      <span><b>Mode</b> — live Meta inference runs only when MODEL_API_KEY is configured; manual mode works end to end without it.</span>
    </footer>
  )
}
