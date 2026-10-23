# Concepts to learn alongside BACKEND.md

Prepared 2026-10-22 against the numbered sections of [BACKEND.md](BACKEND.md). The bold terms below are useful search phrases. These are learning topics, not new implementation requirements or claims that every related technique is used here.

## Before the numbered sections

If these foundations are unfamiliar, start here:

- **Python fundamentals:** functions, classes, modules/packages, imports, dictionaries/lists, exceptions and context managers (`with`).
- **HTTP fundamentals:** client/server requests, methods, URLs, headers, bodies, status codes and cookies.
- **JSON:** the data format used for most API requests/responses and stored document snapshots.
- **SQL and relational databases:** tables, rows, primary/foreign keys, SELECT, INSERT, UPDATE and DELETE.
- **API fundamentals:** how a frontend asks a backend to perform a use case and receives a result.

You do not need to master every topic before reading the guide. Learn enough to follow one request, then revisit the deeper topics where they appear.

## 1. Architecture and dependency direction

- **Modular monolith:** one deployable application whose code is divided into business modules.
- **Layered architecture:** separating HTTP handling, business decisions and storage access.
- **Separation of concerns / single responsibility principle:** assigning each part a clear reason to exist and change.
- **Dependency direction and coupling:** which modules may call/import which others, and what breaks when one changes.
- **Service layer and repository pattern:** the difference between performing a use case and querying/persisting its data.
- **Composition versus inheritance; stateful versus stateless code:** why ordinary functions are often enough, while resource-owning managers need objects.

Reading goal: explain why a router delegates a save instead of containing SQL, model-provider calls and business rules itself.

## 2. Domain map

- **Business domains and domain boundaries:** grouping behavior around concepts such as career records, resumes and applications.
- **Domain-driven design basics / bounded contexts:** understanding where a concept and its rules belong. This is useful vocabulary, not a claim that the application implements every DDD pattern.
- **High cohesion and low coupling:** keeping closely related behavior together while limiting unnecessary dependencies.
- **CRUD versus workflows:** basic record operations versus multi-step generation/review/commit behavior.
- **Shared infrastructure versus domain logic:** engine construction is reusable plumbing; accepting a resume proposal is a product decision.
- **Orchestration:** coordinating several domain operations without absorbing their individual responsibilities.

Reading goal: decide which package should own a new feature and which existing packages it needs to coordinate.

## 3. Application startup and HTTP lifecycle

- **FastAPI and ASGI; Uvicorn:** the web framework, application/server interface and process serving requests.
- **Application factory pattern:** constructing an application with explicit configuration, including isolated tests.
- **Application lifespan and context managers:** acquiring resources at startup and reliably cleaning them up at shutdown.
- **Middleware and request/response lifecycle:** checks/wrappers around route handling; ordering can change behavior.
- **Configuration, environment variables and `.env`:** selecting runtime behavior without embedding machine-specific values in source.
- **CORS, request origins and Host headers:** different request properties and the distinct policies that inspect them.
- **Serialization and request-body limits:** converting typed data to/from wire formats and bounding input before expensive parsing.

Reading goal: distinguish constructing the app, starting it, migrating storage and serving one request.

## 4. Python conventions and contract design

- **Python type hints:** `UUID`, `date`, `Decimal`, `list[T]`, `T | None`, `Literal` and `Annotated`.
- **Static analysis versus runtime validation:** mypy/Ruff check source; Pydantic validates actual boundary values.
- **Pydantic models, validators and discriminated unions:** describing allowed data and selecting a known variant from its `type` field.
- **DTOs, schemas and ORM models:** a data-transfer contract, a validation shape and a database mapping serve different purposes.
- **Serialization/deserialization and JSON Schema:** translating structured values and describing the allowed shape.
- **OpenAPI and generated clients/types:** sharing the API contract with the frontend and detecting generated-artifact drift.
- **Schema evolution and backward compatibility:** extending a document format while preserving valid old snapshots; defaults versus database migrations.

Reading goal: explain why a Pydantic-valid source ID still needs an ownership check, and why generated TypeScript is not runtime validation.

## 5. Routers and dependency injection

