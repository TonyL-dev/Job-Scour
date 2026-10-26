# Resume Tailor

A local-first career and resume workspace with sourced generation/review, actual PDF preview/export, ATS guidance, immutable version history, application tracking, passcode protection, optional encrypted storage, and full data controls. Phase 6 adds reviewed imports, profile fact collection, cover letters, prompt preferences/playground, DOCX export and custom templates. Release verification and environment limits are recorded in IMPLEMENTATION_STATUS.md. Codex is the default AI provider and requires explicit sharing consent; manual editing, ATS, history and tracking work without AI.

## Developer onboarding

Start with the [developer handbook](docs/developer/README.md) for the current architecture, repository map, design principles and traced workflows. Read the detailed [backend](docs/developer/BACKEND.md) and [frontend](docs/developer/FRONTEND.md) guides for code organization, contracts, state, transactions, concurrency, privacy, testing and feature-change recipes. The [new-project architecture template](docs/developer/PROJECT_ARCHITECTURE_TEMPLATE.md) works alongside the reusable coding-practice guides to document future projects. The handbook distinguishes implemented code, historical plans, recommended patterns and known limitations.

## UI/UX style and reuse

The [UI/UX style specification](docs/design/UI_UX_STYLE_GUIDE.md) documents the implemented Apple-inspired typography, colors, spacing, components, layouts and interaction rules. Use the [copyable reference site](docs/design/ui-starter/index.html) to reproduce the style in another project; its token and foundation CSS are synchronized with the app. The [clean UI process](docs/coding-practices/CLEAN_UI_DESIGN_PROCESS.md) explains the design workflow.

## Choose an installation

For reusable standards to copy into future projects, see the [frontend and backend coding practice guides](docs/coding-practices/README.md). They cover architecture, naming, implementation patterns, security, testing and new-project adoption checklists.

For the complete Windows launch, AI setup, optional private-file key and first-use sequence, see [Run on Windows](docs/run-windows.md).

Use the native setup below for Codex generation with your existing ChatGPT login. Docker provides a self-contained manual editing/PDF/ATS/history/tracker/privacy installation; the stock image does not include Codex CLI or an account login. Download or copy the complete repository source, including lockfiles and bundled fonts, into a writable directory. Installation downloads dependencies and Chromium; the manual workspace needs no internet after setup. No public repository or downloadable signed installer is currently provided.

## Reopen your saved workspace on Windows

**For this existing installation, use the native app at http://127.0.0.1:5173.** Your saved master resume is in `backend/resume-tailor.db`. Docker uses a separate PostgreSQL database, even when launched from the same project folder; it does not automatically load or copy the native database. Starting Docker on port 5173 can therefore show an empty workspace while your native resume is still saved.

