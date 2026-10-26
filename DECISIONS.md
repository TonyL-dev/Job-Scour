# Decision log

## Structured master experience — 2026-10-15

Use the existing owned experience record for company/title/dates and store newly entered summary/duties in its description as evidence. Each resume summary/duty is an independently sourced item with its own identity/lock; do not duplicate employer facts into an editable model-authored payload or rewrite historical snapshots. Keep career-save and document-save separate and visibly explain that discarding a draft retains the saved library source. Source-detail edits preserve existing evidence text; manual resume text edits do not alter library facts.

Add the backwards-compatible schema-v1 `experience_summary` flag rather than replacing the item tree or migrating persisted snapshots. Default false retains existing bullet behavior. A true flag selects paragraph presentation in PDF/HTML/DOCX and enforces a conservative one-line, one-sentence, 500-character limit (dotted abbreviations can reject). Preserve it during rewriting/condensation/review and reject invalid AI proposals without replacing the original text. Revalidate internally assigned documents before persistence. No dependencies, model settings, packaged prompt versions, personal stores or deployment configuration change; summary rewrites receive the sentence limit in their existing dynamic style instruction.

Recorded 2026-10-06. Full relational design and future-domain decisions are in docs/design/01-foundations.md.

| ID | Decision | Reason / alternatives |
|---|---|---|
| 001 | Implement Phase 0 under the direct user request; write the design first. | PROJECT.md contains a historical design-only handoff. The current user explicitly asks for implementation; a second approval gate would conflict with that request. |
| 002 | Python task runner and pnpm. | Cross-platform operation without requiring Make on Windows; Node dependencies have a frozen lockfile. |
| 003 | SQLite locally, PostgreSQL in Compose. | Private single-process development and a realistic server database share SQLAlchemy models and Alembic revisions. |
| 004 | Identity-only initial migration. | Career entities and the canonical document implementation belong to Phase 1; no speculative product CRUD in Phase 0. |
| 005 | Separate live/ready endpoints. | A running process with an unmigrated database must not appear ready. Readiness validates the migrated identity table. |
| 006 | Same-origin typed API requests through proxies. | Browser URL/ports need no baked-in API endpoint. OpenAPI generation removes handwritten duplicated response types; drift fails checks. |
| 007 | TypeScript 5.9.3 and a compatible ESLint release. | TypeScript 7 removed a compiler API used by openapi-typescript. Pinned compatible tools passed peer checks. |
| 008 | Compose services on loopback only. | Authentication is future work. Internal container binding does not justify host/LAN exposure. |
| 009 | Provision Redis without a worker. | Keeps the specified stack available while AI and job orchestration remain in later phases. |
| 010 | No runtime migration magic. | Alembic is explicit for native startup and executes before container startup; app lifespan only owns engine resources. |

Future contract choices: snapshot locks; sequential migrations preserving old versions; XOR typed achievement parents; portable relational types with later dialect-specific vector adapters; one HTML artifact for preview and PDF. These are planned, not Phase 0 code.

Validation note: use native tests to check available runtimes without claiming unavailable Docker/hosted CI results. SQLite, isolated PostgreSQL 18, and Python 3.12/3.14 checks passed; Compose is still an outstanding acceptance check.

## Phase 1 decisions — 2026-10-06

