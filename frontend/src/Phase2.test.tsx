import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AISettingsPage } from './AISettingsPage'
import { JobsPage } from './JobsPage'
import * as phase2 from './api/phase2'

vi.mock('./api/phase2', async importOriginal => ({ ...await importOriginal<typeof phase2>(), getSettings: vi.fn(), getPrompts: vi.fn(), getJobs: vi.fn(), saveJob: vi.fn(), analyzeJob: vi.fn(), saveEndpoint: vi.fn(), saveProfile: vi.fn(), assignModel: vi.fn(), testProfile: vi.fn(), detectEndpoints: vi.fn() }))

const job: phase2.Job = { id: 'job', company: 'Example', title: 'Engineer', location: '', url: '', raw_text: 'Required skills: Python and SQL.', created_at: '' }
const result: phase2.AnalysisResult = { id: 'analysis', job_id: 'job', model: 'Local model', prompt_version: 'job_analysis:v1:digest', cached: false, analysis: { required_skills: [{ term: 'Python', evidence: 'Python' }], preferred_skills: [], technologies: [], responsibilities: [], company_values: [], industry_terms: [], keywords: [{ term: 'Python', evidence: 'Python', weight: 5 }], seniority: null, years_experience: null }, match: { items: [], missing_keywords: ['python'], strengths: [], emphasis_areas: [], keyword_coverage: 0, retrieval_mode: 'keywords', warnings: [], career_snapshot_hash: 'hash' } }

function page(element: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{element}</MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(phase2.getJobs).mockResolvedValue([])
  vi.mocked(phase2.getSettings).mockResolvedValue({ endpoints: [], profiles: [], assignments: [] })
  vi.mocked(phase2.getPrompts).mockResolvedValue([])
})

