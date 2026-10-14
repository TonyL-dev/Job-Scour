import { api } from './client'
import { failure } from './workspace'
import type { components } from './schema'

export type EndpointInput = components['schemas']['EndpointInput']
export type Endpoint = components['schemas']['Endpoint']
export type ProfileInput = components['schemas']['ProfileInput']
export type AnalysisResult = components['schemas']['AnalysisResult']
export type Job = components['schemas']['Job']
export type JobInput = components['schemas']['JobInput']
export type Detection = components['schemas']['Detection']

export async function getSettings() {
  const r = await api.GET('/api/settings')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function detectEndpoints() {
  const r = await api.POST('/api/settings/detect')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function saveEndpoint(body: EndpointInput, id?: string) {
  const r = id ? await api.PUT('/api/settings/endpoints/{identifier}', { params: { path: { identifier: id } }, body }) : await api.POST('/api/settings/endpoints', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function listModels(id: string) {
  const r = await api.POST('/api/settings/endpoints/{identifier}/models', { params: { path: { identifier: id } } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data.models
}

export async function saveProfile(body: ProfileInput) {
  const r = await api.POST('/api/settings/profiles', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function assignModel(task: components['schemas']['Assignment']['task'], profile_id: string) {
  const r = await api.PUT('/api/settings/assignments', { body: { task, profile_id } })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function testProfile(id: string) {
  const r = await api.POST('/api/settings/profiles/{identifier}/test', { params: { path: { identifier: id } } })
  if (!r.data) throw failure(r.error, r.response.status)
  if (!r.data.ok) throw new Error('Model returned an unsuccessful connectivity test.')
  return r.data
}

export async function getJobs() {
  const r = await api.GET('/api/jobs')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function saveJob(body: JobInput) {
  const r = await api.POST('/api/jobs', { body })
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function getPrompts() {
  const r = await api.GET('/api/jobs/prompts')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}

export async function readAnalysisStream(stream: ReadableStream<Uint8Array>, stage: (text: string) => void): Promise<AnalysisResult> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done }).replace(/\r/g, '')
      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const event = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const type = event.split('\n').find(line => line.startsWith('event:'))?.slice(6).trim()
        const data = event.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n')
        if (!data) continue
        const payload: unknown = JSON.parse(data)
        if (type === 'result') return payload as AnalysisResult
        if (type === 'error') throw failure(payload, 502)
        if (type === 'progress' && typeof (payload as { stage?: unknown }).stage === 'string') stage((payload as { stage: string }).stage)
      }
      if (done) throw new Error('Analysis connection ended before a result arrived. Retry the saved job.')
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

export async function analyzeJob(id: string, use_embeddings: boolean, signal: AbortSignal, stage: (text: string) => void) {
  const r = await api.POST('/api/jobs/{identifier}/analyze/stream', { params: { path: { identifier: id } }, body: { use_embeddings }, signal, parseAs: 'stream' })
  if (!r.response.ok || !r.data) throw new Error(`Cannot start analysis (${r.response.status}). Check AI settings and retry.`)
  return readAnalysisStream(r.data, stage)
}