| ID | Decision | Alternatives / rationale |
|---|---|---|
| 011 | Fixed repository-resolved local owner; server domain routes disabled. | Request-supplied owner IDs would masquerade as authorization. Full server sessions belong to later work. A lazy local identity makes first use functional without startup schema writes. |
| 012 | Concrete career tables with typed discriminated request data and schema-derived form descriptions. | One arbitrary JSON career table loses database constraints; twelve duplicated CRUD implementations drift. Shared repository plumbing uses a closed model registry, with explicit business relationship checks. |
| 013 | Retire all career records; derive inactive parent chains. | Hard deletion breaks provenance. Stored historical facts survive; new drafts cannot cite retired or dependent inactive records. Custom details are an inert text map in Phase 1, with richer validated payloads deferred. |
| 014 | Built-in templates are a closed immutable registry. | Editable database templates require sandboxed custom-template lifecycle and asset versioning, outside Phase 1. Stable template UUIDs satisfy document contracts without speculative template editors. |
| 015 | Consolidate master metadata in resume_documents; latest version identified by version number. | Separate master metadata and circular version pointers duplicate state. Unique owner/document/version and optimistic compare-and-update give atomic append-only snapshots. Later tailored documents/history APIs extend this base through migrations. Only schema v1 exists; unknown versions reject rather than pretending migration support exists. |
| 016 | Persist locks inside snapshots; manual edits remain allowed. | A separate lock table would detach historical protection from its content. Protection flags are for future AI patches; Phase 1 rejects AI write origins and never invokes an LLM. |
| 017 | Render actual PDFs for live preview, count actual pages. | Continuous HTML alone cannot prove pagination parity. Chromium prints one escaped HTML artifact; PDF.js draws that PDF locally. Native iframe PDF viewing was unreliable in headless Edge, so a bundled viewer removes that dependency. HTML remains a sandboxed accessible alternative. |
| 018 | Bundle OFL Noto variable fonts and use bounded styles. | OS font fallback changes wrapping across platforms; remote fonts violate privacy. Font assets and licenses are packaged with the backend; Chromium/network scripts are blocked while data fonts are permitted. |
| 019 | Explicit saves append immutable snapshots; conflicts return 409. | Mutating the current snapshot violates the blueprint. Autosave/history/restore/duplicate screens are Phase 4. Selecting a gold standard clears the previous flag in the same transaction; a partial unique index enforces one per owner. |
| 020 | Keep saves available without Chromium; preview/export report actionable 503. | Career entry and content persistence should not fail because a rendering runtime is absent. Page counts are computed on preview/export, not stored as speculative estimates at save time. |
| 021 | Serve a local HTML API reference instead of default Swagger/ReDoc assets. | FastAPI's default documentation loads CDN JavaScript. A local method/path table and OpenAPI link honor the no-CDN rule without adding a second JavaScript application. |

Actual PDF drawing-command, page geometry, and text parity are integration-tested for both templates. Real browser tests inspect PDF.js pages and check for external requests. Native PostgreSQL 18 compatibility remains distinct from the PostgreSQL 17 Docker image, and local checks do not substitute for hosted CI.

## Phase 2 decisions — 2026-10-07

| ID | Decision | Rationale |
|---|---|---|
| 022 | Keep all model HTTP in ai; disable proxy inheritance and redirects. | Prevents hidden forwarding of private data and redirect-based changes of consented destination. Detection only contacts two fixed loopback addresses. |
| 023 | Store API-key environment-variable names, not plaintext secrets. | Encryption-at-rest infrastructure is a later phase; environment references provide authenticated endpoints without prematurely adding insecure key storage. |
| 024 | Conservative byte budgeting and one concurrent inference. | Avoids unverifiable tokenizer counts, silent truncation, and oversubscribing local hardware. Profiles must use actual loaded context limits. Exact provider/tokenizer adapters can extend this later. |
| 025 | Append immutable prompt/analysis/match snapshots and fingerprint rendered inputs/schema/configuration. | Reuses stable job analysis while refreshing career matches after edits/retirement. Prompt management/playground and resume history remain later features. |
| 026 | Cache portable JSON embedding vectors; deterministic cosine/keyword ranking. | SQLite and PostgreSQL work without speculative vector extensions. Owner/model/endpoint/content hashes prevent stale or cross-owner reuse. Similarity never proves a skill or fills a gap. |
| 027 | Request-owned SSE analysis with cancellation; no durable generation queue yet. | Phase 2 needs live gateway behavior; generation runs/workers/review belong to Phase 3. Completed validated cache entries can survive cancellation. |
| 028 | Require exact job-description evidence quotes; never mutate career/resume facts. | Extraction has a verifiable source boundary; job text is untrusted and models have no tools. Resume truthfulness and lock-preserving AI patches remain Phase 3. |
| 029 | Evaluate synthetic fixtures and report real-model failures separately. | Offline/mocked tests prove controls, not model quality. Two-local-model acceptance and hosted/container checks require actual runs; resource limits cannot be relabeled as passes. |
| 030 | Preserve prompt v1 and activate v2; share the product's quote-repair path with evaluation. | Real small-model runs exposed paraphrased quotes and missed preferred skills. Explicit extraction examples improve behavior without relaxing schema/evidence checks or hiding quality failures. |
| 031 | Detach analysis DTOs and recheck career snapshots after embeddings. | Avoids implicit service-layer SQL and prevents long-running matches from saving retired/changed sources. A retry can reuse the validated analysis cache. |
| 032 | Parse narrow, explicit posting metadata deterministically; version extraction in cache keys. | Real models omitted nullable seniority/years fields. Leading role titles and explicit required-experience syntax provide exact quotes without inferring company age or unstated qualifications. |
| 033 | Preserve failed model reports and distinguish fresh calls from artifact replay. | Small Qwen quality was mixed; Devstral's seniority omission needed a focused fix/retest. The final replay passes all real outputs but must not be described as twenty fresh final-version calls. |
| 034 | Use an existing CPU embedding runtime for native validation after LM Studio's Nomic loader crashes. | Verifies real vectors and the generic gateway without pretending a third-party loader was repaired. No new embedding runtime is bundled into the product. |


