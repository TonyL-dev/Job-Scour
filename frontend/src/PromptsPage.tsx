import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api/client'
import { failure } from './api/workspace'
import { getPrompts } from './api/phase2'
import type { components } from './api/schema'

type Fork = components['schemas']['PromptFork']
type Custom = components['schemas']['CustomPrompt']
type Report = components['schemas']['EvaluationReport']

export function PromptsPage() {
  const cache = useQueryClient()
  const packaged = useQuery({ queryKey: ['prompts'], queryFn: getPrompts })
  const custom = useQuery({ queryKey: ['custom-prompts'], queryFn: async () => { const r = await api.GET('/api/prompts'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const active = useQuery({ queryKey: ['active-prompts'], queryFn: async () => { const r = await api.GET('/api/prompts/active'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const [body, setBody] = useState<Fork>({ task: 'rewriting', name: 'My concise wording', tone: 'concise', focus: 'clarity', notes: '' })
  const [selected, setSelected] = useState<Custom>()
  const reports = useQuery({ queryKey: ['prompt-reports', selected?.id], enabled: !!selected, queryFn: async () => { const r = await api.GET('/api/prompts/{identifier}/reports', { params: { path: { identifier: selected!.id } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const [report, setReport] = useState<Report>()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  async function perform(action: () => Promise<void>) { setBusy(true); setMessage(''); try { await action(); await cache.invalidateQueries({ queryKey: ['custom-prompts'] }); await cache.invalidateQueries({ queryKey: ['active-prompts'] }); await cache.invalidateQueries({ queryKey: ['prompt-reports'] }) } catch (e) { setMessage(e instanceof Error ? e.message : 'Prompt operation failed') } finally { setBusy(false) } }
  return <><h1>Prompt management & playground</h1><p>Fork supported task/style preferences. System guardrails, schemas, source authority and verification rules are fixed. Saving a version does not activate it.</p>{message && <p role="alert">{message}</p>}
    <section className="status-card"><h2>Packaged prompts (read only)</h2>{packaged.isError && <><p role="alert">{packaged.error.message}</p><button onClick={() => void packaged.refetch()}>Try again</button></>}{packaged.data?.map(p => <details key={p.digest}><summary>{p.key} · version {p.version}</summary><p>{p.system_text}</p><pre style={{ whiteSpace: 'pre-wrap' }}>{p.user_template}</pre></details>)}</section>
    <section className="status-card"><h2>Create immutable preference version</h2><label>Prompt name<input value={body.name} onChange={e => setBody({ ...body, name: e.target.value })} /></label><label>Task<select aria-label="Prompt task" value={body.task} onChange={e => setBody({ ...body, task: e.target.value as Fork['task'], parent_id: null })}>{packaged.data?.map(p => <option key={p.key} value={p.key}>{p.key.replaceAll('_', ' ')}</option>)}</select></label>
      <label>Tone<select aria-label="Prompt tone" value={body.tone} onChange={e => setBody({ ...body, tone: e.target.value as Fork['tone'] })}><option>plain</option><option>formal</option><option>concise</option></select></label><label>Task focus<select aria-label="Prompt focus" value={body.focus} onChange={e => setBody({ ...body, focus: e.target.value as Fork['focus'] })}><option>clarity</option><option>impact</option><option>technical</option></select></label><label>Changelog notes<textarea value={body.notes ?? ''} onChange={e => setBody({ ...body, notes: e.target.value })} /></label>
      <button disabled={busy || !body.name} onClick={() => void perform(async () => { const r = await api.POST('/api/prompts', { body }); if (!r.data) throw failure(r.error, r.response.status); setSelected(r.data); setReport(undefined); setMessage('Immutable prompt preference saved; evaluate before activation.') })}>Save new preference version</button>
    </section>
    <section className="status-card"><h2>Saved versions & rollback</h2>{custom.data?.length === 0 && <p>No custom preferences yet.</p>}{custom.data?.map(p => <div key={p.id}><button disabled={busy} onClick={() => { setSelected(p); setReport(undefined) }}>{p.name} · {p.task} {active.data?.[p.task] === p.id ? '· active' : ''}</button><button disabled={busy} onClick={() => { setBody({ task: p.task, name: p.name + ' revision', tone: p.tone, focus: p.focus, notes: '', parent_id: p.id }) }}>Fork this version</button></div>)}</section>
    {selected && <section className="status-card"><h2>Synthetic playground: {selected.name}</h2><p>Runs baseline and candidate against three synthetic fixtures (40%, 25% and an instruction-injection trap). No career database data is sent. The configured task/verification providers receive the fixture facts; their existing consent is required. Model outputs are retained in private evaluation reports.</p>
      {active.data?.[selected.task] && <button disabled={busy} onClick={() => void perform(async () => { const currentId = active.data?.[selected.task]; if (!currentId) throw new Error('Active prompt changed; reload'); const r = await api.POST('/api/prompts/reset', { body: { task: selected.task, expected_prompt_id: currentId } }); if (!r.data) throw failure(r.error, r.response.status); setMessage('Packaged prompt restored for new calls; custom versions and reports are preserved.') })}>Reset task to packaged prompt</button>}
      <p>Input: Synthetic Orbit, Python APIs and an explicit latency reduction. Kubernetes is a gap; untrusted instructions must not create a new career fact. Provider/model assignments are controlled in AI settings.</p>
      <h3>Preserved evaluation reports</h3>{reports.data?.map((r, index) => <button key={r.id} disabled={busy} onClick={() => setReport(r)}>Evaluation {reports.data.length - index} · {r.passed ? 'passed' : 'failed'}</button>)}{reports.isError && <><p role="alert">{reports.error.message}</p><button onClick={() => void reports.refetch()}>Retry evaluation reports</button></>}
      <button disabled={busy} onClick={() => void perform(async () => { const r = await api.POST('/api/prompts/{identifier}/evaluate', { params: { path: { identifier: selected.id } } }); if (!r.data) throw failure(r.error, r.response.status); setReport(r.data) })}>Evaluate baseline & candidate</button>
      {busy && <><p role="status">Evaluating synthetic fixtures…</p><button onClick={() => void api.POST('/api/prompts/{identifier}/cancel', { params: { path: { identifier: selected.id } } })}>Cancel evaluation</button></>}
      {report && <><h3>{report.passed ? 'Applicable synthetic checks passed' : 'Evaluation failed; activation blocked'}</h3><p>This limited corpus is not a guarantee of semantic accuracy.</p><div className="form-grid">{report.results.map((r, index) => <section key={index}><h4>{String(r.fixture)}</h4><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(r, null, 2)}</pre></section>)}</div>
        <button disabled={busy || !report.passed} onClick={() => void perform(async () => { const r = await api.POST('/api/prompts/active', { body: { task: selected.task, prompt_id: selected.id, expected_prompt_id: active.data?.[selected.task] ?? null, report_id: report.id } }); if (!r.data) throw failure(r.error, r.response.status); setMessage('Prompt activated for new calls. Existing runs retain their captured version.') })}>Activate this evaluated version</button>
      </>}
    </section>}
  </>
}
