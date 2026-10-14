import { api } from './client'
import { failure } from './workspace'
import type { components } from './schema'

export type Run = components['schemas']['GenerationRun']
export type GenerateInput = components['schemas']['GenerateInput']
export type Decision = components['schemas']['Decision']
export type Review = components['schemas']['ReviewInput']

export async function getRuns() {
  const r = await api.GET('/api/generation')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function getRun(identifier: string) {
  const r = await api.GET('/api/generation/{identifier}', { params: { path: { identifier } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function startRun(body: GenerateInput) {
  const r = await api.POST('/api/generation', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function cancelRun(identifier: string) {
  const r = await api.POST('/api/generation/{identifier}/cancel', { params: { path: { identifier } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function saveReview(identifier: string, body: Review) {
  const r = await api.PUT('/api/generation/{identifier}/review', { params: { path: { identifier } }, body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function reviewPreview(identifier: string, body: Review, signal: AbortSignal) {
  const r = await api.POST('/api/generation/{identifier}/preview', { params: { path: { identifier } }, body, signal })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
export async function commitReview(identifier: string, body: Review & { title: string }) {
  const r = await api.POST('/api/generation/{identifier}/commit', { params: { path: { identifier } }, body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
