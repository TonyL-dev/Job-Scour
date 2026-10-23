# Repository instructions

Read PROJECT.md, IMPLEMENTATION_STATUS.md, ARCHITECTURE.md, and DECISIONS.md before making changes. The user's current request takes precedence over the historical design-only handoff in PROJECT.md. Implement roadmap phases in order. Phase 0 scaffolding exists; do not claim later product features exist.

- Keep backend domains separate. Routers handle HTTP, services hold business logic, repositories alone query databases. Shared infrastructure may configure engines/session dependencies; Alembic owns schema changes.
- Only the ai module may call LLM endpoints. Never send career data externally without explicit user configuration/consent. No telemetry or CDN assets.
- Separate content and presentation. AI output must have owner-valid source references; employers, titles, and dates come from stored facts. Preserve immutable versions and locks when those features are built.
- Run `python scripts/tasks.py check` for relevant foundation changes. Regenerate API artifacts with `python scripts/tasks.py api` when contracts change. Report checks accurately; Docker and hosted CI must be verified in their own environments.
- Use Python 3.12+ and Node 24/pnpm 11.19.0. Dependencies are locked. Do not hand-edit generated API types.
- Phase 1 implements career records and manual master resumes. Phase 2 implements AI settings/gateway, prompt evaluation, job analysis, and embedding/keyword matching. The full future entity catalogue remains in docs/design/01-foundations.md; resume generation, ATS scoring, and tracker domains remain future phases.
- Before ending every session, update or create AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md, as required at the bottom of PROJECT.md. Record meaningful changes and unresolved checks without overwriting the original blueprint.

Session 2026-10-06: repository initialized and foundations implemented. No commits, remotes, or publication were requested.

Validation evidence: native check suite and browser smoke passed; Python 3.12 and isolated PostgreSQL 18 compatibility verified. Docker and hosted CI remain unverified. `.validation/` contains ignored local evidence and test environments, not production data or product source.

Session 2026-10-06, Phase 1: all twelve career record/evidence categories, ownership constraints, Resume Document v1, Classic/Modern templates, bundled Noto fonts, Chromium rendering, PDF.js live preview, page counting, manual master editing, gold standard selection, and append-only snapshots are implemented. Run `python scripts/tasks.py renderer-setup` after setup for native PDF checks. Rendering/browser runtime changes require real PDF and browser verification, not mocks alone. All new resume saves require active owner-valid references; historical PDF export renders stored facts even after retirement. Manual edits may change protection flags; future AI patches must respect them. No AI calls occur in Phase 1. Keep the local-mode guard until server authentication exists.

Session-ending files updated: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md. No commits, remote, or publication requested.

Session 2026-10-07, Phase 2: settings, ai, and jobs are separate domains. Endpoint/model settings and assignments, explicit remote HTTPS consent, environment-backed secrets, connectivity/detection, streamed structured output with bounded retries/timeouts/cancellation, file-seeded immutable prompts, synthetic evaluation fixtures/CLI, cached job analyses, and sourced career matching are implemented. Only ai sends model requests. Disabling/changing an endpoint blocks subsequent calls from stale in-flight configurations. Server guards remain enabled. Embedding similarity is relevance, never proof of a skill; gaps must not become career facts.

Maintenance: regenerate contracts after schema changes, bump prompt files/versions deliberately, run the ordinary check suite, and separately run the live evaluation command against at least two local models. Mock model responses do not prove real-model compatibility. Record failed model configurations and hardware limits accurately. Evaluation reads synthetic fixtures, never the career database. Final Phase 2 native checks passed (17 backend/12 frontend tests, strict types, generated drift and build); Python 3.12 and PostgreSQL 18 compatibility passed. Repeated real Qwen2.5/Devstral analysis and actual native Nomic retrieval/browser workflows were verified; retain the small-model quality failures and distinguish original runs, retests, and final artifact replay. See IMPLEMENTATION_STATUS.md for precise evidence. Docker and hosted CI remain unverified. No commits, remotes, or publication were requested.

Prompt v2 is active, v1 remains preserved. `ai/service.py` owns extraction and exact-quote repair; narrow deterministic posting metadata parsing is versioned in cache fingerprints. Repositories return detached analysis DTOs, so session refreshes cannot cause lazy SQL reads in services. Matching rechecks the active career snapshot before persisting. Model tests/task decisions belong in services; routers only adapt HTTP. App logging excludes prompt/response content; model-server logging is independently configured.


