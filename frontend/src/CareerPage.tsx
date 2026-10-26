import { PageHeader, ActionGroup, Button } from './components/ui/Controls'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import { careerTypes, getForms, getHistory, labels, recordLabel, retireCareer, saveCareer } from './api/workspace'
import type { CareerInput, CareerRecord, CareerType } from './api/workspace'

export function CareerPage() {
  const { kind = 'experience' } = useParams()
  if (!careerTypes.includes(kind as CareerType)) return <h1>Unknown career category</h1>
  return <CareerEditor key={kind} kind={kind as CareerType} />
}

function CareerEditor({ kind }: { kind: CareerType }) {
  const client = useQueryClient()
  const history = useQuery({ queryKey: ['history'], queryFn: getHistory })
  const forms = useQuery({ queryKey: ['career-forms'], queryFn: getForms })
  const [editing, setEditing] = useState<CareerRecord>()
  const [values, setValues] = useState<Record<string, string | boolean>>({})
  const [open, setOpen] = useState(false)
  const [message, setMessage] = useState('')
  const fields = forms.data?.find(form => form.type === kind)?.fields ?? []
  const mutation = useMutation({
    mutationFn: (data: CareerInput) => saveCareer(data, editing?.id),
    onSuccess: () => { void client.invalidateQueries({ queryKey: ['history'] }); setOpen(false); setMessage('Career record saved.') },
  })
  const removal = useMutation({ mutationFn: retireCareer, onSuccess: () => { void client.invalidateQueries({ queryKey: ['history'] }); setMessage('Record retired. Saved resume snapshots are preserved.') } })
  function start(record?: CareerRecord) {
    setEditing(record)
    const initial: Record<string, string | boolean> = {}
    for (const field of fields) {
      const value = record ? (record.data as unknown as Record<string, unknown>)[field.name] : field.default_value
      initial[field.name] = typeof value === 'boolean' ? value : Array.isArray(value) ? value.join(', ') : value && typeof value === 'object' ? Object.entries(value).map(([k, v]) => `${k}: ${String(v)}`).join('\n') : String(value ?? '')
    }
    setValues(initial); setOpen(true); mutation.reset(); setMessage('')
  }
  function submit(event: React.FormEvent) {
    event.preventDefault()
    const data: Record<string, unknown> = { type: kind }
    for (const field of fields) {
      const value = values[field.name]
      if (field.input_type === 'checkbox') data[field.name] = !!value
      else if (field.input_type === 'list') data[field.name] = String(value ?? '').split(',').map(s => s.trim()).filter(Boolean)
      else if (field.input_type === 'details') data[field.name] = Object.fromEntries(String(value ?? '').split('\n').filter(Boolean).map(line => { const split = line.indexOf(':'); return split < 0 ? ['Description', line] : [line.slice(0, split).trim(), line.slice(split + 1).trim()] }))
      else if (value !== '' && value !== undefined) data[field.name] = field.input_type === 'number' ? Number(value) : value
    }
    mutation.mutate(data as CareerInput)
  }
  return <>
    <PageHeader title="Start with the facts." eyebrow="YOUR CAREER LIBRARY" />
    <p className="intro">Keep your full history here. Achievements connect to an experience or project; skill evidence records where you used a skill.</p>
    <nav className="category-tabs" aria-label="Career categories">{careerTypes.map(type => <NavLink key={type} to={`/career/${type}`}>{labels[type]}</NavLink>)}</nav>
    {(history.isPending || forms.isPending) && <p role="status">Loading career library…</p>}
    {(history.error || forms.error) && <div role="alert"><p>{history.error?.message ?? forms.error?.message}</p><Button onClick={() => { void history.refetch(); void forms.refetch() }}>Retry</Button></div>}
    <div className="toolbar"><h2>{labels[kind]}</h2><Button variant="primary" disabled={!forms.data || !history.data} onClick={() => start()}>Add record</Button></div>
    {message && <p role="status">{message}</p>}
    {removal.error && <p role="alert">{removal.error.message}</p>}
    {!open && history.data?.filter(r => r.data.type === kind).length === 0 && <div className="empty-state">No {labels[kind].toLowerCase()} yet. Add your first record to start building your library.</div>}
    {!open && <div className="record-list">{history.data?.filter(r => r.data.type === kind).map(record => <article className="panel record-card" key={record.id}>
      <h3>{record.data.type === 'skill_evidence' ? `${recordLabel(history.data.find(r => r.id === ('skill_id' in record.data ? record.data.skill_id : '')) ?? record)} · evidence linked` : recordLabel(record)}</h3>
      <dl>{Object.entries(record.data).filter(([key, value]) => key !== 'type' && value !== null && value !== '' && !(Array.isArray(value) && !value.length)).map(([key, value]) => <div key={key}><dt>{key.replace('_id', '').replaceAll('_', ' ')}</dt><dd>{key.endsWith('_id') ? recordLabel(history.data.find(r => r.id === value) ?? record) : typeof value === 'boolean' ? value ? 'Yes' : 'No' : Array.isArray(value) ? value.join(', ') : typeof value === 'object' ? Object.values(value).join(' · ') : String(value)}</dd></div>)}</dl>
      <ActionGroup><Button variant="ghost" onClick={() => start(record)}>Edit</Button><Button variant="danger" disabled={removal.isPending} onClick={() => removal.mutate(record)}>Retire</Button></ActionGroup>
    </article>)}</div>}
    {open && <form className="panel editor-form" onSubmit={submit}><h2>{editing ? 'Edit record' : 'New record'}</h2><div className="form-grid">{fields.map(field => <label key={field.name} className={['multiline', 'details'].includes(field.input_type) ? 'wide' : ''}>{field.label}{field.required ? ' *' : ''}
      {field.input_type === 'select' ? <select aria-label={field.label + (field.required ? " *" : "")} required={field.required} value={String(values[field.name] ?? '')} onChange={e => setValues({ ...values, [field.name]: e.target.value })}><option value="">Choose…</option>{field.related_type ? history.data?.filter(r => r.data.type === field.related_type).map(r => <option key={r.id} value={r.id}>{recordLabel(r)}</option>) : field.options?.map(option => <option key={option} value={option}>{option.replaceAll('_', ' ')}</option>)}</select>
        : ['multiline', 'details'].includes(field.input_type) ? <textarea required={field.required} value={String(values[field.name] ?? '')} placeholder={field.input_type === 'details' ? 'Title: Speaking engagement\nDescription: Presented at a community event' : undefined} onChange={e => setValues({ ...values, [field.name]: e.target.value })} />
          : field.input_type === 'checkbox' ? <input type="checkbox" checked={!!values[field.name]} onChange={e => setValues({ ...values, [field.name]: e.target.checked })} />
            : <input type={field.input_type === 'list' ? 'text' : field.input_type} step="any" required={field.required} value={String(values[field.name] ?? '')} placeholder={field.input_type === 'list' ? 'Separate entries with commas' : undefined} onChange={e => setValues({ ...values, [field.name]: e.target.value })} />}
    </label>)}</div>
      {mutation.error && <p role="alert">{mutation.error.message}</p>}<ActionGroup><Button variant="primary" disabled={mutation.isPending}>{mutation.isPending ? 'Saving…' : 'Save record'}</Button><Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancel</Button></ActionGroup>
    </form>}
  </>
}
