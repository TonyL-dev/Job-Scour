# Skills and maintenance notes

## Structured experience maintenance — 2026-10-15

No specialized skill/plugin was needed for this application change. Use `python scripts/tasks.py api` for the additive resume contract and `check` for lint/types/backend/frontend/drift/build. Run formatting from `backend` so its 100-character configuration applies to scripts/tests. `tests/test_experience_editor.py` covers both real Chromium templates, PDF content, DOCX paragraph/bullet semantics, immutable source-fact history, legacy defaults and synthetic generation acceptance/rejection. `scripts/e2e.py` additionally exercises structured entry, PDF.js/HTML preview, source date edits, autosave and reload in the disposable SQLCipher workspace. Never run this browser validation against personal data or call live models for these deterministic changes. Existing real-model/platform limitations remain; library source save and resume save are distinct operations.

Updated 2026-10-07, Phase 2. No specialized Codex skill was needed for this repository implementation, and no new reusable skill or plugin was installed.

## Repository workflows

- Setup: `python scripts/tasks.py setup`; install hooks with `python scripts/tasks.py hooks`.
- Schema migrations: `python scripts/tasks.py migrate`; create explicit Alembic revisions for later model changes, and test upgrade/downgrade.
- Contract changes: `python scripts/tasks.py api`; generated schema/types are not hand-edited.
- Validation: `python scripts/tasks.py check`; dependency advisory checks: `python scripts/tasks.py audit`.
- Native development: run the backend and frontend tasks in separate terminals. Container development: `docker compose up --build --wait`.
- PDF runtime setup: `python scripts/tasks.py renderer-setup`; Linux requires Playwright OS dependencies as described in README. Matching Chromium is installed separately from pip dependencies; the Dockerfile and CI include installation.
- Rendering checks: backend integration tests use real Chromium/PDF parsing. Test both built-in templates, font loading, actual A4/page counts, drawing-command/text parity, source facts, escaping, and multipage overflow. Verify the bundled PDF.js worker/pages in a real browser after rendering changes.
- Session completion: update all six mandated root documentation files, preserve the PROJECT.md blueprint, and distinguish actual native evidence from Docker/hosted CI.

## This machine

Python 3.14.8 and bundled Node 24.19.0 were available. The bundled pnpm launcher is at `C:/Users/coolg/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/fallback/pnpm.cmd`; place its directory on PATH when using the task runner in this Codex environment. Regular installations can use any pnpm 11.19.0 launcher on PATH. Docker is unavailable here.

Bundled Python 3.12.14 was used for a clean compatibility check in ignored `.validation/python312`. Native PostgreSQL 18 binaries were used for an isolated test cluster in `.validation/postgres`, bound only to 127.0.0.1:54329 and stopped afterward. This is not the application's normal database; follow README for normal startup.

The machine had a stale TLS certificate-bundle environment path. Dependency installation/auditing used pip's bundled certificate file for the command process only, keeping TLS verification enabled. Do not hard-code that machine-specific environment adjustment into application settings or disable certificate verification.

Phase 1 native evidence in ignored `.validation/`: temporary SQLite stores with synthetic data, PostgreSQL 18 cluster on 127.0.0.1:54330, Python 3.12 locked dependency environment, browser scripts/screenshots, and a sample PDF. PDF preview screenshots were visually inspected on desktop and mobile. The new fonts are product assets in app/rendering/fonts with OFL license files; `.validation/` is never product source. Test processes/clusters should be stopped after validation.

## Phase 2 maintenance — 2026-10-07

No reusable Codex skill/plugin was installed. AI implementation uses the existing locked HTTPX dependency, now explicitly declared as a runtime dependency. Domain/schema changes require migrations plus `python scripts/tasks.py api` and `check`.