## Phase 3 decisions — 2026-10-07

| ID | Decision | Rationale |
|---|---|---|
| 035 | Persist runs/suggestions while using a bounded single local worker. | Browser disconnects must not lose work. Restart marks interrupted runs failed and keeps partial checkpoints; automatic unsafe replays are avoided. Authenticated multi-process/Redis workers remain later infrastructure. |
| 036 | Save review results as separate tailored documents under an atomic revision check. | Neither generation nor acceptance overwrites the master. Retries return the already saved document. Existing resume versions stay append-only. |
| 037 | Fail closed on provenance/numbers/technology and conservative claim vocabulary before semantic verification. | A plausible rewrite is not evidence. Some valid paraphrases may be rejected; the review screen exposes the reason and allows an explicit sourced manual edit. |
| 038 | Run a separate verifier call at temperature zero; preserve v1 and activate generation prompt v2. | Real Devstral tests exposed rejection of JS/JavaScript equivalence and overlooked source sentences. V2 clarifies alias equivalence and full authoritative source values without allowing extra claims. |
| 039 | Recheck both the active career snapshot and cited source text at review/commit. | A completed model run must not apply stale or retired evidence, including non-retrieval career categories. |
| 040 | Keep protection flags in snapshots and persist review lock changes for regeneration. | AI cannot unlock or change protected text/facts. Manual protection choices remain possible; locked skill positions survive reordering. |
| 041 | Fit by measured PDFs with bounded, ordered content changes; allow layout adjustments only by explicit run input. | Heuristic budgets cannot prove page limits. Protected overflow needs an honest warning. Sparse-final-page detection is a text-length heuristic with visual inspection. |
| 042 | Use disposable databases for generation evaluation and keep original failures. | Live model quality, mocked safety controls, browser behavior, and PostgreSQL/Python compatibility prove different things. Evaluation must never read personal career records. |

| 043 | Keep factual context separate from ranking/review metadata and normalize explicit metric fields exactly. | An importance score cannot prove years or impact. Stored decimal/unit fields must support quantification even when prose omits the numeral; negative signs and percentages retain their meaning. |
| 044 | Preserve v2 and activate v3 with a structured-metric verification example. | A fresh real Devstral metric test wrongly treated an associated 40% field as unsupported because the prose omitted the number. V3 clarifies field evidence without permitting different numbers/outcomes. |

## Codex provider decisions — 2026-10-07

| ID | Decision | Reason |
|---|---|---|
| 045 | Default to Codex CLI exec with existing ChatGPT authentication. | The user explicitly replaced local models with Codex. Reuse supported authentication without scraping OAuth tokens, introducing API keys or silently changing billing. |
| 046 | Require sharing consent and isolate each Codex call from project/user tools/configuration. | Supply selected facts through ai, disable unrelated capabilities/telemetry, discard tool events, and bound/cancel child processes. |
| 047 | Default to keyword matching and reject Codex embedding assignments. | Codex CLI provides structured text, not vectors. The workflow must work without a local LLM or embedding server. |
| 048 | Record Codex-managed sampling and configured default honestly. | The CLI does not expose temperature/top-p/output-token caps or account-model listing. Enforce time/bytes/context budgets; explicitly select a supported model when pinning is needed. |

