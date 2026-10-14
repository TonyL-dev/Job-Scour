# Backend coding practices

A reusable engineering standard for Python, FastAPI, Pydantic, SQLAlchemy and Alembic services. Translate framework-specific examples when adopting another stack. This guide recommends patterns for new projects; it does not claim that its source repository implements every recommendation. Examples use a hypothetical projects domain and do not add endpoints to that application.

## Contents

1. [Adoption and priorities](#1-adoption-and-priorities)
2. [Structure and dependency boundaries](#2-structure-and-dependency-boundaries)
3. [Naming, typing and code style](#3-naming-typing-and-code-style)
4. [Configuration and application lifecycle](#4-configuration-and-application-lifecycle)
5. [Schemas and API contracts](#5-schemas-and-api-contracts)
6. [Router, service and repository patterns](#6-router-service-and-repository-patterns)
7. [Persistence, transactions and migrations](#7-persistence-transactions-and-migrations)
8. [Concurrency, versions and idempotency](#8-concurrency-versions-and-idempotency)
9. [Async work and background jobs](#9-async-work-and-background-jobs)
10. [Authentication, security and privacy](#10-authentication-security-and-privacy)
11. [External integrations and AI](#11-external-integrations-and-ai)
12. [Uploads, rendering and caching](#12-uploads-rendering-and-caching)
13. [Errors, logging and operations](#13-errors-logging-and-operations)
14. [Testing, tooling and deployment](#14-testing-tooling-and-deployment)
15. [Implementation and review checklists](#15-implementation-and-review-checklists)

## 1. Adoption and priorities

### Project adoption record

| Choice | Record before implementation |
|---|---|
| Product/use cases | Domain vocabulary, main workflows and exclusions |
| Python/dependencies | Supported interpreter(s), installer and lock mechanism |
| Framework/database | Versions, synchronous/asynchronous persistence, supported dialects |
| Identity/deployment | Local versus authenticated server, tenants, process/worker count |
| Data | Sensitivity, retention, deletion, export and encryption requirements |
| Contract | Wire naming, API versioning, pagination and error format |
| Workload | Request/job limits, deadlines, expected load and availability goals |
| Integrations | Permitted external destinations, credentials and consent policy |
| Quality/operations | Exact check, migration, audit, release and recovery commands |
| Exceptions | Decision records overriding this guide |

Default to domain modules, typed request/response schemas, explicit transactions, locked dependencies and deterministic business logic. Choose one persistence concurrency model deliberately. Start with the infrastructure the workload actually requires; Redis, microservices, event sourcing, vector extensions and generic repository frameworks are conditional choices.

Must make authorization, business invariants, cancellation and failure recovery enforceable in code. Do not rely on frontend controls or model instructions for correctness. Build a minimal vertical slice before expanding the entity catalogue.

## 2. Structure and dependency boundaries

```text
backend/
  app/
    main.py                       # composition, lifespan, middleware
    core/
      config.py                   # validated process settings
      database.py                 # engine/session infrastructure
      errors.py                   # safe common error contracts/mapping
      security.py                 # cross-domain security mechanisms
    auth/
      dependencies.py             # authenticated identity resolution
      service.py
      repository.py
      models.py
      schemas.py
    projects/
      router.py                   # HTTP adaptation
      service.py                  # business operations/transactions
      repository.py               # SQL/ORM access only here
      models.py                   # persistence mapping
      schemas.py                  # public request/response contracts
      errors.py                   # domain failure types if needed
    integrations/
      email.py                    # dedicated outbound adapter, if needed
    ai/                           # only model-call boundary, if needed
    rendering/                    # artifact leaf services, if needed
  migrations/
    versions/
    env.py
  tests/
    unit/
    integration/
    conftest.py
  pyproject.toml
  requirements.lock               # or the chosen tool's lockfile
  alembic.ini
  .env.example
  Dockerfile
```

Small domains can omit unnecessary files; do not add empty abstraction layers. Split a large service by cohesive use cases (`generation_service.py`, for example) or subdomain when navigation and responsibilities become unclear.

### Allowed call direction

```text
HTTP router -> domain service -> domain repository -> database
                        |
                        +-> another domain's public service
                        +-> bounded external/rendering adapter
main/lifespan -> infrastructure and domain runtime initialization
```

- Routers must not query SQL/ORM or implement business decisions.
- Services must not issue database queries. Repositories alone perform application queries; migration code and test setup are explicit exceptions.
- Repositories must not call HTTP integrations, renderers or models.
- Return detached values from repositories when crossing service/session boundaries. Lazy loading in a service is still a hidden database query.
- Another domain uses a deliberate public service contract, not another domain's router or internal ORM rows.
- Avoid cycles. Put workflow orchestration in the domain that owns the result or a deliberately named application service.
- `core` contains infrastructure, not a growing collection of domain rules.
- Database-free rendering and parsing adapters should remain leaf components.
- Only the AI module may invoke model endpoints or inference processes when AI exists.

For small projects, functions and module namespaces are often enough. Introduce classes/protocols when resource lifecycle, several implementations or a meaningful test boundary warrants them. Do not force every table into the same generic CRUD abstraction.

## 3. Naming, typing and code style

| Item | Convention | Example |
|---|---|---|
| Modules/packages | snake_case | `cover_letters`, `generation_service.py` |
| Functions/variables | snake_case | `create_project`, `expected_revision` |
| Classes/types | PascalCase | `ProjectCreate`, `ProjectRead` |
| Constants | UPPER_SNAKE_CASE | `MAX_UPLOAD_BYTES` |
| Boolean | Predicate | `is_active`, `has_permission`, `can_retry` |
| ORM model | Singular domain noun | `Project` |
| Table | Consistent plural snake_case | `projects`, `project_versions` |
| Foreign key | Related entity + `_id` | `project_id`, `owner_id` |
| Timestamp | Event + `_at` | `created_at`, `completed_at` |
| Date-only value | Event + `_date` | `due_date`, `start_date` |
| Request/response | Purpose suffix | `ProjectCreate`, `ProjectUpdate`, `ProjectRead` |
| Repository function | Query/mutation intent | `find_active`, `list_for_owner`, `append_version` |
| Test | Behavior | `test_stale_revision_does_not_append_version` |
| Migration | Tool revision + meaningful description | `..._add_project_versions.py` |

Use a single documented API-field naming convention. Internal Python remains snake_case even when wire aliases are camelCase. Name functions for the result or action, not `handle_data` or `manager`.

- Must annotate public functions, dependencies and DTO boundaries. Enable strict type checking for application code.
- Default to Pydantic schemas for validated public data and frozen dataclasses/typed DTOs for suitable internal values.
- Use `TypedDict` for a truly dictionary-shaped internal contract, not an unstructured bag replacing a schema.
- Narrow `object`/unknown data at boundaries; minimize `Any`, broad casts and unexplained type ignores.
- Use enums/literals for closed vocabulary and exhaustive handling for important state machines.
- Prefer explicit keyword arguments for ambiguous booleans or adjacent IDs.
- Keep functions cohesive, avoid deeply nested branching, and use guard clauses where they improve clarity.
- Do not use mutable function defaults. Avoid import-time side effects and global mutable sessions.
- Comments/docstrings describe invariants, units, transaction ownership, retries or security assumptions.
- Use a configured formatter/linter. Default to four-space Python indentation and a consistent configured line length.

Default tool choices are Ruff and strict mypy or pyright. Run tools with the repository's configuration. Do not use broad auto-fixes that ignore the project's interpreter target or intentional compatibility exceptions.

## 4. Configuration and application lifecycle

Must validate configuration at startup through typed settings. Use a documented environment prefix, sensible development defaults and explicit production requirements. `.env.example` includes names and safe examples only.

- Treat secrets as backend-only values and redact them from repr/logging/error output.
- Validate database schemes, hosts, origins, size/concurrency limits and feature combinations.
- Fail startup for incomplete encryption, unsafe required-auth configuration or invalid critical settings. Avoid fallback to a different store/provider after a security failure.
- Separate configuration values from user-managed persisted preferences. Explain their precedence and whether a restart is required.
- Do not call integrations, migrate schemas or open databases at module import.
- Build engines, clients and worker runtimes in the application lifespan/composition root. Dispose/close them on shutdown.
- Inject request sessions, identity, clients and limits deliberately. Each concurrent worker/task gets its own session.
- Separate liveness from readiness. A database outage should make readiness fail without misrepresenting whether the process is alive.
- A diagnostic command should use synthetic data and never imply migration/authentication/model compatibility it did not check.

Default local development binds to loopback. A public server requires an explicit authenticated deployment design; binding to a different interface is not enough. Validate forwarded headers/trusted proxies according to actual network topology.

## 5. Schemas and API contracts

### Boundary validation

Use distinct create/update/read schemas when permissions or fields differ. Never expose ORM rows wholesale or accept owner IDs, protected status fields and server timestamps through a general mass-assignment endpoint.

- Must bound strings, arrays, files, nesting and numeric ranges before expensive processing.
- Use `extra='forbid'` for closed write/model schemas where unknown fields should be rejected.
- Validate syntax/shape in schemas and business relationships in services/repositories.
- Encode relationship alternatives explicitly, for example discriminated unions or exactly-one-parent validation backed by database constraints.
- Keep PATCH field omission distinct from explicit null. Apply only supplied, allowed fields.
- Store instants consistently as timezone-aware UTC and date-only concepts as dates. Include units in metrics and use Decimal/minor units where exact arithmetic matters.
- Version durable JSON document schemas. Reject unknown versions or use explicit tested conversion; preserve original historical snapshots.
- Keep content facts separate from presentation options. Bound presentation schemas independently.

```python
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)


class ProjectRead(BaseModel):
    id: UUID
    title: str
    revision: int = Field(ge=1)
```

This minimal example leaves semantic whitespace policy to a deliberate validator/service rule. Do not silently normalize identifiers, passwords or user prose under a universal "strip everything" policy.

### HTTP design

- Default to resource-oriented paths with consistent plural names and stable IDs.
- Use POST to create or start an operation, GET for read-only operations, PATCH for partial edits and DELETE for the documented delete/retire action. Use PUT only with a clear replacement/idempotency contract.
- Return 201 for creation, 202 for accepted queued work and 204 only with an empty body, where appropriate.
- Bound list endpoints and define stable ordering, pagination limits and cursor/filter semantics. Avoid unlimited list reads by default.
- Expose safe structured errors with stable codes and optional field errors/correlation IDs. Clients should not parse English sentences to choose behavior.
- Document conflict/retry/cancellation semantics and which results are authoritative.
- Do not disguise deletion, analysis, paid actions or other mutations as GET requests.
- Generate OpenAPI deterministically without connecting to a personal database or calling providers.
- Regenerate frontend artifacts and check drift whenever contracts change. Commit generated files only according to the adopted policy; never hand-edit them.
- Prefer additive compatible changes. Breaking changes require a deliberate rollout/versioning strategy, especially with independent client deployments.

## 6. Router, service and repository patterns

### Router

The router resolves HTTP inputs/dependencies and adapts success/errors to the API contract. Authentication dependency composition is appropriate here; deciding whether a project can be archived is service logic.

```python
from fastapi import APIRouter

from app.auth.dependencies import CurrentOwner, Database
from app.projects import service
from app.projects.schemas import ProjectCreate, ProjectRead

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", status_code=201, response_model=ProjectRead)
def create_project(data: ProjectCreate, session: Database, owner: CurrentOwner) -> ProjectRead:
    return service.create_project(session, owner.id, data)
```

`Database` and `CurrentOwner` are illustrative typed dependencies supplied by the adopting project. They are not runnable imports from this source repository.

### Service

The service applies use-case rules, coordinates repository operations and owns the logical transaction. Pure calculations should not require FastAPI requests. Default in new projects to domain errors mapped centrally to HTTP; this is cleaner for CLI/jobs than throwing transport exceptions everywhere. Existing repositories may use HTTPException historically, which is not the reusable target pattern.

```python
from uuid import UUID

from sqlalchemy.orm import Session

from app.projects import repository
from app.projects.schemas import ProjectCreate, ProjectRead


def create_project(session: Session, owner_id: UUID, data: ProjectCreate) -> ProjectRead:
    # This use case owns a fresh session's transaction; repositories only flush.
    with session.begin():
        return repository.insert_project(session, owner_id=owner_id, title=data.title)
```

The returned DTO is built before the transaction closes; the context manager commits before returning to the caller. If commit fails, no successful response escapes. This pattern assumes a fresh session with no already-open transaction. Identity resolution or earlier queries can trigger SQLAlchemy autobegin: choose request-owned or explicit unit-of-work transaction ownership in that case instead of nesting `session.begin()` blindly. See [SQLAlchemy session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

### Repository

Repositories perform scoped queries/writes and create detached results while the session is valid. SQL constraints remain necessary even when services validate first.

```python
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.projects.models import Project
from app.projects.schemas import ProjectRead


def find_project(session: Session, *, owner_id: UUID, project_id: UUID) -> ProjectRead | None:
    row = session.scalar(
        select(Project).where(Project.owner_id == owner_id, Project.id == project_id)
    )
    if row is None:
        return None
    return ProjectRead(id=row.id, title=row.title, revision=row.revision)


def insert_project(session: Session, *, owner_id: UUID, title: str) -> ProjectRead:
    row = Project(owner_id=owner_id, title=title, revision=1)
    session.add(row)
    session.flush()
    return ProjectRead(id=row.id, title=row.title, revision=row.revision)
```

The illustrative model must define ID generation and the shown fields/constraints. Repository functions do not independently commit inside a larger atomic operation. Avoid leaking ORM rows across domains and relying on later lazy reads.

## 7. Persistence, transactions and migrations

### Ownership and integrity

- Must scope reads and writes by authenticated owner/tenant, not only by record ID.
- Revalidate referenced parent records under the same owner. Where appropriate, enforce composite owner/parent foreign keys as defense in depth.
- Put uniqueness, foreign keys, check constraints and invariants that can be expressed safely in the database.
- Index measured lookup/filter/order paths, including ownership. A UUID index is not an authorization check.
- Use explicit active/deleted predicates when soft deletion exists. Define how retired ancestors affect new operations and historical references.
- Do not soft-delete every table by habit. Choose retirement, hard deletion or immutable retention according to the domain and privacy policy.
- Bound queries and avoid N+1 access. Select required columns or use deliberate eager loading within repositories.
- Normalize search/uniqueness keys explicitly while preserving display text. Choose case/Unicode behavior deliberately across supported dialects.

### Transactions

One business operation must commit its dependent writes atomically. Choose one transaction owner: a request unit of work or the outer service. Repositories flush and return data; helpers must not secretly commit.

- Keep transactions short. Do not hold locks/sessions open across slow model, HTTP or rendering work.
- Read a bounded snapshot, perform slow work, then open a fresh transaction and revalidate revisions, ownership, sources and revocation before persistence.
- Translate expected constraint races to safe domain conflicts; roll back the failed transaction before reusing the session.
- Do not swallow an IntegrityError and continue writing in the failed session.
- For external side effects plus durable state, use an outbox/workflow when delivery guarantees matter. A database commit cannot atomically commit a remote HTTP request.
- Never share Session/AsyncSession across concurrent tasks. SQLAlchemy describes a Session-per-thread and AsyncSession-per-task model in its [session guidance](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

### Migrations

Must use Alembic or the chosen migration system as schema authority. Runtime `create_all()` is not a production migration strategy.

1. Update mappings and create a deliberate revision.
2. Review generated operations, constraints, data conversion and lock/downtime impact.
3. Test a fresh install and an upgrade from the supported previous schema using synthetic representative data.
4. Verify schema drift and relevant database dialects.
5. Document rollback/recovery, including when downgrade would lose data and must be refused.

Prefer expand/backfill/contract for independently deployed clients/workers. Backfills need resumability, bounds and validation. SQLite table rebuilds and foreign-key behavior differ from PostgreSQL; exercise actual supported engines. Dual-database support is conditional and adds real testing cost.

Back up before risky conversions, verify the destination and preserve the source until an authorized retention/deletion decision. Encryption sidecars, salts and keys are part of the recovery contract.

## 8. Concurrency, versions and idempotency

### Optimistic concurrency

Require an expected revision for contested edits. Compare and update atomically; a read followed by an unguarded write is not sufficient.

```python
from sqlalchemy import update

statement = (
    update(Project)
    .where(
        Project.owner_id == owner_id,
        Project.id == project_id,
        Project.revision == expected_revision,
    )
    .values(title=new_title, revision=expected_revision + 1)
)
result = session.execute(statement)
if result.rowcount != 1:
    raise RevisionConflict()
```

This illustrative repository fragment assumes a driver with the project's tested rowcount semantics and a mapped integer revision. Perform dependent version/event writes in the same transaction. Return a safe conflict without overwriting either version; avoid leaking another tenant's existence.

### Immutable history

Conditional: if history/provenance matters, append version snapshots rather than mutate prior versions. Store schema version, revision, creator/origin, lineage, hash and necessary presentation/dependency snapshots. Reference exact versions from reports, submissions and downloads. Restore creates a new version with lineage; it does not rewrite history.

Distinguish current-source validation for new facts from historical export using stored authoritative facts. A hash detects content differences but does not substitute for authorization or semantic validation.

### Idempotency

- Define replay behavior for creation, commits, queued work and external delivery.
- Scope keys to actor/use case and bind them to a request fingerprint. Reject reuse with different content.
- Persist the accepted result/operation ID atomically so concurrent retries cannot duplicate work.
- Return the original exact result, not whatever happens to be current after later edits.
- Bound key retention according to retry windows and storage needs.
- Do not assume POST is replay-safe or cancellation rolls back an already committed side effect.

### Revocation barriers

Conditional for private workspaces/session-sensitive long operations: capture a generation/epoch, invalidate it on every revocation path, and recheck it at stream output and final persistence/cache insertion. It supplements real authentication and must be scoped to the correct identity/workspace.

Explicit logout, passcode change, automatic session expiry, inactivity lock, deletion and shutdown must follow their documented revocation semantics. The source repository has an unresolved automatic-expiry epoch issue; these requirements are a recommended corrective pattern, not evidence it is fixed. Test held responses, streams and commits, not only new requests after expiry.

## 9. Async work and background jobs

### Choose execution deliberately

FastAPI distinguishes normal blocking functions from coroutines; see its [concurrency guidance](https://fastapi.tiangolo.com/async/). Must not put blocking database/file/process work in `async def` and assume it becomes nonblocking. Use compatible async libraries, explicit thread offloading or sync endpoints. Moving a blocking call to a thread does not automatically terminate it on cancellation.

- Async is useful for concurrent I/O. CPU-heavy work belongs in a bounded process/worker arrangement when needed.
- Avoid blocking the event loop with rendering, archive parsing or synchronous SQL during streamed async operations.
- Propagate cancellation and clean up in `finally`. Do not swallow task cancellation as an ordinary error or automatically retry it.
- Bound active work, waiting queue length, bytes and duration. A semaphore bounds execution but can leave unlimited waiters.
- Return explicit overload errors/retry guidance. Use timeouts for queue waiting as well as execution.
- Give each job its own session and resource lifetime.

### Durable job contract

Conditional for work that must survive browser disconnects:

1. Persist a run with immutable inputs/configuration and a scoped ID.
2. Admit it through a bounded queue.
3. Record stage transitions/checkpoints, status, safe errors and terminal result identity.
4. Expose reconnectable progress/status and explicit cancellation.
5. On restart, recover or mark interrupted runs truthfully. Do not pretend in-memory tasks survived.
6. Recheck ownership/revisions/revocation before final writes.

Model valid transitions such as queued -> running -> succeeded/failed/cancelled. Terminal states must not be overwritten by late results. Persist partial results only under an explicit partial-result contract.

An in-process worker is appropriate only for a documented process count and failure model. Multiple API processes need shared admission, durable coordination and cancellation; a local semaphore is not a distributed capacity limit.

### SSE/progress

- Decide whether work is request-owned or durable independently of transport.
- Send typed bounded events, monotonic IDs/cursors, heartbeat and a terminal event.
- Authenticate reconnects and scope replay. Recheck revocation during held streams.
- Disable proxy buffering and validate actual proxy timeouts.
- Bound replay storage and slow-client buffers. Drop/disconnect according to a documented policy.
- Disconnect may stop request-owned work, while durable jobs need explicit cancellation. Test both behaviors.

## 10. Authentication, security and privacy

Must state the deployment threat model. A fixed local owner, loopback listener or local passcode is not public multi-user authentication. Do not expose development/local mode as a hosted service without implementing server identity and authorization.

### Access and request controls

- Derive identity from authenticated server state, never a caller-supplied owner ID.
- Check authorization for every object reference and operation, including exports, downloads, events and status polling.
- Use hardened session cookies, HTTPS and a documented CSRF strategy for cookie-authenticated mutations. CORS is not authentication or a complete CSRF defense.
- Bound login/unlock attempts and use approved password hashing. Keep detailed account existence information out of unauthenticated errors.
- Rotate/revoke sessions according to expiry and sensitive account changes.
- Apply body-size limits before parsing, including chunked uploads; also enforce schema/file/decompression limits after parsing.
- Configure host/origin/proxy trust narrowly. Do not trust arbitrary forwarded headers.
- Apply appropriate no-store/private cache policy and safe security headers to sensitive responses and proxy errors.
- Keep SQL parameterized and logs redacted. Never pass user input to an interpolated shell command.

### Encryption and data lifecycle

- Use maintained cryptographic primitives/libraries; do not design custom encryption.
- Separate password hashing, storage encryption, private-file encryption and transport security. Explain what each protects.
- Keep keys outside exported data and provider children. Define provisioning, rotation, backup and wrong/missing-key failure.
- Authenticated encryption must fail closed on tampering. Migration/field conversion must detect incomplete encrypted states.
- Full-file encryption and field encryption have different metadata/search leakage. Document any plaintext identifiers, timestamps or indexes.
- An unlocked backend can access plaintext; encryption at rest does not prove process-memory isolation.
- Define retention across primary records, versions, runs, caches, files, logs and backups.
- Export/delete must enumerate every relevant entity/file and revoke in-flight writes first.
- Explain external copies accurately; deletion cannot erase downloads, unmanaged backups or prior provider copies.

### Containment

Treat uploads/templates/model outputs as untrusted. Process isolation flags, read-only application logic and tool disabling are distinct from OS filesystem/network/process containment. Native parser/renderer executables may require restricted users, sandbox profiles and resource limits according to the threat model. A Python `-I` child is interpreter isolation, not an OS sandbox. Do not claim takeover resistance without evidence of the actual boundary.

## 11. External integrations and AI

Use a dedicated adapter per outbound integration. Domain services pass the minimum required data; adapters enforce credentials, destination policy, deadlines, size limits and protocol details.

- Must validate URLs/destinations to prevent SSRF, including schemes, redirects and private/metadata networks. Local integration access requires an explicit allowlist exception; do not permit every private address by default.
- Keep TLS verification enabled. Fix certificate/trust configuration instead of using `verify=False`.
- Decide proxy inheritance explicitly, particularly for private data. Disable it when forwarding through inherited proxies violates the consented route.
- Retry only classified transient/replay-safe failures within a shared deadline. Bound attempts/backoff and respect cancellation.
- Treat remote responses as untrusted; validate shape, size and content before persistence.
- Do not return raw provider errors, headers or credential-bearing URLs to the client.

### Conditional AI standard

- Only `ai` may call model HTTP endpoints or launch inference processes.
- Require explicit configuration/consent before sending private content externally. Configuration changes must invalidate stale settings for subsequent calls.
- Separate deterministic tasks from model tasks; use code for counting, exact matching, permissions and schema validation.
- Supply minimum necessary factual context with immutable provenance. User documents and imported text are data, never instructions that grant tools/permissions.
- Use closed structured schemas, bounded validation retries and deadlines. A schema-valid claim can still be unsupported.
- Validate references, ownership, metrics, dates and source authority deterministically where possible. Recheck current evidence before accepting generated edits.
- Keep generated proposals separate from confirmed domain facts; user confirmation must be explicit when the workflow requires it.
- Preserve prompt versions, configuration, evaluation reports and actual rejected outputs in permitted synthetic evidence stores.
- Evaluate with synthetic fixtures and real providers separately from mocked workflow tests. Include adversarial/injection and cancellation cases.
- Report configured versus resolved models and provider-managed controls accurately. Do not claim enforceable sampling/output caps a provider does not expose.
- Inference children get a minimal environment, temporary directory, bounded pipes and process-tree cleanup; never scrape account OAuth tokens or forward unrelated application secrets.
- Tool disabling and post-run output rejection do not undo side effects by an already executing process. Match isolation claims to tested OS/provider boundaries.

These AI practices are architectural standards. They do not require a specific provider, subscription or additional model feature.

## 12. Uploads, rendering and caching

### Parsing/files

- Accept a narrow supported file set; validate actual structure and size, not just filename/MIME.
- Bound archive expansion, entry count, nesting, processing time, image dimensions and extracted text.
- Generate storage identifiers; prevent traversal and refuse links/paths that escape the intended root.
- Quarantine/review extracted candidates before changing trusted records. Atomically remap approved parent/child graphs.
- Retain originals only under the defined policy/consent. Encrypt private assets when required and clean temporary files on success, failure and cancellation.
- Invoke subprocesses with argument arrays and no shell. Set working directory, environment, output bounds, timeout and tree termination deliberately.
- Separate parser syntax validity from OS containment and user-confirmed factual correctness.

### Rendering

Keep rendering a database-free leaf when practical: it receives validated content plus an immutable presentation snapshot and returns artifacts/measurements.

- Escape text and limit supported templates/styles. Avoid arbitrary executable templates and outbound assets.
- Bundle required fonts/assets with licenses when privacy or deterministic layout requires it.
- Bound render admission and runtime; clean up browser contexts/processes.
- Measure actual artifacts for pagination/text/order requirements. Heuristics should be labeled as heuristics.
- Keep exact historical dependencies or embedded snapshots so later template changes do not alter exports.
- Verify PDF/DOCX output visually in the actual named processor; structural tests alone do not establish layout.
- Refuse unsupported export mappings rather than promise arbitrary HTML-to-DOCX fidelity.
- Check the actual renderer sandbox and network restrictions in its deployment environment.

### Caching

- Key caches by owner/tenant and the complete relevant content/configuration/version fingerprint.
- Bound count, bytes and lifetime; define when expired entries are removed.
- Check authorization/current-source policy before returning a cache hit.
- Invalidate entries and late insertion on lock/logout/deletion/configuration changes as applicable.
- Never allow an old render/model response to refill a revoked cache.
- A single-owner process cache is not automatically safe for hosted multi-tenant use.
- Cache effectiveness is a performance property, not a reason to weaken evidence or privacy validation.

## 13. Errors, logging and operations

### Error policy

Separate invalid input, missing/inaccessible resources, business conflicts, overload, dependency failures and unexpected faults. Map domain failures to documented safe HTTP contracts at the boundary.

- Use stable codes for machine handling and useful messages for humans.
- Return conflict when current state/revision prevents an action, not a generic server error.
- Return overload/unavailability with retry guidance where appropriate.
- Do not catch every exception and return success/empty data.
- Record unexpected errors with a correlation ID and sanitized diagnostics. Redaction applies to nested exception/provider output too.
- Treat cancellation as a distinct outcome; release admission slots and resources.

### Observability

Default to structured logs of request/run ID, operation, status, duration and safe error classification. Metrics can track queue depth, rejected admissions, latency and dependency availability without sensitive payloads. Telemetry exporters/external reporting require the adopted privacy policy; local-only apps should not silently enable them.

Must exclude secrets, session cookies, prompt/response bodies, uploaded content and full private DTOs from logs. Database debug parameter logging can leak fields despite safe application logs. Production response bodies must not expose stack traces.

### Operational contract

- Document installation, migrations, startup/shutdown, diagnostics, backup/restore and upgrades.
- Store backups independently and test restoration, including encryption keys/sidecars.
- Stop admission on shutdown, cancel/drain according to job policy, and dispose clients/engines.
- Use readiness to prevent routing to an unready service. Do not restart every healthy process just because one optional provider is down.
- Verify process count, queue/cache scope, proxy timeouts and storage permissions against deployment configuration.
- List unsupported environments and security residuals plainly. Configuration inspection is not runtime proof.

## 14. Testing, tooling and deployment

### Test by boundary and risk

| Layer | Verify |
|---|---|
| Pure unit | Business calculations, validators and state transitions |
| Service | Orchestration, failure classification, cancellation and source checks |
| Repository/database | Ownership, constraints, revisions, transactions and query behavior |
| API | Input/output contracts, status/errors, auth/origin/size controls |
| Integration | Actual migrations, files, renderer and supported database engines |
| Concurrency | Held responses/transactions, revocation, duplicate delivery and stale commits |
| Release | Fresh installation, production proxy, outage/restart and backup restoration |

Must use disposable synthetic data. Seed fixtures through deliberate builders, not copies of production/personal stores. Patch external boundaries rather than mocking all business logic. Avoid tests that merely restate implementation; assert meaningful outcomes and atomic failure behavior.

- Test another owner's IDs and parent references, not only the happy path.
- Test concurrent saves/replays and failure between dependent writes.
- Hold work at deterministic barriers to test lock/expiry/delete during in-flight operations. Prefer events/latches over arbitrary sleeps.
- Assert cleanup after cancellation, parser failure, timeout and overload.
- Exercise migration upgrade paths and each officially supported database.
- Use actual PDFs/files/word processors when artifact behavior matters.
- Label synthetic model/browser fixtures separately from live provider quality.
- Verify the exact environment claimed: native tests do not prove containers, container smoke does not prove account authentication, and a workflow file does not prove hosted CI passed.

### Dependency and quality policy

Pin supported runtimes and install from a reproducible lock. Keep application requirements and development tools explicit. Use isolated environments; check external-terminal runtime availability rather than relying on an editor's bundled PATH.

Default gates: formatting/lint, strict typing, tests, schema/migration drift, generated API drift and dependency audit. Release checks additionally cover relevant browser/artifact workflows and fresh-install/restart behavior. Audit results are time-bound findings, not proof of security.

When adopting this guide, define actual command names. In its source repository, `python scripts/tasks.py check`, `api`, `audit`, `e2e` and `fresh-install` already exist; new projects must implement equivalent tasks rather than assume those commands are provided by Python.

### Packaging/deployment

- Use source allowlists or carefully reviewed build ignores. Exclude databases, `.env`, credentials, private files, downloads, backups and validation evidence from image contexts/artifacts.
- Run with least privileges appropriate to runtime needs and install renderer OS prerequisites explicitly.
- Do not bake account logins or secret files into images.
- Review real proxy behavior: body bounds, TLS/cookies, security headers, SSE buffering/timeouts and static worker MIME types.
- Run migrations under a documented single-run/rollout strategy, not competing arbitrary process startups.
- Fresh-install tests should create new dependencies/storage and copy only permitted source. They are not physical clean-OS certification.
- Keep owned test-resource cleanup separate from user services and unrelated stacks.

## 15. Implementation and review checklists

### New-project setup

- [ ] Adoption record and domain vocabulary complete.
- [ ] Supported runtime/dependency lock and safe configuration examples established.
- [ ] Domain boundaries, identity and transaction owner documented.
- [ ] Lifespan-managed engine/clients and health/readiness implemented.
- [ ] Migration baseline, ownership constraints and synthetic fixtures created.
- [ ] Typed contracts, safe errors and frontend generation/drift pipeline wired.
- [ ] Request/resource limits, logging redaction and cancellation policy defined.
- [ ] One migrated API/UI vertical slice passes relevant real integration checks.
- [ ] Setup, backup/recovery, deployment limits and exact checks documented.

### Feature workflow

1. Define inputs/results, invariants, ownership and failure/replay semantics.
2. Design schemas and constraints; add migration if persistent state changes.
3. Implement bounded/scoped repository operations and detached results.
4. Implement service rules and atomic transaction/concurrency policy.
5. Add thin HTTP routes and regenerate the canonical API/client artifacts.
6. Exercise meaningful failures, concurrency and actual runtime boundaries.
7. Update architecture/decisions/status with exact evidence and residual limits.

### Review questions

- [ ] Are router/service/repository responsibilities intact without hidden lazy SQL?
- [ ] Does every operation enforce ownership, parent validity and authorization?
- [ ] Are dependent writes atomic, and is there one clear transaction owner?
- [ ] Are edits/retries/versions protected against stale or duplicate work?
- [ ] Are blocking work, queues, body/response sizes and deadlines bounded?
- [ ] Do lock/expiry/delete/cancellation stop late writes, streams and cache insertion?
- [ ] Are credentials/private content absent from logs, exports and inference children?
- [ ] Are migrations, contracts, supported engines and artifacts actually tested?
- [ ] Are deployment and security claims limited to their verified scope?

Anti-patterns to reject: SQL in routers/services, shared global sessions, secret-bearing configuration dumps, repository commits inside multi-step workflows, unchecked owner IDs, schema creation on startup, unbounded list/jobs/uploads, synchronous blocking work in async paths, external calls under database locks, mutable historical versions, swallowed errors, limitless retries, shell interpolation and sandbox claims unsupported by OS/runtime evidence.
