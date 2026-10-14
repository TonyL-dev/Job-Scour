import { api } from './client'
import { failure } from './workspace'

export async function letterPdf(id: string) {
  const r = await api.GET('/api/letters/versions/{identifier}/pdf', { params: { path: { identifier: id } }, parseAs: 'blob' })
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(r.data); const a = document.createElement('a'); a.href = url; a.download = 'cover-letter.pdf'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