Generation v3/facts.v1/claim checks 3.2 remain active. Devstral still over-rejected the structured 40% metric after v3; the failed report is preserved. Local-model tuning stopped after the Codex request. Fresh Codex stored-metric generation passed. Original provider evidence and blueprint remain historical records; implementation follows the user's current request.

| 049 | Distinguish Docker stack smoke, hosted checks and live Codex container testing. | The current image lacks the CLI/login. Green health/routing or mocked AI tests do not establish container-based account-backed generation. The user asked for verification instructions, not installation or repository publication. |


## Phase 4 decisions — 2026-10-07

| ID | Decision | Rationale |
|---|---|---|
| 050 | Implement section 9 Phase 4, including privacy, while retaining server guards. | The user authorized implementation and session-ending maintenance. Local passcodes do not establish multi-user/server authentication. |
| 051 | Bind immutable ATS reports and tracker records to exact resume versions. | Later edits/restores must not silently change the resume used for an application or the content scored. Generation commits/downloads also retain their exact saved-version identity. |
| 052 | Restore historical snapshots directly; validate new edits against active sources. | Historical facts and retired-source exports stay intact. Restore/duplicate append lineage instead of rewriting versions; this explicit archival operation differs from introducing a new sourced claim. |
| 053 | Allow append-only manual tailored edits with user origin; reject new AI-origin claims. | Review outputs remain editable without bypassing verification. Unchanged AI items must match stored content and pass current evidence checks. No-op saves avoid history inflation; autosave uses the existing CAS. |
| 054 | Use deterministic English ATS heuristics and actual PDF text/order/page measurements. | Guidance must not imply a vendor verdict. Related terms do not receive exact-keyword credit; gaps cannot become facts. Optional LLM explanations were unnecessary and would add external-data exposure. |
| 055 | Revoke session epochs and guard commits/SSE across lock/delete. | A held model response or pending transaction must not repopulate a deleted workspace or reveal additional data after lock. A deliberate concurrency regression verifies this boundary. |
| 056 | Use SQLCipher with an Argon2id-derived storage passphrase and optional AES-GCM fields. | Full SQLite encryption covers metadata too; field encryption supports PostgreSQL alongside operator disk/volume encryption. Secrets stay outside the store. The lock passcode and boot-time storage unlock are separate, documented mechanisms. |
| 057 | Convert to a new verified SQLCipher file; keep plaintext originals for user-managed handling. | Avoid destructive in-place conversion or deleting unreviewed backups. Preserve the salt/passphrase pair. Field conversion is transactional and leaves historical hashes unchanged. |
| 058 | Do not enable the current wheel's optional cipher_memory_security switch. | It caused a native Windows stack overflow. Standard database encryption, wrong-key rejection and real PDF operations pass; process-memory hardening is not claimed. |
| 059 | Keep browser fixture providers isolated and label them synthetic. | Actual UI/SQLite encryption/PDF tests prove workflow behavior, not fresh model quality or CLI/account container compatibility. CI includes e2e but requires its own hosted run. |

The initial cryptography 46.0.3 pin failed advisory checks; it was replaced by locked 50.0.0 and revalidated. Original roadmap/design decisions and earlier model evidence remain preserved. No commits, remotes or publication were requested.


Phase 4 final verification — 2026-10-07: native check passed (43 backend/17 frontend tests, strict lint/types/contracts/build); final Playwright A/D/E/F passed with actual PDF/SQLCipher and synthetic model responses; Python 3.12 focused tests and PostgreSQL 18 workflows passed; clean dependency audits passed. Docker became available and final isolated builds/health/Alembic/Linux Phase 4 tests/Nginx/PostgreSQL 17 PDF/ATS/tracker/privacy smoke passed. Hosted CI and live Codex container account authentication remain unverified. Validation services/volumes and the started native cluster were stopped/removed; unrelated stacks and the personal store were preserved. All six session files are updated, PROJECT.md's blueprint is retained, and no commit/remote/publication was requested or performed.


## Phase 5 decisions — 2026-10-07

