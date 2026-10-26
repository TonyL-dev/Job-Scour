import { Button } from './components/ui/Controls'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { privacyStatus, unlock, lock } from './api/phase4'

export function WorkspaceGate({ children }: { children: ReactNode }) {
  const client = useQueryClient()
  const status = useQuery({ queryKey: ['privacy-status'], queryFn: privacyStatus, refetchInterval: 15000, retry: false })
  const [blocked, setBlocked] = useState(false)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const { refetch } = status
  useEffect(() => {
    // Evict private data after cancelling queries so an observed lock cannot leave
    // cached screens available on unlock. Preserve the query that drives this gate.
    if (status.data?.locked) void client.cancelQueries().then(() => {
      client.removeQueries({ predicate: q => q.queryKey[0] !== 'privacy-status' })
    })
  }, [client, status.data?.locked])
  useEffect(() => {
    const listener = () => { setBlocked(true); void client.cancelQueries().then(async () => {
      client.clear()
      const fresh = await refetch()
      if (fresh.data) setBlocked(fresh.data.locked)
    }) }
    window.addEventListener('workspace-locked', listener)
    return () => window.removeEventListener('workspace-locked', listener)
  }, [client, refetch])
  useEffect(() => {
    if (!status.data?.passcode_enabled || status.data.locked || blocked) return
    let timer: ReturnType<typeof setTimeout>
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => { void lock().finally(() => window.dispatchEvent(new Event('workspace-locked'))) }, 15 * 60 * 1000)
    }
    reset()
    window.addEventListener('pointerdown', reset)
    window.addEventListener('keydown', reset)
    return () => { clearTimeout(timer); window.removeEventListener('pointerdown', reset); window.removeEventListener('keydown', reset) }
  }, [status.data?.passcode_enabled, status.data?.locked, blocked])
  if (status.isPending) return <main><p role="status">Checking workspace lock…</p></main>
  if (status.error) return <main><h1>Workspace unavailable</h1><p role="alert">{status.error.message}</p><Button onClick={() => void status.refetch()}>Retry connection</Button></main>
  if (!blocked && !status.data?.locked) return children
  return <main className="panel editor-form"><h1>Workspace locked</h1><p>Unlock to view your career records and resumes.</p><form onSubmit={e => { e.preventDefault(); setBusy(true); setError(''); void unlock(code).then(async () => { setCode(''); await status.refetch(); setBlocked(false); client.removeQueries({ predicate: q => q.queryKey[0] !== 'privacy-status' }) }).catch(e => setError(e instanceof Error ? e.message : 'Unlock failed')).finally(() => setBusy(false)) }}><label>Passcode<input autoFocus type="password" autoComplete="current-password" value={code} onChange={e => setCode(e.target.value)} /></label><Button variant="primary" disabled={busy || !code}>Unlock workspace</Button></form>{error && <p role="alert">{error}</p>}</main>
}
