import { QueryNotice } from './QueryNotice'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { getJobs } from './api/phase2'
import { downloadPdf, getResumes } from './api/workspace'
import { cancelRun, commitReview, getRun, getRuns, reviewPreview, saveReview, startRun } from './api/generation'
import type { Decision, GenerateInput, Run } from './api/generation'
import { versionPdf } from './api/phase4'
import { PdfPreview } from './PdfPreview'

const presets: [NonNullable<GenerateInput['preset']>, string][] = [['tailor', 'Tailor to job'], ['rewrite_summary', 'Rewrite summary'], ['quantify', 'Quantify from stored metrics'], ['concise', 'More concise'], ['senior', 'More senior wording'], ['technical', 'More technical'], ['fit', 'Fit to 2 pages']]

export function GenerationPage() {
  const client = useQueryClient()
  const masters = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: getJobs })
  const runs = useQuery({ queryKey: ['generation'], queryFn: getRuns })
  const [masterId, setMasterId] = useState('')
  const [jobId, setJobId] = useState('')
  const [runId, setRunId] = useState('')
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [revision, setRevision] = useState(0)
  const [locks, setLocks] = useState<Record<string, boolean>>({})
  const [title, setTitle] = useState('Tailored resume')
  const [preset, setPreset] = useState<NonNullable<GenerateInput['preset']>>('tailor')
  const [instruction, setInstruction] = useState('')
  const [layout, setLayout] = useState(false)
  const [embeddings, setEmbeddings] = useState(false)
  const [scope, setScope] = useState<string[]>([])
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const run = useQuery({ queryKey: ['generation', runId], queryFn: () => getRun(runId), enabled: !!runId, refetchInterval: q => ['queued', 'running'].includes(q.state.data?.status ?? '') ? 2000 : false })
  const active = run.data?.status === 'queued' || run.data?.status === 'running'
  const reviewable = !!run.data && !active
  const [debounced, setDebounced] = useState({ decisions, locks, expected_revision: revision })
  useEffect(() => { const timer = setTimeout(() => setDebounced({ decisions, locks, expected_revision: revision }), 600); return () => clearTimeout(timer) }, [decisions, locks, revision])
  useEffect(() => {
    if (!runId || !active) return
    const events = new EventSource(`/api/generation/${runId}/events`)
    events.addEventListener('progress', () => { void client.invalidateQueries({ queryKey: ['generation', runId], exact: true }) })
    events.addEventListener('result', () => { events.close(); void client.invalidateQueries({ queryKey: ['generation'] }) })
    events.onerror = () => events.close()
    return () => events.close()
  }, [active, runId, client])
  const preview = useQuery({ queryKey: ['review-preview', runId, debounced], queryFn: ({ signal }) => reviewPreview(runId, debounced, signal), enabled: reviewable && debounced.expected_revision === revision, retry: false, gcTime: 0 })
  function open(result: Run) { setRunId(result.id); setRevision(result.review_revision); setLocks(result.locks ?? {}); setDecisions(result.decisions ?? []); setEmbeddings(result.request.use_embeddings); setLayout(result.request.allow_layout_adjustments); setMasterId(result.request.master_id); setJobId(result.request.job_id); setScope([]); setError(''); setNotice('') }
  async function perform(work: () => Promise<void>) {
    setBusy(true); setError('')
    try { await work(); void client.invalidateQueries({ queryKey: ['generation'] }) } catch (e) { setError(e instanceof Error ? e.message : 'Operation failed') } finally { setBusy(false) }
  }
  function decide(id: string, action: Decision['action'], text?: string) { setDecisions(previous => [...previous.filter(d => d.suggestion_id !== id), { suggestion_id: id, action, text }]) }
  async function generate(regenerate: boolean) {
    await perform(async () => {
      if (regenerate) { const saved = await saveReview(runId, { decisions, locks, expected_revision: revision }); setRevision(saved.review_revision) }
      const sectionKeys = run.data?.base.sections.map(s => s.key) ?? []
      open(await startRun({ master_id: masterId || masters.data?.find(m => m.gold_standard && m.kind === 'master')?.id || '', job_id: jobId, use_embeddings: embeddings, section_keys: regenerate ? scope.filter(k => sectionKeys.includes(k)) : [], item_keys: regenerate ? scope.filter(k => !sectionKeys.includes(k)) : [], instruction, preset, allow_layout_adjustments: layout, parent_run_id: regenerate ? runId : null }))
    })
  }
  const reviewSections = run.data?.base.sections.map(section => {
    const items = [...section.items]
    for (const suggestion of run.data?.suggestions ?? []) {
      if (suggestion.section_key !== section.key || suggestion.order_keys) continue
      const decision = decisions.find(d => d.suggestion_id === suggestion.id)
      if (!decision || decision.action === 'reject') continue
      const index = items.findIndex(i => i.key === suggestion.item_key)
      const proposal = suggestion.proposed ?? (decision.action === 'edit' ? suggestion.original : null)
      if (index >= 0) items.splice(index, 1)
      if (proposal) items.splice(index >= 0 ? index : items.length, 0, { ...proposal, text: decision.action === 'edit' ? decision.text ?? proposal.text : proposal.text })
    }
    return { ...section, items }
  }) ?? []
  return <>
    <p className="eyebrow">GENERATION & REVIEW</p><h1>Tailor with evidence.</h1><p className="intro">Review sourced suggestions and save a separate tailored resume.</p>
    <section className="editor-form"><h2>Start a generation</h2>
      {(masters.error || jobs.error || runs.error) && <p role="alert">{masters.error?.message ?? jobs.error?.message ?? runs.error?.message}</p>}
      <div className="form-grid"><label>Master resume<select aria-label="Generation master" value={masterId} disabled={active || busy} onChange={e => setMasterId(e.target.value)}><option value="">Use gold standard</option>{masters.data?.filter(m => m.kind === 'master').map(m => <option key={m.id} value={m.id}>{m.title}</option>)}</select></label><label>Job description<select aria-label="Generation job" value={jobId} disabled={active || busy} onChange={e => setJobId(e.target.value)}><option value="">Choose saved job</option>{jobs.data?.map(j => <option key={j.id} value={j.id}>{j.title || 'Untitled job'} · {j.company}</option>)}</select></label></div>
      <p className="source-note">Assign analysis, ranking, rewriting, summary, verification and condensing models in <NavLink to="/settings/ai">AI settings</NavLink>. Each rewrite receives a separate source verification pass. Codex controls sampling; HTTP verifiers use temperature 0. Gaps never become career facts.</p>
      <label className="check"><input type="checkbox" checked={embeddings} onChange={e => setEmbeddings(e.target.checked)} />Use embeddings for retrieval</label><label className="check"><input type="checkbox" checked={layout} onChange={e => setLayout(e.target.checked)} />Allow small spacing/font adjustments if content fitting is insufficient</label>
      <button disabled={busy || active || !jobId || (!masterId && !masters.data?.some(m => m.gold_standard))} onClick={() => void generate(false)}>Generate suggestions</button>
    </section>
    <label>Saved generation runs<select aria-label="Saved generation runs" value={runId} disabled={busy} onChange={e => { const selected = runs.data?.find(r => r.id === e.target.value); if (selected) open(selected) }}><option value="">Choose a run</option>{runs.data?.map(r => <option key={r.id} value={r.id}>{new Date(r.created_at).toLocaleString()} · {r.status} · {r.id.slice(0, 8)}</option>)}</select></label>
    <QueryNotice query={masters} label="Resumes" /><QueryNotice query={jobs} label="Saved jobs" /><QueryNotice query={runs} label="Generation runs" />{runId && <QueryNotice query={run} label="Selected run" />}{masters.data?.filter(m => m.kind === "master").length === 0 && <p className="empty-state">Save a master resume before generating suggestions. <NavLink to="/resumes">Build a master resume</NavLink></p>}{jobs.data?.length === 0 && <p className="empty-state">Save a job description before generating suggestions. <NavLink to="/jobs">Add a job</NavLink></p>}
    {run.data && <section className="editor-form"><div className="toolbar"><h2>Run · {run.data.status}</h2>{active && <button className="secondary" disabled={busy} onClick={() => void perform(async () => { open(await cancelRun(runId)) })}>Cancel generation</button>}</div><p role="status">{run.data.events.at(-1)?.stage ?? 'Queued'}</p>{run.data.error && <p role="alert">{run.data.error}</p>}{run.data.warnings.map(w => <p className="warning" key={w}>{w}</p>)}<details><summary>Progress and provenance</summary><ol>{run.data.events.map(e => <li key={e.sequence}>{e.stage} · {e.elapsed_seconds}s</li>)}</ol>{Object.entries(run.data.provenance).map(([task, value]) => <p className="source-note" key={task}>{task}: {value}</p>)}</details></section>}
    {reviewable && run.data && <div className="studio"><div className="resume-controls">
      <section className="editor-form"><h2>Review changes</h2><p>Pending and rejected changes preserve the original. Unsupported changes require your confirmed edit.</p><button className="secondary" onClick={() => setDecisions(run.data!.suggestions.map(s => ({ suggestion_id: s.id, action: s.verification === 'supported' ? 'accept' : 'reject' })))}>Accept all supported changes</button>{!run.data.suggestions.length && <p>No changes available. Check the run error or protected scope.</p>}</section>
      {run.data.suggestions.map(s => { const decision = decisions.find(d => d.suggestion_id === s.id); return <section className="editor-form" key={s.id}><h3>{run.data!.base.sections.find(section => section.key === s.section_key)?.title} · {s.verification.replace('_', ' ')}</h3><div className="review-diff"><div><h4>Original</h4><p>{s.original?.text ?? 'New item'}</p></div><div><h4>Proposed</h4><p>{s.proposed?.text ?? s.rejected_text ?? (s.order_keys ? 'Order skills by relevance (protected positions preserved)' : 'Remove item')}</p></div></div><p className={s.verification === 'supported' ? 'source-note' : 'warning'}>{s.reason}</p><details><summary>Career sources</summary>{Object.entries(s.sources ?? {}).map(([id, text]) => <p className="source-note" key={id}>{id}: {text}</p>)}</details><div className="actions"><button disabled={busy || s.verification !== 'supported'} onClick={() => decide(s.id, 'accept')}>Accept</button><button className="secondary" onClick={() => decide(s.id, 'reject')}>Reject</button><button className="secondary" disabled={!!s.order_keys || (!s.proposed && !s.original)} onClick={() => decide(s.id, 'edit', s.proposed?.text ?? s.original?.text ?? '')}>Edit</button><span role="status">{decision?.action ?? 'pending'}</span></div>{decision?.action === 'edit' && <label>Your confirmed edit<textarea aria-label={`Edit suggestion ${s.id}`} value={decision.text ?? ''} onChange={e => decide(s.id, 'edit', e.target.value)} /></label>}</section> })}
      <section className="editor-form"><h2>Partial regeneration</h2><p>Select sections/items or leave unchecked for a full pass. Protected content stays unchanged.</p>{reviewSections.map(s => <div key={s.key}>{[{ key: s.key, label: s.title, locked: s.locked }, ...s.items.map(i => ({ key: i.key, label: i.text.slice(0, 100), locked: s.locked || i.locked }))].map(target => <label className="check" key={target.key}><input type="checkbox" disabled={(locks[target.key] ?? target.locked ?? false) || (locks[s.key] ?? s.locked ?? false) || !s.visible} checked={scope.includes(target.key)} onChange={() => setScope(scope.includes(target.key) ? scope.filter(k => k !== target.key) : [...scope, target.key])} />{target.label}{target.locked ? ' · protected' : ''}</label>)}{[{ key: s.key, label: s.title, locked: s.locked }, ...s.items.map(i => ({ key: i.key, label: i.text.slice(0, 60), locked: i.locked }))].map(target => <label className="check source-note" key={`lock-${target.key}`}><input type="checkbox" checked={locks[target.key] ?? target.locked ?? false} onChange={e => setLocks({ ...locks, [target.key]: e.target.checked })} />Protect {target.label} for the next generation</label>)}</div>)}<label>Regeneration preset<select aria-label="Regeneration preset" value={preset} onChange={e => setPreset(e.target.value as typeof preset)}>{presets.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Additional instruction<textarea value={instruction} maxLength={1000} onChange={e => setInstruction(e.target.value)} /></label><button disabled={busy} onClick={() => void generate(true)}>Regenerate selected scope</button></section>
    </div><aside className="preview-panel"><div className="toolbar"><h2>Review preview</h2><span className="pill">{preview.data ? `${preview.data.page_count} ${preview.data.page_count === 1 ? 'page' : 'pages'}` : 'A4'}</span></div>{preview.isFetching && <p role="status">Updating PDF preview…</p>}{preview.error && <div role="alert"><p>{preview.error.message}</p><button type="button" disabled={preview.isFetching} onClick={() => void preview.refetch()}>Retry preview</button></div>}{preview.data?.warnings.map(w => <p className="warning" key={w}>{w}</p>)}{preview.data && <PdfPreview encoded={preview.data.pdf_base64} />}<label>Tailored resume title<input value={title} onChange={e => setTitle(e.target.value)} /></label><div className="actions"><button disabled={busy || !title.trim() || !!run.data.saved_resume_id} onClick={() => void perform(async () => { const saved = await commitReview(runId, { decisions, locks, expected_revision: revision, title }); setRevision((await getRun(runId)).review_revision); setNotice(`Tailored resume saved: ${saved.title}`); void client.invalidateQueries({ queryKey: ['resumes'] }); void run.refetch() })}>Save tailored resume</button><button className="secondary" disabled={busy} onClick={() => void perform(async () => { const result = await saveReview(runId, { decisions, locks, expected_revision: revision }); setRevision(result.review_revision); setNotice('Review decisions saved.'); void run.refetch() })}>Save review decisions</button>{run.data.saved_resume_id && <NavLink to={`/history?resume=${run.data.saved_resume_id}&version=${run.data.saved_version_id ?? ''}`}>ATS checks, history & track application →</NavLink>}{run.data.saved_resume_id && <button onClick={() => void perform(async () => { if (run.data!.saved_version_id) await versionPdf(run.data!.saved_version_id); else await downloadPdf(run.data!.saved_resume_id!); setNotice('Saved PDF downloaded.') })}>Download saved PDF</button>}</div></aside></div>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
  </>
}