| ID | Decision | Rationale |
|---|---|---|
| 060 | Bound PDF reuse by full artifact hash, TTL/count/bytes and privacy invalidation epoch. | Repeated preview/download/ATS can reuse identical PDFs without persisting private content or allowing late renders to refill a locked/deleted cache. Retain active-source checks and historical facts. |
| 061 | Bound AI waiters and render admission; reject excess work with retry guidance. | A semaphore alone limits execution but can accumulate waiters indefinitely. Cancellation must restore capacity. |
| 062 | Apply an ASGI write-size bound and handled-response privacy headers, with production CSP and unbuffered SSE. | Pydantic field limits run after body parsing; chunked bodies must also be bounded. Proxy and backend limits agree. Assets remain local. |
| 063 | Validate README installation in fresh dependencies and no-cache Linux container builds, labeling their scope. | A new venv/node_modules/database proves dependency/setup assumptions; containers isolate Linux libraries. Neither is a newly provisioned physical OS or a hosted CI/account-authentication result. |
| 064 | Add keyboard/recovery states and clear queries on polled locks. | Users must reach and recover views without pointer use; a server-observed expiry must clear private cached data even without an explicit lock event. Accessibility checks are not certification. |

The stock Docker release remains usable without AI and does not bundle account credentials. Native Codex is the documented AI path. Phase 5 does not authorize commits, remote creation, publication, authenticated-server deployment, new prompts or importer/backup enhancements. Original roadmap and provider/model evidence remain preserved.

| ID | Decision | Rationale |
|---|---|---|
| 065 | Use source-allowlisted Docker contexts and an explicit .mjs JavaScript MIME location. | Keep local stores/settings/evidence out of build contexts; real production browser checks found that default Nginx MIME handling broke PDF.js workers despite healthy APIs. |


Phase 5 final acceptance — 2026-10-07: native check passed (48 backend/20 frontend tests, strict types/lint/drift/build), final A/D/E/F passed, audits found no known vulnerabilities, isolated README-only native installation/outage/restart passed, and no-cache Linux builds plus final healthy Nginx/PostgreSQL/PDF/privacy browser workflow and 13 Linux focused tests passed. Production .mjs MIME was corrected after a real PDF.js failure; API proxy errors also receive no-store. Source-only Docker contexts exclude local data/settings/evidence. Hosted CI, physical clean-OS certification and live Codex container login remain unverified. All six session documents and the original blueprint are maintained; final rules were reread. Owned validation stores/services/volumes are removed, unrelated services/personal data preserved, and no model calls, commits, remotes or publication occurred. Exact evidence is in IMPLEMENTATION_STATUS.md.


## Roadmap clarification - 2026-10-08

Phase 6 scope is not yet selected. Follow section 9: remaining section 7 high-value enhancements precede differentiators. This clarification adds no implementation decision or authorization.


## Phase 6 acceptance planning - 2026-10-08

Planning scope follows section 9: remaining high-value enhancements precede differentiators. The checklist orders import/review, profile fact collection, sourced cover letters, prompt management, DOCX export and custom templates; existing catalogue overlap is verified instead of rebuilt. OCR, arbitrary design fidelity, external reminder delivery, multi-user mode and later differentiators are excluded. These are acceptance requirements, not implemented architecture or permission to start coding.


## Phase 6 implementation progress - 2026-10-08

Phase 6 interim decisions: stage imports before atomic career commits; parse without model calls by default; retain originals only by explicit encrypted-storage choice. Profile questions never supply facts; confirmation writes user-origin answers under a source revision check. Cover letters use separate immutable versions and exact application links. Prompt customization exposes bounded tone/focus enums while guardrails/schemas remain fixed and evaluation gates activation. Custom templates accept a safe declarative HTML/CSS subset and encrypted sanitized PNG assets; arbitrary designs are unsupported. DOCX refuses unsupported custom HTML/CSS/assets instead of silently mapping them.

### Phase 6 accepted decisions — 2026-10-08

