import { Button } from './components/ui/Controls'
import { Component, useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'

export class RouteRecovery extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  render() {
    if (this.state.failed) return <section role="alert"><h1>This view could not be displayed.</h1><p>Retry the view. Unsaved changes in this view may need to be entered again.</p><Button onClick={() => this.setState({ failed: false })}>Retry view</Button><a href="/">Return to overview</a></section>
    return this.props.children
  }
}

export function RouteFocus() {
  const { pathname } = useLocation()
  const previous = useRef(pathname)
  useEffect(() => {
    const main = document.getElementById('main-content')
    document.title = `${main?.querySelector('h1')?.textContent ?? 'Workspace'} · Resume Tailor`
    if (previous.current !== pathname) main?.focus()
    previous.current = pathname
  }, [pathname])
  return null
}
