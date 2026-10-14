import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from './api/client'
import { getHistory, recordLabel, failure } from './api/workspace'
import { PdfPreview } from './PdfPreview'
import type { components } from './api/schema'
import { letterPdf } from './api/letters'
import { downloadDocx } from './api/docx'

type Run = components['schemas']['LetterRun']
type Content = components['schemas']['LetterContent']
type Version = components['schemas']['LetterVersion']

export function LettersPage() {
  const cache = useQueryClient()
  const records = useQuery({ queryKey: ['career'], queryFn: getHistory })
  const analyses = useQuery({ queryKey: ['analysis-choices'], queryFn: async () => { const r = await api.GET('/api/jobs/analyses'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const runs = useQuery({ queryKey: ['letter-runs'], queryFn: async () => { const r = await api.GET('/api/letters/runs'); if (!r.data) throw failure(r.error, r.response.status); return r.data }, refetchInterval: 3000 })
  const versions = useQuery({ queryKey: ['letter-versions'], queryFn: async () => { const r = await api.GET('/api/letters/versions'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const [analysisId, setAnalysisId] = useState('')
  const [sourceIds, setSourceIds] = useState<string[]>([])
  const [title, setTitle] = useState('Cover letter')
  const [content, setContent] = useState<Content>({ author: { name: '' }, recipient: '', salutation: 'Dear hiring team,', closing: 'Sincerely,', paragraphs: [] })
  const [maxWords, setMaxWords] = useState(400)
  const [run, setRun] = useState<Run>()
  const [saved, setSaved] = useState<Version>()
  const [kept, setKept] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const preview = useQuery({ queryKey: ['letter-preview', saved?.id], enabled: !!saved, queryFn: async () => { const r = await api.GET('/api/letters/versions/{identifier}/preview', { params: { path: { identifier: saved!.id } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  async function perform(action: () => Promise<void>) { setBusy(true); setMessage(''); try { await action(); await cache.invalidateQueries({ queryKey: ['letter-runs'] }); await cache.invalidateQueries({ queryKey: ['letter-versions'] }) } catch (e) { setMessage(e instanceof Error ? e.message : 'Letter operation failed') } finally { setBusy(false) } }
  function selectRun(value: Run) { setRun(value); setContent(value.proposed); setTitle(value.request.title); setKept(value.proposed.paragraphs?.filter(p => value.support[String(p.key)] === 'supported').map(p => p.key) ?? []); setSaved(undefined) }
  return <><h1>Cover letters</h1><p>Generate career paragraphs from selected evidence, review each claim, then save a separate immutable letter.</p>{message && <p role="alert">{message}</p>}
    <section className="status-card"><h2>Letter context</h2>
      <label>Saved job analysis<select aria-label="Saved job analysis" disabled={busy} value={analysisId} onChange={e => setAnalysisId(e.target.value)}><option value="">Choose a saved analysis</option>{analyses.data?.map(a => <option key={a.id} value={a.id}>{a.company} · {a.title}</option>)}</select></label>
      <label>Letter title<input value={title} onChange={e => setTitle(e.target.value)} /></label><label>Your name<input value={content.author.name} onChange={e => setContent({ ...content, author: { ...content.author, name: e.target.value } })} /></label><label>Your email<input value={content.author.email ?? ''} onChange={e => setContent({ ...content, author: { ...content.author, email: e.target.value || null } })} /></label>
      <label>Recipient (optional)<input value={content.recipient ?? ''} onChange={e => setContent({ ...content, recipient: e.target.value })} /></label><label>Salutation<input value={content.salutation ?? ''} onChange={e => setContent({ ...content, salutation: e.target.value })} /></label><label>Closing<input value={content.closing ?? ''} onChange={e => setContent({ ...content, closing: e.target.value })} /></label><label>Maximum paragraph words<input type="number" min={100} max={600} value={maxWords} onChange={e => setMaxWords(Number(e.target.value))} /></label>
      <fieldset disabled={busy}><legend>Career evidence (up to ten records)</legend>{records.data?.filter(r => r.data.type !== 'skill_evidence').map(r => <label key={r.id}><input type="checkbox" checked={sourceIds.includes(r.id)} onChange={e => setSourceIds(e.target.checked ? [...sourceIds, r.id] : sourceIds.filter(id => id !== r.id))} />{recordLabel(r)}</label>)}</fieldset>
      <details><summary>Selected facts shared with configured AI</summary>{records.data?.filter(r => sourceIds.includes(r.id)).map(r => <pre style={{ whiteSpace: 'pre-wrap' }} key={r.id}>{JSON.stringify(r.data, null, 2)}</pre>)}</details><p>Uses explicit cover-letter and verification assignments in <Link to="/settings/ai">AI settings</Link>. Job requirements never become career facts.</p>
      <button disabled={busy || !analysisId || !content.author.name || sourceIds.length === 0 || sourceIds.length > 10} onClick={() => void perform(async () => {
        const analysis = analyses.data?.find(a => a.id === analysisId); if (!analysis) throw new Error('Choose saved analysis')
        const sources = records.data?.filter(r => sourceIds.includes(r.id) && r.data.type !== 'skill_evidence').map(r => ({ entity_type: r.data.type as components['schemas']['SourceRef']['entity_type'], entity_id: r.id })) ?? []
        const start = await api.POST('/api/letters/runs', { body: { title, job_id: analysis.job_id, analysis_id: analysisId, sources, content: { ...content, paragraphs: [] }, max_words: maxWords } }); if (!start.data) throw failure(start.error, start.response.status); selectRun(start.data)
        const r = await api.POST('/api/letters/runs/{identifier}/execute', { params: { path: { identifier: start.data.id }, query: { revision: start.data.revision } } }); if (!r.data) throw failure(r.error, r.response.status); selectRun(r.data)
      })}>Generate letter paragraphs</button>
      {busy && <><p role="status">Working…</p>{run && <button onClick={() => void api.POST('/api/letters/runs/{identifier}/cancel', { params: { path: { identifier: run.id } } })}>Cancel generation</button>}</>}
    </section>
    <section className="status-card"><h2>Generation runs</h2>{runs.isError && <><p role="alert">{runs.error.message}</p><button onClick={() => void runs.refetch()}>Try again</button></>}{runs.data?.length === 0 && <p>No letter runs yet.</p>}{runs.data?.map(r => <button disabled={busy} key={r.id} onClick={() => selectRun(r)}>{r.request.title} · {r.status}</button>)}</section>
    {run && <section className="status-card"><h2>Review paragraphs</h2><p>{run.status} {run.error}</p>{content.paragraphs?.map((p, index) => <fieldset key={p.key} disabled={busy || run.status !== 'review'}><legend>Paragraph {index + 1} · {run.support[String(p.key)]}</legend><p>{run.reasons[String(p.key)]}</p><details><summary>Source evidence</summary>{p.source_refs.map(ref => <pre key={ref.entity_id} style={{ whiteSpace: 'pre-wrap' }}>{run.evidence[ref.entity_id]}</pre>)}</details><textarea aria-label={`Letter paragraph ${index + 1}`} value={p.text} onChange={e => setContent({ ...content, paragraphs: content.paragraphs?.map((item, i) => i === index ? { ...item, text: e.target.value, origin: 'user' } : item) })} /><label><input type="checkbox" disabled={p.origin === 'ai' && run.support[String(p.key)] !== 'supported'} checked={kept.includes(p.key)} onChange={e => setKept(e.target.checked ? [...kept, p.key] : kept.filter(k => k !== p.key))} />Keep paragraph{p.origin === 'user' && ' as user-confirmed sourced wording'}</label></fieldset>)}
      <button disabled={busy || run.status !== 'review' || !kept.length} onClick={() => void perform(async () => { const r = await api.POST('/api/letters/runs/{identifier}/commit', { params: { path: { identifier: run.id } }, body: { expected_revision: run.revision, title, content: { ...content, paragraphs: content.paragraphs?.filter(p => kept.includes(p.key)) ?? [] } } }); if (!r.data) throw failure(r.error, r.response.status); setSaved(r.data); setMessage('Cover letter saved.') })}>Save reviewed letter</button>
    </section>}
    <section className="status-card"><h2>Letter versions</h2>{versions.data?.length === 0 && <p>No saved letters yet.</p>}{versions.data?.map(v => <button key={v.id} disabled={busy} onClick={() => { setSaved(v); setContent(v.content) }}>{v.title} · version {v.version_number}</button>)}</section>
    {saved && <><button disabled={busy} onClick={() => void perform(() => downloadDocx(saved.id, true))}>Download letter DOCX</button><p>DOCX is editable and may paginate differently in your word processor.</p></>}
    {saved && <section className="status-card"><h2>{saved.title} · version {saved.version_number}</h2><button onClick={() => void perform(() => letterPdf(saved.id))}>Download letter PDF</button><Link to={`/applications?letter=${saved.id}&job=${saved.job_id}`}>Link submitted version to application</Link>
      <button disabled={busy} onClick={() => void perform(async () => { const latest = Math.max(...(versions.data?.filter(v => v.document_id === saved.document_id).map(v => v.version_number) ?? [saved.version_number])); const r = await api.POST('/api/letters/versions/{identifier}/restore', { params: { path: { identifier: saved.id }, query: { expected_version: latest } } }); if (!r.data) throw failure(r.error, r.response.status); setSaved(r.data) })}>Restore this version as a new version</button>
      {saved.content.paragraphs?.map((p, index) => <label key={p.key}>Edit saved paragraph {index + 1}<textarea value={content.paragraphs?.[index]?.text ?? ''} onChange={e => setContent({ ...content, paragraphs: content.paragraphs?.map((item, i) => i === index ? { ...item, text: e.target.value, origin: 'user' } : item) })} /></label>)}
      <button disabled={busy} onClick={() => void perform(async () => { const r = await api.PUT('/api/letters/versions/{identifier}', { params: { path: { identifier: saved.id } }, body: { expected_version: saved.version_number, content } }); if (!r.data) throw failure(r.error, r.response.status); setSaved(r.data) })}>Save edits as a new version</button>
      {preview.isError && <p role="alert">{preview.error.message}</p>}{preview.data && <><p>{preview.data.page_count} page(s) · {preview.data.warnings.join(' · ')}</p><PdfPreview encoded={preview.data.pdf_base64} /></>}
    </section>}
  </>
}
