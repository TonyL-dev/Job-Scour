import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { saveCareer } from './api/workspace'
import type { CareerRecord, Item } from './api/workspace'
import { summaryError } from './experience'

export function ExperienceForm({ record, onSaved, onCancel }: {
  record?: CareerRecord
  onSaved: (record: CareerRecord, items?: Item[]) => void
  onCancel: () => void
}) {
  const original = record?.data.type === 'experience' ? record.data : undefined
  const [company, setCompany] = useState(original?.company ?? '')
  const [title, setTitle] = useState(original?.job_title ?? '')
  const [start, setStart] = useState(original?.start_date ?? '')
  const [end, setEnd] = useState(original?.end_date ?? '')
  const [current, setCurrent] = useState(original?.current ?? false)
  const [summary, setSummary] = useState('')
  const [duties, setDuties] = useState([''])
  const invalidSummary = summaryError(summary)
  const invalidDates = !!start && !current && !!end && end < start
  const complete = company.trim() && title.trim() && start && (current || end) && !invalidDates && (original || ((!invalidSummary) && (summary.trim() || duties.some(d => d.trim()))))
  const save = useMutation({ mutationFn: async () => {
    const texts = [summary.trim(), ...duties.map(d => d.trim())].filter(Boolean)
    const saved = await saveCareer({
      ...original, type: 'experience', company: company.trim(), job_title: title.trim(),
      employment_type: original?.employment_type ?? 'full_time', ordering_hint: original?.ordering_hint ?? 0,
      start_date: start, end_date: current ? null : end, current,
      description: original?.description ?? texts.join('\n'),
    }, record?.id)
    const items: Item[] = texts.map((text, index) => ({
      key: crypto.randomUUID(), text, origin: 'user', locked: false,
      experience_summary: !!summary.trim() && index === 0,
      source_refs: [{ entity_type: 'experience', entity_id: saved.id }],
    }))
    return { saved, items: original ? undefined : items }
  } })
  return <form className="item-editor" aria-label={original ? 'Edit experience details' : 'Add experience'} onSubmit={e => { e.preventDefault(); if (complete && !save.isPending) save.mutate(undefined, { onSuccess: ({ saved, items }) => onSaved(saved, items) }) }}>
    <h3>{original ? 'Edit experience details' : 'Add experience'}</h3>
    <p className="source-note">{original ? 'Company, title and dates update the shared career record. Other saved resume snapshots stay unchanged.' : 'This saves a career library record and adds sourced text to this draft. Save the resume to keep it here.'}</p>
    <fieldset disabled={save.isPending}>
      <div className="form-grid">
        <label>Company *<input required value={company} onChange={e => setCompany(e.target.value)} /></label>
        <label>Title *<input required value={title} onChange={e => setTitle(e.target.value)} /></label>
        <label>Start date *<input type="date" required value={start} onChange={e => setStart(e.target.value)} /></label>
        <label>End date<input type="date" required={!current} disabled={current} min={start || undefined} value={current ? '' : end} onChange={e => setEnd(e.target.value)} /></label>
      </div>
      <label className="check"><input type="checkbox" checked={current} onChange={e => setCurrent(e.target.checked)} />Present</label>
      {invalidDates && <p role="alert">End date must not precede start date.</p>}
      {!original && <>
        <label>Summary (one sentence max)<textarea maxLength={500} value={summary} aria-invalid={invalidSummary} onChange={e => setSummary(e.target.value)} /></label>
        {invalidSummary && <p role="alert">Use one sentence on one line, at most 500 characters. Avoid periods in abbreviations.</p>}
        <p>Duties (one bullet per field)</p>
        {duties.map((duty, index) => <div key={index}>
          <label>Duty {index + 1}<textarea maxLength={20000} value={duty} onChange={e => setDuties(duties.map((d, i) => i === index ? e.target.value : d))} /></label>
          <button type="button" className="secondary" onClick={() => setDuties(duties.filter((_, i) => i !== index))}>Remove duty {index + 1}</button>
        </div>)}
        <button type="button" className="secondary" onClick={() => setDuties([...duties, ''])}>Add duty</button>
      </>}
      <div className="actions"><button disabled={!complete}>{original ? 'Save experience details' : 'Add experience to draft'}</button><button type="button" className="secondary" onClick={onCancel}>Cancel</button></div>
    </fieldset>
    {save.error && <p role="alert">{save.error.message}</p>}
  </form>
}
