import { api } from './client'
import type { components } from './schema'

export type CareerRecord = components['schemas']['CareerRecord']
export type CareerType = components['schemas']['CareerForm']['type']
export type CareerInput = CareerRecord['data']
export type Document = components['schemas']['ResumeDocument']
export type MasterResume = components['schemas']['MasterResume']
export type Section = Document['sections'][number]
export type Item = Section['items'][number]
export const careerTypes: CareerType[] = ['experience', 'achievement', 'project', 'education', 'course', 'skill', 'skill_evidence', 'certification', 'volunteer_experience', 'award', 'publication', 'custom_entry']
export const labels: Record<CareerType, string> = { experience: 'Experience', achievement: 'Achievements', project: 'Projects', education: 'Education', course: 'Courses', skill: 'Skills', skill_evidence: 'Skill evidence', certification: 'Certifications', volunteer_experience: 'Volunteer work', award: 'Awards', publication: 'Publications', custom_entry: 'Other history' }

export function failure(error: unknown, status: number): Error {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return new Error(detail)
  if (Array.isArray(detail)) return new Error(detail.map((d: { loc: string[]; msg: string }) => `${d.loc.slice(1).join(' ')}: ${d.msg}`).join('; '))
  return new Error(`Workspace request failed (${status}).`)
}

export async function getForms() {
  const r = await api.GET('/api/career/forms')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function getHistory() {
  const results = await Promise.all(careerTypes.map(async kind => {
    const r = await api.GET('/api/career/{kind}', { params: { path: { kind } } })
    if (!r.data) throw failure(r.error, r.response.status)
    return r.data
  }))
  return results.flat()
}

export function recordLabel(record: CareerRecord): string {
  const data = record.data
  if ('company' in data) return `${data.job_title} · ${data.company}`
  if ('institution' in data) return `${data.degree} · ${data.institution}`
  if ('name' in data) return data.name
  if ('title' in data) return data.title
  if ('text' in data) return data.text
  if ('skill_id' in data) return 'Linked skill evidence'
  return Object.values(data.payload ?? {}).join(' · ') || 'Custom entry'
}

export async function saveCareer(data: CareerInput, id?: string) {
  const r = id ? await api.PUT('/api/career/{identifier}', { params: { path: { identifier: id } }, body: data }) : await api.POST('/api/career', { body: data })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function retireCareer(record: CareerRecord) {
  const r = await api.DELETE('/api/career/{kind}/{identifier}', { params: { path: { kind: record.data.type, identifier: record.id } } })
  if (!r.response.ok) throw failure(r.error, r.response.status)
}

export async function getTemplates() {
  const r = await api.GET('/api/resumes/templates')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function getResumes() {
  const r = await api.GET('/api/resumes')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function saveResume(title: string, content: Document, gold_standard: boolean, saved?: MasterResume, autosave = false) {
  // Both explicit save and autosave use the last acknowledged version; the backend
  // rejects stale writes instead of silently overwriting another editor's changes.
  const body = { title, content, gold_standard, autosave, expected_version: saved?.version_number ?? 0 }
  const r = saved ? await api.PUT('/api/resumes/{identifier}', { params: { path: { identifier: saved.id } }, body }) : await api.POST('/api/resumes', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function getPreview(body: Document, signal?: AbortSignal, id?: string) {
  const r = id ? await api.POST('/api/resumes/{identifier}/preview', { params: { path: { identifier: id } }, body, signal }) : await api.POST('/api/resumes/preview', { body, signal })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function downloadPdf(id: string) {
  const r = await api.GET('/api/resumes/{identifier}/pdf', { params: { path: { identifier: id } }, parseAs: 'blob' })
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(r.data)
  const link = document.createElement('a')
  link.href = url
  link.download = 'resume.pdf'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