Start your local OpenAI-compatible server and load an instruct model plus an embedding model. In **AI settings**, detect/save an endpoint, list models, create profiles with the actual loaded context, test them, and assign job_analysis/embeddings. Chat tests check structured JSON; a profile assigned only to embeddings tests vector output. API keys use backend `LLM_*` variables. Remote destinations require HTTPS and explicit consent; disable an endpoint to revoke future calls. Never put keys in frontend variables or URLs.

Run live synthetic evaluation with `python scripts/tasks.py ai-eval --models MODEL_A MODEL_B --context 8192 --max-output 2048 --output ../.validation/phase2-evaluation.json`. Optional `--structured-mode json_schema|json_object|none`, `--cases backend frontend injection`, and `--repeats 2` select configurations. Run models sequentially when hardware cannot keep both loaded. Fixtures are packaged in app/ai/evaluation and never read the career database. The harness exits nonzero for failed/unstable cases. Extend it with provenance/locks/page-fitting checks when Phase 3 is implemented.

Built-in prompts live in app/ai/prompts; add a new explicit version rather than silently changing a released prompt. Prompt digests and output schemas invalidate analysis caches. Embedding content hashes invalidate vectors when source text changes; current source retirement/ownership is rechecked for each new match. No prompt/response logging is enabled.

This machine has 16 GB system RAM and an AMD Radeon RX 7800 XT. Large context/multiple-slot loading caused allocation failures and interfered with cold test-worker startup. Prefer one loaded validation model at a time, one inference slot, and a context that fits hardware. Qwen3.5-9B exhausted a 4096-token budget; that configuration is not validated. Devstral validated with one slot, 8192 loaded context, offload 0.8, temperature 0 and 2048 output tokens. Small Qwen2.5 is schema compatible but has mixed corpus quality; it is not a substitute for evaluation.

The Qwen2.5-1.5B-Instruct Q4_K_M download completed in the daemon despite its interrupted CLI; its 1.12 GB file matches the publisher hash recorded in IMPLEMENTATION_STATUS.md. It remains in the local LM Studio model library, outside product source/dependencies. LM Studio's bundled Nomic loader crashed; the existing llama.cpp 2.41 CPU binary successfully served the same bundled Nomic file at 127.0.0.1:1235 with `--embeddings --pooling mean --ctx-size 2048 --parallel 1 --no-webui`. This was a temporary validation server, not an app dependency or a repair of LM Studio. Final native browser analysis used actual vectors and had no page errors/external requests at desktop/mobile widths.

Extraction and evaluation share `ai/service.py`; v2 prompts preserve v1 and extraction 2.1 adds exact, narrowly parsed posting metadata. Preserve failed reports, document focused retests, and label final output replay separately from fresh live calls. The final check suite passed 17 backend/12 frontend tests, source types/drift/build; Python 3.12 and native PostgreSQL 18 passed. Temporary diagnostics belong under root `.validation/`, outside frontend test discovery, and must not be removed during collection. Stop only validation processes this session started. All six session-ending files were updated; Docker and hosted CI remain unverified.


## Phase 3 maintenance — 2026-10-07

Phase 3 initially required no specialized skill. The user's subsequent Codex-provider change used the openai-docs skill and official non-interactive/configuration documentation. Apply explicit migrations and regenerate contracts with `python scripts/tasks.py api`; do not edit generated schema/types. Run `python scripts/tasks.py check` after domain/contract changes. Keep model calls in ai, database queries in repositories, and router logic limited to HTTP adaptation.

After career/job/master setup, assign ranking, rewriting, summary, verification, and condensing profiles alongside job_analysis (embeddings optional). Use `/generate` for run/review/partial-regeneration workflows. Verification overrides temperature to zero. Remote configuration requires the existing explicit HTTPS consent; career sources are part of generation context. Save review decisions before regenerating. Lock changes affect the next run, while saved tailored PDFs remain immutable.

