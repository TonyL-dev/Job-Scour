import { Navigation } from './components/Navigation'
import { Button, PageHeader } from './components/ui/Controls'
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
      <PageHeader eyebrow="YOUR CAREER, IN YOUR WORDS" title="Your next chapter starts here." description="A private space for your experience, your documents, and your next opportunity." />
      <div className="start-grid">
        <NavLink className="start-card" to="/resumes"><span className="eyebrow">YOUR DOCUMENTS</span><strong>Start with your story.</strong><span>Continue a saved resume or create a new master, with your experience at its heart.</span><span className="card-link">Open your resumes <span aria-hidden="true">→</span></span></NavLink>
        <NavLink className="start-card" to="/career/experience"><span className="eyebrow">YOUR EXPERIENCE</span><strong>Keep the details together.</strong><span>Build a career library you can draw on for every opportunity.</span><span className="card-link">Open career library <span aria-hidden="true">→</span></span></NavLink>
      </div>
      <p className="overview-note">Start with the facts. Add your experience, shape a resume, and preview the actual document before you download.</p>
      <section className="connection-panel" aria-labelledby="status-title">
        <div className="card-header"><h2 id="status-title">Workspace connection</h2><span className="pill">Local workspace</span></div>
        {health.isPending && <p role="status">Connecting to your workspace…</p>}
        {health.isError && (
          <div role="alert">
            <p>{health.error.message}</p>
            <Button type="button" onClick={() => void health.refetch()}>Try again</Button>
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

    </>
  )
}

export function App() {
  const location = useLocation()
  return (
    <WorkspaceGate><div className="workspace">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Navigation />
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
