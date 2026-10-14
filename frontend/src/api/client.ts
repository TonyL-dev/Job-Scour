import createClient from 'openapi-fetch'
import type { paths } from './schema'

// Same-origin /api is proxied by Vite in development and Nginx in Compose.
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: async (request) => {
    let response: Response
    try { response = await globalThis.fetch(request) }
    catch (error) {
      if (request.signal.aborted) throw error
      throw new Error('Unable to reach your workspace. Check the backend is running and retry.')
    }
    if (response.status === 423) window.dispatchEvent(new Event('workspace-locked'))
    return response
  },
})

export async function getHealth(signal?: AbortSignal) {
  const { data, error, response } = await api.GET('/api/health', { signal })
  if (error || !data) {
    throw new Error(
      error?.database === 'unavailable'
        ? 'The database is not ready. Start the backend and apply its migrations.'
        : `Unable to reach the backend (${response.status}).`,
    )
  }
  return data
}