Live evaluation: `python scripts/tasks.py generation-eval --models MODEL --context 8192 --max-output 2048 --output ../.validation/phase3-evaluation.json`. Optional `--cases ...` and `--structured-mode ...` select cases/configurations. Ten synthetic career/job fixtures run through the actual generation service, verifier, Chromium fitting, and review commit using disposable databases. The report checks supported rewrites, sources, forbidden/gap terms, locks, template identity, two-page output, and review persistence. It exits nonzero on failures; preserving an original sourced master alone is not counted as a successful rewrite. Model outputs are synthetic evidence in ignored `.validation/`, never product assets or personal data.

Generation prompts v1/v2 are packaged under app/ai/prompts. Bump versions deliberately and rerun live evaluation when changing prompts/models. Do not describe a mocked verifier as proof of semantic accuracy. The conservative vocabulary gate can reject valid paraphrases; this is exposed to users. Last-page extracted text length is only a sparse-page warning and does not replace visual PDF QA. Backend restarts retain snapshots and mark interrupted runs failed; one local backend process is supported. Stop validation services/models this session started.

Final prompts: generation v3 active, v1/v2 retained. Factual context `facts.v1` and claim checks 3.2 keep weights/review flags out of numerical evidence and normalize declared metrics exactly. Re-run live generation/verification after changing context or prompts, and label archived-output replay separately from fresh full pipelines. Explicit UTF-8 file reads/writes are required on Windows; a default-codepage write can truncate a Unicode source file on encoding failure.

## Codex setup and maintenance — 2026-10-07

The openai-docs skill was applied for the provider migration. Official references: https://learn.chatgpt.com/docs/non-interactive-mode and https://learn.chatgpt.com/docs/config-file/config-reference. The installed CLI supports ignore-user-config, ephemeral and output-schema and was ChatGPT authenticated. On Windows launch a native .exe, use CREATE_NO_WINDOW, and kill the owned process tree on cancellation. STONKS_CODEX_CLI can specify an absolute executable when PATH lacks it. Do not read or copy CLI token values. Docker needs its own CLI installation/login; native success does not prove container compatibility.

Run migrations, start the app, open AI settings, consent to supplied job/career facts going to OpenAI, then choose Use Codex for AI tasks. This assigns/tests analysis, ranking, rewriting, summary, verification and condensing. No local server is required; leave embeddings unchecked. Codex uses account limits and controls sampling/output length. Profile output tokens reserve input-budget space but do not enforce a CLI token cap. default follows CLI model selection; an explicit supported model pins the requested model.

Both evaluation tasks accept --provider codex (default). Run python scripts/tasks.py generation-eval --provider codex --models default --output ../.validation/phase3-codex.json for synthetic full pipelines or ai-eval for repeated extraction. Local evaluation requires --provider openai_compatible. Fixture commands never open personal databases. Preserve model-specific failures and distinguish fresh pipelines from output replay. Final ordinary checks passed 35 backend/15 frontend tests, strict types, API drift and build. Compatibility/live evidence is in IMPLEMENTATION_STATUS.md. All six session-ending files are updated.

Docker/CI verification guidance — 2026-10-07: use Docker Desktop's Linux container engine, check docker info/compose version, run Compose with an isolated project name, verify readiness through frontend /api/health and run Alembic check inside backend. Exercise synthetic manual resumes/PDF/persistence separately. docker compose down preserves volumes; do not use --volumes on data to retain. GitHub CI triggers on push/pull_request and has checks plus compose-smoke jobs, with no workflow_dispatch or live Codex account tests. Save actual run logs/commit identity before changing verification status.


## Phase 4 maintenance — 2026-10-07

No specialized Codex skill, new skill or plugin was required. ATS/history/applications/privacy follow repository domain boundaries. Run check, regenerate API contracts after schema changes, audit, and python scripts/tasks.py e2e. Backend Ruff explicitly identifies app as first-party so lint behavior is consistent across working directories. Do not edit generated schemas/types.

