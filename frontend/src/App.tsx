import { useQuery } from '@tanstack/react-query'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { getHealth } from './api/client'
import { CareerPage } from './CareerPage'
import { ImportPage } from './ImportPage'
import { ProfilePage } from './ProfilePage'
import { LettersPage } from './LettersPage'
import { PromptsPage } from './PromptsPage'
import { TemplatesPage } from './TemplatesPage'
import { ResumePage } from './ResumePage'
import { AISettingsPage } from './AISettingsPage'
import { JobsPage } from './JobsPage'
import { GenerationPage } from './GenerationPage'
import { HistoryPage } from './HistoryPage'
import { ApplicationsPage } from './ApplicationsPage'
import { PrivacyPage } from './PrivacyPage'
import { WorkspaceGate } from './WorkspaceGate'
import { RouteFocus, RouteRecovery } from './RouteRecovery'

function Overview() {
  const health = useQuery({ queryKey: ['health'], queryFn: ({ signal }) => getHealth(signal) })
  return (
    <>
      <p className="eyebrow">YOUR CAREER, IN YOUR WORDS</p>
      <h1>A stronger story.<br /><span>Built on your experience.</span></h1>
      <p className="intro">A private workspace for your career history, thoughtful resumes, and your next opportunity.</p>
      <section className="status-card" aria-labelledby="status-title">
        <div className="card-header"><h2 id="status-title">Workspace connection</h2><span className="pill">Local workspace</span></div>
        {health.isPending && <p role="status">Connecting to your workspace…</p>}
        {health.isError && (
          <div role="alert">
            <p>{health.error.message}</p>
            <button type="button" onClick={() => void health.refetch()}>Try again</button>
          </div>
        )}
        {health.data && (
          <div role="status">
            <p className="connected"><span aria-hidden="true">●</span> Backend connected</p>
            <dl className="details">
              <div><dt>Database</dt><dd>{health.data.database}</dd></div>
              <div><dt>Mode</dt><dd>{health.data.mode}</dd></div>
              <div><dt>Version</dt><dd>{health.data.version}</dd></div>
            </dl>
          </div>
        )}
      </section>
      <section className="next" aria-labelledby="next-title">
        <p className="eyebrow">WHAT COMES NEXT</p>
        <h2 id="next-title">Start with the facts.</h2>
        <p>Add your career history, build a master resume, and download a PDF from the same renderer used for your preview.</p>
        <div className="actions"><NavLink to="/career/experience">Enter career history →</NavLink><NavLink to="/resumes">Build a master resume →</NavLink></div>
      </section>
    </>
  )
}

export function App() {
  const location = useLocation()
  return (
    <WorkspaceGate><div className="workspace">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <aside className="sidebar">
        <NavLink to="/" className="brand"><span className="brand-mark" aria-hidden="true">r.</span>Resume Tailor</NavLink>
        <p className="nav-caption">WORKSPACE</p>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>Overview</NavLink>
          <NavLink to="/career/experience">Career library</NavLink>
          <NavLink to="/imports">Import resume</NavLink>
          <NavLink to="/profile">Strengthen profile</NavLink>
          <NavLink to="/letters">Cover letters</NavLink>
          <NavLink to="/prompts">Prompt playground</NavLink>
          <NavLink to="/templates">Custom templates</NavLink>
          <NavLink to="/resumes">Master resumes</NavLink>
          <NavLink to="/jobs">Job analysis</NavLink>
          <NavLink to="/generate">Generate & review</NavLink>
          <NavLink to="/settings/ai">AI settings</NavLink>
          <NavLink to="/history">Resume history & ATS</NavLink>
          <NavLink to="/applications">Applications</NavLink>
          <NavLink to="/privacy">Privacy</NavLink>
        </nav>
        <div className="sidebar-note"><span aria-hidden="true">◌</span><p>Designed for your machine.<br />Grounded in your experience.</p></div>
      </aside>
      <div className="content">
        <header className="topbar"><span>Personal workspace</span><span className="local-label">Local first</span></header>
        <main id="main-content" tabIndex={-1}>
          <RouteFocus />
          <RouteRecovery key={location.pathname}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/career/:kind" element={<CareerPage />} />
            <Route path="/imports" element={<ImportPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/letters" element={<LettersPage />} />
            <Route path="/prompts" element={<PromptsPage />} />
            <Route path="/templates" element={<TemplatesPage />} />
            <Route path="/resumes" element={<ResumePage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/generate" element={<GenerationPage />} />
            <Route path="/settings/ai" element={<AISettingsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="*" element={<><h1>Page not found</h1><NavLink to="/">Return to overview</NavLink></>} />
          </Routes>
          </RouteRecovery>
        </main>
        <footer>Resume Tailor · Your local career workspace</footer>
      </div>
    </div></WorkspaceGate>
  )
}