Session 2026-10-07, Phase 3: generation/review is implemented in resumes, with all model calls still confined to ai. Persisted owner-scoped generation runs and suggestion snapshots support a bounded local worker, reconnectable SSE, explicit cancellation, partial checkpoints, and interrupted-run recovery. Only accepted supported AI suggestions (or user-confirmed sourced edits) save a separate tailored document; the master and old snapshots remain unchanged. Review revisions prevent stale decisions. Career snapshot/source checks run again before applying suggestions. Locks live in content snapshots; review lock changes protect the next regeneration. Partial item/section scope and presets must never modify protected content.

Generation prompt v1 is preserved; v2 clarifies source authority and aliases for the verifier. Numbers, source membership and conservative claim vocabulary are checked in code before separate temperature-zero verification. Rejection is deliberately conservative and is not a guarantee of arbitrary semantic truth. Keep actual rejected model outputs and distinguish mocked controls/browser fixtures from live synthetic model evaluations. Use `python scripts/tasks.py generation-eval --models MODEL ...` for live Phase 3 evaluation in disposable synthetic databases. Model evaluation never opens the user's career database.

Fitting uses a bounded initial relevance budget, actual Chromium PDF page measurements, unlocked bullet removal, older fact-group removal, verified condensation, and optional consented spacing/font adjustments. Protected overflow and sparse final pages produce explicit warnings; the sparse-page check uses extracted text length and requires visual inspection. ATS/history/tracker/server authentication/privacy controls remain Phase 4 or later. Local worker deployment is one backend process; Redis/server workers are future authenticated-server work.

Generation prompts v1 and v2 remain preserved; v3 is active. Factual source context `facts.v1` excludes importance/review metadata; claim checks 3.2 normalize exact decimal values/units and preserve negative signs. Stored metric fields are authoritative evidence even when prose omits the number. Accepted AI proposals are checked again against current factual evidence, including older runs. Summary uses only visible selected content and can cite protected education/non-retrieval records. Fit presets keep the saved page target at two or fewer pages.

## Codex provider change — 2026-10-07

The user explicitly replaced local-LLM tooling with Codex during Phase 3. Codex is now the default setup and evaluation provider. All six chat tasks use the installed native CLI's ChatGPT login. Only ai/codex.py launches inference. Never scrape CLI OAuth credentials or forward application/API secrets. Consent is explicit in AI settings; https://chatgpt.com/codex is a fixed provider marker, not an arbitrary HTTP destination. Calls use a temporary working directory, schema output, ephemeral sessions, ignored user config/rules, read-only sandbox, disabled shell/apps/plugins/web/memories/subagents, no telemetry exporters, byte/time bounds and process-tree cancellation. Update older CLI releases instead of bypassing these controls.

Codex controls sampling and output tokens. Do not claim Codex verification runs at temperature zero or that profile output tokens enforce a CLI cap. Provenance records codex-managed sampling and the configured model; default follows the CLI default and is not a pinned resolved model. Codex cannot receive embedding assignments; Jobs/Generate/API defaults use keyword matching. Existing optional HTTP providers and the original blueprint remain preserved. Docker and hosted CI remain unverified. No commits, remotes or publication were requested. All six required session documents are updated; final evidence is in IMPLEMENTATION_STATUS.md.

Session 2026-10-07, verification guidance: inspected Compose, Dockerfiles and GitHub workflow. Docker is absent from PATH and no Git remote is configured. Do not mark Docker/hosted CI verified from instructions alone. The stock backend image lacks Codex CLI/login; its smoke checks do not establish live Codex container compatibility. No commit/push/install was authorized or performed.


Session 2026-10-07, Phase 4: ats and applications are separate router/service/repository domains. Deterministic ATS reports reference exact immutable resume versions and saved analyses, check actual PDF extraction/reading order/pages, and expose heuristic findings with editor/source links. Never describe scores as a vendor verdict or insert a gap as career evidence. Resume history/compare/restore/duplicate and autosave are implemented. Manual master/tailored text edits have user origin; retained AI text must match the saved item and pass current evidence checks. Restore copies historical facts without mutating older snapshots. Generation runs now retain the exact saved version so later edits cannot change their original download or commit replay.

