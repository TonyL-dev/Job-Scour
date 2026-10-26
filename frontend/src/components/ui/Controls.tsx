import { useId, useRef, useState, type ButtonHTMLAttributes, type HTMLAttributes, type ReactNode } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' | 'danger' }

export function Button({ variant = 'secondary', className = '', ...props }: ButtonProps) {
  return <button className={`button button-${variant} ${className}`} {...props} />
}

export function ActionGroup({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`actions ${className}`} {...props} />
}

export function PageHeader({ title, description, eyebrow, children }: { title: string; description?: string; eyebrow?: string; children?: ReactNode }) {
  return <header className="page-header"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1>{description && <p className="intro">{description}</p>}</div>{children}</header>
}

export function StatusNotice({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <p className={`status-notice ${error ? 'status-error' : ''}`} role={error ? 'alert' : 'status'}>{children}</p>
}

/** Native disclosure: ordinary tab navigation, not an ARIA menu with incomplete arrow handling. */
export function Disclosure({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDetailsElement>(null)
  return <details ref={ref} className={`disclosure ${className}`} onKeyDown={event => {
    if (event.key === 'Escape' && ref.current?.open) {
      event.stopPropagation(); ref.current.open = false; ref.current.querySelector('summary')?.focus()
    }
  }}><summary>{title}</summary><div className="disclosure-content">{children}</div></details>
}

/** Panel children stay mounted to preserve drafts and asynchronous preview state. */
export function Tabs({ label, tabs }: { label: string; tabs: { label: string; content: ReactNode }[] }) {
  const id = useId()
  const container = useRef<HTMLDivElement>(null)
  const [selected, setSelected] = useState(0)
  function activate(index: number, focus: boolean) {
    setSelected(index)
    if (focus) container.current?.querySelectorAll<HTMLButtonElement>(':scope > [role=tablist] > button')[index]?.focus()
  }
  return <div ref={container} className="tabs"><div role="tablist" aria-label={label}>{tabs.map((tab, index) => <button type="button" role="tab" key={tab.label} id={`${id}-tab-${index}`} aria-controls={`${id}-panel-${index}`} aria-selected={selected === index} tabIndex={selected === index ? 0 : -1} onClick={() => activate(index, false)} onKeyDown={event => {
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index - 1 + tabs.length) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : undefined
    if (next !== undefined) { event.preventDefault(); activate(next, true) }
  }}>{tab.label}</button>)}</div>{tabs.map((tab, index) => <div role="tabpanel" key={tab.label} id={`${id}-panel-${index}`} aria-labelledby={`${id}-tab-${index}`} hidden={selected !== index}>{tab.content}</div>)}</div>
}
