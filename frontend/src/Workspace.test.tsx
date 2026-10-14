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