| ID | Decision | Rationale |
|---|---|---|
| 066 | Persist import parsing/review/failure separately from career records; atomically remap approved candidate graphs under a review revision. | Cancellation, recovery, duplicates and retries cannot silently create or replace facts. |
| 067 | Keep uploaded originals memory-only unless explicitly retained; encrypt retained uploads and sanitized PNG assets independently of optional field/database encryption. | Avoid default file retention and plaintext private assets; missing keys fail closed. |
| 068 | Profile AI asks bounded questions; proposed edits derive only from user answers and require current-source confirmation. | The model cannot supply missing metrics, dates or skills as factual evidence. |
| 069 | Cover letters have separate immutable versions, source checks/verifier review and exact application links. | Later edits preserve the submitted artifact and all resume snapshots. |
| 070 | Expose supported tone/focus preferences rather than editable system prompts; require exact passing synthetic evaluation for activation/reset/rollback. | Customization cannot override guardrails or reinterpret historical provenance. |
| 071 | Preserve Phase 6 prompt v1 and activate v2; evaluate both metrics and injection through fresh native Codex. | Original failures remain evidence rather than being overwritten by a passing retest. |
| 072 | Bind custom templates and encrypted local asset copies into immutable resume snapshots; permit only a bounded inert HTML/CSS subset. | Retired templates remain exportable without executable templates, network assets or mutable presentation. |
| 073 | Measure a real synthetic PDF before saving a template and retain heuristic extraction/order/contrast/page findings. | Valid syntax alone does not establish readable or ATS-safe output. |
| 074 | Export DOCX using semantic OOXML and local embedded fonts; refuse unsupported custom layout mappings. | Editable output preserves factual content without promising PDF pagination or arbitrary HTML fidelity. |
| 075 | Validate DOCX visually in isolated Linux LibreOffice; record Windows Word and unavailable native renderer as unverified. | A structural ZIP test is insufficient evidence of word-processor layout. |
| 076 | Keep follow-up reminders as an in-app local-date calendar. | Stored due dates survive restart without implying email, push or delivery while the app is closed. |

All new AI calls retain explicit configuration/consent and the ai-only boundary. Single-owner server guards, workspace epochs and source locks remain required. Section 7 differentiators, OCR, automatic encrypted backups and multi-user authentication remain later work; no commit, remote or publication is implied.

Final acceptance evidence is in IMPLEMENTATION_STATUS.md (81 backend/20 frontend tests plus named live/synthetic/native/Linux workflows). Unverified environments remain explicit. The original ending rules were reread, all six session files updated and only owned validation services/network/volumes removed. No commits, remotes, publication or personal-data changes.


Run-guidance session — 2026-10-08: recommend native Windows for the existing Codex integration; retain Docker as a separate manual/offline workflow installation with its own store. Explain completed Phase 0–6 scope separately from future roadmap and unverified environments. No new implementation or deployment decision; no services/data changed.


Native launch session — 2026-10-08: preserve existing Docker stack/default ports; run user-requested native services on 5180/8010 and document restart commands. Back up before migration, persist an independent private-file key without exposing it, and leave AI off until explicit remote sharing consent. No career content edits, commits, remotes or publication.

## Hosting feasibility proposal — 2026-10-09

No hosting route is selected pending audience clarification. Target free-only plans/provider hostnames with no paid fallback; $1 alerts do not cap charges. Propose personal native/private access for full current functionality, public browser-first storage/compute for zero operator subsidy, and free VM only with acknowledged capacity/reclamation risk. Treat existing AI subscription/electricity/internet separately from incremental hosting. Never expose LOCAL_OWNER/stock local credentials or shared native Codex to public users. Browser print cannot establish current measured-PDF/fitting parity. See docs/hosting-under-one-dollar.md for acceptance gates and official sources. Proposal only; original architecture/blueprint preserved.

## Security audit priorities — 2026-10-09

Audit-only findings and remediation backlog are in docs/release/security-audit-2026-10-09.md; no remediation implemented. Retain loopback/public-server guards. Prioritize automatic expiry epoch/stream/commit revocation, native renderer/parser containment, explicit production HTTPS proxy/cookie/owner-only access contract and Codex native trust/compatibility checks. Current optional privacy settings must not be silently changed by an audit. Severity is contextual: missing public authentication and disabled native containment are deployment/hardening risks, not demonstrated internet RCE. No unhackable/zero-retention/absolute sandbox claim is supported. Existing acceptance evidence remains distinct from new checks; preserve blueprint.


