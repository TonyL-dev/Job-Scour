import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import { App } from './App'
import { WorkspaceGate } from './WorkspaceGate'
function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry:false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><App /></MemoryRouter></QueryClientProvider>)
}
const json = (value: unknown, status=200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type':'application/json' } })
describe('workspace privacy boundary', () => {
  it('clears private cached data when a status poll detects a lock', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    let locked = false
    vi.stubGlobal('fetch', vi.fn(async () => json({ locked, passcode_enabled: true, encryption_enabled: false })))
    render(<QueryClientProvider client={client}><WorkspaceGate><p>Private view</p></WorkspaceGate></QueryClientProvider>)
    expect(await screen.findByText('Private view')).toBeInTheDocument()
    client.setQueryData(['resumes'], [{ text: 'Private cached text' }])
    locked = true
    await act(async () => { await client.invalidateQueries({ queryKey: ['privacy-status'] }) })
    expect(await screen.findByRole('heading', { name: 'Workspace locked' })).toBeInTheDocument()
    expect(screen.queryByText('Private view')).not.toBeInTheDocument()
    await waitFor(() => expect(client.getQueryData(['resumes'])).toBeUndefined())
  })
  it('hides workspace content until a locked session is unlocked', async () => {
    let locked = true
    const fetch = vi.fn(async (r: Request) => {
      const path = new URL(r.url).pathname
      if (path === '/api/privacy/status') return json({ locked, passcode_enabled:true, encryption_enabled:false })
      if (path === '/api/privacy/unlock') { locked=false; return json({ locked:false, passcode_enabled:true, encryption_enabled:false }) }
      return json({ status:'ok', mode:'local', database:'ready', service:'Resume Tailor', version:'0.1.0' })
    })
    vi.stubGlobal('fetch', fetch)
    renderApp()
    expect(await screen.findByRole('heading', { name:'Workspace locked' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name:'Career library' })).not.toBeInTheDocument()
    expect(fetch.mock.calls.every(([r]) => new URL(r.url).pathname === '/api/privacy/status')).toBe(true)
    await userEvent.type(screen.getByLabelText('Passcode'), 'synthetic passcode')
    await userEvent.click(screen.getByRole('button', { name:'Unlock workspace' }))
    expect(await screen.findByText('Backend connected')).toBeInTheDocument()
  })
  it('fails closed when lock status cannot be checked', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    renderApp()
    expect(await screen.findByRole('heading', { name:'Workspace unavailable' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name:'Career library' })).not.toBeInTheDocument()
  })
})