describe('Phase 2 workflows', () => {
  it('configures Codex only after consent and assigns tailoring and Phase 6 chat tasks', async () => {
    vi.mocked(phase2.saveEndpoint).mockImplementation(async body => ({ ...body, id: 'codex-endpoint' }))
    vi.mocked(phase2.saveProfile).mockImplementation(async body => ({ ...body, id: 'codex-profile' }))
    vi.mocked(phase2.testProfile).mockResolvedValue({ ok: true })
    page(<AISettingsPage />)
    const setup = await screen.findByRole('button', { name: 'Use Codex for AI tasks' })
    expect(setup).toBeDisabled()
    await userEvent.click(screen.getByLabelText('I consent to sending supplied job text and career facts to OpenAI through Codex.'))
    await userEvent.click(setup)
    expect(await screen.findByText(/Codex is assigned to all nine chat tasks/)).toBeInTheDocument()
    expect(phase2.saveEndpoint).toHaveBeenCalledWith(expect.objectContaining({ provider: 'codex', remote_consent: true }))
    expect(phase2.assignModel).toHaveBeenCalledTimes(9)
    for (const task of ['import_extraction', 'profile_questions', 'cover_letter']) expect(phase2.assignModel).toHaveBeenCalledWith(task, 'codex-profile')
    expect(phase2.assignModel).not.toHaveBeenCalledWith('embeddings', expect.anything())
    expect(phase2.testProfile).toHaveBeenCalledWith('codex-profile')
  })
  it('saves a pasted job and displays requirements and gaps', async () => {
    vi.mocked(phase2.saveJob).mockResolvedValue(job)
    vi.mocked(phase2.analyzeJob).mockResolvedValue(result)
    page(<JobsPage />)
    await userEvent.type(screen.getByLabelText('Job description'), job.raw_text)
    await userEvent.click(screen.getByRole('button', { name: 'Save job description' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Analyze saved job' }))
    expect(await screen.findByRole('heading', { name: 'Career match' })).toBeInTheDocument()
    expect(screen.getByText('0% keyword coverage')).toBeInTheDocument()
    expect(phase2.analyzeJob).toHaveBeenCalledWith('job', false, expect.any(AbortSignal), expect.any(Function))
  })

  it('cancels generation and keeps the saved job ready to retry', async () => {
    vi.mocked(phase2.getJobs).mockResolvedValue([job])
    vi.mocked(phase2.analyzeJob).mockImplementation((_id, _embeddings, signal) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))))
    page(<JobsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Engineer · Example' }))
    await userEvent.click(screen.getByRole('button', { name: 'Analyze saved job' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancel analysis' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Analysis cancelled')
    expect(screen.getByRole('button', { name: 'Analyze saved job' })).toBeEnabled()
  })

  it('requires explicit remote consent in the endpoint form and resets it when the URL changes', async () => {
    vi.mocked(phase2.saveEndpoint).mockImplementation(async body => ({ ...body, id: 'endpoint' }))
    page(<AISettingsPage />)
    await userEvent.selectOptions(screen.getByLabelText('Provider'), 'openai_compatible')
    const url = screen.getByLabelText('Base URL')
    await userEvent.clear(url)
    await userEvent.type(url, 'https://remote.example/v1')
    const consent = screen.getByLabelText('I consent to sending job text and career records to this remote endpoint.')
    expect(consent).not.toBeChecked()
    await userEvent.click(consent)
    await userEvent.click(screen.getByRole('button', { name: 'Save endpoint' }))
    await waitFor(() => expect(phase2.saveEndpoint).toHaveBeenCalledWith(expect.objectContaining({ remote_consent: true, base_url: 'https://remote.example/v1' }), undefined))
    await userEvent.type(url, '/changed')
    expect(consent).not.toBeChecked()
  })

  it('edits and disables an endpoint using only its writable fields', async () => {
    const endpoint: phase2.Endpoint = { id: 'saved-endpoint', name: 'My local model', provider: 'lm_studio', base_url: 'http://127.0.0.1:1234/v1', enabled: true, remote_consent: false, api_key_env: null }
    vi.mocked(phase2.getSettings).mockResolvedValue({ endpoints: [endpoint], profiles: [], assignments: [] })
    vi.mocked(phase2.saveEndpoint).mockImplementation(async body => ({ ...body, id: endpoint.id }))
    page(<AISettingsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Edit My local model' }))
    await userEvent.click(screen.getByLabelText('Endpoint enabled'))
    await userEvent.click(screen.getByRole('button', { name: 'Save endpoint' }))
    await waitFor(() => expect(phase2.saveEndpoint).toHaveBeenCalledWith({ name: endpoint.name, provider: endpoint.provider, base_url: endpoint.base_url, enabled: false, remote_consent: false, api_key_env: null }, endpoint.id))
  })
})

describe('SSE analysis reader', () => {
  it('assembles split UTF-8 events, reports progress and returns the final result', async () => {
    const encoder = new TextEncoder()
    const payload = encoder.encode(`: heartbeat\n\nevent: progress\ndata: {"stage":"Analyzing…"}\n\nevent: result\ndata: ${JSON.stringify(result)}\n\n`)
    const stream = new ReadableStream<Uint8Array>({ start(controller) { for (let i = 0; i < payload.length; i += 7) controller.enqueue(payload.slice(i, i + 7)); controller.close() } })
    const progress = vi.fn()
    expect(await phase2.readAnalysisStream(stream, progress)).toEqual(result)
    expect(progress).toHaveBeenCalledWith('Analyzing…')
  })

  it('surfaces model errors and premature disconnects', async () => {
    const stream = (value: string) => new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new TextEncoder().encode(value)); c.close() } })
    await expect(phase2.readAnalysisStream(stream('event: error\ndata: {"detail":"Model failed"}\n\n'), vi.fn())).rejects.toThrow('Model failed')
    await expect(phase2.readAnalysisStream(stream(': heartbeat\n\n'), vi.fn())).rejects.toThrow('ended before a result')
  })
})
