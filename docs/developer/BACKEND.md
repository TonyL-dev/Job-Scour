# Backend implementation guide

Source review: 2026-10-15. Read [the handbook overview](README.md) first. Paths and examples below describe current source unless explicitly labeled as a future-project recommendation. Repository rules take precedence over illustrative examples.

## Contents

1. [Architecture and dependency direction](#1-architecture-and-dependency-direction)
2. [Domain map](#2-domain-map)
3. [Application startup and HTTP lifecycle](#3-application-startup-and-http-lifecycle)
4. [Python conventions and contract design](#4-python-conventions-and-contract-design)
5. [Routers and dependency injection](#5-routers-and-dependency-injection)
6. [Services and cross-domain coordination](#6-services-and-cross-domain-coordination)
7. [Repositories, models and migrations](#7-repositories-models-and-migrations)
8. [Transactions, history and concurrency](#8-transactions-history-and-concurrency)
9. [AI and evidence boundaries](#9-ai-and-evidence-boundaries)
10. [Long-running work and streams](#10-long-running-work-and-streams)
11. [Rendering, import and private assets](#11-rendering-import-and-private-assets)
12. [Privacy, errors and operations](#12-privacy-errors-and-operations)
13. [Tests and verification](#13-tests-and-verification)
14. [Change and review recipes](#14-change-and-review-recipes)

## 1. Architecture and dependency direction

The backend is a **modular monolith**: one deployable FastAPI process containing business domains. Domain separation is implemented through Python packages and responsibilities rather than network boundaries. This keeps local operation simple while preventing one undifferentiated application service from owning everything.

The normal call direction is:

```text
HTTP request
  -> router.py       transport adaptation, dependencies, status/headers/stream lifetime
  -> service.py      use-case rules, coordination, validation, allowed state transitions
  -> repository.py   owner-scoped queries, conditional writes, persistence serialization
  -> models.py       SQLAlchemy mappings and database constraints

schemas.py           typed inputs/outputs exchanged across those boundaries
core/                shared mechanisms, not product use cases
ai/                  exclusive model endpoint/subprocess boundary
rendering/           database-free document production
```

This is a responsibility rule, not a claim that every package has identical files. `health` needs no business table model. `auth` currently supplies local ownership, not a complete HTTP authentication domain. `ai` contains adapters/pipelines and persistence helpers rather than a public CRUD router. Resume generation is a substantial sub-workflow inside `resumes` with its own `generation_*` files.

The code uses functions and ordinary typed data extensively. It does not require a class for every service or an abstract base repository. Classes appear when they own state or contracts: ORM/Pydantic models, `Gateway`, `RunManager`, `WorkspaceBarrier`, and `LockState`. Do not introduce interfaces solely to mirror every existing function.

The layering is pragmatic. Services and some repositories raise FastAPI `HTTPException`; this is not a framework-independent domain core. Services receive synchronous SQLAlchemy sessions, and some simple repository operations commit internally. A future project can choose transport-neutral errors and stricter transaction units, but should document those as a deliberate variant rather than describing them as this implementation.

## 2. Domain map

All paths in this table are under [`backend/app`](../../backend/app).

| Package | Owns | Key files and important relationships |
|---|---|---|
| `core` | Settings, engine/session construction, ownership mixin, HTTP policy, epochs, encryption and private-file primitives | `config.py`, `database.py`, `workspace.py`, `http.py`, `model_registry.py`, `encryption.py`, `cipher_database.py`, `private_files.py` |
| `auth` | Fixed local owner lookup/initialization and `Owner`/`Database` dependencies | `service.py`, `repository.py`, `models.py`; server mode refuses workspace access |
| `health` | Liveness, migrated-storage readiness, synthetic PDF doctor | `router.py` -> `service.py` -> `repository.py`; `doctor.py` is operational tooling |
| `career` | Twelve typed career/evidence categories, parent relationships, retirement and revision guards | `schemas.py`, closed `MODELS` registry in `models.py`, `service.py`, `repository.py` |
| `resumes` | Resume Document v1, master/tailored saves, source hydration, immutable versions, restore/duplicate/export | `schemas.py`, `models.py`, `service.py`, `repository.py`, `router.py` |
| `resumes/generation_*` | Persisted generation runs, suggestions, partial checkpoints, review and commit | `generation_service.py` coordinates jobs, career, AI and rendering; `generation_repository.py` owns its SQL |
| `settings` | Endpoints, profiles, task assignments, provider setup/consent and model tests | Service validates configuration and calls AI boundary for connectivity/inference tests |
| `ai` | Model gateway, Codex adapter, prompt files, output/evidence checks, retrieval, synthetic evaluations | `gateway.py`, `codex.py`, `service.py`, `generation.py`, `retrieval.py`, `phase6.py`, `operations.py`, prompt/evaluation modules |
| `jobs` | Saved job descriptions, validated analysis snapshots, cache identity and current-evidence matching orchestration | `service.py` calls AI/retrieval; `router.py` owns POST stream lifetime |
| `ats` | Deterministic reports for an exact resume version and optional saved job analysis | Measures actual PDF/extracted order; no model calls |
| `applications` | Exact submitted version/analysis/letter links, stages, dated events and follow-ups | Revisioned writes/events; no external notification delivery |
| `privacy` | Passcode/session control, complete owner export/deletion and offline encryption conversion | `service.py`, `repository.py`, `router.py`, `encrypt_database.py`, `encrypt_store.py` |
| `importers` | Durable parse/review runs, excerpts, candidate graph, atomic approved career commit and opt-in originals | `parser.py` handles bounded formats; `service.py` coordinates review/remapping |
| `profile` | Bounded question sessions and explicitly confirmed user answers against active evidence | Uses AI question generation; does not treat model guesses as career facts |
| `cover_letters` | Sourced paragraphs, generation/review, immutable letter versions and exports | Separate from resumes; application links reference exact versions |
| `prompt_management` | Immutable bounded preferences, baseline/candidate reports and guarded activation | Calls AI evaluation; does not expose unrestricted system prompt replacement |
| `templates` | Safe custom declarations, versions, measured findings, retirement and private PNG assets | `validation.py` constrains HTML/CSS/assets; rendering remains a leaf dependency |
| `rendering` | HTML construction, Chromium PDF bytes/page count/cache and semantic DOCX | `service.py`, `docx.py`, bundled fonts/licenses; no SQL |

The twelve career categories are experience, achievement, project, education, course, skill, skill evidence, certification, volunteer experience, award, publication and custom entry. They map to concrete relational models, not an unrestricted JSON table. The generic CRUD plumbing uses a closed mapping so shared code still operates on explicitly approved types.

The largest orchestration modules, especially generation, intentionally coordinate multiple domains. Do not put their workflow into a router or query another domain's tables directly to save an import. Prefer public service behavior and detached DTOs; repository-to-repository persistence coordination should remain explicit where a shared transaction requires it.

## 3. Application startup and HTTP lifecycle

### Construction versus startup

[`main.py`](../../backend/app/main.py) exposes `create_app(settings=None)` and a module-level `app`. Construction assembles routes, middleware and OpenAPI metadata. Database resource construction happens in the FastAPI lifespan, which lets contract export build the application without opening the career database.

Lifespan performs the following work:

1. Clear the process-local render cache.
2. Build the configured engine.
3. Verify protected storage and read the local passcode state through privacy repository functions.
4. Recover interrupted cover-letter/import state.
5. Initialize the workspace barrier, deleting flag, lock state, AI gateway and generation manager. The manager recovers interrupted generation status.
6. Serve requests.
7. On shutdown, cancel importer/AI operations, close generation work, clear the render cache and dispose the engine.

It does not call `Base.metadata.create_all()` or automatically apply Alembic migrations. Migration is an explicit task for native installation; the container startup command runs it before Uvicorn.

[`__main__.py`](../../backend/app/__main__.py) is the native process entry point. [`core/config.py`](../../backend/app/core/config.py) uses Pydantic Settings with `APP_` environment names, `.env` support and a cached settings accessor. `database_url` accepts the supported SQLite or PostgreSQL/psycopg driver forms; ports are bounded. Some security/provider keys are deliberately read by their own infrastructure modules rather than exposed as ordinary settings response fields.

### Request path

For a typical private write, `PrivateHTTP` applies request-body/privacy policy, workspace middleware checks deletion, origin and lock state, and local trusted-host policy rejects unapproved hosts. FastAPI then validates parameters/body and resolves dependencies. The router calls a service and serializes its typed response. Workspace middleware checks whether access was revoked while the response was being prepared.

Middleware ordering and SSE lifetime matter: a check before starting a response cannot by itself revoke future stream events. Stream loops and database sessions have their own epoch checks. CORS is also not authorization; write-origin checks, host restrictions, the local-mode guard and ownership serve different purposes.

`core/http.py` bounds write bodies to 4 MiB before JSON parsing, including streamed/chunked input, and adds private response headers. Nginx adds production browser policy and the matching body limit. An upload-specific limit may be lower, and base64 request encoding adds overhead; do not equate the HTTP byte cap with a guaranteed file payload size.

## 4. Python conventions and contract design

### Style and typing

[`pyproject.toml`](../../backend/pyproject.toml) sets Python 3.12 as Ruff/mypy's target, a 100-character Ruff line length, lint groups `E/F/I/UP/B`, first-party import sorting for `app`, and strict mypy with the Pydantic plugin. Functions are snake_case; model/class names are PascalCase. UUIDs, dates, decimals, unions and `Literal` values describe domain data explicitly. Modern `list[T]` and `T | None` syntax is normal.

Imports distinguish infrastructure, another domain service and the local repository. Local imports appear in some cross-domain paths to avoid import cycles and defer optional capabilities. They are an existing implementation technique, not permission to hide new cycles without explaining the dependency.

### Pydantic versus ORM models

`schemas.py` describes accepted/returned data and boundary validation. `models.py` describes persisted tables, columns, indexes and database constraints. These are related but different responsibilities. An ORM row is not automatically a safe API response.

[`career/schemas.py`](../../backend/app/career/schemas.py) supplies `Contract`, with `extra='forbid'` and whitespace stripping, and bounded text types. Most product contracts build on this base. Unknown input fields reject instead of silently becoming accepted state. Date validation rejects an end before the start and a `current` entry with an end date. Achievements require exactly one experience/project parent. `CareerInput` is a discriminated union: the `type` selects a known typed body.

Validation exists at three levels:

| Level | Example | What it cannot establish alone |
|---|---|---|
| Schema | Date ordering, enum, source-reference shape, list bounds | Whether a referenced record belongs to the owner |
| Service | Active parent chain, correct section/source type, protected AI edits | An atomic concurrent update unless persistence also checks it |
| Database | Foreign key, owner/parent pair, uniqueness, check constraints | Whether prose is supported by factual evidence |

[`resumes/schemas.py`](../../backend/app/resumes/schemas.py) defines the canonical content tree:

```text
ResumeDocument(schema_version=1)
  header(name, contact fields, links)
  sections[]
    key, type, title, visible, locked
    items[]
      key, text, origin, source_refs[], locked, facts, experience_summary=false
  metadata
    template_id, target_page_limit, job_description_id
    bounded style_overrides, optional immutable custom_template snapshot
```

Section/item keys must be unique across the document. Duplicate source refs reject. AI-origin text needs references at schema level; service rules determine whether those references actually authorize that text. `DisplayFacts` is rehydrated from stored career facts for new editing paths, rather than trusting a caller's employer/title/date values. Schema version 1 is an explicitly supported format, not a promise of automatic arbitrary-version conversion.

`experience_summary=true` is an additive schema-v1 presentation flag, allowed only in experience sections. Such item text must fit one line and 500 characters and pass a conservative sentence-boundary check (punctuation followed by whitespace and more text rejects, including dotted abbreviations). Old snapshots default to false without database rewrites or a migration. HTML/PDF and DOCX render summaries as ordinary paragraphs and duties as bullets. Generation preserves this flag, supplies its limit to rewriting, and records invalid proposals as rejected; services revalidate internally assigned content before source resolution. Company/title/dates still come only from owned career records. The studio uses the existing career-save API and description evidence field; resume text edits do not silently change stored career evidence.

### Contract generation

[`scripts/export_openapi.py`](../../scripts/export_openapi.py) builds the app without lifespan, serializes OpenAPI deterministically and writes `frontend/src/api/openapi.json`. `openapi-typescript` produces `schema.d.ts`; the frontend's `openapi-fetch` uses its `paths` type.

Run from the repository root after contract changes:

```text
python scripts/tasks.py api
python scripts/tasks.py api-check
```

`api-check` compares exported JSON and newly generated TypeScript against checked-in artifacts. It does not run migrations or prove behavior. Generated declarations cannot runtime-validate SSE JSON, decrypted files or model output; those require their own checks.

## 5. Routers and dependency injection

[`auth/service.py`](../../backend/app/auth/service.py) defines reusable annotated dependencies:

```python
Owner = Annotated[UUID, Depends(local_owner)]
Database = Annotated[Session, Depends(get_session)]
```

`local_owner` refuses server mode and asks the auth repository to ensure the fixed local identity. `get_session` creates a request session from the app engine, binds it to the workspace epoch, yields it and closes it. There is no blanket auto-commit at dependency exit.

The actual career creation route illustrates the intended scale:

```python
@router.post("", status_code=201)
def create(data: CareerInput, session: Database, owner: Owner) -> CareerRecord:
    return service.save(session, owner, data)
```

The router chooses path/method, status and response contract. It does not choose a table, validate parent ownership with SQL or call a provider. File/download routers additionally select media type, filename and headers. Streaming routers can own disconnect detection, event framing, heartbeats and sanitized transport errors; that extra transport logic does not make them the owner of model decisions.

When adding a route, inspect ordering of fixed subpaths and parameterized paths, declare a typed return/response model, and register its router in the factory. Owner identity is never accepted from the browser to bypass `Owner` resolution.

## 6. Services and cross-domain coordination

Services implement verbs meaningful to the product: save, retire, validate, analyze, assemble, review, commit, restore, activate. They validate state and orchestrate repositories/other services.

[`career/service.py`](../../backend/app/career/service.py) demonstrates this pattern:

- `get` checks existence and follows parent chains so inactive ancestry is not treated as active evidence.
- `save` checks referenced parents before calling the repository and translates integrity failures into a safe 409 response.
- `forms` derives approved form descriptions from Pydantic properties; the browser does not receive an arbitrary schema execution engine.
- `save_if_current`, `guard_records` and repository revision guards support larger transactional workflows.

[`jobs/service.py`](../../backend/app/jobs/service.py) demonstrates orchestration rather than simple CRUD. It resolves the configured analysis profile, seeds the immutable prompt snapshot, builds a fingerprint from text/configuration/prompt/schema/extraction version, reuses or saves a validated analysis, then matches against current career evidence and persists that match. A cached job analysis does not authorize stale career retrieval.

DTO detachment is significant. Returning a validated schema object or explicit value structure means later session expiration/refresh will not trigger lazy SQL inside a service. Some narrow repository APIs do return mapped rows for immediate persistence operations; do not generalize that into unrestricted ORM graph traversal across services. In particular, job analysis results were deliberately detached to avoid implicit queries after commits.

Services do not invent a generic abstraction for unrelated business workflows. Import review, generation review and prompt activation each have different acceptance rules, even though all use a revision number.

## 7. Repositories, models and migrations

### Persistence conventions

[`core/database.py`](../../backend/app/core/database.py) defines `Base` and `OwnedRecord`: UUID primary key, indexed owner FK and UTC timestamps. Domain models add explicit relationships and constraints. Composite owner/parent references prevent an otherwise valid foreign ID from linking to a different owner. Query filters must still include the owner; constraints alone do not protect reads.

Repositories use SQLAlchemy 2 `select`, `update`, `Session.scalar/scalars` and explicit writes. A normal lookup includes both identity and `user_id`. Career lookups also exclude retired records. Serialization explicitly builds a Pydantic contract; internal fields such as normalized skill indexes are not casually exposed.

`build_engine` enables pool health checks and hides SQL parameter values in engine diagnostics. SQLite connections enable foreign keys and secure deletion. A configured full-database passphrase selects file-backed SQLCipher construction. These are shared connection mechanisms, not business queries.

### Retirement and archival behavior

Retirement is a timestamp/state change rather than erasing referenced facts. New active library reads/matching exclude retired data and inactive ancestry. Saved document versions already contain historical display facts. Download/restore rules intentionally differ from introducing a new current-source claim. Do not “refresh all history” from the live career tables.

### Alembic owns schema

[`migrations/env.py`](../../backend/migrations/env.py) configures migration metadata/environment. [`core/model_registry.py`](../../backend/app/core/model_registry.py) registers the complete domain catalogue for offline storage validation. The migration chain includes foundation identity, career/resumes, settings/jobs, generation/review, provider support, ATS/tracker, and ordered Phase 6 additions through `606f_templates`.

For a new persisted concept:

1. Define the mapped table and constraints, including ownership, lookup uniqueness and parent semantics.
2. Register the model where required by migration/offline validation metadata.
3. Create a new migration after the current head; do not rewrite a deployed historical revision.
4. Review generated DDL for SQLite and PostgreSQL, data backfills, nullability and downgrade consequences.
5. Test migration/storage behavior with synthetic stores and preserve existing immutable snapshots.
6. Extend export/delete/encryption handling; a new table is also a lifecycle responsibility.

Use the backend environment and Alembic configuration. `python scripts/tasks.py migrate` is a real migration of the selected database, not a harmless schema check. The check suite is not permission to migrate a developer's personal store.

## 8. Transactions, history and concurrency

### Who commits?

Simple repository writes often commit and refresh internally. Composable operations accept `commit=False` and flush so a coordinating workflow can commit multiple related changes atomically. Read the exact callee before nesting operations: calling a helper that commits can accidentally end the transaction you intended to keep open.

`flush` sends pending writes and exposes constraint failures/generated IDs within the transaction. `commit` finalizes the unit and normally expires ORM attributes. `refresh` reloads a row. `rollback` is necessary after integrity errors before the session can be used safely again. The request session dependency only closes the session; it is not the transaction policy.

### Optimistic compare-and-update

[`resumes/repository.py`](../../backend/app/resumes/repository.py) updates a document only when owner, ID and `expected_version` still match. It then adds version `N+1` with the entire content snapshot and a SHA-256 digest. Metadata advancement and version insertion commit together.

The service also checks the observed version first for understandable errors, but the conditional SQL update is the atomic race protection. If two clients both read version 8, one can save version 9; the other receives a conflict. A disabled save button cannot replace this protection because requests/tabs/processes can race.

One gold-standard master per owner is enforced by both transactional flag handling and a partial unique index. Unchanged saves are deduplicated at the service level. A content hash records identity/integrity for application behavior; it is not a digital signature or independent tamper-proof audit log.

### Exact version identity

ATS reports, application submissions and committed generation output point to exact saved version IDs. Restore appends a historical snapshot as a new version. Duplicate creates another document with lineage. Neither rewrites the original. The `MasterResume` response name is historical: it can carry a `kind='tailored'` document, so callers must inspect `kind` rather than infer it from the TypeScript/Python type name.

### Current-source checks after long operations

Models and rendering can take time. A source valid at the start can be edited or retired before acceptance. Generation/matching/import/profile workflows therefore use current snapshot hashes, review revisions, source checks and guarded writes at their persistence boundaries. `career.repository.guard_active` uses a conditional no-op write to hold active source rows through the transaction without changing their provenance timestamps.

### Workspace epochs

[`core/workspace.py`](../../backend/app/core/workspace.py) binds each session to an epoch. Invalidation advances the workspace epoch. Session execution/flush/commit checks reject stale bindings. A reentrant lock serializes commit against invalidation; event hooks release the lock after commit/rollback. Stream readers also check the epoch around emitted events. Renderer caching has a separate invalidation epoch to reject late cache insertion.

This solves a different problem from document revisions: a review can have the current document revision yet still be unauthorized after a workspace lock/delete. The known automatic-expiry gap remains: expiry does not consistently initiate the epoch invalidation used by explicit lock/delete. Do not cite the existence of barrier hooks as proof that every revocation trigger is correct.

## 9. AI and evidence boundaries

### Provider boundary

Only the [`ai`](../../backend/app/ai) package calls model endpoints or launches inference. `settings`, jobs, resumes and Phase 6 services request typed AI operations. They do not use HTTPX or subprocesses to add an alternate model path.

[`ai/gateway.py`](../../backend/app/ai/gateway.py) owns provider validation, capacity, budgeting, structured requests and response handling. It allows one active inference, bounds active-plus-waiting calls to five and limits admission waiting to 30 seconds. Settings updates are tracked so a queued stale endpoint configuration cannot silently be used later. Already transmitted data cannot be retroactively undisclosed.

HTTP providers disable inherited proxies and redirects. Endpoints use bounded consent/URL rules; API keys are named environment references rather than stored secret values. Structured output modes still converge on Pydantic validation and bounded retry. Context budgeting uses a conservative UTF-8 byte estimate, not an exact tokenizer; it refuses overflow rather than silently cutting facts.

[`ai/codex.py`](../../backend/app/ai/codex.py) is the native inference launcher. It uses CLI-owned ChatGPT login, a temporary working directory, schema output and ephemeral execution, ignores user rules/configuration, restricts tools/capabilities, bounds process output/time and kills the owned process tree on cancellation. It does not scrape OAuth tokens or forward application keys. Old unsupported CLI versions must be updated rather than bypassing required controls.

Codex's fixed URL marker is provider identity, not an arbitrary HTTP endpoint. Codex does not provide embedding assignments. Sampling and output length are provider-managed; a profile output-token value reserves context budget but does not enforce a CLI output cap. `default` records configured selection, not a resolved model identity. These statements describe the adapter's source contract, not fresh compatibility verification in this documentation session.

### Prompt and output ownership

Packaged JSON prompts are deliberately versioned and retained. Job analysis v2, generation v3 and Phase 6 v2 are the documented active families. Prompt snapshots/digests and output schemas participate in provenance/cache identity. Changes require deliberate new versions and synthetic/live evaluation appropriate to the provider.

Job text and source text are untrusted data, not model instructions granting authority. Exact job evidence quotes must appear in the posting. Model extraction uses closed schemas and bounded repair/validation. Generation additionally enforces owner-valid source membership, exact numeric/unit normalization, technology aliases and conservative claim vocabulary before a separate support verifier.

`facts.v1` contains factual source context without ranking/review metadata. An importance score must never become evidence of years/impact. Structured metric fields are authoritative even if prose omits the number. Decimal normalization preserves precise values, signs and percentages. Summary context uses visible selected evidence, including protected records, rather than the whole library.

Matching combines lexical evidence and optional vector relevance. Similarity is not proof of a skill. Keyword gaps are output guidance and never become career records. Cached vectors include owner/entity/configuration/content identity; retrieval must recheck current facts before persisting a match.

Prompt management exposes bounded preferences with exact passing report/configuration/revision gates. It is not a UI for replacing system guardrails. Evaluation tools use synthetic disposable databases/fixtures; never substitute a real owner's database for convenience.

## 10. Long-running work and streams

### Two lifetimes

| Property | Job analysis | Resume generation |
|---|---|---|
| Initiation | Analyze saved job by request | Create persisted generation run |
| Ownership | Request-owned task | Local `RunManager` task |
| Progress | POST SSE response | GET SSE observer of saved events |
| Browser disconnect | Cancels request-owned inference | Observer disconnect does not cancel run |
| Persistence | Validated analysis/match/cache results | Run, checkpoints, suggestions, decisions and exact committed output |
| Restart | Request ends; retry saved job | Interrupted run marked failed; partial snapshots retained |

[`jobs/router.py`](../../backend/app/jobs/router.py) frames progress/result/error events, emits heartbeats, bounds its event queue and cancels tasks in `finally`. An error after SSE headers have been sent must be an event or stream closure; it cannot become a new ordinary HTTP error response.

[`resumes/generation_service.py`](../../backend/app/resumes/generation_service.py) contains the pipeline and `RunManager`. The manager tracks up to four local tasks and runs one pipeline through its semaphore. It validates master/job/scope/configuration before queuing. A worker owns its own session; a request session is not shared casually across concurrent tasks. Cancel retains partial suggestions and durable terminal status.

Generation events carry sequence IDs; the backend observer supports an `after` position and checks the workspace epoch. The current browser also polls the full run, which provides recovery when EventSource closes. Do not promise automatic mid-stage resume: persisted results survive, but interrupted model execution is not transparently resumed.

Generation stages include analysis/retrieval, bounded ranking/budgeting, unlocked rewrites, summary, evidence verification and fitting. Fitting measures actual PDFs, removes eligible unlocked bullets/older groups, may request verified condensation and can apply bounded spacing/font changes only when permitted. Protected overflow remains a warning rather than breaking locks. Sparse-final-page text length is a heuristic requiring visual inspection.

`ai/operations.py` separately tracks cancellable request-owned Phase 6 work by owner/run identity. Import parsing also has explicit cancellation/recovery. These are process-local coordination mechanisms. Multiple backend workers/replicas would require a new owner-scoped worker, cache and revocation design; adding Uvicorn workers is not a safe scaling toggle for the current architecture.

## 11. Rendering, import and private assets

### PDF and DOCX

[`rendering/service.py`](../../backend/app/rendering/service.py) accepts a validated document and returns HTML, PDF bytes, actual page count and HTML hash. It escapes content, applies bounded style metadata, embeds packaged Noto fonts and constructs semantic document markup. Chromium disables page JavaScript and outbound requests/offline access for content rendering, waits for fonts and prints the exact artifact. pypdf counts actual pages.

Rendering is synchronous Playwright work. Async orchestration paths must use the existing offloading pattern where needed rather than block the event loop with a direct call. Sync FastAPI handlers have a different execution context; “the app is async” does not make synchronous database/browser calls non-blocking automatically.

The process-local cache is keyed by the complete HTML artifact hash, with 60-second validity, eight entries and 24 MiB payload bounds. Expired entries are removed on access. A semaphore permits two renders with a five-second admission timeout. Privacy/lifecycle invalidation clears entries and rejects late insertion. Validation must happen before cache access; a cached PDF is not permission to bypass current-source checks. Historical exports intentionally render stored snapshot facts.

[`rendering/docx.py`](../../backend/app/rendering/docx.py) produces semantic OOXML rather than converting arbitrary HTML. It preserves text/headings/bullets/links/factual content and embeds local fonts. Unsupported custom mappings refuse rather than silently degrading. Word-processor pagination is not promised to match Chromium PDF.

The audit records a containment limitation: the Chromium launch does not explicitly enable its sandbox. Offline routing and disabled page JavaScript are not OS process containment. Preserve the documented distinction.

### Imports and templates

[`importers/parser.py`](../../backend/app/importers/parser.py) applies format/signature/archive/content/size checks and bounded parsing. Parsing runs in an isolated Python invocation, but Python `-I` is interpreter isolation, not an OS sandbox. OCR and arbitrary layout reconstruction remain outside supported scope.

Import runs persist parsing/review/failure separately from career facts. Candidates carry excerpts/locators and temporary graph identities. Review can correct/accept/reject them. Commit remaps accepted parents into actual career IDs in one transaction under the review revision. A parse/extraction success must never silently write career facts. Originals are memory-only unless retention is explicitly chosen.

Custom templates accept only the approved inert HTML/CSS subset. Sanitized local PNG assets require encryption. Template save measures a real synthetic PDF and stores heuristic findings. Immutable snapshots carry the presentation/asset copies required for old exports even after template retirement. “Custom” does not mean arbitrary executable template code.

[`core/private_files.py`](../../backend/app/core/private_files.py) uses AES-GCM with random nonces and authenticated owner/asset context. `APP_UPLOAD_KEY` supplies a base64-encoded 32-byte key, with `APP_ENCRYPTION_KEY` fallback. This mandatory private-asset protection is independent of optional field/database encryption. Missing/wrong keys fail closed; never invent a new temporary key to make an existing encrypted asset readable.

## 12. Privacy, errors and operations

### Distinct controls

| Control | Protects | Does not establish |
|---|---|---|
| Local passcode | UI/API unlock with salted scrypt, process-local cookie sessions and bounded failures | Public multi-user authentication or disk encryption |
| Workspace epoch | Pending session/stream/commit revocation when invalidated | Correct automatic-expiry trigger behavior; known audit gap remains |
| SQLCipher + `.salt` | Complete file-backed SQLite database using derived boot-time key | PostgreSQL encryption or encrypted downloaded exports |
| Field AES-GCM | Selected descriptive text/JSON; blind skill equality index | Encryption of queryable IDs/dates/numbers/status/configuration metadata |
| Private asset AES-GCM | Retained originals and PNG assets | Erasure of external/downloaded/provider copies |

Passcode sessions have a 30-minute server expiry; the browser initiates inactivity lock after 15 minutes. Process restart invalidates sessions. Cookies are HTTP-only and SameSite Strict. Read the current cookie/deployment code before adapting it for remote HTTPS; the stock local contract is not remote authentication.

Offline conversion creates/verifies a new SQLCipher file and preserves the source; optional field conversion is explicit and transactional. Store keys stay in the backend environment and out of model children, logs and exports. Fail-closed checks cover wrong/missing keys, tampering and incomplete protected-field conversion. The tested SQLCipher configuration omits the wheel's crashing optional memory-security pragma; no memory-hardening guarantee is supported.

Complete JSON export includes the owner data graph while excluding local identity/password hashes. ZIP export includes historical PDF artifacts. Typed delete-all removes the graph and caches/settings/assets/runs while retaining local identity/passcode. It coordinates cancellation and epoch invalidation against late results. New domains must be included in both operations and their tests. Deletion cannot remove provider records, downloads or user backups.

### Error contracts

Common responses have these meanings, though individual routes may specialize them:

| Status | Typical meaning | Client response |
|---|---|---|
| 401 | Wrong unlock credential | Correct credential; observe bounded retries |
| 403 | Untrusted origin or unsupported mode | Fix deployment/request configuration |
| 404 | Missing/unavailable owner-scoped record | Refresh selection; do not expose another owner's existence |
| 409 | Stale version/review/configuration or incompatible current state | Refresh/review before resubmitting |
| 422 | Invalid schema, sources, output budget or unsupported mapping | Correct input; blind retry is unhelpful |
| 423 | Workspace locked/revoked | Clear private UI state and unlock/reload |
| 429 | Bounded operation/queue/unlock admission | Wait or cancel outstanding work |
| 502/503 | Provider/renderer/storage availability or invalid response | Surface safe detail and actionable retry/configuration guidance |

Services generally raise safe `HTTPException` details; routers sanitize unexpected stream failures. Do not return raw provider stderr, SQL parameters, decrypted source content or arbitrary exception traces. Operational metadata can include timings/provider/token usage where available; prompt/response bodies are excluded from application logging. Provider-side logging is outside that control.

Liveness answers whether the process is running; readiness checks migrated storage. Doctor additionally renders synthetic content. None proves live provider authentication, end-user browser behavior or public deployment safety. Use logs/status to distinguish DNS, migration, key, database and provider failures rather than treating all 503 responses as “the API is down.”

## 13. Tests and verification

[`tests/conftest.py`](../../backend/tests/conftest.py) provides a temporary migrated SQLite URL and resets cached configuration. Tests use FastAPI `TestClient(create_app(Settings(...)))`, real migrations/storage and synthetic fixtures. Some test modules supply specialized fixtures; read their environment selection rather than assuming every fixture is interchangeable.

| Concern | Source/examples | Evidence boundary |
|---|---|---|
| Startup, readiness, host/CORS, identity/migrations | `test_foundations.py` | Real local FastAPI/storage behavior |
| Career/manual snapshots/rendering | `test_phase1.py`, `test_master_selection.py` | Source/ownership/history plus renderer tests where configured |
| Provider/settings/matching | `test_phase2.py`, `test_codex.py`, `test_matching_concurrency.py` | Mocked transports/process controls do not prove fresh provider quality |
| Generation/review/locks/races | `test_phase3.py` | Synthetic accepted/rejected proposals and persistence controls |
| ATS/tracker/privacy/encryption | `test_phase4.py` | Exact-version/data lifecycle and concurrency controls |
| Admission/cache/HTTP hardening | `test_phase5.py` | Resource/privacy policy regressions |
| Imports/profile/letters/prompts/templates/DOCX | `test_phase6_*.py`, `phase6_fixtures.py` | Synthetic feature and adversarial cases |
| Full browser workflows | `scripts/e2e.py`, `tests/e2e_server.py` | Real browser/PDF/encrypted synthetic store; model responses are synthetic |
| Model quality | AI/generation/Phase 6 evaluation commands | Explicit real provider calls on synthetic input; record exact configuration |

`python scripts/tasks.py check` runs Ruff check/format-check, strict mypy, backend pytest, generated-contract drift, frontend lint/types/tests/build. Run `api` after contract changes. Audit checks dependencies. Rendering/browser changes need actual PDF/browser verification, not mocks alone. Release changes add e2e/fresh-install and applicable isolated container checks.

The recorded Phase 6 acceptance includes 81 backend and 20 frontend tests plus named native/Linux/browser/model checks. Those are historical results in `IMPLEMENTATION_STATUS.md`, not a fresh execution claim from this handbook. Hosted CI, physical clean-OS certification, native Microsoft Word and live Codex container account login remain unverified in that record. A workflow file is an instruction, not evidence it ran.

## 14. Change and review recipes

### Add an ordinary field

1. Determine whether it is source fact, snapshot content, presentation or operational metadata.
2. Update the owning schema/model; add a migration for stored relational changes.
3. Add service rules and explicit repository serialization; check encryption/export/delete behavior.
4. Regenerate OpenAPI/types; update request wrappers and UI using generated types.
5. Exercise valid/invalid input, ownership and existing snapshots. Do not assume adding a nullable column alone provides backward document compatibility.

### Add a new domain

Create a domain package with explicit schemas and use cases; add models/repository only if persistence is needed. Register the router, model catalogue and migration metadata. Integrate lifecycle/export/delete/cancellation if the domain stores data or starts work. Keep provider calls in `ai`, rendering database-free and public-server guards intact. Add one complete vertical slice before broad speculative helpers.

### Add long-running behavior

Decide request-owned versus durable-run behavior first. Define state transitions, admission, timeout, cancellation, recovery, terminal results and replay. Give background work its own session and current-access checks. Revalidate sources/configuration before writes after awaits. Test cancellation/lock/delete while holding the expensive step; a test that only cancels before the task starts misses the important race.

### Review a backend change

- Does the package own this decision, and are all SQL reads/writes in repositories or deliberate migration/infrastructure tooling?
- Does every lookup/write include the resolved owner and appropriate active-source checks?
- Can a helper commit midway through a larger transaction?
- Is the version/revision check atomic at the write, and is replay behavior explicit?
- Can old snapshots still export without borrowing mutable current facts/presentation?
- Can delayed work save or emit data after lock/delete/configuration change?
- Are model/provider/file/browser operations bounded, consented and confined to their owning boundaries?
- Are export/delete/encryption/model-registration and generated contracts complete?
- Do reported checks prove the changed environment/behavior, or only a mocked approximation?

For future projects, reuse these responsibilities and questions. Choose your actual identity model, database, transaction/error style, worker architecture and versions explicitly using [the architecture template](PROJECT_ARCHITECTURE_TEMPLATE.md) and [backend practices](../coding-practices/BACKEND_CODING_PRACTICES.md).
