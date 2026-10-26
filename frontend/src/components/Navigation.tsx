import { useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { Button } from './ui/Controls'

const groups = [
  { label: 'Workspace', links: [['/', 'Overview']] },
  { label: 'Career', links: [['/career/experience', 'Career library'], ['/imports', 'Import resume'], ['/profile', 'Strengthen profile']] },
  { label: 'Documents', links: [['/resumes', 'Master resumes'], ['/letters', 'Cover letters'], ['/history', 'Resume history & ATS'], ['/templates', 'Custom templates']] },
  { label: 'Opportunities', links: [['/jobs', 'Job analysis'], ['/generate', 'Generate & review'], ['/applications', 'Applications']] },
  { label: 'Settings', links: [['/settings/ai', 'AI settings'], ['/prompts', 'Prompt playground'], ['/privacy', 'Privacy']] },
]

function NavigationLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { pathname } = useLocation()
  return <nav aria-label="Main navigation">{groups.map(group => <section className="nav-group" key={group.label}><h2>{group.label}</h2>{group.links.map(([path, label]) => <NavLink key={path} to={path === '/career/experience' && pathname.startsWith('/career/') ? pathname : path!} end={path === '/'} onClick={onNavigate}>{label}</NavLink>)}</section>)}</nav>
}

export function Navigation() {
  const dialog = useRef<HTMLDialogElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  const location = useLocation()
  const current = groups.flatMap(g => g.links).find(([path]) => path === location.pathname)?.[1] ?? 'Career library'
  return <>
    <aside className="sidebar"><NavLink to="/" className="brand"><span className="brand-mark" aria-hidden="true">r.</span>Resume Tailor</NavLink><NavigationLinks /><p className="sidebar-note">Your career. Your workspace.</p></aside>
    <div className="mobile-navigation"><button className="button button-ghost" ref={trigger} type="button" aria-haspopup="dialog" onClick={() => dialog.current?.showModal()}>Navigation</button><span>{current}</span></div>
    <dialog className="navigation-dialog" ref={dialog} aria-label="Workspace navigation" onClose={() => trigger.current?.focus()} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close() }}>
      <div className="toolbar"><strong>Resume Tailor</strong><Button type="button" onClick={() => dialog.current?.close()}>Close navigation</Button></div>
      <NavigationLinks onNavigate={() => { dialog.current?.close(); requestAnimationFrame(() => document.getElementById('main-content')?.focus()) }} />
    </dialog>
  </>
}
