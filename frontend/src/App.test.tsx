import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}><MemoryRouter><App /></MemoryRouter></QueryClientProvider>)
}

describe('workspace connection', () => {
  it('calls the API and shows connection details', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      status: 'ok', service: 'Resume Tailor', version: '0.1.0', mode: 'local', database: 'ready',
    }), { headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', (r: Request) => new URL(r.url).pathname === '/api/privacy/status' ? Promise.resolve(new Response(JSON.stringify({ passcode_enabled: false, locked: false, encryption_enabled: false }), { headers: { 'Content-Type': 'application/json' } })) : fetchMock(r))
    renderApp()
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
    expect(screen.getByText('ready')).toBeInTheDocument()
    expect(fetchMock.mock.calls.filter(([r]) => new URL((r as Request).url).pathname === '/api/health')).toHaveLength(1)
    const request = fetchMock.mock.calls.find(([r]) => new URL((r as Request).url).pathname === '/api/health')?.[0] as Request
    expect(new URL(request.url).pathname).toBe('/api/health')
  })

  it('shows readiness failures and allows retry', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({
      status: 'degraded', database: 'unavailable',
    }), { status: 503, headers: { 'Content-Type': 'application/json' } })))
    vi.stubGlobal('fetch', (r: Request) => new URL(r.url).pathname === '/api/privacy/status' ? Promise.resolve(new Response(JSON.stringify({ passcode_enabled: false, locked: false, encryption_enabled: false }), { headers: { 'Content-Type': 'application/json' } })) : fetchMock(r))
    renderApp()
    expect(await screen.findByRole('alert')).toHaveTextContent('database is not ready')
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(fetchMock.mock.calls.filter(([r]) => new URL((r as Request).url).pathname === '/api/health')).toHaveLength(2))
  })

  it('navigates to privacy details', async () => {
    vi.stubGlobal('fetch', (r: Request) => new URL(r.url).pathname === '/api/privacy/status' ? Promise.resolve(new Response(JSON.stringify({ passcode_enabled: false, locked: false, encryption_enabled: false }), { headers: { 'Content-Type': 'application/json' } })) : Promise.reject(new Error('offline')))
    renderApp()
    await userEvent.click(await screen.findByRole('link', { name: 'Privacy' }))
    expect(screen.getByRole('heading', { name: 'Privacy controls.' })).toBeInTheDocument()
  })
})