Privacy implements local passcode cookies, bounded unlock attempts, restart/session/inactivity locks, complete JSON and JSON/PDF ZIP export, and typed delete-all. Workspace epochs revoke old sessions, pending commits and SSE readers on lock/delete; preserve that barrier when adding workers or repositories. Deletion must cancel local generation and must not allow in-flight analysis to repopulate caches. It retains the local passcode and does not erase downloads, backups or provider copies. Server guards remain enabled.

Optional SQLCipher encrypts the full SQLite file using an Argon2id-derived backend passphrase and a paired .salt sidecar. Offline conversion creates a new verified file and preserves the source. Optional AES-GCM protects descriptive text/JSON on SQLite/PostgreSQL, with a blind skill index; IDs/dates/numbers/status/configuration metadata are still queryable unless full database encryption is enabled. Keys stay in backend process environment and out of logs/exports/model children. Startup must fail closed on missing/wrong keys, tampering and incomplete field conversion. The current SQLCipher Windows wheel crashes with optional cipher_memory_security enabled; retain the tested default without claiming memory hardening.

Use python scripts/tasks.py check, api after contracts, audit, and e2e. E2E uses disposable SQLCipher databases, actual Chromium/PDF.js and synthetic model responses for Flows A/D/E/F; it never opens personal data or calls Codex. Final validation and environment limits are recorded in IMPLEMENTATION_STATUS.md. Update all six session files and preserve the blueprint. No commit, remote or publication was requested.


Phase 4 final verification — 2026-10-07: native check passed (43 backend/17 frontend tests, strict lint/types/contracts/build); final Playwright A/D/E/F passed with actual PDF/SQLCipher and synthetic model responses; Python 3.12 focused tests and PostgreSQL 18 workflows passed; clean dependency audits passed. Docker became available and final isolated builds/health/Alembic/Linux Phase 4 tests/Nginx/PostgreSQL 17 PDF/ATS/tracker/privacy smoke passed. Hosted CI and live Codex container account authentication remain unverified. Validation services/volumes and the started native cluster were stopped/removed; unrelated stacks and the personal store were preserved. All six session files are updated, PROJECT.md's blueprint is retained, and no commit/remote/publication was requested or performed.


## Phase 5 hardening — 2026-10-07

Phase 5 adds bounded private PDF reuse, render/AI admission errors, 4 MiB ASGI write limits, API privacy headers and production CSP, keyboard skip/route focus, query retry/empty states, route recovery, accessible PDF/board scrolling, and cache clearing on polled workspace locks. Preserve workspace epoch barriers and source checks before any cached render. The cache supports only the existing single-owner process; future server work must scope it by owner. Lock/passcode/delete/shutdown invalidate both entries and late insertion. Expired entries are removed at the next lookup.

Use check, audit, e2e and fresh-install for release changes. Fresh installation uses an explicit source allowlist and new dependency environments; it never copies personal stores/environment files/credentials or calls models. doctor only checks migrated storage and a synthetic PDF. Node 24.x and pnpm 11.19.0 are enforced. Retain the blueprint and all six session documents. Section 8 coverage/residual risks are in docs/release/security-review.md; server authentication/importers/automatic encrypted backups remain future enhancements. No commits, remotes or publication are requested. Final validation follows in IMPLEMENTATION_STATUS.md.


Phase 5 final acceptance — 2026-10-07: native check passed (48 backend/20 frontend tests, strict types/lint/drift/build), final A/D/E/F passed, audits found no known vulnerabilities, isolated README-only native installation/outage/restart passed, and no-cache Linux builds plus final healthy Nginx/PostgreSQL/PDF/privacy browser workflow and 13 Linux focused tests passed. Production .mjs MIME was corrected after a real PDF.js failure; API proxy errors also receive no-store. Source-only Docker contexts exclude local data/settings/evidence. Hosted CI, physical clean-OS certification and live Codex container login remain unverified. All six session documents and the original blueprint are maintained; final rules were reread. Owned validation stores/services/volumes are removed, unrelated services/personal data preserved, and no model calls, commits, remotes or publication occurred. Exact evidence is in IMPLEMENTATION_STATUS.md.


## Roadmap clarification - 2026-10-08

Roadmap clarification: section 9 defines Phase 6+ as the section 7 high-value enhancements followed by differentiators. This informational review authorizes no implementation; preserve existing completed features and verification limits.


## Phase 6 acceptance planning - 2026-10-08