The e2e runner starts only its own disposable SQLCipher backend/Vite processes on free loopback ports, uses test-only synthetic gateway responses, exercises A/D/E/F plus real PDF.js/ATS/ZIP/passcode/delete, and cleans its temporary database/services. Screenshots, PDFs and logs under .validation are synthetic evidence, not product assets or personal databases. Hosted CI includes the command but must be verified by an actual run.

Read the new README sections before enabling encryption. Set APP_DATABASE_PASSPHRASE only in the backend process; retain its .salt sidecar. Use python -m app.privacy.encrypt_database --output NEW_PATH with the backend stopped for an existing plaintext SQLite store, then select the new URL and verify it. It never removes the plaintext source. SQLCipher's optional cipher_memory_security setting crashed the current Windows wheel; preserve the tested configuration. Do not bypass key validation.

Optional APP_ENCRYPTION_KEY is base64 of 32 random bytes. With the backend stopped, run python -m app.privacy.encrypt_store before restarting an existing store. Typed envelopes use AES-GCM; skill equality uses a blind index. Complete SQLite and PostgreSQL field/volume protections are different scopes. Exports/PDFs are plaintext; deletion does not erase external copies or secret environment variables. Never log or send either key to models. Key recovery/rotation and authenticated server deployments remain later work.

When extending jobs/workers or SSE, preserve workspace-epoch session binding and revocation checks. Privacy deletion must reject late model results and pending commits, cancel generation and clear the full owner graph. Generation runs retain an exact version for idempotent commit/download; never replace that with the latest edited document.

Final test/compatibility/container evidence and remaining limits are tracked in IMPLEMENTATION_STATUS.md. Stop only validation services/volumes/clusters created or started during this session; preserve unrelated stacks and user data. All six session-ending files are maintained, including PROJECT.md's appended record.


Phase 4 final verification — 2026-10-07: native check passed (43 backend/17 frontend tests, strict lint/types/contracts/build); final Playwright A/D/E/F passed with actual PDF/SQLCipher and synthetic model responses; Python 3.12 focused tests and PostgreSQL 18 workflows passed; clean dependency audits passed. Docker became available and final isolated builds/health/Alembic/Linux Phase 4 tests/Nginx/PostgreSQL 17 PDF/ATS/tracker/privacy smoke passed. Hosted CI and live Codex container account authentication remain unverified. Validation services/volumes and the started native cluster were stopped/removed; unrelated stacks and the personal store were preserved. All six session files are updated, PROJECT.md's blueprint is retained, and no commit/remote/publication was requested or performed.


## Phase 5 maintenance — 2026-10-07

The openai-docs skill was used for current Codex installation/sign-in documentation: https://learn.chatgpt.com/docs/codex/cli and https://learn.chatgpt.com/docs/auth. No new skill/plugin or delegated agent was needed. Codex remains the default selected provider, with explicit consent; no model calls were needed for hardening or release installation tests.

Run python scripts/tasks.py check, audit, e2e and fresh-install for release work. doctor verifies storage/PDF prerequisites without sending personal data or checking account login. fresh-install uses a source allowlist and cleans only its own temp stores/processes. It uses host runtimes and caches; record that separately from no-cache container setup and hosted CI. All generated contracts remain tool-owned; no schema change was required for Phase 5.

Never call ruff --fix from the root without the backend configuration: the Python 3.12 target and deliberate E402/UP036 suppressions are required by pre-venv scripts. Run configured lint/format via the task runner or from backend. Keep SSL verification enabled; invalid inherited TLS certificate paths need valid operator configuration, not verify=False. The isolated installer discards host certificate override variables and uses normal trust roots.

When extending the renderer, invalidate both entries and in-flight cache insertion on privacy events; enforce byte/count/age bounds. Do not bypass source or database epochs because a PDF is cached. Preserve one local workspace assumption until authenticated server design exists. Keyboard/screen-reader labels, retry/empty/loading states and contrast need browser inspection after runtime changes. Exact checks and limits belong in IMPLEMENTATION_STATUS.md. All six session-ending files must be maintained.

