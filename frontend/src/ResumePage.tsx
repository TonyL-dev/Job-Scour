import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { downloadPdf, getHistory, getPreview, getResumes, getTemplates, recordLabel, saveResume } from './api/workspace'
import type { CareerRecord, Document, Item, MasterResume, Section } from './api/workspace'
import { PdfPreview } from './PdfPreview'
import { ExperienceForm } from './ExperienceForm'
import { summaryError } from './experience'

const sectionTypes: Section['type'][] = ['summary', 'experience', 'projects', 'skills', 'education', 'certifications', 'volunteer', 'awards', 'publications', 'custom']
const sources: Record<Section['type'], string[]> = { summary: [], experience: ['experience', 'achievement'], projects: ['project', 'achievement'], skills: ['skill'], education: ['education', 'course'], certifications: ['certification'], volunteer: ['volunteer_experience'], awards: ['award'], publications: ['publication'], custom: ['custom_entry'] }

function blank(): Document {
  return { schema_version: 1, header: { name: '', email: '', phone: '', location: '', links: [] }, sections: [], metadata: { template_id: '00000000-0000-4000-8000-000000000101', target_page_limit: 2, style_overrides: {} } }
}

function sourceText(record: CareerRecord): string {
  const data = record.data
  if (data.type === 'certification') return [data.name, data.issuer, data.issue_date, data.credential_id, data.url].filter(Boolean).join(' · ')
  if (data.type === 'publication') return [data.title, data.venue, data.date, data.co_authors?.join(', '), data.url].filter(Boolean).join(' · ')
  if (data.type === 'award') return [data.title, data.issuer, data.date, data.description].filter(Boolean).join(' · ')
  if (data.type === 'project') return [data.description, data.challenges_solved, data.results, data.url].filter(Boolean).join('\n') || data.name
  if ('text' in data) return data.text
  if ('description' in data) return data.description || recordLabel(record)
  if ('name' in data) return data.name
  if ('payload' in data) return Object.values(data.payload ?? {}).join('\n') || 'Custom entry'
  return recordLabel(record)
}

function move<T>(items: T[], index: number, offset: number): T[] {
  const result = [...items]
  const next = index + offset
  if (next < 0 || next >= items.length) return result
  ;[result[index], result[next]] = [result[next]!, result[index]!]
  return result
}