PROJECT.md now contains the detailed Phase 6 acceptance checklist. Treat 6A import, 6B profile helper, 6C cover letters, 6D prompt playground, 6E DOCX and 6F custom templates as ordered planning milestones, followed by 6G regression/release gates. No feature implementation is authorized or claimed by this documentation task.


## Phase 6 implementation progress - 2026-10-08

Phase 6 implementation is active. Ordered milestones 6A-6F now have API/UI implementations and explicit migrations through 606f_templates; acceptance is still in progress. Preserve strict closed model extraction schemas, transactional parent remapping, user-confirmed profile facts, immutable letter/template versions, evaluated prompt activation, mandatory private asset encryption and privacy epochs. No completion or fresh model/container compatibility is yet claimed.

## Phase 6 final acceptance — 2026-10-08

Phase 6 checklist 6A-6G is implemented and accepted within its documented local scope. Final check passed 81 backend/20 frontend tests, lint/strict types/generated drift/build; audits passed; real PDF/SQLCipher A/D/E/F/6A-6F browser and fresh-install/outage/restart passed. Python 3.12/Linux passed 28 Phase 6 cases plus the final six-case profile suite. Fresh native Codex v2 baseline/candidate evaluation passed all three new tasks on two metrics and an injection case; original v1 failures remain preserved. Codex uses explicit consent, nine assigned chat tasks only after setup, provider-managed sampling and configured model default, not a resolved pinned model.

Keep import parsing durable and cancellation behind workspace epochs; encrypt opt-in originals and all local PNG assets with backend-only keys. Profile AI asks questions, while confirmed facts remain user supplied. Cover letters and exact application links use immutable versions/current evidence checks. Prompt preference activation needs the exact passing report/configuration and optimistic revision. Template saves measure actual synthetic PDFs and record heuristic findings; historical snapshots embed immutable presentation/assets. DOCX semantic export refuses unsupported custom mappings. Complete export/delete includes every new entity/run/version/file; downloaded/provider copies remain external.

Actual Linux LibreOffice Writer 25.2.3 DOCX visual QA and fresh production Nginx/PostgreSQL 17 PDF.js/PDF/DOCX workflows passed. Hosted CI, physical clean-OS certification, native Microsoft Word and live Codex container login remain unverified. OCR, arbitrary layout fidelity, external reminders, automatic encrypted backups and section 7 differentiators remain later scope. All six session documents are updated; preserve the blueprint and precise failure/retest evidence in IMPLEMENTATION_STATUS.md. No personal store changes, commits, remotes or publication were requested/performed.

The original RULES BEFORE ENDING A SESSION block was reread before conclusion. Owned Phase 6 validation services/network/volumes are removed; unrelated stacks and personal data are preserved. Ignored synthetic evidence remains available.


Run-guidance session — 2026-10-08: docs/run-windows.md records native setup/start/doctor, explicit Codex consent, optional persistent private-file keys and restart/backup guidance. Keep nine task assignments and native codex.exe requirements accurate. No app services or model calls were started; no personal database was read/migrated. All six ending files updated; blueprint preserved.


Native launch session — 2026-10-08: user authorized installation/startup. Existing SQLite store backed up before migration; locked setup, Chromium, migration and doctor passed. Native backend/frontend intentionally remain running on loopback 8010/5180, preserving unrelated Docker services on 8000/5173. Persistent private-file key created in Windows user environment, never printed. Codex signed in; AI configuration remains off pending explicit sharing consent. Real browser/PDF.js verification passed without AI or saved records. All six ending files updated; blueprint preserved.

## Hosting budget planning — 2026-10-09

User requested an implementation plan for hosting at no cost or at most $1/month. docs/hosting-under-one-dollar.md proposes owner-only private access on existing hardware, a separate public browser-first edition, and a conditional Oracle Always Free VM alternative. Audience is pending clarification; no route selected. Preserve local/server guards, ai-only calls, explicit consent, workspace epochs and accepted local feature scope. No code, deployment, personal data, services, models, accounts, commits, remotes or publication changed. Hosting prices were checked from official sources; compatibility remains untested. All six ending documents updated; blueprint preserved.

## Security audit — 2026-10-09