Production PDF.js verification must include Nginx: .mjs assets need JavaScript MIME, and Vite-only success does not prove worker loading in a container. Preserve source allowlists in both .dockerignore files.


Phase 5 final acceptance — 2026-10-07: native check passed (48 backend/20 frontend tests, strict types/lint/drift/build), final A/D/E/F passed, audits found no known vulnerabilities, isolated README-only native installation/outage/restart passed, and no-cache Linux builds plus final healthy Nginx/PostgreSQL/PDF/privacy browser workflow and 13 Linux focused tests passed. Production .mjs MIME was corrected after a real PDF.js failure; API proxy errors also receive no-store. Source-only Docker contexts exclude local data/settings/evidence. Hosted CI, physical clean-OS certification and live Codex container login remain unverified. All six session documents and the original blueprint are maintained; final rules were reread. Owned validation stores/services/volumes are removed, unrelated services/personal data preserved, and no model calls, commits, remotes or publication occurred. Exact evidence is in IMPLEMENTATION_STATUS.md.


## Roadmap clarification - 2026-10-08

For roadmap questions, cross-reference PROJECT.md section 9 with section 7 and current implementation status; distinguish completed overlapping features from remaining enhancements. No specialized skill or new validation was needed for this review.


## Phase 6 acceptance planning - 2026-10-08

This task created repository Markdown acceptance criteria using the existing blueprint/status; no specialized skill, plugin or delegated agent was needed. Implementation must use actual parser/PDF/browser/export evidence and fresh synthetic model evaluations where applicable, preserving distinct native/container/hosted results. Documentation-only editing does not establish a passing product test run.


## Phase 6 implementation progress - 2026-10-08

Documents skill was read for DOCX structural/render QA. Windows bundled workspace dependencies contain no LibreOffice renderer; visual compatibility remains pending separate isolated verification. No delegated agents were used. Run phase6-eval for fresh Codex synthetic task evaluation in disposable stores; it never reads the personal database. Reuse check/api/audit/e2e/fresh-install and label all model/environment evidence accurately.

### Phase 6 final workflow guidance — 2026-10-08

Use `python scripts/tasks.py phase6-eval --models default --output .validation/phase6-evaluation.json` for the three new tasks. It uses disposable synthetic stores and explicit provider consent, never the career database. Baseline/candidate results include two differing metrics and an injection case, raw failures, provenance and timings. Preserve failed original runs separately from retests; `default` is the CLI configuration, not a pinned resolved model, and sampling is Codex-managed. Mocked browser responses prove controls/workflows, not live model quality.

The documents skill's packaged render_docx.py was used for actual DOCX QA. Its native Windows invocation failed because soffice is absent. An isolated disposable Python 3.12 Linux container with LibreOffice Writer 25.2.3, Poppler and Noto rendered short resumes/letters and long Classic/Modern documents. Inspect every page PNG for clipping, sequence, Unicode, headings, links and margins; final letter closing includes the stored author name. This establishes the named Linux processor only, not Windows Word compatibility. QA inputs and evidence stay in ignored .validation, with no personal data.

After parser/template changes, test actual files, worker cancellation/recovery, encrypted assets and historical render/export. After contract changes run api; never edit generated types. Template save now renders a synthetic PDF, so mocked syntax checks alone cannot verify it. Test production Nginx/PDF.js separately from Vite. Use isolated Compose projects and specific ports/volumes, preserve unrelated stacks, and remove owned validation resources before ending. Maintain all six session files and reread PROJECT.md's literal ending rules.

Final session checks passed with the evidence/environment distinctions in IMPLEMENTATION_STATUS.md; all six ending documents are updated, the original rules reread and owned validation services/network/volumes removed. No delegated agents, commits, remotes, publication or personal-data changes.


