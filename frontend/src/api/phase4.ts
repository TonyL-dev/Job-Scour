import { api } from './client'
import { failure } from './workspace'
import type { components } from './schema'
export type Version = components['schemas']['ResumeVersion']
export type Report = components['schemas']['Report']
export type Application = components['schemas']['Application']
export type ApplicationSave = components['schemas']['ApplicationSave']
export type Stage = Application['stage']

export async function versions(id: string) {
  const r = await api.GET('/api/resumes/{identifier}/versions', { params: { path: { identifier: id } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function versionAction(id: string, expected_version: number, duplicate: boolean) {
  const options = { params: { path: { identifier: id } }, body: { expected_version } }
  const r = duplicate ? await api.POST('/api/resumes/versions/{identifier}/duplicate', options) : await api.POST('/api/resumes/versions/{identifier}/restore', options)
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function versionPdf(id: string) {
  const r = await api.GET('/api/resumes/versions/{identifier}/pdf', { params: { path: { identifier: id } }, parseAs: 'blob' })
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(r.data)
  const a = document.createElement('a'); a.href = url; a.download = 'resume-version.pdf'; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export async function createReport(version_id: string, analysis_id?: string) {
  const r = await api.POST('/api/ats/reports', { body: { version_id, analysis_id: analysis_id || null } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function getReports(version_id: string) {
  const r = await api.GET('/api/ats/reports/{version_id}', { params: { path: { version_id } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function getApplications() {
  const r = await api.GET('/api/applications')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function saveApplication(body: ApplicationSave, id?: string) {
  const r = id ? await api.PUT('/api/applications/{identifier}', { params: { path: { identifier: id } }, body }) : await api.POST('/api/applications', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function applicationEvents(id: string) {
  const r = await api.GET('/api/applications/{identifier}/events', { params: { path: { identifier: id } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function addEvent(id: string, body: components['schemas']['EventInput']) {
  const r = await api.POST('/api/applications/{identifier}/events', { params: { path: { identifier: id } }, body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function privacyStatus() {
  const r = await api.GET('/api/privacy/status')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function unlock(passcode: string) {
  const r = await api.POST('/api/privacy/unlock', { body: { passcode } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function setPasscode(passcode: string, current_passcode?: string) {
  const r = await api.POST('/api/privacy/passcode', { body: { passcode, current_passcode } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function lock() {
  const r = await api.POST('/api/privacy/lock')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function exportData() {
  const r = await api.GET('/api/privacy/export')
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(new Blob([JSON.stringify(r.data, null, 2)], { type: 'application/json' }))
  const a = document.createElement('a'); a.href = url; a.download = 'stonks-export.json'; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export async function deleteData(confirmation: string) {
  const r = await api.POST('/api/privacy/delete-all', { body: { confirmation } })
  if (!r.response.ok) throw failure(r.error, r.response.status)
}

export async function getAnalyses() {
  const r = await api.GET('/api/jobs/analyses')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function exportArchive() {
  const r = await api.GET('/api/privacy/export/archive', { parseAs: 'blob' })
  if (!r.data) throw failure(r.error, r.response.status)
  const url = URL.createObjectURL(r.data)
  const a = document.createElement('a'); a.href = url; a.download = 'stonks-export.zip'; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