- **Routing and REST-style API basics:** methods, paths, path/query parameters, bodies and responses.
- **Python decorators:** how `@router.post(...)` registers a function as an HTTP handler.
- **Dependency injection and FastAPI `Depends`:** supplying sessions/owner identity without constructing them in every handler.
- **Request-scoped resources and `yield` dependencies:** creating a resource for a request and closing it afterward.
- **Authentication, authorization and ownership:** identifying a caller, deciding what they may do and constraining access to owned data. This app's local owner is not public authentication.
- **HTTP status/response contracts:** making success, conflict, invalid input, missing records and locked access distinguishable.

Reading goal: trace where `Owner` and `Database` come from and what the router does with them.

## 6. Services and cross-domain coordination

- **Business rules and use cases:** rules about what the application permits, beyond whether input has the right shape.
- **Application services and workflow orchestration:** implementing a meaningful action by coordinating other operations.
- **Invariants, preconditions and state transitions:** conditions that must remain true and the allowed ways to change state.
- **DTO detachment and ORM lazy loading:** avoiding accidental database reads when passing data outside its intended persistence boundary.
- **Error translation and exception handling:** converting a database/provider failure into an understandable application response.
- **Cache keys, fingerprints and invalidation:** identifying reusable results and knowing when their inputs have changed.

Reading goal: explain why a cached job analysis can be reused while career matching still needs current evidence.

## 7. Repositories, models and migrations

- **Relational modeling:** primary/foreign keys, one-to-many relationships, owner relationships and normalization basics.
- **Constraints and indexes:** UNIQUE/CHECK/foreign-key enforcement versus indexes for efficient lookups; composite keys and indexes.
- **SQLAlchemy ORM:** mapped classes, `Mapped`, `mapped_column`, `select`, `update`, result access and sessions.
- **Database engine, connection pool and session:** connection infrastructure versus an ORM work context. A database session is not a login session.
- **Soft deletion / retirement:** removing data from active use while preserving historical references.
- **Alembic migrations:** revision chains, upgrades/downgrades, schema drift and data backfills.
- **Database portability:** why SQLite and PostgreSQL need their own constraint/migration verification.

Reading goal: explain what changes in `schemas.py`, `models.py` and a migration when a stored field is added.

## 8. Transactions, history and concurrency

- **Database transactions and ACID:** related writes succeed or fail together; learn atomicity, consistency, isolation and durability.
- **SQLAlchemy flush, commit, rollback, refresh and expiration:** distinct operations in a session's lifecycle.
- **Race conditions and time-of-check/time-of-use bugs:** data/access can change between a check and its later use.
- **Optimistic concurrency control / compare-and-swap:** a write succeeds only if the expected version is still current.
- **Idempotency:** retrying an operation does not create a second unintended effect.
- **Immutable snapshots, version history and lineage:** preserving exact prior artifacts and where new ones came from. Snapshots alone do not imply full event sourcing.
- **Hashes, locks and revocation epochs:** hashes identify content; locks coordinate access; epochs invalidate previously authorized work. These mechanisms solve different problems.

Reading goal: predict what happens when two tabs save version 8, or a delayed task tries to commit after workspace deletion.

## 9. AI and evidence boundaries

- **Gateway/adapter patterns:** one controlled place to call an external provider while exposing typed operations internally.
- **External I/O policy:** explicit configuration/consent, secret handling, destination validation and avoiding unintended forwarding.
- **Structured model output and bounded retries:** parseable JSON must still pass schema and business validation.
- **Prompt injection and untrusted input:** source text must not acquire authority to override application rules.
- **Provenance and evidence validation:** tracing output to source records; distinguishing factual support from plausible wording.
- **LLM context windows, token budgeting and sampling:** input capacity and generation behavior; byte estimates are not exact token counts.
- **Embeddings, cosine similarity and keyword matching:** vector relevance versus exact lexical evidence; relevance does not prove a claim.
- **Synthetic evaluation and regression testing:** measuring output/control behavior without using personal records.

Reading goal: explain why valid JSON and a verifier's approval are insufficient on their own to establish factual truth.

## 10. Long-running work and streams

- **`async`/`await`, coroutines and the event loop:** cooperative waiting, task scheduling and blocking versus non-blocking work.
- **Request-owned tasks versus persisted runs:** whether work should stop or survive when the browser disconnects.
- **Queues, semaphores, admission control and backpressure:** limiting concurrent work and how much can wait for capacity.
- **Timeouts, cancellation and `try/finally`:** stopping work and releasing resources across success/failure/interruption.
- **Server-Sent Events (SSE):** one-way event streams, framing, heartbeats, event IDs, reconnect observation and polling fallback.
- **Checkpoints, terminal states and restart recovery:** preserving completed steps without claiming interrupted execution automatically resumes.
- **Process-local versus distributed coordination:** what changes when workers/caches/revocation span multiple processes or machines.

