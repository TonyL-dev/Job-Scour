import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { RouteRecovery } from './RouteRecovery'
import { QueryNotice } from './QueryNotice'

it('offers query recovery and announces loading', async () => {
  const refetch = vi.fn()
  const { rerender } = render(<QueryNotice query={{ isPending: true, error: null, refetch }} label="Applications" />)
  expect(screen.getByRole('status')).toHaveTextContent('Loading applications')
  rerender(<QueryNotice query={{ isPending: false, error: new Error('Offline'), refetch }} label="Applications" />)
  expect(screen.getByRole('alert')).toHaveTextContent('Offline')
  await userEvent.click(screen.getByRole('button', { name: 'Retry applications' }))
  expect(refetch).toHaveBeenCalledOnce()
})

it('contains a failed view and retries without displaying private exception content', async () => {
  let failed = true
  function View() { if (failed) throw new Error('private career text'); return <h1>Recovered</h1> }
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
  try {
    render(<RouteRecovery><View /></RouteRecovery>)
    expect(screen.getByRole('alert')).not.toHaveTextContent('private career text')
    failed = false
    await userEvent.click(screen.getByRole('button', { name: 'Retry view' }))
    expect(screen.getByRole('heading', { name: 'Recovered' })).toBeInTheDocument()
  } finally { consoleError.mockRestore() }
})