Detailed report: docs/release/security-audit-2026-10-09.md. Current native listeners remain loopback; read-only status showed no passcode/field/full-database encryption, and dev UI lacks production headers. Synthetic audit reproduced automatic session expiry failing to advance workspace epoch: existing generation SSE and bound sessions can continue while new requests receive 423. Explicit lock/delete barriers remain; fix expiry before private remote access and add held-stream/commit tests. Chromium launch omits sandbox enablement; parser -I is not OS containment. No RCE/PC takeover demonstrated; public exposure remains unsupported. Full check passed 81 backend/20 frontend tests and all gates; audit retest passed with certifi TLS after initial temporary pip preparation failure. No code/privacy/data/service/model/account/remote/publication changes. All six ending files updated; blueprint preserved.


## Node PATH troubleshooting — 2026-10-13

User reported node unrecognized in an outside terminal. Codex process resolves bundled Node v24.19.0 at C:\Users\coolg\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe; this does not establish the outside terminal PATH. Guidance uses a temporary PowerShell PATH prepend and optional user PATH configuration. Bundled pnpm currently reports 11.25.0, whereas this repository requires 11.19.0; do not assume bundled pnpm meets the prerequisite. No runtime configuration, installations, services, personal data or model calls changed. Product checks were not rerun for this guidance-only session; previous environment limits remain. All six session documents maintained; original blueprint preserved.


Node follow-up — 2026-10-13: clarified bundled app runtime versus an independently installed Windows development runtime. Prior cache PATH advice is a temporary workaround; recommend standalone Node 24.x with installer PATH setup for regular outside-terminal use. No install/PATH mutation performed. OpenAI Docs skill consulted; bundle location is established by local dependency metadata, not a public cache stability guarantee.



## Reusable coding practices - 2026-10-13

Reusable standards are in docs/coding-practices/FRONTEND_CODING_PRACTICES.md and BACKEND_CODING_PRACTICES.md; the directory README explains adoption. They are guidance for new projects, not a runtime refactor or proof that every recommendation is implemented here. Existing repository instructions and pinned runtimes remain authoritative. Preserve the known expiry-revocation and native containment findings; no remediation was performed.


pnpm version guidance — 2026-10-13: user reported setup rejecting pnpm 12.11.2. Source inspection confirms scripts/tasks.py enforces exactly 11.19.0 and frontend/package.json pins the same release. Advise installing pnpm@11.19.0, verifying resolution/version, then rerunning setup; do not bypass the guard or change lockfiles to accommodate an unvalidated major version. If resolution remains wrong, inspect where.exe pnpm/Get-Command pnpm -All for PATH precedence. No installation, PATH mutation, application code/dependency change, service/data access or model call performed. Product checks not rerun for guidance-only work. Original ending rules reread, all six session documents updated and blueprint preserved.


pnpm pin rationale — 2026-10-13: 11.19.0 is the locked and validated installation/build baseline. Repository evidence establishes reproducibility and exact-version enforcement, not a demonstrated incompatibility or known defect in 12.11.2. A pnpm 12 upgrade would require an intentional toolchain/lockfile review and fresh checks/build/install evidence; none was requested or performed. No runtime/dependency/PATH/service/data changes or product tests. All six session documents maintained; original blueprint and ending rules preserved.


pnpm home guidance — 2026-10-13: inspected the user-specified Local/pnpm/bin launchers read-only; pnpm.cmd targets a native executable under Local/pnpm/global/v11, with sibling pnpx/pn launchers. npm global uninstall alone may not remove this separate installation. Verified installed self-update --help and official pnpm.io/cli/self-update; recommend explicit self-update 11.19.0 outside the project then verify, rather than deleting the pnpm home/store or changing project pins. No uninstall/update/PATH mutation executed; all six ending documents updated, rules reread and blueprint preserved.


Codex PATH diagnosis — 2026-10-13: user reported codex unrecognized in outside PowerShell while using port 5173. Read-only listeners confirm this is now native Vite/python on 5173/8000, not the old Docker stack; Docker daemon is unavailable. Codex process resolves native executable C:\Users\coolg\AppData\Local\OpenAI\Codex\bin\2e5e00daee91c61d\codex.exe and login status reports ChatGPT authentication. Advise setting STONKS_CODEX_CLI to that executable in the backend terminal, checking login status via full path and restarting backend; explicit in-app remote consent still required. Versioned app path can change after updates. No installation, PATH/environment mutation, service restart, data/AI-settings change or model call performed. Product tests not rerun for guidance. All six ending documents updated and original rules/blueprint preserved.


