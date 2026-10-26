import { PageHeader, ActionGroup, Button } from './components/ui/Controls'
import { QueryNotice } from './QueryNotice'
import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { analyzeJob, getJobs, saveJob } from './api/phase2'
import type { AnalysisResult, Job, JobInput } from './api/phase2'

const blank: JobInput = { company: '', title: '', location: '', url: '', raw_text: '' }

export function JobsPage() {
  const cache = useQueryClient()
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: getJobs })
  const [draft, setDraft] = useState<JobInput>(blank)
  const [selected, setSelected] = useState<Job>()
  const [result, setResult] = useState<AnalysisResult>()
  const [embeddings, setEmbeddings] = useState(false)
  const [busy, setBusy] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [stage, setStage] = useState('')
  const [error, setError] = useState('')
  const controller = useRef<AbortController | null>(null)
  useEffect(() => () => controller.current?.abort(), [])

  async function run(job: Job) {
    const abort = new AbortController()
    controller.current = abort
    setBusy(true); setAnalyzing(true); setResult(undefined); setError(''); setStage('Starting analysis…')
    try { setResult(await analyzeJob(job.id, embeddings, abort.signal, setStage)); setStage('Analysis complete.') }
    catch (e) { if (abort.signal.aborted) setStage('Analysis cancelled. The saved job is ready to retry.'); else { setError(e instanceof Error ? e.message : 'Analysis failed.'); setStage('') } }
    finally { setBusy(false); setAnalyzing(false); if (controller.current === abort) controller.current = null }
  }

  return <>
    <PageHeader title="Job analysis" eyebrow="UNDERSTAND YOUR NEXT OPPORTUNITY" />
    <p>Paste a job description to extract requirements and find relevant career evidence. <Link to="/settings/ai">Connect and assign your models</Link> first.</p>
    <p className="muted">Relevance and keyword coverage help you review your fit. Missing terms remain gaps; generate a sourced resume in Generate & review, then run ATS checks in Resume history.</p>
    {error && <p role="alert">{error}</p>}<QueryNotice query={jobs} label="Saved jobs" />
    {stage && <p role="status" aria-live="polite">{stage}</p>}
    <div className="phase2-grid">
      <section className="panel status-card"><h2>{selected ? 'Saved job description' : 'Add a job description'}</h2>
        <form onSubmit={e => { e.preventDefault(); void (async () => { setBusy(true); setError(''); try { const job = await saveJob(draft); setSelected(job); await cache.invalidateQueries({ queryKey: ['jobs'] }); setStage('Job description saved.'); } catch (e) { setError(e instanceof Error ? e.message : 'Save failed.') } finally { setBusy(false) } })() }}>
          <label>Company<input disabled={busy || !!selected} value={draft.company} onChange={e => setDraft({ ...draft, company: e.target.value })} /></label>
          <label>Job title<input disabled={busy || !!selected} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label>
          <label>Location<input disabled={busy || !!selected} value={draft.location} onChange={e => setDraft({ ...draft, location: e.target.value })} /></label>
          <label>Job URL<input type="url" disabled={busy || !!selected} value={draft.url} onChange={e => setDraft({ ...draft, url: e.target.value })} /></label>
          <label>Job description<textarea required minLength={20} maxLength={30000} rows={10} disabled={busy || !!selected} value={draft.raw_text} onChange={e => setDraft({ ...draft, raw_text: e.target.value })} /></label>
          {!selected && <Button variant="primary" disabled={busy}>Save job description</Button>}
        </form>
        <label className="check-label"><input type="checkbox" disabled={busy} checked={embeddings} onChange={e => setEmbeddings(e.target.checked)} />Use embeddings with keyword matching</label>
        <ActionGroup>{selected && <Button variant="primary" disabled={busy} onClick={() => void run(selected)}>Analyze saved job</Button>}<Button disabled={!analyzing} onClick={() => controller.current?.abort()}>Cancel analysis</Button><Button disabled={busy} onClick={() => { setSelected(undefined); setDraft(blank); setResult(undefined); setStage(''); setError('') }}>New job</Button></ActionGroup>
      </section>
      <section className="panel status-card"><h2>Saved jobs</h2>{jobs.data?.length === 0 && <p>No jobs saved yet.</p>}<ul>{jobs.data?.map(job => <li key={job.id}><Button disabled={busy} onClick={() => { setSelected(job); setDraft(job); setResult(undefined); setStage(''); setError('') }}>{job.title || 'Untitled job'}{job.company ? ` · ${job.company}` : ''}</Button></li>)}</ul></section>
    </div>
    {result && <>
      <section className="panel status-card"><h2>Requirements</h2><p className="muted">Model: {result.model} · {result.cached ? 'Saved analysis reused; career matches refreshed' : 'New analysis'} · Prompt: {result.prompt_version.split(':').slice(0, 2).join(':')}</p>
        <div className="phase2-grid">{(['required_skills', 'preferred_skills', 'technologies', 'responsibilities', 'company_values', 'industry_terms'] as const).map(key => <div key={key}><h3>{key.replace(/_/g, ' ')}</h3>{result.analysis[key].length ? <ul>{result.analysis[key].map((r, i) => <li key={i}><strong>{r.term}</strong><blockquote>{r.evidence}</blockquote></li>)}</ul> : <p>Not stated.</p>}</div>)}</div>
        <p>Seniority: {result.analysis.seniority?.term ?? 'Not stated'} · Experience: {result.analysis.years_experience?.term ?? 'Not stated'}</p>
        <h3>Weighted keywords</h3><ul>{result.analysis.keywords.map((k, i) => <li key={i}>{k.term} · weight {k.weight}/5 <span className="muted">— {k.evidence}</span></li>)}</ul>
      </section>
      <section className="panel status-card"><h2>Career match</h2><p><strong>{result.match.keyword_coverage}% keyword coverage</strong> · {result.match.retrieval_mode === 'keywords' ? 'Keyword matching' : 'Embeddings + keyword matching'}</p>{result.match.warnings.map(w => <p key={w}>{w}</p>)}
        <h3>Missing keywords</h3><p>{result.match.missing_keywords.join(', ') || 'No missing keywords in the current career library.'}</p><h3>Strengths</h3><p>{result.match.strengths.join(', ') || 'No matching keywords yet.'}</p><h3>Suggested emphasis</h3><ul>{result.match.emphasis_areas.map((v, i) => <li key={i}>{v}</li>)}</ul>
        <h3>Ranked career evidence</h3>{result.match.items.length === 0 && <p>Add experience, achievements, projects or skills to your career library to see matches.</p>}
        <ol>{result.match.items.map(item => <li key={item.source_ref.entity_id}><strong>{item.label}</strong> · relevance {item.score}/100<p>{item.reasons.join('. ') || 'No matching keywords.'}</p><Link to={`/career/${item.source_ref.entity_type}`}>Review {item.source_ref.entity_type.replace(/_/g, ' ')} source</Link><p className="muted">Source: {item.source_ref.entity_id}</p></li>)}</ol>
      </section>
    </>}
  </>
}
