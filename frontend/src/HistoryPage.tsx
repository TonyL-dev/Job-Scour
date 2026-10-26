import { PageHeader, ActionGroup, Button, Disclosure } from './components/ui/Controls'
import { QueryNotice } from './QueryNotice'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getJobs } from './api/phase2'
import { getResumes } from './api/workspace'
import { versions, versionAction, versionPdf, createReport, getReports, getAnalyses, getApplications } from './api/phase4'
import type { Report } from './api/phase4'
import type { Item, Document } from './api/workspace'
import { downloadDocx } from './api/docx'
function facts(item?: Item) { const f = item?.facts; return f ? [f.title, f.employer, f.institution, f.degree, f.location, f.start_date, f.current ? 'Present' : f.end_date].filter(Boolean).join(' · ') : '' }
function contact(document: Document) { return [document.header.email, document.header.phone, document.header.location, ...(document.header.links ?? []).map(l => `${l.label}: ${l.url}`)].filter(Boolean).join(' · ') }

export function HistoryPage() {
  const [params] = useSearchParams()
  const client = useQueryClient()
  const documents = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const [id, setId] = useState(params.get('resume') ?? '')
  const [selected, setSelected] = useState(params.get('version') ?? '')
  const [compare, setCompare] = useState('')
  const [filter, setFilter] = useState('')
  const [analysis, setAnalysis] = useState('auto')
  const [statusFilter, setStatusFilter] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: getJobs })
  const applications = useQuery({ queryKey: ['applications'], queryFn: getApplications })
  const [report, setReport] = useState<Report>()
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const history = useQuery({ queryKey: ['versions', id], queryFn: () => versions(id), enabled: !!id })
  const version = history.data?.find(v => v.id === selected) ?? history.data?.[0]
  const other = history.data?.find(v => v.id === compare)
  const reports = useQuery({ queryKey: ['ats', version?.id], queryFn: () => getReports(version!.id), enabled: !!version })
  const analyses = useQuery({ queryKey: ['analyses'], queryFn: getAnalyses })
  const current = documents.data?.find(d => d.id === id)
  const chosenAnalysis = analysis === 'auto' ? analyses.data?.find(a => a.job_id === version?.content.metadata.job_description_id)?.id ?? '' : analysis
  const activeReport = report?.version_id === version?.id ? report : reports.data?.[0]
  async function perform(task: () => Promise<void>) {
    setBusy(true); setNotice('')
    try { await task() } catch (e) { setNotice(e instanceof Error ? e.message : 'Operation failed') } finally { setBusy(false) }
  }
  const previous = new Map(other?.content.sections.flatMap(s => s.items.map(i => [i.key, i] as const)))
  return <><PageHeader title="Every version, preserved." eyebrow="RESUME LIBRARY" />
    {version && <><Button disabled={busy} onClick={() => void perform(() => downloadDocx(version.id))}>Download selected version DOCX</Button><p>DOCX is editable; pagination depends on your word processor. Custom HTML/CSS/assets require a style-only template for DOCX.</p></>}
    <p>Restore appends a new snapshot. Duplicate creates a separate document. Historical downloads keep their stored facts.</p>
    <QueryNotice query={documents} label="Resume library" /><QueryNotice query={jobs} label="Saved jobs" /><QueryNotice query={applications} label="Applications" />{id && <QueryNotice query={history} label="Versions" />}<QueryNotice query={analyses} label="Job analyses" />{documents.data?.length === 0 && <p className="empty-state">No resumes saved yet. <Link to="/resumes">Build your first master resume</Link> to start its history.</p>}
    <label>Filter by company, role, title or date<input value={filter} onChange={e => setFilter(e.target.value)} /></label>
    <div className="form-grid"><label>Kind<select value={kindFilter} onChange={e => setKindFilter(e.target.value)}><option value="">All documents</option><option value="master">Masters</option><option value="tailored">Tailored</option></select></label><label>Application status<select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option value="">All statuses</option><option value="untracked">Untracked</option>{['saved','applied','screen','interview','offer','rejected','withdrawn'].map(s => <option key={s}>{s}</option>)}</select></label></div><label>Resume<select aria-label="Resume history document" value={id} onChange={e => { setId(e.target.value); setSelected(''); setCompare(''); setReport(undefined) }}><option value="">Choose a document</option>{documents.data?.filter(d => {
      const job = jobs.data?.find(j => j.id === d.content.metadata.job_description_id)
      const tracked = applications.data?.filter(a => a.document_id === d.id) ?? []
      return (!kindFilter || d.kind === kindFilter) && (!statusFilter || (statusFilter === 'untracked' ? !tracked.length : tracked.some(a => a.stage === statusFilter))) && `${d.title} ${d.updated_at} ${job?.company ?? ''} ${job?.title ?? ''}`.toLowerCase().includes(filter.toLowerCase())
    }).map(d => <option key={d.id} value={d.id}>{d.title} · {d.kind}</option>)}</select></label>
    {version && current && <><div className="form-grid"><label>Version<select aria-label="Version" value={version.id} onChange={e => setSelected(e.target.value)}>{history.data?.map(v => <option key={v.id} value={v.id}>Version {v.version_number} · {v.change_kind} · {new Date(v.created_at).toLocaleString()}</option>)}</select></label><label>Compare with<select aria-label="Compare with" value={compare} onChange={e => setCompare(e.target.value)}><option value="">No comparison</option>{history.data?.map(v => <option key={v.id} value={v.id}>Version {v.version_number}</option>)}</select></label></div>
      <ActionGroup>{<Link to={`/resumes?resume=${id}`}>Edit current resume →</Link>}<Button disabled={busy} onClick={() => void perform(async () => { await versionPdf(version.id) })}>Download this version</Button><Disclosure title="More version actions" className="context-actions"><ActionGroup><Button disabled={busy} onClick={() => void perform(async () => { await versionAction(version.id, current.version_number, false); await client.invalidateQueries({ queryKey: ['resumes'] }); await history.refetch(); setSelected(''); setNotice('Restored as a new version.') })}>Restore as new version</Button><Button disabled={busy} onClick={() => void perform(async () => { const copy = await versionAction(version.id, current.version_number, true); await client.invalidateQueries({ queryKey: ['resumes'] }); setId(copy.id); setSelected(''); setNotice('Separate copy created.') })}>Duplicate</Button></ActionGroup></Disclosure><Link to={`/applications?version=${version.id}&job=${version.content.metadata.job_description_id ?? ''}`}>Track this application →</Link></ActionGroup>
      <section className="panel editor-form"><h2>ATS guidance</h2><label>Job analysis (optional)<select aria-label="Job analysis (optional)" value={analysis} onChange={e => setAnalysis(e.target.value)}><option value="auto">Linked job (latest saved analysis)</option><option value="">General resume checks</option>{analyses.data?.map(a => <option key={a.id} value={a.id}>{a.company} · {a.title} · {new Date(a.created_at).toLocaleString()}</option>)}</select></label><Button disabled={busy || (analysis === 'auto' && analyses.isPending)} onClick={() => void perform(async () => { setReport(await createReport(version.id, chosenAnalysis)); void reports.refetch() })}>Run ATS checks on this PDF</Button>{reports.error && <p role="alert">{reports.error.message}</p>}
      {activeReport && <><h3>{activeReport.overall_score}/100 · {activeReport.page_count} pages</h3><p>{activeReport.guidance}</p><p>{Object.entries(activeReport.sub_scores).map(([k,v]) => `${k}: ${v}`).join(' · ')}</p>{activeReport.findings.map((f,n) => <p key={n}><a href={f.item_key ? `#item-${f.item_key}` : f.section_key ? `#section-${f.section_key}` : '#version-content'}>{f.message}</a>{version.version_number === current.version_number && (f.item_key || f.section_key) && <Link to={`/resumes?resume=${id}#${f.item_key ? `item-${f.item_key}` : `section-${f.section_key}`}`}> Open in editor</Link>}{f.source_refs?.map(r => <Link key={r.entity_id} to={`/career/${r.entity_type}`}> Career evidence</Link>)}</p>)}</>}
      </section>
      <article id="version-content">{other && JSON.stringify(other.content.header) !== JSON.stringify(version.content.header) && <p><del>{other.content.header.name} · {contact(other.content)}</del></p>}<h2>{version.content.header.name}</h2><p>{contact(version.content)}</p>{version.content.sections.map(s => <section id={`section-${s.key}`} key={s.key}><h3>{s.title}{!s.visible && ' (hidden)'}</h3>{s.items.map(i => <div id={`item-${i.key}`} key={i.key} className="panel editor-form">{other && (previous.get(i.key)?.text !== i.text || facts(previous.get(i.key)) !== facts(i)) && <p><del>{previous.get(i.key)?.text ?? '(new item)'} · {facts(previous.get(i.key))}</del></p>}<p className="source-note">{facts(i)}</p><p>{i.text}</p></div>)}</section>)}{other?.content.sections.flatMap(s => s.items).filter(i => !version.content.sections.some(s => s.items.some(v => v.key === i.key))).map(i => <p key={i.key}><del>{i.text}</del> (removed)</p>)}</article>
    </>}{notice && <p role="status">{notice}</p>}</>
}
