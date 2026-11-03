// App shell — cinematic landing + slim-nav forensic workbench.
import { useState } from 'react'
import Landing from './Landing'
import Workspace from './Workspace'
import { HistoryPage, MLPage, SettingsPage, SoftwarePage } from './pages'
import { ProjectsPage } from './Projects'
import { EvalPage } from './Eval'
import { LabPage } from './Lab'
import { NewInvestigationPage } from './NewInvestigation'

type Page = 'landing' | 'new' | 'cases' | 'software' | 'ml' | 'projects' | 'eval' | 'lab' | 'history' | 'settings'

const NAV: { key: Page; label: string }[] = [
  { key: 'landing', label: 'Home' },
  { key: 'new', label: 'New Investigation' },
  { key: 'cases', label: 'Case Studies' },
  { key: 'projects', label: 'Projects' },
  { key: 'history', label: 'History' },
  { key: 'eval', label: 'Evaluation' },
  { key: 'lab', label: 'Laboratory' },
  { key: 'software', label: 'Software' },
  { key: 'settings', label: 'Settings' },
]

function WorkbenchNav({ page, go }: { page: Page; go: (p: Page) => void }) {
  return (
    <header className="topnav">
      <button className="brand" onClick={() => go('landing')}>
        <span className="mark" aria-hidden>∿</span>
        Model Autopsy
      </button>
      <nav className="pagestabs" aria-label="Primary">
        {NAV.map((n) => (
          <button key={n.key}
            className={n.key === page ? 'active' : ''}
            onClick={() => go(n.key)}
            aria-current={n.key === page ? 'page' : undefined}>
            {n.label}
          </button>
        ))}
      </nav>
      <span className="modechip cyan"><span className="dot" aria-hidden />Workbench</span>
    </header>
  )
}

export default function App() {
  const [page, setPage] = useState<Page>('landing')
  const [detailId, setDetailId] = useState<string | null>(null)

  function go(p: Page) {
    // 'ml' is the legacy Demand Zone route — it now lives under Case Studies.
    const mapped = p === 'ml' ? 'cases' : p
    setPage(mapped); setDetailId(null); window.scrollTo(0, 0)
  }
  function open(id: string) { setDetailId(id); window.scrollTo(0, 0) }

  if (page === 'landing' && !detailId) {
    return <Landing onOpen={open} onGo={go} />
  }

  return (
    <div className="appframe">
      <WorkbenchNav page={page} go={go} />
      <div className="main">
        {detailId
          ? <Workspace id={detailId} onBack={() => { setDetailId(null); window.scrollTo(0, 0) }} />
          : page === 'new'
            ? <NewInvestigationPage onOpen={open} onGo={go} />
            : page === 'cases'
              ? <MLPage onOpen={open} />
              : page === 'software'
              ? <SoftwarePage onOpen={open} />
              : page === 'projects'
              ? <ProjectsPage onOpen={open} />
              : page === 'eval'
              ? <EvalPage />
              : page === 'lab'
              ? <LabPage />
              : page === 'history'
                ? <HistoryPage onOpen={open} />
                : <SettingsPage />}
      </div>
    </div>
  )
}
