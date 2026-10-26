import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { Disclosure, Tabs } from './Controls'

it('supports keyboard tabs without remounting a draft', async () => {
  const user = userEvent.setup()
  function Draft() { const [text, setText] = useState(''); return <label>Draft<input value={text} onChange={event => setText(event.target.value)} /></label> }
  render(<Tabs label="Editor" tabs={[{ label: 'Content', content: <Draft /> }, { label: 'Appearance', content: <p>Style controls</p> }]} />)
  await user.type(screen.getByLabelText('Draft'), 'Keep this work')
  screen.getByRole('tab', { name: 'Content' }).focus()
  await user.keyboard('{ArrowRight}')
  expect(screen.getByRole('tab', { name: 'Appearance' })).toHaveFocus()
  expect(screen.getByRole('tab', { name: 'Appearance' })).toHaveAttribute('aria-selected', 'true')
  expect(screen.getByLabelText('Draft')).not.toBeVisible()
  await user.keyboard('{Home}')
  expect(screen.getByLabelText('Draft')).toBeVisible()
  expect(screen.getByLabelText('Draft')).toHaveValue('Keep this work')
})

it('closes a disclosure on Escape and restores trigger focus', async () => {
  const user = userEvent.setup()
  render(<Disclosure title="More actions"><button>Duplicate</button></Disclosure>)
  await user.click(screen.getByText('More actions'))
  await user.click(screen.getByRole('button', { name: 'Duplicate' }))
  await user.keyboard('{Escape}')
  expect(screen.getByText('More actions')).toHaveFocus()
  expect(screen.getByText('More actions').closest('details')).not.toHaveAttribute('open')
})
