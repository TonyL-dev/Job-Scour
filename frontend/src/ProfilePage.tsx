import { StatusNotice, PageHeader, Button } from './components/ui/Controls'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'
import { api } from './api/client'
import { getHistory, recordLabel, failure } from './api/workspace'
import type { CareerInput } from './api/workspace'
import type { components } from './api/schema'

type Review = components['schemas']['ProfileReview']

export function ProfilePage() {
  const cache = useQueryClient()
  const career = useQuery({ queryKey: ['career'], queryFn: getHistory })
  const reviews = useQuery({ queryKey: ['profile-reviews'], queryFn: async () => { const r = await api.GET('/api/profile'); if (!r.data) throw failure(r.error, r.response.status); return r.data } })
  const [id, setId] = useState('')
  const [review, setReview] = useState<Review>()
  const [answers, setAnswers] = useState<string[]>([])
  const [proposed, setProposed] = useState<CareerInput>()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)
  const source = career.data?.find(r => r.id === id)
  function select(value: Review) { setReview(value); setAnswers(value.answers.length ? value.answers : value.questions.map(() => '')); setProposed(value.proposed ?? undefined) }
  async function perform(action: () => Promise<Review>) {
    setBusy(true); setFailed(false); setMessage('')
    try { select(await action()); await cache.invalidateQueries({ queryKey: ['profile-reviews'] }); await cache.invalidateQueries({ queryKey: ['career'] }) }
    catch (e) { setFailed(true); setMessage(e instanceof Error ? e.message : 'Profile review failed') }
    finally { setBusy(false) }
  }
  return <><PageHeader title="Strengthen my profile" /><p>AI asks questions. You supply and confirm facts. Unknown, skipped and qualitative answers are welcome; a metric is optional.</p>
    {message && <StatusNotice error={failed}>{message}</StatusNotice>}
    <section className="panel status-card"><h2>Choose evidence</h2>
      {career.isError && <><p role="alert">{career.error.message}</p><Button onClick={() => void career.refetch()}>Try again</Button></>}
      <label>Career evidence<select aria-label="Career evidence" disabled={busy} value={id} onChange={e => setId(e.target.value)}><option value="">Choose</option>{career.data?.filter(r => ['achievement', 'project', 'experience'].includes(r.data.type)).map(r => <option key={r.id} value={r.id}>{recordLabel(r)}</option>)}</select></label>
      {source && <><h3>Source context</h3><p>{recordLabel(source)}</p><p>{'text' in source.data ? source.data.text : 'description' in source.data ? source.data.description : ''}</p><details><summary>All source facts shared with configured AI</summary><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(source.data, null, 2)}</pre></details></>}
      <p>Questions use the profile questions assignment and sharing consent in <NavLink to="/settings/ai">AI settings</NavLink>.</p>
      <Button variant="primary" disabled={!source || busy} onClick={() => void perform(async () => { if (!source || !['achievement', 'project', 'experience'].includes(source.data.type)) throw new Error('Choose supported evidence'); const r = await api.POST('/api/profile', { body: { kind: source.data.type as 'achievement' | 'project' | 'experience', record_id: source.id } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Ask follow-up questions</Button>
      {busy && <><p role="status">Working…</p><Button onClick={() => void api.POST('/api/profile/{source_id}/cancel', { params: { path: { source_id: id } } })}>Cancel questions</Button></>}
    </section>
    <section className="panel status-card collection-panel"><h2>Saved reviews</h2>{reviews.isPending && <p role="status">Loading…</p>}{reviews.isError && <><p role="alert">{reviews.error.message}</p><Button onClick={() => void reviews.refetch()}>Try again</Button></>}{reviews.data?.length === 0 && <p>No reviews yet.</p>}{reviews.data?.map(r => <Button key={r.id} disabled={busy} onClick={() => select(r)}>{recordLabel(r.source)} · {r.status}</Button>)}</section>
    {review && <section className="panel status-card"><h2>Review answers</h2><p>{review.status} · {recordLabel(review.source)}</p>
      {review.questions.map((q, index) => <label key={index}>{q}<textarea aria-label={`Answer ${index + 1}`} disabled={busy || review.status !== 'review'} maxLength={2000} value={answers[index] ?? ''} onChange={e => setAnswers(answers.map((a, i) => i === index ? e.target.value : a))} /></label>)}
      {review.status === 'review' && <>
        <Button disabled={busy} onClick={() => void perform(async () => { const r = await api.PUT('/api/profile/{identifier}/answers', { params: { path: { identifier: review.id } }, body: { expected_revision: review.revision, answers } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Prepare factual edit</Button>
        {proposed && <><h3>Current wording</h3><p>{'text' in review.source.data ? review.source.data.text : 'description' in review.source.data ? review.source.data.description : ''}</p><label>Proposed wording<textarea aria-label="Proposed wording" value={'text' in proposed ? proposed.text : 'description' in proposed ? proposed.description : ''} onChange={e => setProposed({ ...proposed, ...('text' in proposed ? { text: e.target.value } : { description: e.target.value }) } as CareerInput)} /></label>
          {proposed.type === 'achievement' && <><label>Metric value (optional)<input type="number" value={proposed.metric_value ?? ''} onChange={e => setProposed({ ...proposed, metric_value: e.target.value || null })} /></label><label>Metric unit (optional)<input value={proposed.metric_unit ?? ''} onChange={e => setProposed({ ...proposed, metric_unit: e.target.value || null })} /></label></>}
          <p>This records your supplied facts; it does not certify their accuracy. Historical resumes remain unchanged.</p><Button variant="primary" disabled={busy} onClick={() => void perform(async () => { const r = await api.POST('/api/profile/{identifier}/confirm', { params: { path: { identifier: review.id } }, body: { expected_revision: review.revision, data: proposed } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Confirm my factual edit</Button>
        </>}
        <Button variant="danger" disabled={busy} onClick={() => void perform(async () => { const r = await api.POST('/api/profile/{identifier}/discard', { params: { path: { identifier: review.id }, query: { revision: review.revision } } }); if (!r.data) throw failure(r.error, r.response.status); return r.data })}>Discard review</Button>
      </>}
    </section>}
  </>
}
