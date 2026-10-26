import { ActionGroup, PageHeader, Button } from './components/ui/Controls'
import { QueryNotice } from './QueryNotice'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getApplications, saveApplication, versions, versionPdf, applicationEvents, addEvent } from './api/phase4'
import type { ApplicationSave, Stage, Application } from './api/phase4'
import { getResumes } from './api/workspace'
import { getJobs } from './api/phase2'
import { api } from './api/client'
import { failure } from './api/workspace'
import { letterPdf } from './api/letters'
function editable(a: Application): ApplicationSave {
  return { company:a.company, position:a.position, version_id:a.version_id, cover_letter_version_id:a.cover_letter_version_id, job_id:a.job_id, date_applied:a.date_applied, stage:a.stage, channel:a.channel, notes:a.notes, follow_up_date:a.follow_up_date, follow_up_done:a.follow_up_done, expected_revision:a.revision }
}
const stages: Stage[] = ['saved', 'applied', 'screen', 'interview', 'offer', 'rejected', 'withdrawn']

export function ApplicationsPage() {
  const [params] = useSearchParams()
  const client = useQueryClient()
  const applications = useQuery({ queryKey: ['applications'], queryFn: getApplications })
  const resumes = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: getJobs })
  const letters = useQuery({ queryKey: ['letter-versions'], queryFn: async () => { const r = await api.GET('/api/letters/versions'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const [document, setDocument] = useState('')
  const history = useQuery({ queryKey: ['versions', document], queryFn: () => versions(document), enabled: !!document })
  const [editing, setEditing] = useState<Application>()
  const [body, setBody] = useState<ApplicationSave>({ company: '', position: '', version_id: params.get('version') ?? '', cover_letter_version_id: params.get('letter') || null, job_id: params.get('job') || null, expected_revision: 0, stage: 'saved', notes: '', channel: '', follow_up_done: false })
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [filter, setFilter] = useState('')
  const [board, setBoard] = useState(false)
  const events = useQuery({ queryKey: ['application-events', editing?.id], queryFn: () => applicationEvents(editing!.id), enabled: !!editing })
  async function perform(task: () => Promise<void>) { setBusy(true); setNotice(''); try { await task() } catch(e) { setNotice(e instanceof Error ? e.message : 'Operation failed') } finally { setBusy(false) } }
  const rows = applications.data?.filter(a => `${a.company} ${a.position} ${a.stage}`.toLowerCase().includes(filter.toLowerCase())) ?? []
  const today = new Date().toLocaleDateString('en-CA')
  const due = applications.data?.filter(a => a.follow_up_date && a.follow_up_date <= today && !a.follow_up_done) ?? []
  const responded = applications.data?.filter(a => ['screen', 'interview', 'offer', 'rejected'].includes(a.stage)).length ?? 0
  const byVersion = new Map<string, { total: number, responses: number }>()
  for (const a of applications.data ?? []) {
    if (a.stage === 'saved') continue
    const stats = byVersion.get(a.version_id) ?? { total: 0, responses: 0 }
    stats.total++; if (['screen', 'interview', 'offer', 'rejected'].includes(a.stage)) stats.responses++
    byVersion.set(a.version_id, stats)
  }
  return <><PageHeader title="Follow your next step." eyebrow="APPLICATION TRACKER" /><p>{due.length} follow-ups due · {responded} applications with a recorded response stage. Links always use the exact submitted version.</p>
    <label>Exact cover letter version<select aria-label="Exact cover letter version" value={body.cover_letter_version_id ?? ''} onChange={e => setBody({ ...body, cover_letter_version_id: e.target.value || null })}><option value="">No cover letter</option>{letters.data?.map(v => <option key={v.id} value={v.id}>{v.title} · version {v.version_number}</option>)}</select></label>
    {body.cover_letter_version_id && <Button disabled={busy} onClick={() => void perform(() => letterPdf(body.cover_letter_version_id!))}>Submitted letter PDF</Button>}
    <section className="panel status-card"><h2>Upcoming & overdue follow-ups</h2><p>Dates use your device's local calendar. Follow-ups persist across restarts; reminders appear in the app while it is open.</p>{applications.data?.filter(a => a.follow_up_date && !a.follow_up_done).sort((a, b) => a.follow_up_date!.localeCompare(b.follow_up_date!)).map(a => <p key={a.id}><Button onClick={() => { setEditing(a); setBody(editable(a)) }}>{a.company} · {a.position}</Button> · {a.follow_up_date} · {a.follow_up_date! < today ? 'Overdue' : a.follow_up_date === today ? 'Due today' : 'Upcoming'}</p>)}{applications.data && !applications.data.some(a => a.follow_up_date && !a.follow_up_done) && <p>No upcoming follow-ups.</p>}</section>
    <QueryNotice query={applications} label="Applications" /><QueryNotice query={resumes} label="Resumes" /><QueryNotice query={jobs} label="Saved jobs" />{document && <QueryNotice query={history} label="Resume versions" />}{editing && <QueryNotice query={events} label="Stage history" />}
    <details><summary>Response stages by exact resume version</summary>{[...byVersion].map(([id, s]) => <p key={id}>{id.slice(0, 8)}: {s.responses}/{s.total} · {Math.round(100 * s.responses/s.total)}%</p>)}</details><section className="panel editor-form"><h2>{editing ? 'Edit application' : 'Track an application'}</h2><form onSubmit={e => { e.preventDefault(); void perform(async () => { const result = await saveApplication(body, editing?.id); setEditing(result); setBody(editable(result)); await client.invalidateQueries({ queryKey: ['applications'] }); setNotice('Application saved.') }) }}><div className="form-grid"><label>Company<input required value={body.company} onChange={e => setBody({ ...body, company: e.target.value })} /></label><label>Position<input required value={body.position} onChange={e => setBody({ ...body, position: e.target.value })} /></label><label>Job<select value={body.job_id ?? ''} onChange={e => setBody({ ...body, job_id: e.target.value || null })}><option value="">No saved job</option>{jobs.data?.map(j => <option key={j.id} value={j.id}>{j.company} · {j.title}</option>)}</select></label>
    <label>Choose resume document<select value={document} onChange={e => setDocument(e.target.value)}><option value="">Select to browse versions</option>{resumes.data?.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}</select></label><label>Exact resume version<select required value={body.version_id} onChange={e => setBody({ ...body, version_id: e.target.value })}><option value="">Choose version</option>{body.version_id && !history.data?.some(v => v.id === body.version_id) && <option value={body.version_id}>Linked version {body.version_id}</option>}{history.data?.map(v => <option key={v.id} value={v.id}>Version {v.version_number}</option>)}</select></label><label>Stage<select aria-label="Stage" value={body.stage ?? 'saved'} onChange={e => setBody({ ...body, stage: e.target.value as Stage })}>{stages.map(s => <option key={s}>{s}</option>)}</select></label><label>Date applied<input type="date" value={body.date_applied ?? ''} onChange={e => setBody({ ...body, date_applied: e.target.value || null })} /></label><label>Source/channel<input value={body.channel ?? ''} onChange={e => setBody({ ...body, channel: e.target.value })} /></label><label>Next follow-up<input type="date" value={body.follow_up_date ?? ''} onChange={e => setBody({ ...body, follow_up_date: e.target.value || null })} /></label><label className="check"><input type="checkbox" checked={body.follow_up_done ?? false} onChange={e => setBody({ ...body, follow_up_done: e.target.checked })} />Follow-up completed</label></div><label>Notes<textarea value={body.notes ?? ''} onChange={e => setBody({ ...body, notes: e.target.value })} /></label><Button variant="primary" disabled={busy || !body.version_id}>Save application</Button></form>
    {editing && <><Button variant="secondary" onClick={() => { setEditing(undefined); setBody({ company: '', position: '', version_id: '', expected_revision: 0, stage: 'saved', notes: '', channel: '', follow_up_done: false }) }}>New application</Button><h3>Stage history</h3>{events.data?.map(e => <p key={e.id}>{e.date} · {e.stage} · {e.notes}</p>)}<Button disabled={busy} onClick={() => void perform(async () => { const r = await addEvent(editing.id, { stage: body.stage ?? 'saved', date: today, notes: body.notes ?? '', expected_revision: editing.revision }); setEditing(r); setBody(editable(r)); await client.invalidateQueries({ queryKey: ['applications'] }); await events.refetch(); setNotice('Stage event recorded.') })}>Record stage event</Button></>}
    </section><label>Filter applications<input value={filter} onChange={e => setFilter(e.target.value)} /></label><Button variant="secondary" aria-pressed={board} onClick={() => setBoard(!board)}>{board ? 'Table view' : 'Board view'}</Button>
    {!applications.isPending && !applications.error && rows.length === 0 && <p className="empty-state">{filter ? "No applications match this filter." : "No applications tracked yet. Choose a saved resume version above to track your first application."}</p>}{board ? <div className="tracker-board" role="region" aria-label="Application board" tabIndex={0}>{stages.map(s => <section key={s}><h2>{s}</h2>{rows.filter(a => a.stage === s).map(a => <Button key={a.id} onClick={() => { setEditing(a); setBody(editable(a)) }}>{a.company} · {a.position}</Button>)}</section>)}</div> : <div className="tracker-table" role="region" aria-label="Application table" tabIndex={0}><table><thead><tr><th>Company / role</th><th>Stage</th><th>Applied</th><th>Follow-up</th><th>Resume</th></tr></thead><tbody>{rows.map(a => <tr key={a.id}><td><Button variant="secondary" onClick={() => { setEditing(a); setBody(editable(a)) }}>{a.company} · {a.position}</Button></td><td>{a.stage}</td><td>{a.date_applied}</td><td>{a.follow_up_date}{a.follow_up_done && ' ✓'}</td><td>Version {a.version_number}<ActionGroup><Link to={`/history?resume=${a.document_id}`}>History</Link><Button onClick={() => void perform(async () => { await versionPdf(a.version_id) })}>Submitted PDF</Button></ActionGroup></td></tr>)}</tbody></table></div>}
    <Link to="/history">Resume history →</Link>{notice && <p role="status">{notice}</p>}</>
}