Reading goal: explain why closing analysis can cancel it, while closing a generation observer does not cancel the saved run.

## 11. Rendering, import and private assets

- **HTML/CSS print rendering and headless browsers:** producing actual paginated output using Chromium/Playwright.
- **PDF text extraction and semantic DOCX/OOXML:** visual layout, reading order and editable document structure are separate concerns.
- **Output escaping and HTML/CSS allowlists:** preserving text safely and restricting user-defined presentation.
- **File signatures, archive limits and bounded parsing:** checking actual input content and resisting oversized/malicious documents.
- **Subprocess isolation versus OS sandboxing:** an isolated interpreter or offline page is not complete process containment.
- **Caching: LRU, TTL, byte limits and invalidation:** controlling reuse, age, capacity and late results after revocation.
- **Authenticated encryption (AES-GCM), nonces and associated data:** protecting private assets and detecting modification; encoding such as base64 is not encryption.

Reading goal: explain why document syntax validation, successful PDF creation and real visual inspection prove different things.

## 12. Privacy, errors and operations

- **Password hashing versus encryption:** checking a passcode versus protecting recoverable data; salts and password-based key derivation.
- **Session cookies and expiry:** session tokens, HttpOnly, SameSite, Secure, inactivity locks and restart behavior.
- **Encryption scope:** full-database SQLCipher versus selected-field/asset encryption, backend key storage and recovery requirements.
- **Fail-closed behavior and least privilege:** unavailable authorization/keys should not expose data or silently disable protection.
- **HTTP error semantics, rate limits and safe diagnostics:** actionable errors without leaking secrets or private content.
- **Data lifecycle:** retention, complete export/delete, backups, delayed writes and external/provider copies.
- **Operational observability:** sanitized logs, liveness versus readiness, dependency failures and synthetic diagnostic checks.

Reading goal: explain why locking the app, encrypting its database and deleting its data are three different controls. Use the guide's known expiry finding as an example of a missing connection between mechanisms, not as a completed fix.

## 13. Tests and verification

- **Unit, integration, API and end-to-end tests:** different boundaries and the evidence each level supplies.
- **pytest fixtures and test isolation:** disposable migrated stores, configuration overrides and cleanup.
- **FastAPI TestClient and dependency replacement:** testing HTTP behavior without using the personal installation.
- **Mocks/fakes versus real dependencies:** deterministic control tests versus actual browser/database/provider compatibility.
- **Regression and concurrency tests:** preserve fixed behavior and exercise a state change during a held operation.
- **Linting, formatting, static typing and contract drift:** separate checks for source quality and agreement between API artifacts.
- **Dependency audits, reproducible builds and CI:** lockfile/advisory checks and automated workflows; configuration does not prove an actual successful run.

Reading goal: say what a mocked model test, real PDF test, browser workflow and live synthetic model evaluation each establishes.

## 14. Change and review recipes

- **Vertical-slice development:** make one complete UI-to-storage behavior work before broadening the implementation.
- **Change-impact analysis:** follow a field through schemas, storage, services, generated contracts, UI and tests.
- **Backward compatibility and safe schema evolution:** preserve prior persisted data and historical artifacts.
- **Integration/lifecycle completeness:** new data also needs ownership, export/delete, encryption, cancellation and recovery where applicable.
- **Risk-based code review and testing:** focus on authority, races, irreversible effects and exact artifact identity.
- **Architecture decision records and evidence maintenance:** explain why a choice was made and what actually verified it.

Reading goal: produce an implementation checklist for a new field, domain or long-running operation before editing code.

## Suggested study order

1. Learn the prerequisites, then sections **1-2** for the map of responsibilities.
2. Study **3-7**, alongside one simple career-create request, for HTTP/framework/contract/storage mechanics.
3. Spend extra time on **8**; transactions and races explain many safeguards elsewhere.
4. Study **10** before the async details in **9** and **11**. Then revisit their security implications in **12**.
5. Use **13-14** while making a small synthetic change, checking what each tool/test really proves.

The guide's section order is a reference structure; this study order lets you learn prerequisites before the more complex workflows.
