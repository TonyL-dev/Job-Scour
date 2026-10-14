import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'
import { api } from './api/client'
import { failure } from './api/workspace'
import type { components } from './api/schema'
import { getForms, getHistory, recordLabel } from './api/workspace'
import type { CareerRecord } from './api/workspace'

type Run = components['schemas']['ImportRun']
type Candidate = components['schemas']['Candidate']
const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

export function ImportPage() {
  const cache = useQueryClient()
  const forms = useQuery({ queryKey: ['career-forms'], queryFn: getForms })
  const records = useQuery({ queryKey: ['career'], queryFn: getHistory })
  const runs = useQuery({ queryKey: ['imports'], queryFn: async () => {
    const r = await api.GET('/api/imports'); if (!r.data) throw failure(r.error, r.response.status); return r.data
  }, refetchInterval: 3000 })
  const [run, setRun] = useState<Run>()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [file, setFile] = useState<File>()
  const [retain, setRetain] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  function select(value: Run) { setRun(value); setCandidates(value.candidates) }
  async function perform(action: () => Promise<Run>) {
    setBusy(true); setMessage('')
    try { select(await action()); await cache.invalidateQueries({ queryKey: ['imports'] }); await cache.invalidateQueries({ queryKey: ['career'] }) }
    catch (e) { setMessage(e instanceof Error ? e.message : 'Import failed') }
    finally { setBusy(false) }
  }
  async function saveReview() {
    if (!run) throw new Error('Select an import')
    const r = await api.PUT('/api/imports/{identifier}', { params: { path: { identifier: run.id } }, body: { expected_revision: run.revision, candidates } })
    if (!r.data) throw failure(r.error, r.response.status)
    return r.data
  }
  return <><h1>Import a resume</h1><p>Import content from a text PDF or DOCX, review facts, then build a master. Uploaded layout is not reproduced. OCR is unsupported.</p>
    {message && <p role="alert">{message}</p>}
    {forms.isError && <><p role="alert">{forms.error.message}</p><button onClick={() => void forms.refetch()}>Retry career fields</button></>}
    <section className="status-card"><h2>Upload</h2><p>Maximum 2 MiB, 30 PDF pages, 200,000 extracted characters. Parsing runs locally; AI extraction is optional.</p>
      <label>Resume file<input type="file" accept=".pdf,.docx" disabled={busy} onChange={e => setFile(e.target.files?.[0])} /></label>
      <label><input type="checkbox" checked={retain} disabled={busy} onChange={e => setRetain(e.target.checked)} />Retain encrypted original (requires a backend upload key)</label>
      <button disabled={!file || busy} onClick={() => void perform(async () => {
        if (!file || file.size > 2 * 1024 * 1024) throw new Error('Choose a PDF/DOCX up to 2 MiB')
        const bytes = new Uint8Array(await file.arrayBuffer()); let binary = ''; for (const byte of bytes) binary += String.fromCharCode(byte)
        const r = await api.POST('/api/imports', { body: { filename: file.name, mime: file.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : DOCX, content_base64: btoa(binary), retain_original: retain } })
        if (!r.data) throw failure(r.error, r.response.status); return r.data
      })}>Parse locally</button>
    </section>
    <section className="status-card"><h2>Saved imports</h2>{runs.isPending && <p role="status">Loading imports…</p>}{runs.isError && <><p role="alert">{runs.error.message}</p><button onClick={() => void runs.refetch()}>Try again</button></>}
      {runs.data?.length === 0 && <p>No imports yet.</p>}{runs.data?.map(value => <button key={value.id} disabled={busy} onClick={() => select(value)}>{value.filename} · {value.status}</button>)}
    </section>
    {run && <section className="status-card"><h2>Review {run.filename}</h2><p>Status: {run.status} · revision {run.revision}</p>
      {run.error && <p role="alert">{run.error}</p>}
      <details><summary>Extracted text and source locators (shared if you request AI extraction)</summary>{run.fragments.map(f => <section key={f.locator}><h3>{f.locator}</h3><pre style={{ whiteSpace: 'pre-wrap' }}>{f.text}</pre></section>)}</details>
      {run.status === 'review' && <>
        <p>AI uses the configured import extraction assignment and consented endpoint in <NavLink to="/settings/ai">AI settings</NavLink>. Confirming facts is your review, not independent verification.</p>
        <button disabled={busy} onClick={() => void perform(async () => { const r = await api.POST('/api/imports/{identifier}/extract', { params: { path: { identifier: run.id }, query: { revision: run.revision } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Extract candidates with configured AI</button>
        <button disabled={busy} onClick={() => setCandidates([...candidates, { key: `entry_${candidates.length + 1}`, data: { type: 'project', name: '', description: '' }, locator: run.fragments[0]?.locator ?? '', excerpt: run.fragments[0]?.text.slice(0, 200) ?? '', decision: 'pending', user_supplied: true, duplicate_ids: [] }])}>Add candidate manually</button>
        {candidates.map((candidate, index) => <CandidateEditor key={`${run.id}:${candidate.key}`} candidate={candidate} forms={forms.data ?? []} records={records.data ?? []} candidates={candidates} disabled={busy} onChange={value => setCandidates(candidates.map((c, i) => i === index ? value : c))} />)}
        <button disabled={busy} onClick={() => void perform(saveReview)}>Save review</button>
        <button disabled={busy || !candidates.some(c => c.decision === 'accepted')} onClick={() => void perform(async () => { const saved = await saveReview(); const r = await api.POST('/api/imports/{identifier}/commit', { params: { path: { identifier: run.id }, query: { revision: saved.revision } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Commit approved facts</button>
        <button disabled={busy} onClick={() => void perform(async () => { const r = await api.POST('/api/imports/{identifier}/discard', { params: { path: { identifier: run.id }, query: { revision: run.revision } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Discard import</button>
      </>}
      {run.status === 'committed' && <p>{run.saved_ids.length} approved records saved. <NavLink to="/career/experience">Review career library</NavLink> · <NavLink to="/resumes">Build master resume</NavLink></p>}
      {run.original_available && <button disabled={busy} onClick={() => void perform(async () => { const r = await api.DELETE('/api/imports/{identifier}/original', { params: { path: { identifier: run.id } } }); if (r.error) throw failure(r.error, r.response.status); return { ...run, original_available: false } })}>Delete retained original</button>}
    </section>}
    {busy && <><p role="status">Processing import…</p>{runs.data?.filter(r => r.status === 'parsing').map(r => <button key={r.id} onClick={() => void api.POST('/api/imports/{identifier}/cancel', { params: { path: { identifier: r.id } } })}>Cancel parsing {r.filename}</button>)}{run && <button onClick={() => void api.POST('/api/imports/{identifier}/cancel', { params: { path: { identifier: run.id } } })}>Cancel AI extraction</button>}</>}
  </>
}

function CandidateEditor({ candidate, forms, records, candidates, disabled, onChange }: { candidate: Candidate; forms: components['schemas']['CareerForm'][]; records: CareerRecord[]; candidates: Candidate[]; disabled: boolean; onChange: (value: Candidate) => void }) {
  const form = forms.find(f => f.type === candidate.data.type)
  function field(name: string, value: unknown) { onChange({ ...candidate, data: { ...candidate.data, [name]: value }, user_supplied: true }) }
  return <fieldset disabled={disabled}><legend>Candidate {candidate.key}</legend>
    <label>Record category<select value={String(candidate.data.type)} onChange={e => onChange({ ...candidate, data: { type: e.target.value }, user_supplied: true })}>{forms.map(f => <option key={f.type} value={f.type}>{f.type.replaceAll('_', ' ')}</option>)}</select></label>
    {form?.fields.map(f => <label key={f.name}>{f.label}{f.required ? ' (required)' : ''}
      {f.related_type && <span>Choose an existing record or an accepted parent in this import.</span>}
      {f.related_type ? <select aria-label={f.label} value={String(candidate.data[f.name] ?? '')} onChange={e => field(f.name, e.target.value || null)}><option value="">No link selected</option>{candidates.filter(c => c.key !== candidate.key && c.data.type === f.related_type).map(c => <option key={c.key} value={'@' + c.key}>Import: {String(c.data.name ?? c.data.company ?? c.data.institution ?? c.data.text ?? c.data.type)} · {c.decision}</option>)}{records.filter(r => r.data.type === f.related_type).map(r => <option key={r.id} value={r.id}>Existing: {recordLabel(r)}</option>)}</select>
        : f.input_type === 'checkbox' ? <input type="checkbox" checked={Boolean(candidate.data[f.name] ?? f.default_value)} onChange={e => field(f.name, e.target.checked)} />
        : f.input_type === 'select' && !f.related_type ? <select value={String(candidate.data[f.name] ?? f.default_value ?? '')} onChange={e => field(f.name, e.target.value || null)}><option value="">Choose</option>{f.options?.map(o => <option key={o}>{o}</option>)}</select>
        : f.input_type === 'multiline' ? <textarea value={String(candidate.data[f.name] ?? '')} onChange={e => field(f.name, e.target.value)} />
        : f.input_type === 'list' ? <input value={(candidate.data[f.name] as string[] | undefined)?.join(', ') ?? ''} onChange={e => field(f.name, e.target.value.split(',').map(v => v.trim()).filter(Boolean))} />
        : f.input_type === 'details' ? <DetailsFields value={(candidate.data[f.name] ?? {}) as Record<string, string>} onChange={value => field(f.name, value)} />
        : <input type={f.input_type === 'date' ? 'date' : f.input_type === 'number' ? 'number' : 'text'} step={f.input_type === 'number' ? 'any' : undefined} value={String(candidate.data[f.name] ?? f.default_value ?? '')} onChange={e => field(f.name, e.target.value === '' ? null : f.input_type === 'number' && !['metric_value', 'gpa', 'years_of_use'].includes(f.name) ? Number(e.target.value) : e.target.value)} />}
    </label>)}
    <label>Source locator<input value={candidate.locator} onChange={e => onChange({ ...candidate, locator: e.target.value })} /></label>
    <label>Exact source excerpt<textarea value={candidate.excerpt} onChange={e => onChange({ ...candidate, excerpt: e.target.value })} /></label>
    {!!candidate.duplicate_ids?.length && <p>Possible duplicates: {candidate.duplicate_ids.map(id => { const record = records.find(r => r.id === id); return record ? recordLabel(record) : 'Existing record (reload library)' }).join(', ')}. Reject a duplicate candidate and link its children to the existing record; existing facts will not change.</p>}
    <label>Decision<select aria-label="Decision" value={candidate.decision} onChange={e => onChange({ ...candidate, decision: e.target.value as Candidate['decision'] })}><option value="pending">Pending</option><option value="accepted">Accept as user-confirmed facts</option><option value="rejected">Reject</option></select></label>
  </fieldset>
}

function DetailsFields({ value, onChange }: { value: Record<string, string>; onChange: (value: Record<string, string>) => void }) {
  const entries = Object.entries(value)
  return <span>{entries.map(([key, text], index) => <span className="form-grid" key={index}><input aria-label={`Detail label ${index + 1}`} value={key} onChange={e => { if (entries.some(([other], i) => i !== index && other === e.target.value)) return; onChange(Object.fromEntries(entries.map((entry, i) => i === index ? [e.target.value, text] : entry))) }} /><input aria-label={`Detail value ${index + 1}`} value={text} onChange={e => onChange({ ...value, [key]: e.target.value })} /></span>)}<button type="button" onClick={() => { let number = entries.length + 1; while (`Detail ${number}` in value) number++; onChange({ ...value, [`Detail ${number}`]: '' }) }}>Add detail</button></span>
}