Run-guidance session — 2026-10-08: used OpenAI Docs skill, local codex login help and fetched official CLI/authentication documentation to verify setup instructions. Generic app commands were checked against repository code/README. Save full steps in docs/run-windows.md; do not infer outside-terminal PATH from the Codex process or store file keys only in Pydantic .env. All six ending files maintained; no new product tests/model calls.


Native launch session — 2026-10-08: verified runtime/CLI via existing commands; used real Playwright browser/PDF.js fallback after CUA kernel-asset initialization failed. No Windows native UI control or delegated agents used. Browser verification used only synthetic unsaved preview and made no model calls. Initial combined background launch was rejected; separate task-runner service launches succeeded. All six session files updated; running user services intentionally preserved.

## Hosting planning workflow — 2026-10-09

OpenAI Docs skill was read and used to check official authentication, billing and public execution guidance; other hosting facts came from primary provider documentation. No Sites skill was applied because this is planning deployment of an existing repository, not building a Sites project. No delegated agents, account changes, model calls or runtime validation. Recheck free allocations/eligibility before any deployment; verify ARM, HTTPS origins/cookies/proxy identity, actual PDFs and browser companion pairing in their target environments. Documentation-only research does not establish hosted acceptance. All six session-ending documents maintained.

## Security audit workflow — 2026-10-09

Reused OpenAI Docs skill/official documentation for Codex auth, secure transport, credentials and agent-command sandbox semantics; used primary Playwright/Tailscale docs for Chromium default sandbox and private transport claims. No security plugin/agents or model calls used. Audit custom probes use a fresh migrated synthetic store, no provider calls, isolated process sentinels and source hashes; they distinguish passed probe execution from secure behavior. check passed 81/20; audit retest passed with trusted certifi TLS after initial pip setup failure. No new browser e2e/fresh-install/hosted binary attestation. Use actual OS deny/cancellation/SSE/commit tests for remediation, preserve privacy barriers and accurately label mocked run lookups versus real stream implementation. Session-ending files maintained.


## Node PATH troubleshooting — 2026-10-13

User reported node unrecognized in an outside terminal. Codex process resolves bundled Node v24.19.0 at C:\Users\coolg\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe; this does not establish the outside terminal PATH. Guidance uses a temporary PowerShell PATH prepend and optional user PATH configuration. Bundled pnpm currently reports 11.25.0, whereas this repository requires 11.19.0; do not assume bundled pnpm meets the prerequisite. No runtime configuration, installations, services, personal data or model calls changed. Product checks were not rerun for this guidance-only session; previous environment limits remain. All six session documents maintained; original blueprint preserved.


Node follow-up — 2026-10-13: clarified bundled app runtime versus an independently installed Windows development runtime. Prior cache PATH advice is a temporary workaround; recommend standalone Node 24.x with installer PATH setup for regular outside-terminal use. No install/PATH mutation performed. OpenAI Docs skill consulted; bundle location is established by local dependency metadata, not a public cache stability guarantee.



## Reusable coding practices - 2026-10-13

Created repository Markdown directly after reading project guidance and representative frontend/backend modules/configuration. Checked primary React, TypeScript, SQLAlchemy and FastAPI documentation for effect, strictness, session and async guidance, with links beside the relevant guide passages. No specialized skill, plugin, delegated agent or model call was needed. Documentation validation does not establish a new product test pass.


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

For developer onboarding, trace a complete UI/request/service/repository/storage flow and inspect actual imports/manifests instead of copying blueprint library suggestions. The handbook and new-project architecture template are ordinary repository Markdown documents; no new Codex skill/plugin was created. Check local relative links/heading anchors and source examples for documentation changes; label historical test evidence separately from fresh checks. Maintain all six ending documents and preserve the original blueprint.