GitHub commit guidance - 2026-10-13: read-only Git inspection confirms an initialized repository on master with no commits and no remote. Explained initial local commit, empty GitHub repository, HTTPS remote and first push, with staged-file review and existing ignore rules. No staging, commit, branch/remote mutation, account change or publication executed. Product tests not rerun for guidance-only work; earlier validation limits remain. Original ending rules reread; all six session documents updated and blueprint preserved.


Pre-publication privacy review - 2026-10-13: inspected all 239 Git-eligible source/documentation files with credential/contact/path patterns and reviewed flagged examples without reading the personal database or environment credential contents. No recognized live credential signatures or real contact/resume records were identified; this bounded review is not an exhaustive secret-scan guarantee. Six root session documents contain the Windows username/local executable paths; docs/run-windows.md includes the local project path. The security audit and session history disclose point-in-time privacy settings and unresolved vulnerabilities. Email matches are synthetic examples; Compose includes a documented local development database password. Existing .gitignore excludes the actual backend/resume-tailor.db, .env files and .validation, but does not broadly exclude arbitrary exports/backups, alternate SQLite suffixes or SQLCipher salt sidecars. Recommend private GitHub visibility and redacting machine-specific details before public release. No redaction, ignore-rule change, staging, commit, remote, publication, service/data/model change or product test performed. Original ending rules/blueprint preserved; all six session documents updated.

## Docker startup recovery — 2026-10-15

User reported `docker compose up --build --wait` failing on the backend dependency. Actual backend logs showed psycopg unable to resolve `postgres` during Alembic startup; PostgreSQL and Redis were healthy. Recreated only backend/frontend using `docker compose up -d --force-recreate --wait backend frontend`, preserving existing database/Redis volumes and unrelated stacks. All four services became healthy; frontend HTTP 200 and `/api/health` status ok/database ready were verified. Recovery establishes successful current startup, not the underlying Docker DNS failure mechanism or full product/container AI compatibility. No application/configuration/dependency change, volume deletion, manual career-data access, model call, commit or publication. Full product checks were not rerun for operational recovery. All six session documents updated; original blueprint and prior validation limits preserved; original ending rules reread.

README Docker troubleshooting — 2026-10-15: documented backend dependency failure diagnosis with Compose status/logs and the verified backend/frontend force-recreation recovery for PostgreSQL hostname resolution failure. Explicitly preserves database/Redis volumes, retains standard build/start instructions, and distinguishes other startup errors. Documentation-only follow-up; inspected README placement/commands against the preceding successful recovery. No new service/data/model changes or product tests. All six session documents maintained; original ending rules and blueprint preserved.


## Saved resume diagnosis — 2026-10-15

Read-only inspection found the running Docker frontend/backend on loopback 5173/8000 using PostgreSQL in resume-tailor_postgres_data, with zero resume documents/versions. The separate native backend/resume-tailor.db contains one master and 76 immutable saved versions; latest saved timestamp is 2026-10-14 02:49:05 UTC (October 13, 10:49 p.m. America/Toronto). Counts and timestamps only were inspected, not resume content. Native services are not listening on 5180/8010. The empty Docker workspace does not establish deletion: native and Compose stores are separate. Resume studio also opens a blank new draft by default; use Saved resumes after opening the correct installation. Autosave begins only after the first explicit save. Existing alternate-port restart instructions are in docs/run-windows.md. No services, databases, settings, model calls or dependencies changed; no migration/transfer/commit/publication performed. Product checks were not rerun for this read-only diagnosis. Original ending rules reread and blueprint preserved; all six session documents updated.


## Native saved-work restart — 2026-10-15

User authorized starting the native installation to access saved work. Created a consistent SQLite backup in ignored .validation/native-restart-20261015/resume-tailor-before-start.db before launch. Native backend/frontend now run on loopback 8010/5180 with explicit existing SQLite path and frontend proxy; Docker services/volumes remain untouched. Proxied health reports database ready, frontend HTTP 200, and GET /api/resumes returns the existing master at version 76. Opened its direct editor URL in the Codex browser panel. Services intentionally remain running; no migrations, data transfer, resume edits or model calls performed. Full product/browser/PDF checks were not rerun for startup. A combined hidden-process launch command was blocked by automatic policy review; backup and ordinary task-runner launches succeeded separately. Original ending rules were reread in this conversation; all six session documents updated and blueprint preserved.


## README saved-work restart — 2026-10-15