After restarting Windows, open two PowerShell terminals. If Docker is serving this project on port 5173, first run `docker compose stop frontend backend` from the project folder. This frees the app ports and preserves its database volumes. Use the native commands below for your saved SQLite workspace; `docker compose up` starts the separate Docker workspace again. In the first, start the backend against the existing database:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
if (-not (Test-Path -LiteralPath 'backend/resume-tailor.db' -PathType Leaf)) {
    throw 'Saved database not found. Check the project folder before starting.'
}
$env:APP_DATABASE_URL = 'sqlite:///' + (Resolve-Path -LiteralPath 'backend/resume-tailor.db').Path.Replace('\', '/')
$env:APP_API_HOST = '127.0.0.1'
$env:APP_API_PORT = '8000'
$env:APP_FRONTEND_ORIGINS = '["http://127.0.0.1:5173","http://localhost:5173"]'
if (-not $env:APP_UPLOAD_KEY) {
    $env:APP_UPLOAD_KEY = [Environment]::GetEnvironmentVariable('APP_UPLOAD_KEY', 'User')
}
python scripts/tasks.py backend
```

In the second terminal, start the frontend with its API pointed at that backend:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
$env:API_PROXY_TARGET = 'http://127.0.0.1:8000'
pnpm --dir frontend dev --host 127.0.0.1 --port 5173 --strictPort
```

Keep both terminals open, then open [Master resumes](http://127.0.0.1:5173/resumes) and choose your master from **Saved resumes**. The editor initially opens **New master resume**; blank fields do not mean your saved resume was deleted. Bookmark your selected resume's editor URL to reopen it directly.

These are restart commands for the already installed project; no setup or migration is needed for an ordinary restart. If you move the project, update `Set-Location` in both commands. If either port is already occupied, use the existing native instance or stop it before starting another. See [Run on Windows](docs/run-windows.md) for first-time setup, upgrades and optional storage keys.

Click **Save master** or **Save & download PDF** once when creating a new resume. Autosave applies only after that first save and only while enabled; wait for the saved indicator before closing. Saved resumes and their versions persist in the database when the browser or computer shuts down. Use **Privacy** exports for additional backups, and retain any encryption keys separately.

## Start with Docker (separate workspace)

To reopen the existing native resume, use the Windows restart instructions above. The following starts Docker's own persistent workspace.

Install Docker Desktop with Compose v2, then from the repository root:

```sh
docker compose up --build --wait
```

Open http://127.0.0.1:5173. The overview shows “Backend connected” when PostgreSQL is migrated and ready. API documentation is at http://127.0.0.1:8000/docs. The stack includes the React build served by Nginx, FastAPI, PostgreSQL, and Redis. Redis is reserved for future authenticated server workers. Generation currently uses one local backend worker with persisted runs; job analysis uses request-owned tasks. An LLM is not required for manual career/resume workflows and is contacted only by explicit model actions. Domain routes require local mode until server authentication exists; Phase 5 no-cache builds and final Docker browser/PDF/domain/privacy checks were verified in an isolated stack; hosted CI and live Codex container authentication remain separate checks.

Only frontend/backend loopback ports are published. Container services communicate over their internal network. The included database credentials are for this local development stack. This is not an authenticated server deployment.

`docker compose down` stops services and preserves database volumes. `docker compose down --volumes` explicitly deletes their data. Root `.env` may set `FRONTEND_PORT` and `BACKEND_PORT`; port changes do not require a frontend rebuild because API requests use the same origin.

### Troubleshoot a backend startup failure

If startup reports `dependency backend failed to start`, inspect the service status and backend logs:

```sh
docker compose ps -a
docker compose logs --tail 100 backend
```

If PostgreSQL is healthy and the logs show `failed to resolve host 'postgres'`, recreate the backend and frontend to refresh their container network connections:

```sh
docker compose up -d --force-recreate --wait backend frontend
docker compose ps
```

This recovered the observed Docker DNS startup failure and preserves the existing database and Redis volumes. Once all four services are healthy, open http://127.0.0.1:5173. If startup still fails or the logs show a different error, inspect the latest backend logs before choosing another fix. Do not use `docker compose down --volumes` for this recovery; it deletes stored data.

## Start without Docker

This section covers first-time setup with default ports. For the existing Windows workspace, use **Reopen your saved workspace on Windows** above on subsequent launches.

Requires Python 3.12+ and Node.js 24.x. Use 64-bit Python and install pnpm 11.19.0 (for example, `npm install -g pnpm@11.19.0`) and put Python, Node, pnpm, and Git on PATH. Commands work in PowerShell and POSIX shells.

```sh
python scripts/tasks.py setup
python scripts/tasks.py renderer-setup
python scripts/tasks.py migrate
python scripts/tasks.py doctor
```

On Linux, install Chromium system libraries before `doctor` using `backend/.venv/bin/python -m playwright install --with-deps chromium` (requires administrator access for OS packages). `doctor` verifies migrated storage and a real PDF made from synthetic text, with no AI calls. Git hooks are optional for development: `python scripts/tasks.py hooks` requires a Git repository.

In separate terminals:

```sh
python scripts/tasks.py backend
python scripts/tasks.py frontend
```

Open http://127.0.0.1:5173. The backend binds to 127.0.0.1:8000; Vite forwards `/api` requests to it. Local mode uses `backend/resume-tailor.db` (ignored by Git). Copy `backend/.env.example` to `backend/.env` to change backend settings. Settings use the `APP_` prefix. Frontend origins are a JSON string array. Set `API_PROXY_TARGET` in the frontend process environment when changing the backend port. Never put credentials into frontend variables.

## Checks and generated API contracts

```sh
python scripts/tasks.py check
python scripts/tasks.py audit
```

The check runs Ruff lint/format, strict mypy, pytest, OpenAPI/type drift detection, ESLint, strict TypeScript, React tests, and a production build. Audits query package advisory services; app runtime does not do this. Dependencies are pinned by `backend/requirements.lock` and `frontend/pnpm-lock.yaml`.

After changing response schemas or routes:

```sh
python scripts/tasks.py api
```

Commit `frontend/src/api/openapi.json` and `frontend/src/api/schema.d.ts` with the backend change. Generation imports the app without running its lifespan, so it needs no running database. TypeScript 5.9.3 is deliberately pinned because the API generator requires its compiler API. The client uses `openapi-fetch` with generated `paths`; no handwritten duplicate response types.

Pre-commit runs the same checks using the local venv and pnpm. Git must be initialized before installing the hook. GitHub Actions runs checks/audits and a separate Docker Compose smoke job, which checks migrations, health through Nginx, and SPA deep links. A local successful check is not a hosted CI result.

## API

| Endpoint | Meaning |
|---|---|
| GET /api/health/live | Process liveness; returns 200 without database access. |
| GET /api/health | Database readiness against the migrated users table; 200 when ready, 503 with a typed degraded result otherwise. |
| GET /openapi.json | Live generated API schema. |
| GET /docs | Local API reference with an OpenAPI schema link; no CDN scripts. |
| GET /api/career/forms | Typed category forms and field choices. |
| GET /api/career/{kind} | Active career records; inactive parent chains are excluded. |
| POST /api/career | Create a typed career record. |
| GET /api/career/{kind}/{identifier} | Read an owned, active record. |
| PUT /api/career/{identifier} | Replace a career record with validated facts. |
| DELETE /api/career/{kind}/{identifier} | Retire a record, preserving historical references. |
| GET /api/resumes/templates | Built-in Classic and Modern template definitions. |
| GET /api/resumes | Saved manual masters with their latest snapshots. |
| POST /api/resumes | Create a master and its first immutable snapshot. |
| GET /api/resumes/{identifier} | Read a saved master. |
| PUT /api/resumes/{identifier} | Save a new snapshot using expected_version for conflict protection. |
| POST /api/resumes/preview | Render an unsaved draft to HTML and PDF, with real page count and warnings. |
| GET /api/resumes/{identifier}/pdf | Download the latest saved PDF; headers expose page count and HTML hash. |

## Build a master resume

Open **Career library** and enter your experiences, projects, education, courses, skills, certifications, volunteer work, awards, publications, and other history. Add achievements with metrics under exactly one experience or project. Link each skill to an experience, project, or achievement through **Skill evidence**. Edit records or retire them when no longer relevant. Dependent records become inactive when a parent is retired.

Open **Master resumes**, enter your contact details, and add sections. Use **Add from library** to insert records with source references; employer/title/date display facts are resolved by the backend. You can also enter manual text, which is marked unverified if it has no sources. Move sections and items with the arrow buttons; change titles, visibility, fonts, colors, spacing, and margins. Protection flags prevent AI regeneration from changing protected content; they do not prevent your own manual edits. At most one master is the gold standard.

In an **experience** section, choose **Add experience** to enter **Company**, **Title**, **Start date**, **End date** or **Present**, an optional **Summary (one sentence max)** and **Duties**. Add one duty per field; at least a summary or one duty is needed. The summary is limited to 500 characters on one line; sentence validation is conservative, so avoid periods in abbreviations. Summaries render as paragraphs and each duty as a bullet in PDF/HTML and DOCX. The action saves a career library experience containing the supplied text as evidence and adds sourced items to your draft. Save the master once to persist the document; subsequent edits follow the autosave setting. Cancelling or discarding the resume draft does not delete an already saved library record.

Use **Edit details: …** to change a linked experience's company/title/dates. This explicitly updates the shared library record; save/autosave captures the current facts in a new resume version while old versions retain their original facts. Other saved resumes refresh those facts only when edited/saved. Edit summary/duty text, choose its **Experience text type**, or reorder/remove individual items in the master editor. These text edits affect the resume, not the library evidence; update the career record separately when the underlying facts change. Existing experience items remain duty bullets until you explicitly mark one as a summary. No AI call is needed.

The default preview displays actual PDF pages using bundled PDF.js, with the same Chromium renderer and bundled Noto fonts used for download. The alternate sandboxed HTML preview is continuous and offers accessible text. Page targets produce warnings; generation can fit unlocked content to the target. **Save & download PDF** saves your draft first. Saves append immutable snapshots and reject stale expected versions. Enable autosave after the first save, and use Resume history for compare, restore and duplicate.

Native PDF rendering requires the matching Playwright Chromium install from `renderer-setup`; on Linux also install its OS dependencies with `backend/.venv/bin/python -m playwright install --with-deps chromium`. The Dockerfile includes Chromium and its dependencies. If unavailable, preview/export return an actionable 503; career entry and saving remain available. If a custom web server cannot draw PDF pages, ensure its .mjs module workers are served as JavaScript; the included Nginx configuration does this.

Retired sources remain in saved snapshots and PDFs. New drafts cannot cite inactive sources; remove or replace those items before saving an edited draft. Source edits are resolved on the next save, while previous snapshots retain their original facts.

## Scope and privacy

AI calls occur when you request connection tests, job analysis or resume generation. Codex requires explicit data-sharing consent. There are no telemetry exporters or third-party runtime assets. Passcode locking, optional SQLCipher/AES-GCM encryption and full export/delete controls are implemented. Storage is plaintext unless you explicitly enable encryption using the instructions below. The passcode is a workspace access lock; it does not encrypt an existing database automatically. Server authentication remains future work. Domain APIs refuse server mode until authentication is implemented. Local mode initializes one fixed local identity, ignores client-supplied ownership, and scopes all domain queries to it. Only use the local loopback deployment; it is not a multi-user server.

Resume templates escape all text, allow only bounded style overrides, use embedded licensed Noto fonts, and block scripts and external rendering requests. A source reference proves ownership/existence, not semantic truth of a manually rewritten statement.

See `docs/design/01-foundations.md` for the complete planned foundations design, `ARCHITECTURE.md` for implemented boundaries, and `IMPLEMENTATION_STATUS.md` for verified results and remaining acceptance checks.

## Connect models and analyze a job (Phase 2)

Run migrations after updating: `python scripts/tasks.py migrate`. Install a current [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) on the backend machine and sign in with `codex login` using ChatGPT. In **AI settings**, check the OpenAI data-sharing consent and choose **Use Codex for AI tasks**. This assigns all nine text tasks, including the three Phase 6 tasks, and tests the connection. It uses your ChatGPT/Codex account, without an API key or local LLM server. If the executable is not on PATH, set `STONKS_CODEX_CLI` to its absolute native executable path (on Windows, `codex.exe`, not a `.cmd` shim). Docker requires its own CLI installation and login; the host's login is not automatically available inside the container.

The model name `default` selects the installed CLI's default; an explicit account-supported model can be entered in a profile. This does not enumerate your account's models or pin a future CLI default. Codex uses schema-constrained isolated, ephemeral runs and controls sampling/output length. Temperature/top-p are unused for Codex; the profile output-token value is an input-budget reservation, not a CLI-enforced generation cap. A wall timeout and response byte limits bound the process. No user configuration, MCP/apps/plugins, shell, web search, project instructions or telemetry exporters are enabled by the adapter. CLI authentication remains CLI-owned. Application prompts/diagnostics are not logged; ephemeral temporary schema/results are removed after completion.

Other OpenAI-compatible providers remain optional under **Other providers**. Their context/sampling settings still apply. A passed connection test does not establish model quality.

Use **Job analysis** to paste/save a description and run analysis. Progress is streamed; cancel closes the request and keeps the saved job available to retry. Results show required/preferred skills, technologies, responsibilities, values, industry terms, seniority/years when stated, and weighted keywords with exact source quotes. Career matches combine semantic relevance and keyword evidence with recency/importance, and link to the active source records. Missing keywords stay gaps. Keyword coverage is not an ATS score. Matching without an assigned embedding model explicitly falls back to keywords; uncheck embeddings for a keyword-only run.

Validated job analyses are cached by input/prompt/schema/model settings, while career matches always refresh. Text edits invalidate embedding caches; retired or inactive ancestor records are excluded. Completed validated cache entries can survive cancellation. Job analysis does not change career facts. Use Generate & review for sourced tailoring; missing skills cannot be inserted as facts.

Only loopback is treated as local. Other endpoints need HTTPS and explicit consent to send job text and career records; disable an endpoint to revoke future calls. An already transmitted request needs cancellation. Redirects and environment proxies are disabled. For authentication, set an `LLM_*` variable in the backend environment and enter its name in settings; no key value is stored or returned. Prompt/response logging is disabled; only model/timing/usage metadata is logged when available. There are no automatic model downloads by the app.

The prompt registry is read-only; built-in versioned files are under `backend/app/ai/prompts`. To run synthetic job-analysis evaluation through your Codex login:

```sh
python scripts/tasks.py ai-eval --provider codex --models default --repeats 2 --output ../.validation/codex-analysis.json
```

On limited hardware, load/evaluate one model at a time and produce separate reports. The command uses synthetic fixtures only and exits nonzero on schema/evidence/classification/injection/stability failures. Optional `--structured-mode json_object` or `none` evaluates those gateway modes. The separate generation-eval command checks resume provenance, protection flags and page fitting. See IMPLEMENTATION_STATUS.md for actually verified models/configurations; do not assume compatibility from a mocked test. [LM Studio structured-output documentation](https://lmstudio.ai/docs/developer/openai-compat/structured-output) and [Ollama compatibility documentation](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx) describe their server interfaces.


## Generate and review a tailored resume (Phase 3)

1. Enter career facts, save a master resume (optionally gold standard), and save a job description.
2. In AI settings, use the Codex setup above. Embeddings are optional and default off: Codex does not provide vectors, so keyword matching requires no local model. The gateway uses conservative input budgeting. Model quality must be evaluated.
3. Open **Generate & review**, choose the master/job, and start generation. Runs continue if you navigate away. Return through Saved generation runs; Cancel explicitly stops a run. Backend restart preserves partial suggestions and marks interrupted work failed for retry.
4. Review original/proposed text, source evidence and support labels. Pending/rejected suggestions preserve the original. Unsupported AI changes need a sourced edit confirmed by you. Accept supported changes individually or together, then inspect the actual PDF and page warnings.
5. Save review decisions/locks, choose section/item scope and a preset or instruction to regenerate. Protected content stays unchanged. Optional layout fitting requires the checkbox.
6. Save a separate tailored resume and download its saved PDF. The master is unchanged. Later review edits do not overwrite the saved tailored snapshot; create another generation to derive a new document.

Run `python scripts/tasks.py generation-eval --provider codex --models default --output ../.validation/phase3-codex.json` to test the ten synthetic fixtures through actual generation, source/verifier guards, locks, PDF fitting and review saves. This sends only synthetic fixtures to Codex, uses disposable databases and never opens personal career data. Optional local evaluation requires `--provider openai_compatible --base-url http://127.0.0.1:1234/v1`. Rejected valid paraphrases remain a known tradeoff of conservative validation.


## Phase 4: ATS, history, applications and privacy

Open **Resume history & ATS** to browse master and tailored documents, filter by company/role/title/date/kind/application status, inspect or compare versions, restore an older snapshot as a new version, duplicate a separate document, or download an exact historical PDF. The editor opens either kind of saved document. After the first explicit save, valid edits autosave after 1.8 seconds; disable the checkbox to save manually. Conflicts preserve your draft and require a reload. Text edits become user content; existing AI text cannot be changed or newly introduced with AI origin through the manual API. Current evidence checks still apply. Restore/duplicate intentionally copy historical facts, including retired references; subsequent edits require active valid sources.

Run **ATS checks on this PDF** for a selected version and saved job analysis (linked job defaults to its latest analysis). Reports are immutable, dated guidance from engine `ats.1`, not a vendor prediction. Weighted keywords/aliases, career-backed missing terms versus gaps, action verbs, stored metrics, structure/chronology, readability/stuffing heuristics, actual PDF extraction/reading order/contact/facts, and measured pages produce linked findings. Findings open the snapshot or current editor and point to relevant career categories. No model call occurs. Historical reports reflect career evidence when created; rerun after changing sources. English readability and sparse-page checks are heuristics, so inspect the PDF visually.

**Track this application** carries the exact resume-version ID and linked job into **Applications**. Store company/role, dates, source, notes, stage and next follow-up. Stage changes append events under a revision check. The tracker has table/board views, due follow-ups and response-stage counts by exact version. Submitted PDF links keep that version even after later resume edits/restores. These are recorded stages, not automatic recruiter outcome detection or external reminders.

**Privacy** provides a passcode of at least eight characters, lock/unlock, JSON export, JSON plus every version PDF as a ZIP, and typed delete-all. Passcodes use salted scrypt; authentication uses HttpOnly SameSite=Strict cookies. Restart locks protected workspaces, sessions expire after 30 minutes, and the screen locks after 15 minutes without interaction. Lock/delete cancels local generation. Delete-all removes career records (including retired ones), jobs, analyses, embeddings, prompt/settings caches, runs/suggestions, resumes, ATS reports and tracker/events, while retaining the local passcode. Downloads, external provider copies and existing backups are outside this deletion. No server authentication is claimed.

### Optional complete SQLite encryption

SQLCipher encrypts the entire database file, including identifiers, dates and numeric metadata. Its key is derived from a backend-only `APP_DATABASE_PASSPHRASE` using Argon2id (64 MiB, three iterations, four lanes). This storage passphrase may be the same value as your app passcode, but the browser lock and storage unlock are separate mechanisms. Keep the database's `.salt` sidecar with backups and retain the passphrase securely. Losing the passphrase or salt prevents reopening the encrypted file.

Stop the backend before converting an existing SQLite database. The converter creates a new file, verifies database integrity/foreign keys, and refuses to overwrite the source or another target. Example from the repository root in PowerShell:

```powershell
$storageSecret = Read-Host 'Database passphrase' -AsSecureString
$env:APP_DATABASE_PASSPHRASE = [System.Net.NetworkCredential]::new('', $storageSecret).Password
Push-Location backend
$env:APP_DATABASE_URL = 'sqlite:///./resume-tailor.db'
& .venv/Scripts/python.exe -m app.privacy.encrypt_database --output resume-tailor.encrypted.db
$env:APP_DATABASE_URL = 'sqlite:///./resume-tailor.encrypted.db'
& .venv/Scripts/python.exe -m alembic upgrade head
& .venv/Scripts/python.exe -m app
```

For a new empty store, select a new SQLite filename and set the passphrase before running migrations; a salt is created once. In future backend terminals, provide the same URL/passphrase. On POSIX, export those environment variables and use `.venv/bin/python`. Encryption secrets are read from the backend process environment, not exposed by the settings API. Never supply them to the frontend or commit them. Conversion deliberately retains the original plaintext database: verify the encrypted copy and independently manage that original and earlier backups. JSON/PDF exports are plaintext.

The locked SQLCipher wheel is bundled in dependencies. Its optional `cipher_memory_security` switch crashed the native Windows wheel during validation and is not enabled; database encryption remains enabled and tested. This does not claim protection against a compromised running backend or OS memory inspection.

### Optional sensitive-field encryption (SQLite or PostgreSQL)

`APP_ENCRYPTION_KEY` accepts base64 of 32 random bytes. Keep this key outside database files, exports and source control. It encrypts descriptive career/job/tracker text, resume/generation/analysis/report JSON, prompt text and vectors with AES-GCM; a keyed blind index preserves normalized skill uniqueness. Relational IDs, dates, numeric values and constrained status/configuration/index metadata remain queryable. This is a supplement to complete SQLite encryption or PostgreSQL disk/volume encryption, not a claim that every PostgreSQL column is encrypted.

Set the key in the backend process. With the backend stopped, convert existing protected fields before restarting:

```sh
cd backend
python -m app.privacy.encrypt_store
```

Use the virtual environment's Python. The conversion is transactional and preserves snapshot content hashes; SQLite vacuum removes freed pages from the live file. Startup fails closed on missing/incorrect keys, tampering or incomplete plaintext conversion. Existing backups/export files are not rewritten. Save the key securely; there is no automatic key recovery or rotation flow.

### Browser acceptance checks

```sh
python scripts/tasks.py e2e
```

This launches disposable backend/Vite services on loopback ports, uses SQLCipher storage and synthetic model responses, exercises Flows A/D/E/F with actual Chromium/PDF.js/ATS/exports, and stops only its own services. It never opens the career database or calls Codex. Evidence is written under ignored `.validation/`. CI includes this command, but a local pass does not prove a hosted run or live Codex container authentication. Live model evaluation commands remain documented above.


## Model choice and hardware

Start with Codex and `default`, then use the synthetic evaluation commands above before relying on any different configured model. The current app does not enumerate account models; `default` follows the CLI configuration. Choose an explicit supported model only when you want to pin the requested name. Sign-in/install options are described in [official Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli), and account authentication/data policies in [official authentication documentation](https://learn.chatgpt.com/docs/auth). This application requires ChatGPT sign-in for its Codex adapter; it does not fall back to API-key billing.

Codex inference runs remotely, so no GPU or model weights are needed on your machine. A practical starting budget for native manual editing/PDFs is 8 GB system RAM and several GB of free disk for Python/Node/Chromium; 16 GB is more comfortable for Docker and other running apps. These are planning estimates, not measured minimums or a hardware certification. Chromium, optional local inference and the OS share memory. The app permits two concurrent PDF renders, one AI inference, four waiting AI requests, and four outstanding local generation tasks. AI waits expire after 30 seconds; retry after the current task completes. PDF saturation returns a retryable error after five seconds.

Optional local models require their own server and enough RAM/VRAM for the quantized model, context and runtime. Do not size hardware by parameter count alone. Historical synthetic tests found mixed results with Qwen2.5 1.5B and conservative over-rejections with Devstral; those configurations are not a guarantee for your writing. LM Studio's Nomic loader failed on the validation host; keyword matching avoids that dependency. No automatic model downloads occur. Set the actual loaded context limit and leave embeddings off unless a separate embedding model is configured. Review every generated proposal and the final PDF.

## Recovery and accessible use

Keyboard users can Tab to **Skip to main content** and press Enter. Navigation moves focus to the main view; form fields and reorder buttons have labels. PDF pages expose extracted-text labels, and the PDF/table/board scroll regions accept keyboard focus. Select HTML preview for readable continuous text. Status updates and errors are announced; important text uses contrasting colors. These checks are a practical accessibility pass, not a WCAG certification or a substitute for testing with your own screen reader.

- Connection unavailable: start the backend, run migrations, then Retry connection. Failed libraries have a Retry button; empty screens explain the first record to add.
- PDF unavailable: run renderer-setup with the backend venv; on Linux install OS dependencies as above. A busy renderer can be retried without reinstalling Chromium. Manual saves remain available.
- AI busy/queue full: wait for another analysis/generation to finish or cancel it, then retry. Interrupted runs preserve checkpoints and require a new run after restart.
- Conflicting save: preserve your unsaved text, reload the latest version and reapply edits; history remains immutable. Unsupported AI text requires a sourced user-confirmed edit or rejection.
- Install TLS error: inspect inherited SSL_CERT_FILE, REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE or PIP_CERT. Correct/remove an invalid path in that terminal, or provide your organization's valid CA bundle. Keep certificate verification enabled.
- Runtime mismatch: setup requires Python 3.12+, Node 24.x and pnpm exactly 11.19.0. Open a new terminal after installing them. Use a writable source directory, and stop existing services or select free ports.

PDF reuse is limited to eight entries/24 MiB and 60 seconds of validity in process memory. Expired entries are removed on the next cache access; lock, passcode change, session expiry detection, deletion and shutdown clear the cache and reject late cache insertion. It is never persisted. All API responses are no-store. Native development uses Vite; built previews and Nginx add restrictive CSP, no framing, no referrer and nosniff headers. No public server deployment is supported.

## Release verification

```sh
python scripts/tasks.py check
python scripts/tasks.py audit
python scripts/tasks.py e2e
python scripts/tasks.py fresh-install
```

`fresh-install` copies an explicit source allowlist into a temporary directory, installs new Python/Node dependency environments, follows setup → renderer-setup → migrate → doctor, builds the frontend, and runs the production UI against a real empty backend. It verifies keyboard navigation, manual save/PDF, ATS and persistence after restart. It never copies the personal store, environment files or credentials, and never calls models. Evidence/logs/screenshots are in ignored `.validation/`; its own services and temporary copy are removed. It uses the installed host runtimes and package/browser caches, so it does not claim a newly provisioned physical OS. Clean container builds independently validate Linux installation using the Docker path. See [release security review](docs/release/security-review.md) for section 8 coverage and residual risks.

Back up before upgrading; stop the backend, retain the SQLite file and its salt (and retain keys separately), or use a PostgreSQL backup. Update source, run setup/migrate/doctor, then restart. Alembic owns migrations. JSON/PDF exports are plaintext recovery artifacts, not an automatic database restore/import feature. Do not downgrade or replace the original database to bypass a failed migration. Docker `down` preserves volumes; use `--volumes` only to intentionally delete a disposable store. Publishing, signing, hosted CI, authenticated server deployment and live Codex container login require their own validation and are not implied by local checks.
# Phase 6 workflows

Phase 6 adds resume import/review, profile fact collection, sourced cover letters, an evaluated prompt playground, DOCX downloads and immutable custom templates. The original blueprint is retained in PROJECT.md; implementation details and acceptance evidence are in IMPLEMENTATION_STATUS.md and docs/design/06-enhancements.md. This remains a local single-owner application.

## Import and review a resume

Open **Import resume**, select a text PDF or DOCX, and choose **Parse locally**. Parsing makes no model call. Expand the extracted text to inspect its source locators. Add candidate records manually, or explicitly request AI extraction after configuring the import extraction task. Review each record, correct missing/ambiguous fields, select parent records from the import or existing library, and accept/reject candidates. **Commit approved facts** writes the approved graph together; invalid/missing parents roll back the whole commit. Duplicate hints do not merge or overwrite existing facts. After commit, use the career library/master editor to assemble a sourced resume.

Limits: 2 MiB file bytes (base64 JSON under the 4 MiB write limit), 30 PDF pages, 256 DOCX archive members/8 MiB expansion, 200,000 extracted characters/500 fragments, ten pending imports, two parsing workers and 15 seconds per parse. Corrupt/password-protected, active/embedded and unsupported documents are rejected. OCR/image-only PDF import and exact reproduction of an uploaded design are unsupported. A busy machine can reach the parser deadline; retry when less busy or simplify the file.

Default uploads are parsed in memory; original bytes are not stored. **Retain encrypted original** is an explicit choice requiring a backend `APP_UPLOAD_KEY`, encoded as base64 of 32 random bytes. `APP_ENCRYPTION_KEY` is accepted as a fallback. Keep this key outside the database and out of model processes. Retained bytes are AES-GCM encrypted in the private database, not exposed as public static files; losing/changing the key prevents recovery. Original download/deletion is owner/passcode checked. Discard clears original bytes and staged text. Complete JSON/ZIP export includes encrypted retained originals with base64 envelopes; it does not export keys. Downloaded originals and exports are outside delete-all's control. Extracted text/metadata follow the existing optional database/field encryption settings.

## Strengthen profile facts and write cover letters

**Strengthen profile** asks questions about an active experience, project or achievement. Select the source, inspect context, request questions, then provide your own answers. Skip/unknown and qualitative answers are supported. **Prepare factual edit** appends only supplied answers; review the wording/optional metric fields and explicitly confirm. Questions do not change facts, and confirmation is user-supplied evidence, not independent verification. If the source or an active parent changed, start a refreshed review. Existing resumes stay immutable.

**Cover letters** requires a saved job analysis, selected active career sources and user-confirmed author/recipient fields. Configure cover-letter and verification models, generate paragraphs, inspect source/verification findings, and keep/reject/edit paragraphs before saving. Unsupported AI text cannot be accepted directly; explicit sourced edits have user origin. Letters have append-only versions, manual editing, restore, actual PDF preview and PDF/DOCX downloads. An application links to the exact submitted letter version, so later editing never changes that submission. Cancellation/restart and privacy changes stop pending work or mark it interrupted; stale responses cannot create saved results. Historical exports retain saved wording after source retirement. Word limits apply to generated career paragraphs (100–600, default 400); actual PDFs warn on more than one page.

Clicking **Use Codex for AI tasks** explicitly configures the six tailoring tasks plus import extraction, profile questions and cover letters after the existing consent action. Existing settings are not migrated silently; task assignments can also be configured individually. Only ai invokes providers. Codex uses the native CLI's ChatGPT login and its own sampling/output behavior; a configured `default` is not a pinned resolved model. The stock container still does not include CLI/login credentials.

## Prompt versions and synthetic playground

**Prompt playground** displays packaged prompts read-only and saves immutable preference versions. Supported customization is a task with plain/formal/concise tone and clarity/impact/technical focus. Guardrails, schema, source authority and verification cannot be edited. Saving/forking does not activate a version.

Evaluation compares captured baseline/candidate configurations using three synthetic cases: two different explicit metrics and an instruction-injection case, with applicable schema/source checks. It never reads the career database. Results are retained privately and included in workspace export/delete. Activation requires a passing report for the exact task/base/preference and current task/verifier configuration, plus an expected-active-version check. Failed evaluations remain visible. Select a preserved version and evaluate/activate it to roll back, or use **Reset task to packaged prompt**. Changed base prompts require a new fork/evaluation. Existing runs retain captured provenance. Passing this small corpus is not proof of all model configurations or arbitrary semantic truth.

Run fresh native Codex acceptance with `python scripts/tasks.py phase6-eval --output .validation/phase6-codex.json`. Optional `--models MODEL ...` and `--tasks TASK ...` select configurations/tasks. The command creates/discards synthetic stores, never opens personal records and preserves failed output reports. Phase 6 prompt v1 remains packaged; v2 is active. Use ordinary `ai-eval`/`generation-eval` as well when changing their existing task prompts.

## Editable DOCX and custom templates

**Resume history & ATS** downloads the selected immutable resume version as DOCX. Cover-letter versions also provide DOCX. The exporter uses semantic headings/paragraphs, real bullets, links, stored facts, Unicode and bundled Noto fonts. It excludes source IDs, prompts, rejected output and secret metadata. DOCX remains editable; pagination depends on the word processor, and PDF page counts do not establish Word layout. Supported/verified editors and platforms are recorded in IMPLEMENTATION_STATUS.md; do not infer Microsoft Word compatibility from a LibreOffice-only check.

**Custom templates** copies Classic/Modern, edits bounded presentation, imports a safe HTML/CSS subset, previews actual synthetic PDFs and saves immutable revisions. Choose a revision in the master editor. Editing/retiring a template preserves old resumes' saved template and encrypted asset snapshots. A custom template is not unconditionally ATS-safe: inspect its measured PDF, reading order and ATS findings before use.

HTML is limited to 16,000 characters and exactly one `{{header}}` and `{{sections}}` placeholder. Inert wrappers are main/div/section/header/footer/p/span, with simple classes; img must use a selected owner asset and alt text. Literal career text, unknown placeholders, scripts, handlers, unsafe attributes, executable template expressions and remote/file URLs are refused. CSS is limited to 4,000 characters; supported selectors are main/header/section/article/h1/h2/p/.contact/.facts/.text/.bullet/img. Allowed declarations are hex colors, left/center alignment, weight 400/600/700, font size 9–24 pt, vertical margin/padding 0–15 mm and width 0–170 mm. Imports/URLs, absolute positioning and unsupported syntax are rejected. Template styles keep the existing body font 9–14 pt and margin 10–30 mm bounds; custom contrast must be at least 4.5:1 on the checked background. These checks do not certify accessibility or every combination of inherited styles.

Local assets are sanitized non-interlaced RGB/RGBA PNGs only, up to 256 KiB/1024 pixels per side, four per template and 100 per owner library. CRC/decompressed-size/filter checks remove metadata and reject animation/unsupported encoding. Assets require the private upload key and never fetch remote resources. Complete export/delete covers template revisions and assets. Style-only templates with canonical placeholders export to DOCX; custom HTML/CSS/assets receive an explicit DOCX refusal so arbitrary design fidelity is not implied.

Follow-up dates persist across restart and appear in the application's **Upcoming & overdue follow-ups** view using the device's local calendar. The app does not send email/SMS/push or deliver reminders while closed. Server authentication, OCR, automatic encrypted backups and the section 7 differentiators remain future work.