## Node PATH troubleshooting — 2026-10-13

User reported node unrecognized in an outside terminal. Codex process resolves bundled Node v24.19.0 at C:\Users\coolg\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe; this does not establish the outside terminal PATH. Guidance uses a temporary PowerShell PATH prepend and optional user PATH configuration. Bundled pnpm currently reports 11.25.0, whereas this repository requires 11.19.0; do not assume bundled pnpm meets the prerequisite. No runtime configuration, installations, services, personal data or model calls changed. Product checks were not rerun for this guidance-only session; previous environment limits remain. All six session documents maintained; original blueprint preserved.


Node follow-up — 2026-10-13: clarified bundled app runtime versus an independently installed Windows development runtime. Prior cache PATH advice is a temporary workaround; recommend standalone Node 24.x with installer PATH setup for regular outside-terminal use. No install/PATH mutation performed. OpenAI Docs skill consulted; bundle location is established by local dependency metadata, not a public cache stability guarantee.



## Reusable coding practices - 2026-10-13

Use two independently copyable stack-specific Markdown guides plus a short adoption index. Require project-specific runtime/deployment/data/quality decisions rather than copying this application's version pins or optional infrastructure automatically. Distinguish recommended new-project patterns from historical/current implementation; explicitly preserve audited limitations. Generic examples do not introduce API contracts or authorize runtime changes.


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

Use a current source-linked handbook separately from the preserved chronological architecture/blueprint and separately from recommended coding practices. Provide a fill-in architecture/onboarding document template for future projects rather than presenting this product's entities, version pins, local identity or optional infrastructure as universal defaults. Document existing tradeoffs (large page modules, framework-coupled errors, repository commit conventions, duplicate career cache keys and partial signal forwarding) candidly; no refactor/remediation is implied.


## Saved-work port correction — 2026-10-16

User reported missing old template on 5173. Read-only counts found native SQLite has one master/80 versions and zero custom-template records/revisions/assets; Docker has zero resumes/custom templates. A separate custom template was not recovered or claimed. Created/preserved ignored .validation/native-restart-20261016/before-start.db via SQLite backup. Stopped only Compose frontend/backend (volumes and PostgreSQL/Redis preserved), then launched native backend/frontend on loopback 8000/5173 against the explicit existing SQLite path. Proxied health reports ready, UI HTTP 200, resume API returns version 80, custom-template API returns empty. Requested opening the saved master directly. README restart commands now use 5173/8000 and explain stopping Docker app services before native startup; run-windows guidance supersedes old alternate-port history. No migration, resume edit, model call, dependency change, commit or publication. Product suite and real PDF/browser rendering were not rerun; operational HTTP checks only. All six session documents updated, original ending rules reread and blueprint preserved.


## Experience editor visibility — 2026-10-16

Inspected the actual native resume editor in the in-app browser. The structured editor is present but collapsed behind Add experience. Opened that form and verified Company, Title, Start date, End date, Present, summary and duty controls in the live accessibility tree; screenshot confirms the visible date inputs. No code, resume/library data or settings changed; master remained at version 80. Product tests not rerun for UI navigation. All six ending documents maintained; original blueprint and ending rules preserved.


## Backend learning companion — 2026-10-22

Teach the backend through prerequisites, exact search vocabulary and a learning goal per existing numbered section. Separate conceptual related topics (such as bounded contexts) from claims of implemented patterns. Explain distinctions including DTO/ORM, DB/login sessions, relevance/truth, hashing/encryption and request-owned/persisted work.


## UI refinement planning — 2026-10-22

Propose a user-requested UI refinement phase next after Phase 6, ahead of remaining differentiators, without rewriting the original blueprint. Interpret Apple-inspired as restrained hierarchy, spacing and predictable controls. Prefer existing CSS/React with explicit variants over a framework migration; begin with Resume Studio. Use a neutral light palette and one accent as a proposed direction, with contrast and usability gates. No new backend/API/storage behavior or UI implementation is authorized by the planning request.


## Phase 7 implementation and Apple UI analysis — 2026-10-25