README now puts the existing Windows native restart sequence before Docker: explicit existing SQLite path with missing-file check, loopback 8010 backend, 5180 frontend/proxy, reuse of the existing private-upload key, and Saved resumes selection/direct-URL bookmarking. It distinguishes first-time default-port setup from routine restarts and explains separate Docker persistence, first-save/autosave behavior and backups. PowerShell blocks parsed successfully; resolved database URL matches the existing store and save labels were checked against ResumePage.tsx. Documentation only: no application/data/service/dependency/model changes, no product-suite rerun, no commit/publication. All six ending documents updated; original ending rules and blueprint preserved.


## Developer onboarding handbook — 2026-10-15

Current source-linked onboarding is in docs/developer/README.md, BACKEND.md and FRONTEND.md; keep it aligned with actual code when changing boundaries. PROJECT_ARCHITECTURE_TEMPLATE.md is a fill-in future-project document, used with the existing coding-practice guides. It does not authorize refactoring or replace current repository/runtime rules. Preserve documented query-key/cancellation inconsistencies and unresolved expiry/containment findings until explicitly remediated.

## Structured master experience — 2026-10-15

Resume Studio supports company/title/start/end-or-present entry, an optional one-sentence summary and individual duty bullets. Source details use existing career records; new summary/duties are saved as description evidence before referenced draft items are added. This library save is separate from resume persistence and survives draft discard. Text edits in a resume do not change library evidence. The additive schema-v1 `experience_summary` flag defaults false for historical items; true permits one line/500 characters with conservative sentence detection. Preserve this role in generation/review, reject invalid summary proposals, and render summaries as paragraphs in HTML/PDF/DOCX. All locks, source checks, immutable versions and privacy barriers still apply. No database migration or personal-data operation is needed. Validation evidence follows in IMPLEMENTATION_STATUS.md; prior security/environment limits remain.

Structured experience browser acceptance — 2026-10-15: actual PDF.js/HTML entry/detail-edit/autosave/reload passed in the isolated SQLCipher harness with existing A/D/E/F/6A–6F workflows and no browser errors/external requests. Use accessible textbox roles for saved textarea assertions. No personal-store migration/edit, deployment or live model call occurred; final combined check evidence is in IMPLEMENTATION_STATUS.md. Original blueprint and prior environment/security limitations remain.

Structured experience final validation — 2026-10-15: check passed 86 backend/23 frontend tests, lint/strict types/generated drift/build; audits and actual SQLCipher/Chromium/PDF.js browser workflows passed. Details and corrected intermediate failures are in IMPLEMENTATION_STATUS.md. No database migration, personal data/service change, live inference, dependency change or deployment. Restart native backend/refresh frontend or rebuild Docker to load the updated contract. All six session files updated; original ending rules reread and blueprint preserved.


## Saved-work port correction — 2026-10-16

User reported missing old template on 5173. Read-only counts found native SQLite has one master/80 versions and zero custom-template records/revisions/assets; Docker has zero resumes/custom templates. A separate custom template was not recovered or claimed. Created/preserved ignored .validation/native-restart-20261016/before-start.db via SQLite backup. Stopped only Compose frontend/backend (volumes and PostgreSQL/Redis preserved), then launched native backend/frontend on loopback 8000/5173 against the explicit existing SQLite path. Proxied health reports ready, UI HTTP 200, resume API returns version 80, custom-template API returns empty. Requested opening the saved master directly. README restart commands now use 5173/8000 and explain stopping Docker app services before native startup; run-windows guidance supersedes old alternate-port history. No migration, resume edit, model call, dependency change, commit or publication. Product suite and real PDF/browser rendering were not rerun; operational HTTP checks only. All six session documents updated, original ending rules reread and blueprint preserved.


## Experience editor visibility — 2026-10-16

Inspected the actual native resume editor in the in-app browser. The structured editor is present but collapsed behind Add experience. Opened that form and verified Company, Title, Start date, End date, Present, summary and duty controls in the live accessibility tree; screenshot confirms the visible date inputs. No code, resume/library data or settings changed; master remained at version 80. Product tests not rerun for UI navigation. All six ending documents maintained; original blueprint and ending rules preserved.


## Backend learning companion — 2026-10-22

Added docs/developer/BACKEND_READING_LIST.md as a learning companion matching BACKEND.md sections 1-14. It explains prerequisite/search topics, reading goals and study order; no new implementation or dependency requirement is implied.