export function ResumePage() {
  const client = useQueryClient()
  const [search] = useSearchParams()
  const requested = search.get('resume')
  const opened = useRef(false)
  const templates = useQuery({ queryKey: ['templates'], queryFn: getTemplates })
  const resumes = useQuery({ queryKey: ['resumes'], queryFn: getResumes })
  const history = useQuery({ queryKey: ['history'], queryFn: getHistory })
  const [saved, setSaved] = useState<MasterResume>()
  const [title, setTitle] = useState('My master resume')
  const [gold, setGold] = useState(false)
  const [content, setContent] = useState<Document>(blank)
  const [debounced, setDebounced] = useState<Document>()
  const [newType, setNewType] = useState<Section['type']>('summary')
  const [notice, setNotice] = useState('')
  const [sourceRevision, setSourceRevision] = useState(0)
  const [savedSourceRevision, setSavedSourceRevision] = useState(0)
  const [experienceForm, setExperienceForm] = useState<{ sectionKey: string; record?: CareerRecord }>()
  useEffect(() => {
    if (opened.current || !requested || !resumes.data) return
    opened.current = true
    const target = resumes.data.find(r => r.id === requested)
    if (!target) return
    const frame = requestAnimationFrame(() => {
      setSaved(target); setContent(target.content); setTitle(target.title); setGold(target.gold_standard)
      requestAnimationFrame(() => document.getElementById(window.location.hash.slice(1))?.scrollIntoView())
    })
    return () => cancelAnimationFrame(frame)
  }, [requested, resumes.data])
  const [autosave, setAutosave] = useState(true)
  const [view, setView] = useState<'pdf' | 'html'>('pdf')
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(content), 600)
    return () => clearTimeout(timer)
  }, [content])
  const valid = !!content.header.name.trim() && content.sections.every(s => s.title.trim() && s.items.every(i => i.text.trim() && (!i.experience_summary || !summaryError(i.text))))
  const preview = useQuery({ queryKey: ['preview', saved?.id, debounced], queryFn: ({ signal }) => getPreview(debounced!, signal, saved?.id), enabled: !!debounced?.header.name.trim() && debounced.sections.every(s => s.title.trim() && s.items.every(i => i.text.trim() && (!i.experience_summary || !summaryError(i.text)))), retry: false, gcTime: 0 })
  const save = useMutation({ mutationFn: async (download: boolean | 'auto') => {
    const submitted = content
    const submittedSourceRevision = sourceRevision
    const result = await saveResume(title, submitted, gold, saved, download === 'auto')
    setSavedSourceRevision(submittedSourceRevision)
    setSaved(result); setContent(previous => JSON.stringify(previous) === JSON.stringify(submitted) ? result.content : previous)
    void client.invalidateQueries({ queryKey: ['resumes'] })
    setNotice('Resume saved.')
    if (download === true) { await downloadPdf(result.id); setNotice('Resume saved and PDF downloaded.') }
    return result
  } })
  const dirty = sourceRevision !== savedSourceRevision || !saved || saved.title !== title || saved.gold_standard !== gold || JSON.stringify(saved.content) !== JSON.stringify(content)
  const { mutate, isPending, error: saveError } = save
  useEffect(() => {
    if (!autosave || !saved || !dirty || !valid || !title.trim() || isPending || saveError) return
    const timer = setTimeout(() => mutate('auto'), 1800)
    return () => clearTimeout(timer)
  }, [autosave, saved, dirty, valid, title, content, gold, isPending, saveError, mutate])
  function openResume(resume?: MasterResume) {
    if (dirty && (content.header.name || content.sections.length) && !window.confirm('Discard unsaved changes and open another resume?')) return
    setSaved(resume); setGold(resume?.gold_standard ?? false); setTitle(resume?.title ?? 'My master resume'); setContent(resume?.content ?? blank()); setNotice(''); setExperienceForm(undefined); setSourceRevision(0); setSavedSourceRevision(0); save.reset()
  }
  function updateSection(index: number, update: Partial<Section>) {
    setContent({ ...content, sections: content.sections.map((s, i) => i === index ? { ...s, ...update } : s) })
  }
  function updateItem(index: number, itemIndex: number, update: Partial<Item>) {
    const section = content.sections[index]!
    updateSection(index, { items: section.items.map((item, i) => i === itemIndex ? { ...item, ...update, origin: update.text !== undefined ? 'user' : item.origin } : item) })
  }
  function addItem(index: number, record?: CareerRecord) {
    const section = content.sections[index]!
    if (record?.data.type === 'skill_evidence') return
    updateSection(index, { items: [...section.items, { key: crypto.randomUUID(), text: record ? sourceText(record) : '', origin: 'user', source_refs: record ? [{ entity_type: record.data.type, entity_id: record.id }] : [], locked: false, experience_summary: false }] })
  }
  function options(section: Section) {
    return history.data?.filter(record => record.data.type !== 'skill_evidence' && (section.type === 'summary' || sources[section.type].includes(record.data.type)) && (record.data.type !== 'achievement' || (section.type === 'experience' ? !!record.data.experience_id : section.type === 'projects' ? !!record.data.project_id : true))) ?? []
  }
  function experienceSaved(record: CareerRecord, sectionKey: string, items?: Item[]) {
    if (record.data.type !== 'experience') return
    const data = record.data
    setSourceRevision(revision => revision + 1)
    const facts = { employer: data.company, title: data.job_title, start_date: data.start_date, end_date: data.end_date, current: data.current, location: data.location }
    setContent(previous => ({ ...previous, sections: previous.sections.map(section => ({
      ...section,
      items: [...section.items.map(item => item.origin === 'user' && item.source_refs.some(ref => ref.entity_id === record.id || history.data?.some(r => r.id === ref.entity_id && r.data.type === 'achievement' && r.data.experience_id === record.id)) && section.type === 'experience' ? { ...item, facts } : item), ...(section.key === sectionKey ? items?.map(item => ({ ...item, facts })) ?? [] : [])],
    })) }))
    void client.invalidateQueries({ queryKey: ['history'] })
    void client.invalidateQueries({ queryKey: ['career'] })
    setExperienceForm(undefined)
    setNotice(items ? 'Experience saved to the career library and added to this draft.' : 'Career details updated. Save the resume to capture the updated facts.')
  }
  return <>
    <p className="eyebrow">RESUME STUDIO</p><h1>Shape your story.</h1><p className="intro">Edit your master or tailored resume by hand. Text edits are recorded as user content. Pick from your library, arrange sections, and preview the actual PDF as you edit.</p>
    {(templates.error || resumes.error || history.error) && <div role="alert"><p>{templates.error?.message ?? resumes.error?.message ?? history.error?.message}</p><button onClick={() => { void templates.refetch(); void resumes.refetch(); void history.refetch() }}>Retry</button></div>}
    <div className="toolbar"><label>Saved resumes<select aria-label="Saved resumes" value={saved?.id ?? ''} onChange={e => openResume(resumes.data?.find(r => r.id === e.target.value))}><option value="">New master resume</option>{resumes.data?.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}</select></label><button className="secondary" onClick={() => openResume()}>New resume</button></div>
    <label className="check"><input type="checkbox" checked={autosave} onChange={e => setAutosave(e.target.checked)} />Autosave edits after first save</label>{saved && <Link to={`/history?resume=${saved.id}`}>History & ATS guidance →</Link>}
    <div className="studio">
      <div className="resume-controls">
        <section className="editor-form"><h2>Resume details</h2><label>Resume title<input value={title} required onChange={e => setTitle(e.target.value)} /></label>
          <label className="check"><input type="checkbox" disabled={saved?.kind === 'tailored'} checked={gold} onChange={e => setGold(e.target.checked)} />Use as my gold standard master</label>
          <div className="form-grid">{(['name', 'email', 'phone', 'location'] as const).map(field => <label key={field}>{field === 'name' ? 'Full name *' : field.charAt(0).toUpperCase() + field.slice(1)}<input value={content.header[field] ?? ''} onChange={e => setContent({ ...content, header: { ...content.header, [field]: e.target.value } })} /></label>)}</div>
          <label>Contact links (label | URL, one per line)<textarea value={content.header.links?.map(l => `${l.label} | ${l.url}`).join('\n') ?? ''} onChange={e => setContent({ ...content, header: { ...content.header, links: e.target.value.split('\n').filter(Boolean).map(line => { const [label, ...url] = line.split('|'); return { label: label?.trim() ?? '', url: url.join('|').trim() } }) } })} /></label>
        </section>
        <section className="editor-form"><h2>Template & style</h2><div className="form-grid">
          <label>Template<select aria-label="Template" value={content.metadata.template_id} onChange={e => setContent({ ...content, metadata: { ...content.metadata, template_id: e.target.value } })}>{templates.data?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
          <label>Page target<input type="number" min="1" max="10" value={content.metadata.target_page_limit ?? 2} onChange={e => setContent({ ...content, metadata: { ...content.metadata, target_page_limit: Number(e.target.value) } })} /></label>
          <label>Font<select aria-label="Font" value={content.metadata.style_overrides?.font_family ?? ''} onChange={e => setContent({ ...content, metadata: { ...content.metadata, style_overrides: { ...content.metadata.style_overrides, font_family: (e.target.value || null) as 'sans' | 'serif' | null } } })}><option value="">Template default</option><option value="sans">Sans serif</option><option value="serif">Serif</option></select></label>
          {([{ key: 'font_size_pt', label: 'Font size (pt)', min: 9, max: 14, step: .5 }, { key: 'line_height', label: 'Line height', min: 1, max: 2, step: .05 }, { key: 'margin_mm', label: 'Margins (mm)', min: 10, max: 30, step: 1 }, { key: 'section_spacing_mm', label: 'Section spacing (mm)', min: 0, max: 15, step: 1 }] as const).map(field => <label key={field.key}>{field.label}<input type="number" min={field.min} max={field.max} step={field.step} placeholder="Default" value={content.metadata.style_overrides?.[field.key] ?? ''} onChange={e => setContent({ ...content, metadata: { ...content.metadata, style_overrides: { ...content.metadata.style_overrides, [field.key]: e.target.value === '' ? null : Number(e.target.value) } } })} /></label>)}
          <label>Accent color<input type="color" value={content.metadata.style_overrides?.accent_color ?? '#24362e'} onChange={e => setContent({ ...content, metadata: { ...content.metadata, style_overrides: { ...content.metadata.style_overrides, accent_color: e.target.value } } })} /></label>
        </div></section>
        {content.sections.map((section, index) => <section id={`section-${section.key}`} key={section.key} className="editor-form section-editor">
          <div className="toolbar"><h2>{section.type}</h2><div className="actions"><button className="secondary" disabled={index === 0} aria-label={`Move ${section.title} up`} onClick={() => setContent({ ...content, sections: move(content.sections, index, -1) })}>↑</button><button className="secondary" disabled={index === content.sections.length - 1} aria-label={`Move ${section.title} down`} onClick={() => setContent({ ...content, sections: move(content.sections, index, 1) })}>↓</button><button className="secondary" aria-label={`Remove ${section.title} section`} onClick={() => setContent({ ...content, sections: content.sections.filter((_, i) => i !== index) })}>Remove</button></div></div>
          <label>Section title<input value={section.title} onChange={e => updateSection(index, { title: e.target.value })} /></label>
          <div className="actions"><label className="check"><input type="checkbox" checked={section.visible ?? true} onChange={e => updateSection(index, { visible: e.target.checked })} />Visible</label><label className="check"><input type="checkbox" checked={section.locked ?? false} onChange={e => updateSection(index, { locked: e.target.checked })} />Protect from future AI edits</label></div>
          {section.type === 'experience' && <>
            <p>Company, title and dates come from your career library. Summaries render as paragraphs and duties as bullets; use the arrows to arrange them.</p>
            {[...new Set(section.items.flatMap(item => item.source_refs.flatMap(ref => {
              if (ref.entity_type === 'experience') return [ref.entity_id]
              const record = history.data?.find(r => r.id === ref.entity_id)
              return record?.data.type === 'achievement' && record.data.experience_id ? [record.data.experience_id] : []
            })))].map(id => { const record = history.data?.find(r => r.id === id && r.data.type === 'experience'); return record && <button key={id} className="secondary" onClick={() => setExperienceForm({ sectionKey: section.key, record })}>Edit details: {recordLabel(record)}</button> })}
            <button className="secondary" onClick={() => setExperienceForm({ sectionKey: section.key })}>Add experience</button>
            {experienceForm?.sectionKey === section.key && <ExperienceForm key={experienceForm.record?.id ?? 'new'} record={experienceForm.record} onCancel={() => setExperienceForm(undefined)} onSaved={(record, items) => experienceSaved(record, section.key, items)} />}
          </>}
          {section.items.map((item, itemIndex) => <div id={`item-${item.key}`} className="item-editor" key={item.key}>
            {section.type === 'experience' && <>
              {item.facts && <p className="source-note">{[item.facts.title, item.facts.employer, item.facts.start_date, item.facts.current ? 'Present' : item.facts.end_date].filter(Boolean).join(' · ')}</p>}
              <label>Experience text type<select value={item.experience_summary ? 'summary' : 'duty'} onChange={e => updateItem(index, itemIndex, { experience_summary: e.target.value === 'summary' })}><option value="summary">Summary (one sentence)</option><option value="duty">Duty (bullet point)</option></select></label>
            </>}
            <label>{section.type === 'experience' ? item.experience_summary ? 'Summary (one sentence max)' : 'Duty (bullet point)' : 'Item text'}<textarea value={item.text} onChange={e => updateItem(index, itemIndex, { text: e.target.value })} /></label>
            {item.experience_summary && summaryError(item.text) && <p role="alert">Use one sentence on one line, at most 500 characters. Avoid periods in abbreviations.</p>}
            <p className="source-note">{item.source_refs.length ? item.source_refs.map(ref => { const record = history.data?.find(r => r.id === ref.entity_id); return record ? recordLabel(record) : 'Retired or unavailable source (saved snapshot preserved)' }).join(' · ') : 'Manual draft · unverified'}</p>
            <div className="actions"><button className="secondary" aria-label="Move item up" disabled={itemIndex === 0} onClick={() => updateSection(index, { items: move(section.items, itemIndex, -1) })}>↑</button><button className="secondary" aria-label="Move item down" disabled={itemIndex === section.items.length - 1} onClick={() => updateSection(index, { items: move(section.items, itemIndex, 1) })}>↓</button><button className="secondary" onClick={() => updateSection(index, { items: section.items.filter((_, i) => i !== itemIndex) })}>Remove item</button><label className="check"><input type="checkbox" checked={item.locked ?? false} onChange={e => updateItem(index, itemIndex, { locked: e.target.checked })} />Protect item</label></div>
          </div>)}
          <div className="actions"><button className="secondary" onClick={() => addItem(index)}>Add manual text</button><label>Add from library<select aria-label="Add from library" value="" onChange={e => { const record = history.data?.find(r => r.id === e.target.value); if (record) addItem(index, record) }}><option value="">Choose a source…</option>{options(section).map(record => <option key={record.id} value={record.id}>{recordLabel(record)}</option>)}</select></label></div>
        </section>)}
        <div className="editor-form actions"><label>New section<select aria-label="New section" value={newType} onChange={e => setNewType(e.target.value as Section['type'])}>{sectionTypes.map(t => <option key={t} value={t}>{t}</option>)}</select></label><button onClick={() => setContent({ ...content, sections: [...content.sections, { key: crypto.randomUUID(), type: newType, title: newType.charAt(0).toUpperCase() + newType.slice(1), visible: true, locked: false, items: [] }] })}>Add section</button></div>
      </div>
      <aside className="preview-panel"><div className="toolbar"><h2>Live preview</h2><span className="pill">{preview.data ? `${preview.data.page_count} ${preview.data.page_count === 1 ? 'page' : 'pages'}` : 'A4'}</span></div>
        <label>Preview format<select aria-label="Preview format" value={view} onChange={e => setView(e.target.value as 'pdf' | 'html')}><option value="pdf">PDF (exact pagination)</option><option value="html">HTML (continuous, accessible text)</option></select></label>
        {preview.isFetching && <p role="status">Updating preview…</p>}
        {preview.error && <div role="alert"><p>{preview.error.message}</p><button type="button" disabled={preview.isFetching} onClick={() => void preview.refetch()}>Retry preview</button></div>}
        {preview.data?.warnings.map(w => <p className="warning" key={w}>{w}</p>)}
        {!valid && <p>Enter your name and complete each item to see a preview.</p>}
        {preview.data && (view === 'pdf' ? <PdfPreview encoded={preview.data.pdf_base64} /> : <iframe title="Resume HTML preview" sandbox="" srcDoc={preview.data.html} />)}
        <p className="source-note">PDF preview shows the same rendered pages used for download. HTML preview uses a continuous page layout.</p>
        <div className="actions"><button disabled={!valid || !title.trim() || save.isPending} onClick={() => save.mutate(false)}>{save.isPending ? 'Saving…' : saved?.kind === 'tailored' ? 'Save tailored edits' : 'Save master'}</button><button disabled={!valid || !title.trim() || save.isPending} onClick={() => save.mutate(true)}>Save & download PDF</button></div>
        {save.error && <p role="alert">{save.error.message}</p>}{notice && <p role="status">{notice}</p>}<p className="source-note">{dirty ? 'Unsaved changes' : `Saved · version ${saved?.version_number}`}</p>
      </aside>
    </div>
  </>
}