Structured experience validation: real disposable SQLCipher browser workflows passed, including new structured entry, HTML/PDF.js, detail-date autosave/reload, existing Phase 4/6 flows, exports and delete-all. Five targeted backend cases and 23 frontend tests passed; the final combined check is recorded in IMPLEMENTATION_STATUS.md. A minimal Chromium reproduction distinguished exact wrapping-label lookup from accessible textbox roles for initially populated textareas; use the accessible role in reload assertions rather than increasing arbitrary waits. No personal data or live model calls.

Final structured experience gates passed: native check (86 backend/23 frontend tests, lint/strict types/generated drift/build), audits with process-local trusted certifi CA configuration, and real disposable SQLCipher browser workflows. No new dependency or reusable skill was installed; see IMPLEMENTATION_STATUS.md for original failures, corrected assertions and current environment limits. Existing product services remain untouched; reload the backend API before using the new fields against a native installation, or rebuild Docker.


## Saved-work port correction — 2026-10-16

User reported missing old template on 5173. Read-only counts found native SQLite has one master/80 versions and zero custom-template records/revisions/assets; Docker has zero resumes/custom templates. A separate custom template was not recovered or claimed. Created/preserved ignored .validation/native-restart-20261016/before-start.db via SQLite backup. Stopped only Compose frontend/backend (volumes and PostgreSQL/Redis preserved), then launched native backend/frontend on loopback 8000/5173 against the explicit existing SQLite path. Proxied health reports ready, UI HTTP 200, resume API returns version 80, custom-template API returns empty. Requested opening the saved master directly. README restart commands now use 5173/8000 and explain stopping Docker app services before native startup; run-windows guidance supersedes old alternate-port history. No migration, resume edit, model call, dependency change, commit or publication. Product suite and real PDF/browser rendering were not rerun; operational HTTP checks only. All six session documents updated, original ending rules reread and blueprint preserved.


## Experience editor visibility — 2026-10-16

Inspected the actual native resume editor in the in-app browser. The structured editor is present but collapsed behind Add experience. Opened that form and verified Company, Title, Start date, End date, Present, summary and duty controls in the live accessibility tree; screenshot confirms the visible date inputs. No code, resume/library data or settings changed; master remained at version 80. Product tests not rerun for UI navigation. All six ending documents maintained; original blueprint and ending rules preserved.


## Backend learning companion — 2026-10-22

Use docs/developer/BACKEND_READING_LIST.md when learning or explaining BACKEND.md. The list preserves sections 1-14 and offers a dependency-aware study order. No new skill/plugin or external research was needed; this is a local documentation companion.


## UI refinement planning — 2026-10-22

Use docs/coding-practices/CLEAN_UI_DESIGN_PROCESS.md as a copyable future-project method: brief, audit, workflow hierarchy, wireframes, tokens, stateful components, one complete slice, usability/accessibility verification and maintained evidence. It is ordinary Markdown, not an installed Codex skill. Separate source findings from screenshot observations, use synthetic data, and distinguish project heuristics from Apple/WCAG requirements.


## Phase 7 implementation and Apple UI analysis — 2026-10-25

Apple website inspection method: inspect public pages visually, measure visible DOM/computed styles, read responsive production CSS, and label observation versus inference versus proposed application values. The report docs/design/apple-website-ui-analysis.md and reusable CLEAN_UI_DESIGN_PROCESS.md support future projects. UI component guidance is docs/developer/UI_COMPONENTS.md. No installed design skill or remote assets were added. Keep release evidence and real participant usability results separate.


Phase 7 final native evidence — 2026-10-25: For Python audit/install on this host, the inherited PostgreSQL CA path can be invalid; process-local certifi CA variables retain TLS verification without persistent environment mutation. Run Ruff for scripts with backend/pyproject.toml settings. Async browser assertions need to account for documented parser/render bounds; do not treat Playwright default assertion timing as the service contract. Actual final native check/audit/e2e/fresh-install passed; retain all unsuccessful runs and external acceptance limits. Recursive cleanup of two owned disposable failed-run folders was rejected by automatic review and was not bypassed.


## Apple-inspired UI and reusable style specification — 2026-10-25

