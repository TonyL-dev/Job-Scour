import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GenerationPage } from './GenerationPage'
import * as generation from './api/generation'
import * as workspace from './api/workspace'
import * as jobs from './api/phase2'
import type { Run } from './api/generation'

vi.mock('./api/generation')
vi.mock('./api/workspace')
vi.mock('./api/phase2')
vi.mock('./PdfPreview', () => ({ PdfPreview: () => <p>Rendered review PDF</p> }))

const content: workspace.Document = { schema_version: 1, header: { name: 'Synthetic' }, metadata: { template_id: 'template', target_page_limit: 2 }, sections: [{ key: 'section', type: 'experience', title: 'Experience', visible: true, locked: false, items: [{ key: 'item', text: 'Original source text', origin: 'user', locked: false, source_refs: [{ entity_type: 'achievement', entity_id: 'source' }] }] }] }
const run: Run = { id: 'run', created_at: '2026-10-07T12:00:00Z', status: 'succeeded', request: { master_id: 'master', job_id: 'job', allow_layout_adjustments: false, use_embeddings: false, instruction: '', preset: 'tailor' }, base: content, proposed: content, suggestions: [{ id: 'suggestion', section_key: 'section', item_key: 'item', original: content.sections[0]!.items[0]!, proposed: { ...content.sections[0]!.items[0]!, text: 'Proposed text', origin: 'ai' }, verification: 'supported', reason: 'Cited source supports the text', sources: { source: 'Career source evidence' } }, { id: 'unsafe', section_key: 'section', item_key: 'unsafe-item', original: null, proposed: { key: 'unsafe-item', text: 'Unsupported metric 400%', origin: 'ai', locked: false, source_refs: [{ entity_type: 'achievement', entity_id: 'source' }] }, verification: 'unsupported', reason: 'Metric absent from source', sources: { source: 'Career source evidence' } }], events: [], page_count: 1, warnings: [], error: null, provenance: {}, saved_resume_id: null, review_revision: 0, decisions: [] }

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(generation.getRuns).mockResolvedValue([run])
  vi.mocked(generation.getRun).mockResolvedValue(run)
  vi.mocked(workspace.getResumes).mockResolvedValue([])
  vi.mocked(jobs.getJobs).mockResolvedValue([])
  vi.mocked(generation.reviewPreview).mockResolvedValue({ page_count: 1, html: '', pdf_base64: '', html_hash: '', warnings: [] })
  vi.mocked(generation.saveReview).mockResolvedValue({ ...run, review_revision: 1 })
})

async function open() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}><MemoryRouter><GenerationPage /></MemoryRouter></QueryClientProvider>)
  await waitFor(() => expect(screen.getByLabelText('Saved generation runs').querySelectorAll('option')).toHaveLength(2))
  await userEvent.selectOptions(screen.getByLabelText('Saved generation runs'), 'run')
  await screen.findByRole('heading', { name: 'Review changes' })
}

describe('generation review', () => {
  it('shows sources and side by side changes, excludes unsafe accepts, and persists decisions', async () => {
    await open()
    expect(screen.getByText('Original source text', { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText('Proposed text')).toBeInTheDocument()
    const unsafe = screen.getByText('Unsupported metric 400%').closest('section')!
    expect(within(unsafe).getByRole('button', { name: 'Accept' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Accept all supported changes' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save review decisions' }))
    await waitFor(() => expect(generation.saveReview).toHaveBeenCalledWith('run', { expected_revision: 0, locks: {}, decisions: [{ suggestion_id: 'suggestion', action: 'accept' }, { suggestion_id: 'unsafe', action: 'reject' }] }))
  })
  it('edits a suggestion as confirmed manual text and previews selected decisions', async () => {
    await open()
    const supported = screen.getByText('Proposed text').closest('section')!
    await userEvent.click(within(supported).getByRole('button', { name: 'Edit' }))
    const editor = screen.getByLabelText('Edit suggestion suggestion')
    await userEvent.clear(editor)
    await userEvent.type(editor, 'My confirmed wording')
    await waitFor(() => expect(generation.reviewPreview).toHaveBeenCalledWith('run', { expected_revision: 0, locks: {}, decisions: [{ suggestion_id: 'suggestion', action: 'edit', text: 'My confirmed wording' }] }, expect.any(AbortSignal)), { timeout: 2500 })
  })
})
