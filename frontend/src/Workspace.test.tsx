import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CareerPage } from './CareerPage'
import { ResumePage } from './ResumePage'
import * as workspace from './api/workspace'
vi.mock('./PdfPreview', () => ({ PdfPreview: () => <div title="Resume PDF preview" /> }))

vi.mock('./api/workspace', async importOriginal => ({ ...await importOriginal<typeof workspace>(), getForms: vi.fn(), getHistory: vi.fn(), saveCareer: vi.fn(), retireCareer: vi.fn(), getTemplates: vi.fn(), getResumes: vi.fn(), getPreview: vi.fn(), saveResume: vi.fn(), downloadPdf: vi.fn() }))

function renderPage(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><Routes><Route path="/career/:kind" element={<CareerPage />} /><Route path="/resumes" element={<ResumePage />} /></Routes></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(workspace.getHistory).mockResolvedValue([])
  vi.mocked(workspace.getResumes).mockResolvedValue([])
  vi.mocked(workspace.getTemplates).mockResolvedValue([{ id: '00000000-0000-4000-8000-000000000101', name: 'Classic', builtin_key: 'classic', default_styles: {}, ats_safe: true }])
  vi.mocked(workspace.getPreview).mockResolvedValue({ html: '<p>Ada</p>', pdf_base64: '', page_count: 1, html_hash: 'digest', warnings: [] })
})

describe('career library', () => {
  it('submits a user-entered record and shows saved status', async () => {
    vi.mocked(workspace.getForms).mockResolvedValue([{ type: 'skill', fields: [{ name: 'name', label: 'Name', input_type: 'text', required: true }, { name: 'aliases', label: 'Aliases', input_type: 'list', required: false }] }])
    vi.mocked(workspace.saveCareer).mockResolvedValue({ id: 'id', created_at: '', updated_at: '', deleted_at: null, data: { type: 'skill', name: 'Python', category: 'tool', aliases: ['Python 3'] } })
    renderPage('/career/skill')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Add record' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Add record' }))
    await userEvent.type(screen.getByLabelText('Name *'), 'Python')
    await userEvent.type(screen.getByLabelText('Aliases'), 'Python 3')
    await userEvent.click(screen.getByRole('button', { name: 'Save record' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Career record saved')
    expect(workspace.saveCareer).toHaveBeenCalledWith({ type: 'skill', name: 'Python', aliases: ['Python 3'] }, undefined)
  })
})

