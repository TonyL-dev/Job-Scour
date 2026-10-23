# Frontend implementation guide

Source review: 2026-10-15. Read [the handbook overview](README.md) for product vocabulary and backend boundaries. This guide describes the current React implementation. The separate [frontend coding practices](../coding-practices/FRONTEND_CODING_PRACTICES.md) describes standards to adopt in future projects, including a possible feature-directory layout that this repository does not currently use.

## Contents

1. [Stack and actual organization](#1-stack-and-actual-organization)
2. [Bootstrap, routing and page boundaries](#2-bootstrap-routing-and-page-boundaries)
3. [TypeScript and coding conventions](#3-typescript-and-coding-conventions)
4. [API contracts and request adapters](#4-api-contracts-and-request-adapters)
5. [State ownership and query behavior](#5-state-ownership-and-query-behavior)
6. [Forms and career editing](#6-forms-and-career-editing)
7. [Resume editing, preview and autosave](#7-resume-editing-preview-and-autosave)
8. [Streaming, generation and review](#8-streaming-generation-and-review)
9. [Phase 6 and exact-version workflows](#9-phase-6-and-exact-version-workflows)
10. [Privacy, files and browser resources](#10-privacy-files-and-browser-resources)
11. [CSS, accessibility and recovery](#11-css-accessibility-and-recovery)
12. [Testing, build and delivery](#12-testing-build-and-delivery)
13. [Change and review recipes](#13-change-and-review-recipes)

## 1. Stack and actual organization

[`package.json`](../../frontend/package.json) is authoritative for installed direct versions. The frontend uses React 19, strict TypeScript, Vite, React Router, TanStack Query, `openapi-fetch`, generated OpenAPI declarations and locally bundled PDF.js. Vitest, jsdom and React Testing Library support component tests; external Python-run browser scripts exercise full workflows.

It uses native HTML inputs, selects, textareas and buttons with ordinary CSS. It has no general component-library dependency, form-library dependency or separate global editor store. Do not search for a Zustand slice, Tailwind configuration or TipTap editor implementation merely because the original blueprint proposed one.

```text
src/
  main.tsx              providers and initial render
  App.tsx               navigation, layout, route table and overview
  CareerPage.tsx        schema-described career forms
  ResumePage.tsx        manual document editor, preview and autosave
  JobsPage.tsx          saved jobs and request-owned analysis
  GenerationPage.tsx    persistent generation observation and review
  AISettingsPage.tsx    endpoint/profile/task/consent setup
  HistoryPage.tsx       exact versions, compare/restore/duplicate/ATS
  ApplicationsPage.tsx  tracker table/board/events/follow-ups
  PrivacyPage.tsx       passcode/export/delete controls
  ImportPage.tsx        parse/candidate review/commit
  ProfilePage.tsx       questions, user answers, confirmation
  LettersPage.tsx       sourced letter review and versions
  PromptsPage.tsx       bounded preference evaluation/activation
  TemplatesPage.tsx     custom declarations/assets/measurements
  WorkspaceGate.tsx     access state and private cache removal
  RouteRecovery.tsx     render-error recovery and route focus
  QueryNotice.tsx       small shared loading/error/retry presentation
  PdfPreview.tsx        PDF.js resource lifecycle and canvases
  styles.css            global and feature class rules
  api/
    openapi.json        generated backend contract
    schema.d.ts         generated TypeScript declarations
    client.ts           typed shared transport
    workspace.ts        career/resume helpers and shared error conversion
    phase2.ts           settings/jobs and POST stream decoding
    generation.ts       generation/review request helpers
    phase4.ts           versions/ATS/applications/privacy helpers
    letters.ts          cover-letter helpers
    docx.ts             DOCX downloads
  *.test.tsx            colocated component/workflow tests
  test/setup.ts         jest-dom matchers and cleanup
```

The structure is flat and page-oriented. Pages often combine data access, state, event handlers and JSX in one file. This makes a feature easy to locate but some files are dense. API helper names such as `phase2` and `phase4` reflect implementation history rather than ideal domain naming. Several Phase 6 pages call the typed `api` client directly instead of using a separate request module. These are existing patterns, not an assertion that every request has already been extracted.

For a future growing project, a feature directory containing page/components/hooks/API adapters can make ownership clearer. Move code because responsibilities have become distinct, not merely to create empty folders. Any refactor here should be separately scoped and behavior-preserving.

## 2. Bootstrap, routing and page boundaries

### Provider order

[`main.tsx`](../../frontend/src/main.tsx) mounts into `#root` under React StrictMode. The provider tree is:

```text
StrictMode
  QueryClientProvider
    BrowserRouter
      App
        WorkspaceGate
          workspace shell
            navigation
            main
              RouteFocus
              RouteRecovery keyed by pathname
                Routes -> selected page
```

The shared query client defaults to one query retry and a 30-second stale time. The client exists outside React rendering so it is not recreated on each component render. `BrowserRouter` supplies browser history; all API requests remain same-origin through the selected proxy.

StrictMode makes effect cleanup especially important during development. Starting a request/task in an effect without cancellation or cleanup can duplicate work. User-initiated writes normally belong in submit/click handlers or mutations, not an unguarded mount effect.

### Routes

[`App.tsx`](../../frontend/src/App.tsx) explicitly imports page components and declares the route table. There is no file-based router, route loader framework or current route-level lazy-import strategy.

| Route | Component | Main responsibility |
|---|---|---|
| `/` | `Overview` in `App.tsx` | Health/readiness status and starting links |
| `/career/:kind` | `CareerPage` | Active typed career library |
| `/resumes` | `ResumePage` | Master/tailored editing |
| `/jobs` | `JobsPage` | Saved posting and analysis/matching |
| `/generate` | `GenerationPage` | Run initiation, observation, review and tailored save |
| `/settings/ai` | `AISettingsPage` | Explicit model/provider configuration |
| `/history` | `HistoryPage` | Immutable versions and ATS guidance |
| `/applications` | `ApplicationsPage` | Submitted-artifact tracking |
| `/privacy` | `PrivacyPage` | Local controls and lifecycle operations |
| `/imports`, `/profile` | Import/profile pages | Reviewed fact acquisition |
| `/letters`, `/prompts`, `/templates` | Corresponding pages | Phase 6 artifact/configuration workflows |
| Unmatched route | Inline fallback | Page-not-found navigation |

`NavLink` provides active navigation state. Query parameters select saved entities where implemented, for example `/resumes?resume=<document-id>`, and history links can include an exact version. Item/section hashes provide editor anchors. These are navigation hints; backend authorization still determines access.

`RouteRecovery` catches descendant rendering failures, shows safe retry/navigation copy and does not print exception text. Its pathname key resets the boundary on path changes. Async event-handler/request errors still need their own `catch`/mutation error state; an error boundary does not automatically catch all async failures. Query-string changes alone do not change this pathname key.

`RouteFocus` updates the document title from the current heading and focuses main content after pathname navigation. This supports keyboard/screen-reader orientation. Entity selection within a page may need explicit focus/scroll behavior because it is not necessarily a pathname change.

## 3. TypeScript and coding conventions

[`tsconfig.json`](../../frontend/tsconfig.json) enables `strict`, unused-local/parameter checking, fallthrough checks and `noUncheckedIndexedAccess`, with ES2022/DOM libraries and bundler module resolution. Output comes from Vite; `tsc` validates without emitting application JavaScript.

Components use PascalCase names and named exports. Functions/variables use camelCase. Ordinary imports carry runtime values; `import type` carries declarations. Product enums/discriminated unions generally come from generated schemas rather than hand-maintained duplicate interfaces.

Examples from [`api/workspace.ts`](../../frontend/src/api/workspace.ts):

```ts
export type Document = components['schemas']['ResumeDocument']
export type Section = Document['sections'][number]
export type Item = Section['items'][number]
```

Deriving nested types keeps the UI tied to the canonical contract. `Document` here means resume content, not the browser's global DOM `Document`; the alias is historical and should be understood from its import.

Discriminated career data is narrowed using `data.type` or known-property checks. Array indexing may require guarding against undefined. Existing non-null assertions generally accompany a validated index or enabled query; adding `!` indiscriminately can mask a real load/selection race.

Inputs from runtime JSON/files and SSE remain untrusted. TypeScript types disappear at runtime, and `as CareerInput` or `as AnalysisResult` does not validate a payload. The backend validates writes/model output. Future changes should validate any new untrusted browser boundary where the backend contract cannot supply that guarantee.

The source uses concise object/array updates and JSX, sometimes with multiple expressions per line. ESLint is configured, but no separate Prettier formatter is present. Match surrounding conventions for small edits; a new project can adopt a consistent formatter deliberately. Do not mix a broad formatting rewrite into a behavioral change.

## 4. API contracts and request adapters

### One shared transport

[`api/client.ts`](../../frontend/src/api/client.ts) builds `createClient<paths>` with `baseUrl: window.location.origin`. Vite proxies `/api` during development; Nginx proxies it in Compose. Pages do not embed a backend host or contact model providers.

Its custom fetch adapter gives network failures a readable workspace message, preserves explicit abort errors and dispatches `workspace-locked` on HTTP 423. It returns the response so domain helpers can handle typed status/body errors.

A normal helper follows this pattern:

```ts
export async function getResumes() {
  const r = await api.GET('/api/resumes')
  if (!r.data) throw failure(r.error, r.response.status)
  return r.data
}
```

Generated `paths` constrains endpoint/method/body/parameter shapes. The helper converts transport details into a promise of domain data. The page decides whether it belongs in a query, mutation or explicit multi-step operation. Phase 6 pages sometimes perform this helper-shaped code inline using the same typed client.

`failure` converts a string `detail`, Pydantic validation detail arrays or a fallback status into an `Error`. It is shared presentation plumbing, not permission to display raw unexpected exceptions. A 204 DELETE is successful without `data`, so retirement checks `response.ok` rather than requiring a JSON body.

### Regenerate instead of duplicating

The source-of-truth chain is:

```text
Python schemas + route contracts
  -> scripts/export_openapi.py
  -> src/api/openapi.json
  -> openapi-typescript
  -> src/api/schema.d.ts
  -> handwritten adapters/pages
```

Run `python scripts/tasks.py api` after a contract change and let `api-check` detect drift. Never fix a compiler error by hand-editing `schema.d.ts`. If an API response is wrong, fix the backend response contract or runtime behavior and regenerate.

### Cancellation support

TanStack Query supplies an `AbortSignal`; cancellation works only when the query function forwards it through the helper/client. Health and preview do this. Many simple list helpers currently omit a signal parameter. `cancelQueries()` therefore must not be described as aborting every HTTP request in the application. Backend epoch/lock/source checks remain necessary independently of browser cancellation.

## 5. State ownership and query behavior

Use this classification when reading a page:

| State kind | Current mechanism | Example |
|---|---|---|
| Server state | TanStack Query | Saved resumes, active career history, run status |
| Unsaved draft | Local `useState` | Editor content/title, candidate decisions, answer text |
| Navigation selection | Route/search parameter plus local selection where needed | Career kind, requested document/version |
| Resource/lifecycle handle | `useRef` and effect cleanup | AbortController, PDF task, mount/open marker |
| Derived state | Compute from inputs/query result | `dirty`, `valid`, `active`, allowed source options |
| Mutation/error/status | `useMutation` or explicit async `perform` helper | Save pending/error, notices, workflow busy flag |

The query cache represents a server snapshot. The editable draft must not be the same mutable object. If a background refetch replaced every controlled field, the user would lose work. Pages copy/open a selected record into draft state, then only replace it intentionally.

### Keys and invalidation

The current code uses keys including:

| Key | Data |
|---|---|
| `['health']`, `['privacy-status']` | Infrastructure/access state |
| `['history']` | Active career library in the original workspace pages |
| `['career']` | Active career library in several Phase 6 pages |
| `['career-forms']` | Pydantic-derived form descriptions |
| `['templates']`, `['resumes']` | Available presentation/saved documents |
| `['preview', savedId, debouncedContent]` | Computed draft preview |
| `['generation', runId]` | Selected generation status/result |
| `['review-preview', runId, debouncedReview]` | Computed review preview |

Query keys are cache identity, not labels. A request input that changes its result belongs in the key. Invalidating the `['generation']` prefix reaches the selected-run keys; `exact: true` narrows an invalidation when intended.

There is a maintenance inconsistency: `getHistory` is cached under both `['history']` and `['career']`. Invalidating one does not automatically invalidate the other. When changing career mutations, inspect all consumers and refresh both relevant keys or deliberately unify them in a separately tested change. This documentation does not remediate the inconsistency.

Preview queries use `retry: false` and `gcTime: 0`: expensive or invalid preview input should not retry automatically or linger as unused private cache data. The document object is part of the key; a debounce reduces how often that object changes. Ordinary queries inherit a 30-second stale window and one retry unless overridden. These defaults do not implement persistent/offline storage.

Mutation success normally invalidates relevant lists, updates selected state and shows a notice. Failures preserve the draft and show actionable errors. Some pages use `useMutation`; others use a `perform` wrapper with `busy`, `try/catch/finally` and explicit invalidation. Both exist; do not invent a universal application mutation framework that is not present.

## 6. Forms and career editing

[`CareerPage.tsx`](../../frontend/src/CareerPage.tsx) validates `:kind` against the closed category list. It renders `CareerEditor key={kind}`, intentionally remounting category-local state when the category changes.

The editor queries active history and form descriptions. A form field description includes name, label, required state, input type, options, related category and default value. Rendering maps these to native controls. Relationship choices are labels/IDs from current records, not arbitrary free-text table references.

Local form values are strings or booleans. Submission converts them according to the field metadata: comma-separated lists become arrays; numeric controls become numbers; details lines become a string map; optional empty values are omitted. That conversion is convenience rather than authoritative validation. The backend still rejects invalid dates, incompatible parents, invalid enum values and cross-owner references.

On success the editor invalidates career history and closes. Retirement is distinct from deletion: the active list changes while saved document snapshots remain. `recordLabel` is shared display logic for a heterogeneous discriminated union. A skill-evidence link needs related record labels rather than a nonexistent free-text name.

For a new field, inspect the backend form derivation as well as frontend controls. An unsupported input type or missing relation mapping can make a valid API field unusable in the UI even when generated TypeScript compiles. Test actual labels and submitted payload conversion.

## 7. Resume editing, preview and autosave

[`ResumePage.tsx`](../../frontend/src/ResumePage.tsx) has three important snapshots:

- `content`: current editable document.
- `saved`: last successful server response with version identity.
- `debounced`: content selected for the next preview after 600 ms.

It also keeps title, gold-standard choice, selected preview mode, notices and editor controls locally. `dirty` compares title/gold/content to `saved`; `valid` is a local completeness gate. Backend validation remains stronger, so local validity does not guarantee save/preview acceptance.

### Immutable updates and identity

Section/item changes use spreads and `map`, not in-place mutation of cached arrays. Each section and item has a stable UUID key. Moving an item changes order without changing identity. Editing item text changes its origin to `user`; retaining an AI item without changing text preserves its origin and lets the backend enforce existing-evidence rules.

Source choices are filtered by section type and achievement parent category. Employer/title/date display values are not a separate editable AI fact source. Manual source-free text can be a draft, with its unverified status exposed; no such text should be presented as verified AI evidence.

[`ExperienceForm.tsx`](../../frontend/src/ExperienceForm.tsx) adds structured company/title/start/end-or-present entry inside an experience section. New entries save one career experience through `saveCareer`, with summary/duties joined into its evidence description, then append separate referenced resume items. Library persistence precedes document save; discarding a draft does not roll it back. Existing source-detail editing preserves the library description and other source metadata. Both career query keys (`history`, `career`) are invalidated. Per-call mutation success callbacks prevent a form unmounted by switching drafts from inserting its result into the other draft.

The additive `experience_summary` flag selects paragraph presentation; false/absent preserves existing duty bullets. [`experience.ts`](../../frontend/src/experience.ts) mirrors the backend's conservative one-line, one-sentence, 500-character summary gate. Item text editing remains manual/user-origin; source fact updates never relabel AI claims. A local source revision marks detail edits dirty even when every affected item retains AI origin, so save/autosave can rehydrate current facts without forging a manual claim. Summary/duty items keep independent keys, locks, sources and ordering. Empty or invalid summaries block preview/autosave/save until corrected. The source-details action updates shared career facts, while edited resume text stays in its own snapshot.

Opening another resume asks before discarding an occupied dirty draft. The page starts as a new blank draft unless a saved resume is selected or a supported query parameter opens it. This explains why an empty editor does not establish that saved work has disappeared.

### Preview is a query

Preview POSTs compute output but do not persist content, so they are modeled as a query keyed by the draft. The query is enabled only when basic content is complete, passes a cancellation signal, disables retries and drops unused results. A failed preview shows recovery guidance while editing remains available.

The response contains `pdf_base64`, HTML, actual page count, hash and warnings. The UI renders PDF.js by default or a sandboxed `srcDoc` HTML iframe. Continuous HTML cannot establish page parity; the PDF view shows actual printed bytes. Download helpers fetch saved output; “Save & download” saves first and then downloads the returned document identity.

### Autosave race handling

Autosave starts only after the first explicit save. It waits 1.8 seconds after valid dirty changes, avoids overlapping saves and stops after an error until the user resolves/retries the state. It sends the last saved `expected_version` so the backend can reject stale writes.

The content response guard follows this logic:

```ts
const submitted = content
const result = await saveResume(title, submitted, gold, saved, isAutosave)
setSaved(result)
setContent(previous =>
  JSON.stringify(previous) === JSON.stringify(submitted)
    ? result.content
    : previous,
)
```

The code is an excerpt of the implementation pattern; the page also invalidates the resume list and manages notices/downloads. If the user types while the request runs, `previous` no longer equals `submitted`, so those new edits remain visible. The new `saved` baseline makes them dirty for a subsequent save.

This is not collaborative merge/CRDT logic. A 409 preserves the draft and asks for recovery; it does not silently overwrite or automatically merge two tabs. Debouncing controls traffic, a pending flag controls local overlap, and SQL compare-and-update controls server races. Do not treat one as a substitute for another.

## 8. Streaming, generation and review

### Request-owned job analysis

[`JobsPage.tsx`](../../frontend/src/JobsPage.tsx) owns an AbortController for analysis. [`api/phase2.ts`](../../frontend/src/api/phase2.ts) starts the POST with `parseAs: 'stream'`, reads chunks and incrementally decodes UTF-8. It retains partial event text until a blank-line event boundary, reads `event:`/`data:` fields, reports progress and returns only a terminal result.

Network chunks are not event boundaries. A Unicode code point or JSON object may be split across reads. The decoder and buffer avoid assuming one chunk is one event. End-of-stream before a result is an explicit failure. The reader is cancelled/released in `finally`.

The parser casts result JSON to the generated result type; the cast is not browser runtime validation. The backend validates the emitted result. If adding a new untrusted stream origin or event schema, add appropriate runtime validation rather than assuming a declaration makes it safe.

### Persistent generation observation

[`GenerationPage.tsx`](../../frontend/src/GenerationPage.tsx) starts a saved run, queries its current state and opens `EventSource('/api/generation/<id>/events')` while active. Progress invalidates the selected run; completion closes the stream and refreshes results. Errors close EventSource. Polling every two seconds while queued/running remains the fallback; the current UI does not rely exclusively on automatic browser reconnection.

Effect cleanup closes the observer when run/active state changes or the page unmounts. Closing an observer is not cancelling the generation. The explicit cancel endpoint is the user's instruction to stop the persisted task.

### Review state

Decisions, locks and review revision are local until saved. The page debounces a review-preview payload and requests actual PDF output. Buttons offer accept/reject/edit; direct accept is disabled for unsupported suggestions. Manual edits are explicit user-confirmed content and still pass backend source checks.

Partial regeneration selects section/item UUIDs and preserves protected scope. Saving review decisions advances the review revision; subsequent preview/commit must use the current revision. A stale decision cannot be fixed safely by replacing the revision number without rereading the changed review state.

The UI shows original/proposed text and verifier/source reasons as a side-by-side view, not a general diff library integration. Pending/rejected decisions preserve the original. Committing creates a separate tailored document. History/download links prefer the run's exact saved version so later manual edits cannot change the artifact attributed to the run.

The page computes proposed display sections for review convenience. That computation is not the source of authority for final content. The backend reassembles, validates current evidence and persists the accepted result atomically.

## 9. Phase 6 and exact-version workflows

### Imports and profile

[`ImportPage.tsx`](../../frontend/src/ImportPage.tsx) queries saved runs, accepts a bounded PDF/DOCX, converts it to base64 JSON and asks the backend to parse locally. `accept`/file-size checks improve feedback, but the backend checks real content/signature/limits. Retaining the encrypted original is an explicit choice.

The selected run and candidate edits are local review state. Candidate keys are temporary graph references, not career UUIDs. The UI saves review to obtain the latest revision before commit. Only approved facts are committed; parse/extraction success alone does not populate career history. Optional AI extraction is labeled with the configured sharing boundary.

[`ProfilePage.tsx`](../../frontend/src/ProfilePage.tsx) selects active evidence, displays the context to be shared, requests questions, collects user answers and separately confirms a proposed factual edit. Unknown/skipped answers are supported. Model questions do not become facts automatically. Source/current-review checks are enforced by the backend even when the UI still holds an older selected record.

### Letters, prompts and templates

`LettersPage` maintains proposal/review state separately from immutable saved versions and exact application links. The workflow is not a textarea that overwrites the submitted letter. Historical export and restore retain stored facts.

`PromptsPage` presents bounded tone/focus choices and synthetic baseline/candidate results. Activation is a guarded operation tied to the exact evaluated configuration and revision. A successful evaluation shown in a previous selection is not permission to activate arbitrary newer settings.

`TemplatesPage` edits supported inert declarations, handles local PNG assets and shows measured findings from real synthetic PDF output. The browser is not a trusted HTML sanitizer. Backend validation, encryption and immutable presentation snapshots enforce those rules. DOCX download may refuse a custom layout that lacks a supported semantic mapping; do not hide that refusal by dropping presentation silently.

### History, ATS and applications

`HistoryPage` distinguishes a document from its versions and lets the owner compare, restore, duplicate, export or request an ATS report for a selected exact version. Findings link back to relevant editor/source areas. Restoring appends a new snapshot; the history UI must not imply that the old artifact was rewritten.

`ApplicationsPage` stores submitted document/letter versions and tracks table/board state, stages, events and due follow-ups. Selecting a board card opens its editor; changing and saving its stage updates persistence and its board column. The board is not a drag-and-drop implementation. Concurrent updates carry revisions. Follow-ups are in-app local-date information, not scheduled email/push delivery while the app is closed. ATS results are heuristic guidance, not a vendor verdict.

## 10. Privacy, files and browser resources

### Access gate

[`WorkspaceGate.tsx`](../../frontend/src/WorkspaceGate.tsx) polls privacy status every 15 seconds with query retries disabled. While initial status is pending it shows a checking state; unavailable status shows recovery instead of revealing private child content. Locked/blocked state shows an unlock form in place of the application tree.

On a `workspace-locked` event it blocks the workspace, cancels queries, clears the cache and refetches status. When polling discovers a lock it removes private queries while preserving the status query. With a configured passcode, pointer/keyboard activity resets the 15-minute browser inactivity timer; expiry calls explicit lock and dispatches the event. Unlock clears the passcode input and refreshes access state.

Unmounting the gated application also removes route-local draft state. This is a privacy tradeoff: a lock can discard unsaved drafts. Adding draft persistence later requires an explicit sensitive-storage policy; do not place career/resume content into localStorage merely to avoid that behavior. There is no current persistent query-cache/localStorage editor architecture.

UI cache removal is not server authorization. A direct caller can bypass the frontend entirely. Server checks/epochs must enforce access on requests, streams and commits. The known automatic server-expiry epoch gap remains unresolved; browser polling hides/clears UI state but cannot repair an already bound backend stream or transaction.

### Files and object URLs

Download helpers request `Blob` data, create an object URL, click a temporary download anchor and revoke the URL shortly afterward. JSON export similarly creates a Blob from returned data. Preserve URL cleanup when adding formats. Avoid storing sensitive blobs indefinitely in a global store/query cache.

Uploads send only the user-selected file through the application API. The frontend holds a `File`; the backend owns parsing/security and original-retention rules. A MIME/extension picker is not content verification. Base64 expands size, so request-body and file limits are distinct.

### PDF.js lifecycle

[`PdfPreview.tsx`](../../frontend/src/PdfPreview.tsx) dynamically imports PDF.js and uses Vite's `?url` import for the local `.mjs` worker. It decodes base64 bytes, loads the PDF with system fonts disabled and draws pages to canvases. Extracted text becomes an accessible page label. A focusable region supports scrolling; an HTML alternative remains available from the editor.

An effect owns the loading task and container. On input change it clears old canvases, uses a cancellation flag to reject late appends and destroys the PDF task during cleanup. Loading/failure state is visible. This is imperative DOM work isolated inside one resource-owning component; React still owns the surrounding UI. Follow this ownership pattern for other third-party viewers rather than allowing several components to mutate the same DOM subtree.

PDF worker delivery must be verified in production Nginx. A previous real failure required explicit JavaScript MIME for `.mjs`; passing Vite preview alone does not prove container worker loading.

## 11. CSS, accessibility and recovery

[`styles.css`](../../frontend/src/styles.css) defines the application shell, colors, native controls, feature panels, responsive layout and reduced-motion behavior. It uses semantic classes such as `.workspace`, `.sidebar`, `.editor-form`, `.studio`, `.preview-panel`, `.record-card` and `.warning`. Shared class names have broad effects because this is a global stylesheet, not CSS Modules or a utility framework.

The shell is flex-based; editor/preview layouts use grid; controls/panels use `min-width: 0` and wrapping to avoid long content breaking the viewport. Application UI fonts are system fonts; document export fonts are separately bundled Noto assets. Changing the UI font does not automatically change document pagination.

Use native semantic elements and labels. Current patterns include labeled controls, real disabled buttons, `role='status'` for progress, `role='alert'` for failures, a skip link, main focus on route navigation, visible focus rings and keyboard-focusable PDF/table/board regions. Reorder uses explicit buttons with labels, not a pointer-only drag library.

`QueryNotice` is a small shared loading/error/retry presentation helper. It does not decide whether zero records is meaningful; pages provide their own empty-state guidance. Read-only empty, loading, invalid selection, unavailable data and failed mutation are distinct states. Rendering all of them as an empty list would hide actionable failures.

The route boundary displays safe recovery copy. Query/mutation failures need inline retry or correction, and a stale save should preserve the draft. Avoid presenting raw stack traces/provider diagnostics. Browser accessibility checks and labels are useful evidence, not a claim of full accessibility certification.

## 12. Testing, build and delivery

### Component tests

[`vite.config.ts`](../../frontend/vite.config.ts) configures Vitest with jsdom and [`test/setup.ts`](../../frontend/src/test/setup.ts) loads jest-dom matchers and cleans up renders. Tests use a fresh QueryClient with retries disabled, MemoryRouter routes and mocked API helpers/fetch as appropriate.

[`Workspace.test.tsx`](../../frontend/src/Workspace.test.tsx) is a useful starting example: it verifies payload conversion, section ordering, preview/save/download behavior and retaining edits on conflict. Other suites cover settings/job analysis, generation, privacy and hardening. The file layout is historical, not a one-test-file-per-page completeness guarantee.

Prefer testing visible behavior and boundary payloads: a record submitted correctly, a conflict leaves content visible, a lock removes private content, an observer is closed, a PDF failure offers recovery. A mocked `PdfPreview` proves editor composition, not real worker/canvas behavior. jsdom cannot establish layout, pagination, production CSP or keyboard behavior in an actual browser.

### Build and policy

ESLint combines JavaScript/TypeScript and React Hooks rules and checks with zero warnings. Generated `schema.d.ts` and `dist` are excluded. `pnpm build` runs TypeScript then Vite; `typecheck`, `lint` and `test` are separate scripts. The repository task runner invokes them as part of `check` and enforces Node 24.x/pnpm 11.19.0 during setup. Broad manifest engine ranges do not override that exact validated toolchain.

Vite development proxies `/api` to `API_PROXY_TARGET` or backend port 8000. It uses strict port selection, so an occupied port fails instead of silently selecting another workspace address. Vite production preview also configures security headers; the development server is not the production-header acceptance environment.

Nginx serves compiled static assets, falls back to `index.html` for SPA navigation and proxies `/api` before static extension rules. It disables proxy buffering for SSE and adds production CSP/no-store policy. The PDF.js worker MIME rule is explicit. App assets/providers are not loaded from CDNs.

Use `python scripts/tasks.py check` for the integrated suite. Contract changes require `api`; browser/rendering/runtime changes require actual e2e/PDF verification; release changes add audit/fresh-install and the relevant production/container workflow. Record what was really executed. The historical Phase 6 20-test frontend result is not a new test run from writing this documentation, and a configured hosted CI workflow does not establish a successful hosted execution.

## 13. Change and review recipes

### Add a page or workflow

1. Define the user action and backend contract/invariants first, including authorization and historical identity.
2. Regenerate contracts if required; add a typed helper or keep a narrowly scoped inline client call consistent with the owning feature.
3. Decide which data is a query, local draft, navigation selection or resource handle.
4. Include every result-changing input in query identity; account for existing duplicate career keys.
5. Implement loading/error/empty/success/conflict states and accessible controls with the initial UI.
6. Clean up streams/timers/viewer tasks and forward cancellation signals where supported.
7. Invalidate the server-state consumers affected by a successful write without overwriting newer local draft edits.
8. Register navigation/route, add meaningful boundary tests and verify the real browser when behavior/layout/resources require it.

### Extract an oversized page

Separate pure formatting/transforms, typed API adapters, resource-owning hooks and reusable visual components by responsibility. Keep one clear owner of the editable draft. A form component can receive a typed draft/update callback without creating another hidden copy. Preserve query keys, revision checks, URL selection, mutation ordering, effect cleanup and lock behavior during extraction.

Do not introduce a global store solely because a page has many fields. First ask whether the state must survive routes or be shared by several independent components. In a sensitive application, persistence and lifetime are privacy decisions as well as ergonomics.

### Review a frontend change

- Is the visible type generated/derived rather than independently copied?
- Is the selected saved entity different from the unsaved draft, and can refetch/save overwrite new edits?
- Do query inputs/keys and post-write invalidation reach every affected consumer?
- Can an abort/unmount leave a stream, timer, worker, object URL or late state update behind?
- Does a UI revision reflect actual current server state rather than a guessed replacement value?
- Do exact-version downloads/ATS/application links remain exact after later edits?
- Does lock/unavailable status remove private content and queries?
- Can keyboard users reach the controls, identify progress/failure and scroll preview/board regions?
- Was production proxy/CSP/worker behavior exercised when relevant?

Use [the architecture template](PROJECT_ARCHITECTURE_TEMPLATE.md) to record a future project's choices and [frontend practices](../coding-practices/FRONTEND_CODING_PRACTICES.md) for adopted standards. Reuse state ownership and lifecycle reasoning; choose libraries and folder depth based on the next project's needs.