For another website, copy docs/design/ui-starter with UI_UX_STYLE_GUIDE.md, complete the product brief and use the included implementation prompt. It is a local reference kit and ordinary documentation, not a newly installed Codex skill/plugin. scripts/ui_style.py sync refreshes CSS copies, manifest and generated token block; check detects drift/contrast; browser exercises only a temporary loopback reference server. Keep local demonstration saving separate from real production persistence.


Clean workspace 1.0 final native evidence — 2026-10-25: Final check passed (Ruff lint/format across 155 files, mypy 119 source files, 86 backend/26 frontend tests, ESLint, strict TypeScript, generated API drift and production build). Python/pnpm audits passed with no known vulnerabilities. Product e2e passed A/D/E/F, 6A–6F, structured experience and Phase 7 keyboard/responsive workflows with disposable SQLCipher, actual Chromium/PDF.js and synthetic model responses. The distributed reference browser passed 320/390/768/1280/1440px reflow, keyboard/draft/focus/control checks with zero page errors or remote requests. Eleven principal contrast pairs and exact CSS/manifest/documented-token synchronization passed; 94 local documentation links/assets were verified. Final isolated fresh-install passed production browser/PDF/ATS/outage/restart after correcting new test-only TypeScript fixture/query errors; the first failed run remains recorded in docs/design/07-ui-implementation.md. Desktop/editor/narrow/reference/forced-colors screenshots were reviewed. Canonical reusable specification: docs/design/UI_UX_STYLE_GUIDE.md; exact portable kit: docs/design/ui-starter/. All six ending documents maintained and original ending rules reread; blueprint preserved. No new follow-up dependencies/API contracts, personal-store operations, live inference, deployment, commits, remotes or publication. Successful disposable harness services/stores cleaned up by their own finally blocks. Earlier ignored failed-run stores and inherited security findings remain. Representative task/timing studies, actual 200% browser zoom, screen-reader interoperability, Docker/Nginx, hosted CI, clean OS, native Word and live Codex container login were not newly verified.


## Application comment audit — 2026-10-26

Used local source inspection, targeted inline comments, Python AST/non-comment-token comparison and TypeScript transpilation with comments removed to verify executable equivalence against the pre-audit working tree. No external research, new skill/plugin, dependency, test fixture or model call was needed. Keep comments about constraints and reasons, not restatements of syntax; record known limits candidly. See docs/developer/COMMENT_AUDIT.md.


## Git lock diagnosis — 2026-10-26

Commit troubleshooting found a zero-byte .git/index.lock last modified October 25 at 12:41 p.m. local time, with no git/ssh/gpg process matching the read-only process check. This suggests an abandoned index lock; the originating operation is unknown and a process snapshot cannot exclude later activity. Guidance: finish/close Git operations, remove only the stale index.lock, then retry the commit. The lock was not removed; no staging, commit, remote, application/service/data/model changes or product tests occurred. All six ending documents maintained; original blueprint and prior verification limits preserved.



## Cross-platform CI typing fix - 2026-10-26

For platform-specific Python APIs, use sys.platform statement guards; mypy still checked CREATE_NO_WINDOW inside conditional expressions in this repository. Reproduce Linux typing locally with backend/.venv/Scripts/python.exe -m mypy --platform linux from backend. python scripts/tasks.py check now covers both linux and win32 stubs. This is static cross-platform validation, not an Ubuntu runtime or hosted CI result. No specialized skill/plugin was needed.


## Generic README folder examples - 2026-10-26

README Windows restart commands now use C:\path\to\resume-tailor with an explicit instruction to substitute the repository folder in both terminals. Original machine-specific names are absent from README; all three PowerShell blocks pass syntax parsing without execution. Documentation only; no product checks rerun, runtime/data/service/dependency changes, model calls, commits or publication. Prior CI fix/evidence and original blueprint remain preserved; all six session documents maintained and ending rules reread.