describe('master resume studio', () => {
  it('adds structured experience facts, a summary and separate duty bullets', async () => {
    const user = userEvent.setup()
    vi.mocked(workspace.saveCareer).mockImplementation(async data => ({ id: 'experience-id', data, created_at: '', updated_at: '', deleted_at: null }))
    vi.mocked(workspace.saveResume).mockImplementation(async (title, content, gold) => ({ id: 'saved', title, gold_standard: gold, kind: 'master', content, version_number: 1, updated_at: '' }))
    renderPage('/resumes')
    await user.type(screen.getByLabelText('Full name *'), 'Ada')
    await user.selectOptions(screen.getByLabelText('New section'), 'experience')
    await user.click(screen.getByRole('button', { name: 'Add section' }))
    await user.click(screen.getByRole('button', { name: 'Add experience' }))
    const form = within(screen.getByRole('form', { name: 'Add experience' }))
    await user.type(form.getByLabelText('Company *'), 'Example Company')
    await user.type(form.getByLabelText('Title *'), 'Engineer')
    await user.type(form.getByLabelText('Start date *'), '2020-01-01')
    await user.click(form.getByLabelText('Present'))
    expect(form.getByLabelText('End date')).toBeDisabled()
    await user.type(form.getByLabelText('Summary (one sentence max)'), 'Built reliable systems.')
    await user.type(form.getByLabelText('Duty 1'), 'Maintained APIs')
    await user.click(form.getByRole('button', { name: 'Add duty' }))
    await user.type(form.getByLabelText('Duty 2'), 'Reviewed changes')
    await user.click(form.getByRole('button', { name: 'Add experience to draft' }))
    expect(await screen.findByText('Experience saved to the career library and added to this draft.')).toBeInTheDocument()
    expect(workspace.saveCareer).toHaveBeenLastCalledWith(expect.objectContaining({ company: 'Example Company', job_title: 'Engineer', start_date: '2020-01-01', end_date: null, current: true, description: 'Built reliable systems.\nMaintained APIs\nReviewed changes' }), undefined)
    await user.click(screen.getByRole('button', { name: 'Save master' }))
    await waitFor(() => expect(workspace.saveResume).toHaveBeenLastCalledWith('My master resume', expect.objectContaining({ sections: [expect.objectContaining({ items: [expect.objectContaining({ text: 'Built reliable systems.', experience_summary: true }), expect.objectContaining({ text: 'Maintained APIs', experience_summary: false }), expect.objectContaining({ text: 'Reviewed changes', experience_summary: false })] })] }), false, undefined, false))
  })

  it('blocks multiple-sentence summaries and preserves inputs on a career save error', async () => {
    const user = userEvent.setup()
    vi.mocked(workspace.saveCareer).mockRejectedValue(new Error('Workspace locked'))
    renderPage('/resumes')
    await user.selectOptions(screen.getByLabelText('New section'), 'experience')
    await user.click(screen.getByRole('button', { name: 'Add section' }))
    await user.click(screen.getByRole('button', { name: 'Add experience' }))
    const form = within(screen.getByRole('form', { name: 'Add experience' }))
    await user.type(form.getByLabelText('Company *'), 'Example')
    await user.type(form.getByLabelText('Title *'), 'Engineer')
    await user.type(form.getByLabelText('Start date *'), '2020-01-01')
    await user.type(form.getByLabelText('End date'), '2021-01-01')
    await user.type(form.getByLabelText('Summary (one sentence max)'), 'One sentence. Two sentences.')
    expect(form.getByRole('button', { name: 'Add experience to draft' })).toBeDisabled()
    await user.clear(form.getByLabelText('Summary (one sentence max)'))
    await user.type(form.getByLabelText('Summary (one sentence max)'), 'One sentence.')
    await user.click(form.getByRole('button', { name: 'Add experience to draft' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Workspace locked')
    expect(form.getByLabelText('Company *')).toHaveValue('Example')
    expect(form.getByLabelText('Summary (one sentence max)')).toHaveValue('One sentence.')
  })

  it('autosaves shared date changes while preserving retained AI text and origin', async () => {
    const user = userEvent.setup()
    const experience: workspace.CareerRecord = { id: 'source', created_at: '', updated_at: '', deleted_at: null, data: { type: 'experience', company: 'Example', job_title: 'Engineer', start_date: '2020-01-01', current: true, description: 'Built reliable systems.', employment_type: 'contract', ordering_hint: 2 } }
    const content: workspace.Document = { schema_version: 1, header: { name: 'Ada' }, metadata: { template_id: '00000000-0000-4000-8000-000000000101', target_page_limit: 2 }, sections: [{ key: 'section', type: 'experience', title: 'Experience', visible: true, locked: false, items: [{ key: 'item', text: 'Built reliable systems.', origin: 'ai', locked: false, experience_summary: true, source_refs: [{ entity_type: 'experience', entity_id: 'source' }], facts: { employer: 'Example', title: 'Engineer', current: true, start_date: '2020-01-01' } }] }] }
    const saved: workspace.MasterResume = { id: 'saved', title: 'Master', gold_standard: false, kind: 'master', content, version_number: 1, updated_at: '' }
    vi.mocked(workspace.getHistory).mockResolvedValue([experience])
    vi.mocked(workspace.getResumes).mockResolvedValue([saved])
    vi.mocked(workspace.saveCareer).mockImplementation(async data => ({ ...experience, data }))
    vi.mocked(workspace.saveResume).mockImplementation(async (title, draft) => ({ ...saved, title, content: draft, version_number: 2 }))
    renderPage('/resumes?resume=saved')
    await user.click(await screen.findByRole('button', { name: 'Edit details: Engineer · Example' }))
    const form = within(screen.getByRole('form', { name: 'Edit experience details' }))
    await user.click(form.getByLabelText('Present'))
    await user.type(form.getByLabelText('End date'), '2025-12-31')
    await user.click(form.getByRole('button', { name: 'Save experience details' }))
    await waitFor(() => expect(workspace.saveResume).toHaveBeenLastCalledWith('Master', expect.objectContaining({ sections: [expect.objectContaining({ items: [expect.objectContaining({ text: 'Built reliable systems.', origin: 'ai', locked: false, experience_summary: true, facts: expect.objectContaining({ current: true }) })] })] }), false, saved, true), { timeout: 4000 })
    expect(workspace.saveCareer).toHaveBeenLastCalledWith(expect.objectContaining({ current: false, end_date: '2025-12-31', employment_type: 'contract', ordering_hint: 2, description: 'Built reliable systems.' }), 'source')
  })

  it('orders sections, previews and saves before downloading', async () => {
    renderPage('/resumes')
    await userEvent.type(screen.getByLabelText('Full name *'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Add section' }))
    await userEvent.selectOptions(screen.getByLabelText('New section'), 'skills')
    await userEvent.click(screen.getByRole('button', { name: 'Add section' }))
    await userEvent.click(screen.getByRole('button', { name: 'Move Skills up' }))
    const editors = document.querySelectorAll('.section-editor')
    expect(within(editors[0] as HTMLElement).getByLabelText('Section title')).toHaveValue('Skills')
    await waitFor(() => expect(screen.getByTitle('Resume PDF preview')).toBeInTheDocument(), { timeout: 2500 })
    vi.mocked(workspace.saveResume).mockImplementation(async (title, content, gold) => ({ id: 'saved', title, gold_standard: gold, kind: 'master' as const, content, version_number: 1, updated_at: '' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save & download PDF' }))
    expect(await screen.findByText('Resume saved and PDF downloaded.')).toBeInTheDocument()
    expect(workspace.downloadPdf).toHaveBeenCalledWith('saved')
    expect(workspace.saveResume).toHaveBeenCalledWith('My master resume', expect.objectContaining({ sections: [expect.objectContaining({ type: 'skills' }), expect.objectContaining({ type: 'summary' })] }), false, undefined, false)
  })

  it('keeps edits visible when saving conflicts', async () => {
    vi.mocked(workspace.saveResume).mockRejectedValue(new Error('Resume changed elsewhere. Reload before saving.'))
    renderPage('/resumes')
    await userEvent.type(screen.getByLabelText('Full name *'), 'Ada')
    await userEvent.click(screen.getByRole('button', { name: 'Save master' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Resume changed elsewhere')
    expect(screen.getByLabelText('Full name *')).toHaveValue('Ada')
  })
})