Use native details/summary with Escape/focus return for occasional actions rather than introducing an incomplete ARIA menu. Use a native dialog for narrow navigation and accessible mounted tabs for Content/Appearance. Keep save/download at document level and retain first-save/autosave semantics. Treat Apple website values as measured examples, not universal tokens: desktop homepage headline 56px/medium48px/narrow32px, selected narrow cards radius28px, and marketing-scale gaps are adapted to a working editor. Bounded dependency patches address newly reported audit findings without changing framework or application contracts.


Phase 7 final native evidence — 2026-10-25: Resolve new release-audit findings with bounded compatible pins (pypdf6.21.2, certifi2026.10.19, filelock4.2.1, setuptools84.1.0, virtualenv21.14.10, Vite8.3.3 and pnpm-resolved Zod4.6.7/Undici8.12.3). Keep initial failures and final retests separate. Keep 44px app controls despite sampled Apple marketing controls being smaller; neutral palette and grouped actions matter more than copying every radius/marketing gap. No participant or deployment acceptance can be inferred from native automation.


## Apple-inspired UI and reusable style specification — 2026-10-25

Use Clean workspace style 1.0.0 as an explicit, reproducible visual contract: action blue #0071E3, links #0066CC, neutral #F5F5F7 canvas, white borderless 24px panels, 28px feature cards, pill actions and dark selected segments. Keep system fonts and 44px minimum targets; adapt marketing typography to a working app. Share actual CSS with the portable kit and detect documentation/distribution drift instead of maintaining a loosely matching mockup. Keep native controls/accessibility and truthful persistence feedback. Consecutive experience grouping affects presentation only.


Clean workspace 1.0 final native evidence — 2026-10-25: Final check passed (Ruff lint/format across 155 files, mypy 119 source files, 86 backend/26 frontend tests, ESLint, strict TypeScript, generated API drift and production build). Python/pnpm audits passed with no known vulnerabilities. Product e2e passed A/D/E/F, 6A–6F, structured experience and Phase 7 keyboard/responsive workflows with disposable SQLCipher, actual Chromium/PDF.js and synthetic model responses. The distributed reference browser passed 320/390/768/1280/1440px reflow, keyboard/draft/focus/control checks with zero page errors or remote requests. Eleven principal contrast pairs and exact CSS/manifest/documented-token synchronization passed; 94 local documentation links/assets were verified. Final isolated fresh-install passed production browser/PDF/ATS/outage/restart after correcting new test-only TypeScript fixture/query errors; the first failed run remains recorded in docs/design/07-ui-implementation.md. Desktop/editor/narrow/reference/forced-colors screenshots were reviewed. Canonical reusable specification: docs/design/UI_UX_STYLE_GUIDE.md; exact portable kit: docs/design/ui-starter/. All six ending documents maintained and original ending rules reread; blueprint preserved. No new follow-up dependencies/API contracts, personal-store operations, live inference, deployment, commits, remotes or publication. Successful disposable harness services/stores cleaned up by their own finally blocks. Earlier ignored failed-run stores and inherited security findings remain. Representative task/timing studies, actual 200% browser zoom, screen-reader interoperability, Docker/Nginx, hosted CI, clean OS, native Word and live Codex container login were not newly verified.


## Application comment audit — 2026-10-26

Document non-obvious intent at the implementation point, especially transaction/cancellation ownership and security limits. Avoid boilerplate comments on straightforward CRUD and preserve existing useful explanations. Verify against a pre-audit working-tree snapshot rather than HEAD because unrelated changes already exist. Do not broaden a comment audit into behavior/security remediation or generated-contract edits. Audit scope/index: docs/developer/COMMENT_AUDIT.md.


## Git lock diagnosis — 2026-10-26

Commit troubleshooting found a zero-byte .git/index.lock last modified October 25 at 12:41 p.m. local time, with no git/ssh/gpg process matching the read-only process check. This suggests an abandoned index lock; the originating operation is unknown and a process snapshot cannot exclude later activity. Guidance: finish/close Git operations, remove only the stale index.lock, then retry the commit. The lock was not removed; no staging, commit, remote, application/service/data/model changes or product tests occurred. All six ending documents maintained; original blueprint and prior verification limits preserved.

