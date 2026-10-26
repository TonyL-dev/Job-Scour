import { ActionGroup, PageHeader, Button, Disclosure } from './components/ui/Controls'
import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { assignModel, detectEndpoints, getPrompts, getSettings, listModels, saveEndpoint, saveProfile, testProfile } from './api/phase2'
import type { Detection, EndpointInput, ProfileInput } from './api/phase2'

const defaultEndpoint: EndpointInput = { name: 'Codex', provider: 'codex', base_url: 'https://chatgpt.com/codex', remote_consent: false, enabled: true, api_key_env: null }

export function AISettingsPage() {
  const cache = useQueryClient()
  const settings = useQuery({ queryKey: ['ai-settings'], queryFn: getSettings })
  const prompts = useQuery({ queryKey: ['prompts'], queryFn: getPrompts })
  const [endpoint, setEndpoint] = useState<EndpointInput>(defaultEndpoint)
  const [editingId, setEditingId] = useState<string>()
  const [detections, setDetections] = useState<Detection[]>([])
  const [models, setModels] = useState<string[]>([])
  const [profile, setProfile] = useState<ProfileInput>({ endpoint_id: '', model: '', context_window: 32768, max_output_tokens: 2048, temperature: 0.1, top_p: 1, structured_mode: 'json_schema' })
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [codexConsent, setCodexConsent] = useState(false)
  const codexProfile = settings.data?.endpoints.find(e => e.id === profile.endpoint_id)?.provider === 'codex'

  async function perform(action: () => Promise<void>) {
    setBusy(true); setError(''); setMessage('')
    try { await action(); await cache.invalidateQueries({ queryKey: ['ai-settings'] }) }
    catch (e) { setError(e instanceof Error ? e.message : 'Settings request failed.') }
    finally { setBusy(false) }
  }

  return <>
    <PageHeader title="AI settings" eyebrow="CONNECT CODEX" />
    <p>Use your installed Codex CLI and ChatGPT sign-in for job analysis, ranking, writing, summaries, verification and fitting. Requests use your Codex account limits. Career data stays local until you enable sharing below.</p>
    {(error || settings.error) && <p role="alert">{error || settings.error?.message}</p>}
    {message && <p role="status">{message}</p>}
    {settings.isPending && <p role="status">Loading AI settings…</p>}
    <section className="panel status-card"><h2>Use Codex</h2><p>Sign in with <code>codex login</code> on the backend machine. Codex receives only the supplied job text and source facts. Keyword matching works without a local model.</p>
      <label className="check-label"><input type="checkbox" checked={codexConsent} onChange={e => setCodexConsent(e.target.checked)} />I consent to sending supplied job text and career facts to OpenAI through Codex.</label>
      <Button variant="primary" disabled={busy || !codexConsent || settings.isPending} onClick={() => void perform(async () => {
        const existing = settings.data?.endpoints.find(e => e.provider === 'codex' && e.enabled && e.remote_consent)
        const destination = existing ?? await saveEndpoint({ ...defaultEndpoint, remote_consent: true })
        const selected = settings.data?.profiles.find(p => p.endpoint_id === destination.id && p.model === 'default') ?? await saveProfile({ endpoint_id: destination.id, model: 'default', context_window: 131072, max_output_tokens: 4096, temperature: 0, top_p: 1, structured_mode: 'json_schema' })
        for (const task of ['job_analysis', 'ranking', 'rewriting', 'summary', 'verification', 'condensing', 'import_extraction', 'profile_questions', 'cover_letter'] as const) await assignModel(task, selected.id)
        await testProfile(selected.id)
        setMessage('Codex is assigned to all nine chat tasks and its connection test passed. Use keyword matching in Jobs and Generate.')
      })}>Use Codex for AI tasks</Button>
    </section>
    <details><summary>Other providers (optional)</summary>
    <Button disabled={busy} onClick={() => void perform(async () => { setDetections(await detectEndpoints()); setMessage('Local endpoint detection finished.') })}>Detect local endpoints</Button>
    <ul>{detections.map(d => <li key={d.provider}>{d.name}: {d.available ? `${d.models.length} models available` : 'Not running'} {d.available && <Button disabled={busy} onClick={() => { setEditingId(undefined); setEndpoint({ ...defaultEndpoint, name: d.name, provider: d.provider, base_url: d.base_url }); setModels(d.models) }}>Use {d.name}</Button>}</li>)}</ul>
    </details>
    <Disclosure title="Advanced AI configuration"><p>Manage endpoints, model profiles and task assignments. Changes affect future calls.</p><div className="phase2-grid">
      <section className="panel status-card"><h2>{editingId ? 'Edit endpoint' : 'Add endpoint'}</h2>
        <form onSubmit={event => { event.preventDefault(); void perform(async () => { const saved = await saveEndpoint(endpoint, editingId); setProfile(p => ({ ...p, endpoint_id: saved.id })); setEditingId(saved.id); setMessage('Endpoint saved. List its models to create a profile.') }) }}>
          <label>Endpoint name<input required value={endpoint.name} onChange={e => setEndpoint({ ...endpoint, name: e.target.value })} /></label>
          <label>Provider<select aria-label="Provider" value={endpoint.provider} onChange={e => { const provider = e.target.value as EndpointInput['provider']; setEndpoint({ ...endpoint, provider, base_url: provider === 'codex' ? defaultEndpoint.base_url : 'http://127.0.0.1:1234/v1', api_key_env: null, remote_consent: false }) }}><option value="codex">Codex (ChatGPT login)</option><option value="lm_studio">LM Studio</option><option value="ollama">Ollama</option><option value="openai_compatible">OpenAI compatible</option></select></label>
          <label>Base URL<input required type="url" disabled={endpoint.provider === 'codex'} value={endpoint.base_url} onChange={e => setEndpoint({ ...endpoint, base_url: e.target.value, remote_consent: false })} /></label>
          {endpoint.provider !== 'codex' && <label>API key environment variable<input placeholder="LLM_API_KEY (optional)" value={endpoint.api_key_env ?? ''} onChange={e => setEndpoint({ ...endpoint, api_key_env: e.target.value || null })} /></label>}
          <label className="check-label"><input type="checkbox" checked={endpoint.enabled ?? true} onChange={e => setEndpoint({ ...endpoint, enabled: e.target.checked, remote_consent: e.target.checked ? endpoint.remote_consent : false })} />Endpoint enabled</label>
          <label className="check-label"><input type="checkbox" checked={endpoint.remote_consent ?? false} onChange={e => setEndpoint({ ...endpoint, remote_consent: e.target.checked })} />I consent to sending job text and career records to this remote endpoint.</label>
          <p className="muted">Loopback endpoints need no remote consent. Remote endpoints require HTTPS. Disable an endpoint to revoke consent and stop new requests.</p>
          <ActionGroup><Button variant="primary" disabled={busy}>Save endpoint</Button> <Button type="button" disabled={busy} onClick={() => { setEndpoint(defaultEndpoint); setEditingId(undefined) }}>New endpoint</Button></ActionGroup>
        </form>
        <ul>{settings.data?.endpoints.map(e => <li key={e.id}><strong>{e.name}</strong> · {e.enabled ? 'Enabled' : 'Disabled'}<p className="muted">{e.base_url}</p><Button disabled={busy} onClick={() => { setEndpoint({ name: e.name, provider: e.provider, base_url: e.base_url, remote_consent: e.remote_consent, enabled: e.enabled, api_key_env: e.api_key_env }); setEditingId(e.id); setProfile(p => ({ ...p, endpoint_id: e.id })); setModels([]) }}>Edit {e.name}</Button></li>)}</ul>
      </section>
      <section className="panel status-card"><h2>Create model profile</h2>
        <form onSubmit={event => { event.preventDefault(); void perform(async () => { await saveProfile(profile); setMessage('Model profile saved. Assign it to a task below.') }) }}>
          <label>Endpoint<select aria-label="Endpoint" required value={profile.endpoint_id} onChange={e => { const codex = settings.data?.endpoints.find(p => p.id === e.target.value)?.provider === 'codex'; setProfile({ ...profile, endpoint_id: e.target.value, model: codex ? 'default' : '', context_window: codex ? 131072 : 32768 }); setModels([]) }}><option value="">Choose endpoint</option>{settings.data?.endpoints.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select></label>
          <Button type="button" disabled={busy || !profile.endpoint_id} onClick={() => void perform(async () => { setModels(await listModels(profile.endpoint_id)); setMessage('Model list refreshed.') })}>List models</Button>
          <label>Model<input required list="available-models" value={profile.model} onChange={e => setProfile({ ...profile, model: e.target.value })} /></label><datalist id="available-models">{models.map(m => <option key={m} value={m} />)}</datalist>
          {codexProfile && <p className="muted">Use “default” for the CLI default, or a model available to your Codex account. Codex controls sampling and output length; the configured output limit reserves space in the input budget.</p>}
          <label>Context window<input type="number" required min="512" max="2000000" value={profile.context_window} onChange={e => setProfile({ ...profile, context_window: Number(e.target.value) })} /></label>
          <label>Output token limit<input type="number" required min="32" max="32768" value={profile.max_output_tokens} onChange={e => setProfile({ ...profile, max_output_tokens: Number(e.target.value) })} /></label>
          <label>Temperature<input disabled={codexProfile} type="number" min="0" max="2" step="0.1" value={profile.temperature} onChange={e => setProfile({ ...profile, temperature: Number(e.target.value) })} /></label>
          <label>Top P<input disabled={codexProfile} type="number" min="0.01" max="1" step="0.01" value={profile.top_p} onChange={e => setProfile({ ...profile, top_p: Number(e.target.value) })} /></label>
          <label>Structured output<select disabled={codexProfile} aria-label="Structured output" value={profile.structured_mode} onChange={e => setProfile({ ...profile, structured_mode: e.target.value as ProfileInput['structured_mode'] })}><option value="json_schema">JSON schema (recommended)</option><option value="json_object">JSON object</option><option value="none">Prompt only</option></select></label>
          <Button variant="primary" disabled={busy || !profile.endpoint_id}>Save model profile</Button>
        </form>
      </section>
    </div>
    <section className="panel status-card"><h2>Task assignments</h2><p>HTTP providers can use temperature 0–0.2 for analysis. Codex manages sampling itself. Embedding profiles need an embedding model; they do not use chat temperature or output settings. Assign profiles before testing so embedding models use the vector test.</p>
      {(['job_analysis', 'embeddings', 'ranking', 'rewriting', 'summary', 'verification', 'condensing', 'import_extraction', 'profile_questions', 'cover_letter'] as const).map(task => <label key={task}>{task === 'job_analysis' ? 'Job analysis model' : task === 'embeddings' ? 'Embedding model' : task.charAt(0).toUpperCase() + task.slice(1).replaceAll('_', ' ') + ' model'}<select aria-label={task === 'job_analysis' ? 'Job analysis model' : task === 'embeddings' ? 'Embedding model' : task.charAt(0).toUpperCase() + task.slice(1).replaceAll('_', ' ') + ' model'} disabled={busy} value={settings.data?.assignments.find(a => a.task === task)?.profile_id ?? ''} onChange={e => void perform(async () => { await assignModel(task, e.target.value); setMessage('Task assignment saved.') })}><option value="" disabled>Choose profile</option>{settings.data?.profiles.filter(p => task !== 'embeddings' || settings.data?.endpoints.find(e => e.id === p.endpoint_id)?.provider !== 'codex').map(p => <option key={p.id} value={p.id}>{p.model} · {settings.data?.endpoints.find(e => e.id === p.endpoint_id)?.name} · {p.context_window} context</option>)}</select></label>)}
      <ul>{settings.data?.profiles.map(p => <li key={p.id}>{p.model} <Button disabled={busy} onClick={() => void perform(async () => { await testProfile(p.id); setMessage(`Model connection test passed for ${p.model}.`) })}>Test {p.model}</Button></li>)}</ul>
    </section>
    </Disclosure><section className="panel status-card"><h2>Prompt registry</h2><p>Built-in prompts are versioned files. Each analysis records its model and prompt digest. The developer evaluation command tests synthetic job descriptions.</p>{prompts.error && <p role="alert">{prompts.error.message}</p>}{prompts.data?.map(p => <details key={p.digest}><summary>{p.key} · version {p.version}</summary><p>{p.system_text}</p><pre className="prompt-text">{p.user_template}</pre><p className="muted">SHA-256: {p.digest}</p></details>)}</section>
  </>
}
