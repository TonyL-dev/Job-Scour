import { api } from './client'
import { failure } from './workspace'

export async function downloadDocx(id: string, letter = false) {
  const options = { params: { path: { identifier: id } }, parseAs: 'blob' as const }
  const r = letter ? await api.GET('/api/letters/versions/{identifier}/docx', options) : await api.GET('/api/resumes/versions/{identifier}/docx', options)
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = letter ? 'cover-letter-version.docx' : 'resume-version.docx'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
