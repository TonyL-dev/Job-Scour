# Frontend coding practices

A reusable engineering standard for React and TypeScript applications. Use the principles with another framework if needed, translating framework-specific examples. This guide describes a proposed standard for new projects, not a certification of its source repository. Examples use a hypothetical projects API.

## Contents

1. [Adoption and priorities](#1-adoption-and-priorities)
2. [Structure and dependencies](#2-structure-and-dependencies)
3. [Naming and formatting](#3-naming-and-formatting)
4. [TypeScript and contracts](#4-typescript-and-contracts)
5. [Components and composition](#5-components-and-composition)
6. [State and effects](#6-state-and-effects)
7. [API requests and server state](#7-api-requests-and-server-state)
8. [Forms, editing and autosave](#8-forms-editing-and-autosave)
9. [Routing and recovery](#9-routing-and-recovery)
10. [Styling and accessibility](#10-styling-and-accessibility)
11. [Streams, files and previews](#11-streams-files-and-previews)
12. [Security and privacy](#12-security-and-privacy)
13. [Performance and observability](#13-performance-and-observability)
14. [Testing and delivery](#14-testing-and-delivery)
15. [Implementation and review checklists](#15-implementation-and-review-checklists)

## 1. Adoption and priorities

### Project adoption record

Complete these choices in the copied guide or link to a repository decision record:

| Choice | Record before implementation |
|---|---|
| Product scope | Intended users, essential workflows and explicitly excluded features |
| Runtime | Supported Node release and exact package-manager version |
| Framework | React/TypeScript/build-tool versions, SPA versus SSR requirements |
| Deployment | Same-origin proxy, base path, browser targets and HTTPS policy |
| Data | Sensitivity, authentication model, retention and offline requirements |
| API | Contract source, generator, error shape and compatibility strategy |
| UI | Styling approach, component primitives and accessibility target |
| Quality | Exact commands for lint, types, tests, build and browser verification |
| Exceptions | Link to decisions that override this guide |

Default to a small React application with strict TypeScript, a router, a server-state library, a generated API client and one consistent styling system. Add a form library, global store, rich-text editor or component kit when complexity justifies it. SSR, SEO, offline synchronization and mobile packaging need explicit architectural choices; a SPA is not automatically appropriate for every product.

Must preserve user work, show failures honestly, and make important actions usable with a keyboard. Prefer explicit, inspectable code over clever abstractions. A feature is complete when loading, success, empty, failure, cancellation and recovery are handled, as applicable.

## 2. Structure and dependencies

### Default layout for a growing application

```text
frontend/
  public/                         # public non-sensitive static assets
  src/
    app/
      App.tsx                     # shell and composition
      providers.tsx               # router/query/theme providers
      routes.tsx
    features/
      projects/
        api.ts                    # domain requests and generated type aliases
        queries.ts                # query keys/options and mutations
        types.ts                  # UI-only types, not copied API schemas
        ProjectsPage.tsx
        ProjectForm.tsx
        useProjectEditor.ts
        project-form.ts           # pure transformations/validation
        ProjectsPage.test.tsx
    shared/
      api/
        client.ts                 # transport/error/auth policy
        generated/                # generated OpenAPI/types
      ui/                         # domain-independent primitives
      hooks/                      # truly shared hooks
      lib/                        # small named utilities
    styles/
      tokens.css
      global.css
    test/
      setup.ts
      fixtures.ts
    main.tsx
  e2e/
  package.json
  pnpm-lock.yaml
  tsconfig.json
  vite.config.ts
```

For a small application, keep a flat `src/` until grouping improves navigation. This source repository currently uses a flatter page/API structure; the tree above is an adoption recommendation, not its current tree. Do not create empty folders just to match the example.

### Dependency direction

```text
app -> features -> shared
page -> feature hooks/query adapters -> domain API -> shared transport
feature component -> shared UI
```

- `shared` must not import feature or application modules.
- Feature API modules must not import React components.
- Prefer another feature's deliberately exposed API over its internal files. Move multi-feature orchestration into application composition when appropriate.
- Keep business calculations in pure functions or backend services. Components format and explain authoritative results.
- Extract shared code after a genuine second use or a clear boundary; avoid speculative `BasePage`, universal form builders and catch-all utility modules.
- Avoid barrel exports that conceal cycles or pull large modules into otherwise small imports. Use named, narrow exports.

## 3. Naming and formatting

| Item | Convention | Example |
|---|---|---|
| React component/file | PascalCase | `ProjectCard.tsx`, `ProjectCard` |
| Custom hook/file | `use` + PascalCase | `useProjectEditor.ts` |
| Variables/functions | camelCase | `selectedProjectId`, `saveProject` |
| Boolean | Meaningful predicate | `isSaving`, `hasChanges`, `canDelete` |
| Types/interfaces | PascalCase, no `I` prefix | `ProjectDraft`, `ProjectCardProps` |
| Fixed module constant | UPPER_SNAKE_CASE | `MAX_UPLOAD_BYTES` |
| Non-component module | Descriptive kebab-case | `project-form.ts` |
| Feature directory | Lowercase domain noun | `projects`, `billing` |
| Component test | Same basename | `ProjectCard.test.tsx` |
| Browser test | Workflow name | `project-edit.spec.ts` |
| CSS token/class | Consistent kebab-case | `--color-danger`, `.project-card` |
| Handler | `handle` + event/intent | `handleSubmit`, `handleArchive` |
| Callback prop | `on` + intent | `onSave`, `onDismiss` |

Choose a wire-field convention with the backend. If the API uses `snake_case`, keep generated wire types intact; map to camelCase at one named boundary only when it improves UI code. Avoid repeated invisible conversion.

Must use UTF-8, final newlines, consistent import ordering and a configured formatter. Default to two-space indentation in frontend code. Quote/semicolon choices are formatter policy; do not debate or switch them per file. Import types with `import type`. Remove unused code and imports. Comments explain constraints or intent, not the syntax immediately below them.

Names should identify the domain: prefer `applicationStatus` to `status2`, `originalTitle` to `oldValue`, and `projectsById` to `data`. Avoid ambiguous `manager`, `helper`, `common`, `stuff` and `processData`. Use abbreviations only when established in the domain.

## 4. TypeScript and contracts

Must enable `strict`. Evaluate `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` when establishing a new baseline; these are additional choices, not claims about the source repository. The [TypeScript strict documentation](https://www.typescriptlang.org/tsconfig/strict.html) explains the grouped checks.

- Use `unknown` at untrusted boundaries and narrow or parse it. Do not use `any` to silence a disagreement between the contract and implementation.
- Avoid unchecked `as` casts and non-null assertions. Validate assumptions or represent absence explicitly.
- Generated static types do not validate arbitrary runtime JSON. Parse external data, local-storage values, imports and streamed events when their trust boundary requires it.
- Model distinct states with discriminated unions, especially when several booleans permit impossible combinations.
- Use `null` for explicitly absent wire values and optional properties for omitted values according to the API contract. Do not interchange them silently.
- Keep timestamps and date-only values distinguishable. Do not convert a calendar date to a UTC instant just to display it.
- Use backend decimal strings or minor units for money; ordinary floating-point UI arithmetic is not authoritative financial logic.
- Create view models only when they differ meaningfully from the API. Do not mirror every generated schema in handwritten interfaces.

```ts
type SaveState =
  | { status: 'idle' }
  | { status: 'saving'; revision: number }
  | { status: 'saved'; revision: number }
  | { status: 'conflict'; message: string }
  | { status: 'error'; message: string }

function saveLabel(state: SaveState): string {
  switch (state.status) {
    case 'idle': return 'Unsaved changes'
    case 'saving': return 'Saving…'
    case 'saved': return 'Saved'
    case 'conflict': return state.message
    case 'error': return state.message
    default: {
      const exhaustive: never = state
      return exhaustive
    }
  }
}
```

Must generate API types from a canonical contract and check drift. Fix backend schemas or generator configuration rather than editing generated output. Generated directories should have a clear ownership comment and be excluded only from inappropriate formatting/lint rules, not from contract verification.

## 5. Components and composition

Default to function components with named exports and explicit prop types. A component should have a coherent responsibility: a form, a card, a route or a reusable control. Split when responsibilities, independent state, reuse or test seams become hard to understand; line count alone is not a rule.

- Route components coordinate queries and workflow state. Presentational components receive values and intent callbacks.
- Keep rendering pure. Do not start requests, write storage or mutate shared objects during render.
- Use stable domain IDs for list keys. Array indices are inappropriate for editable/reorderable lists.
- Keep component definitions outside other component bodies to preserve identity.
- Prefer explicit props and composition over many mode flags. A button should not know how project persistence works.
- Use native HTML semantics before custom widgets. Choose accessible maintained primitives when building complex dialogs, menus and comboboxes.
- Use `useId` for DOM relationships where appropriate; do not treat it as a persistent domain ID.
- Pass callback intent, not transport details: `onArchive(project.id)` is clearer than a child assembling an HTTP request.
- Default to explicit prop types instead of a universal component wrapper. Prefer `children` only when composition is an actual part of the contract.

```tsx
type ProjectCardProps = {
  title: string
  isArchiving: boolean
  onArchive: () => void
}

export function ProjectCard({ title, isArchiving, onArchive }: ProjectCardProps) {
  return (
    <article>
      <h2>{title}</h2>
      <button type="button" disabled={isArchiving} onClick={onArchive}>
        {isArchiving ? 'Archiving…' : 'Archive project'}
      </button>
    </article>
  )
}
```

## 6. State and effects

| Kind of value | Default home |
|---|---|
| Backend-owned records | Query cache |
| Unsaved form/editor draft | Form state or local reducer |
| Open dialog/selected panel | Local component state |
| Shareable search/filter/page | URL search parameters |
| Cross-route client preference | Context or small store if needed |
| Derived count/filter/label | Calculate from existing state |
| Sensitive authenticated data | Memory; explicit persistence decision |

Must avoid two independently mutable sources for the same value. A draft may deliberately diverge from a server record; record its base revision and dirty status. Refetching must not overwrite dirty input.

Use a reducer for meaningful state transitions across several related values. Context supplies shared dependencies or modest shared state; splitting contexts can avoid unrelated consumers rerendering. Add a global state library for a demonstrated need, not as project ceremony.

Effects synchronize with external systems such as subscriptions, browser APIs and third-party widgets. Derived values belong in render and user-triggered actions belong in handlers; see [React's effect guidance](https://react.dev/learn/you-might-not-need-an-effect).

- Include actual dependencies; fix the design rather than disabling hook lint rules.
- Clean up listeners, timers, subscriptions, object URLs and requests.
- Make setup/cleanup robust to development remounts.
- A ref holds an imperative handle or latest callback; it is not a way to hide UI state changes.
- Prevent stale asynchronous results from replacing a newer selection. Use query keys, request cancellation and sequence/revision checks as needed.
- Debounce expensive previews/search when useful. Do not debounce confirmation of destructive actions or imply that unsent edits are saved.

## 7. API requests and server state

### Transport policy

Use one shared transport for base URL, credentials, abort signals, sanitized error mapping and authentication/privacy events. Default to relative same-origin API paths behind a development/production proxy. Environment variables exposed to the browser are public; API secrets must stay on the backend.

Domain adapters expose meaningful operations, not raw response handling repeated in pages. Distinguish a network failure from a valid empty list, a conflict, a validation error and an authorization denial. Check status and handle 204 without expecting a JSON body.

Illustrative generated-client adapter; the schema and endpoint must exist in the adopting project:

```ts
import { api } from '../../shared/api/client'
import type { components } from '../../shared/api/generated/schema'

export type Project = components['schemas']['ProjectRead']

export async function getProject(id: string, signal?: AbortSignal): Promise<Project> {
  const result = await api.GET('/api/projects/{project_id}', {
    params: { path: { project_id: id } },
    signal,
  })
  if (!result.response.ok || !result.data) {
    throw toApiError(result.error, result.response.status)
  }
  return result.data
}
```

`toApiError` represents the adopting project's shared error mapper. It must narrow unknown payloads, preserve safe status/code information, and avoid showing raw tracebacks.

### Query policy

- Include every input that changes the result in its query key: identity/workspace scope, ID, filter, ordering and page.
- Use key factories for consistency. Do not put secrets or large private payloads in keys.
- Pass the query library's `AbortSignal` to transport.
- Choose freshness and retention per data sensitivity and use case. Private preview bytes need shorter retention than static public catalogues.
- Bound automatic retries. Do not repeatedly retry validation, authentication or conflict responses. Respect overload guidance and distinguish cancellation from failure.
- On mutation, update or invalidate the detail, affected lists and dependent summaries. Use optimistic updates only with rollback and a safe conflict strategy.
- Never automatically retry a non-idempotent write without a backend replay contract.
- Show stale-data refresh failures without pretending stale results are current. Explain when the user can continue using cached data.

```ts
export const projectKeys = {
  root: (scopeId: string) => ['projects', scopeId] as const,
  detail: (scopeId: string, id: string) => ['projects', scopeId, 'detail', id] as const,
}
```

Every major query-driven view should explicitly implement initial loading, success with data, success with no results, background refresh, actionable failure and inaccessible/locked state. Error boundaries handle rendering failures; query errors still need explicit UI.

## 8. Forms, editing and autosave

Default to simple controlled forms for small screens; introduce a form library/schema validator for complex nested forms, conditional fields or substantial reuse. Backend validation remains authoritative.

- Label every control. Use correct input types, `autocomplete`, descriptions and field-level errors.
- Keep partially typed input as strings where necessary. Parse/normalize on an explicit boundary; do not turn an empty numeric input into zero.
- Preserve drafts on validation, network and conflict failures.
- Map server validation paths to fields and retain a form-level summary for errors without a field target.
- Use `aria-invalid` and `aria-describedby` appropriately; focus the first relevant error after failed submission.
- Disable duplicate submit while pending. Disable a field only when editing would violate the workflow; disabled text can be harder to inspect/copy.
- Distinguish pristine, dirty, submitting, saved, failed and conflicted states. Show a confirmed save indicator only after the server acknowledges it.
- Confirm destructive actions in proportion to their effect. Use an explicit typed confirmation for complete irreversible deletion when required by the product.

### Autosave contract

1. Track a draft, its base server revision and an edit sequence.
2. Debounce eligible edits and serialize writes for the same document.
3. Submit the exact snapshot with its expected revision.
4. Advance the known server revision on success, while retaining edits made since that snapshot.
5. On conflict, stop overwriting and offer reload, compare or a deliberate reconciliation flow.
6. On network failure, retain the draft and provide retry. Explain the risk before leaving with unsaved work.

Export-after-save must use the exact acknowledged version. A pending save and a separate "latest" download can race. Do not silently merge rich documents or replace newer server versions.

## 9. Routing and recovery

- Use the selected router for links/navigation, nested layouts and route parameters. Validate parameters before using them in requests.
- Put shareable filters in the URL. Test back/forward behavior and deep-link reloads under the production server.
- Provide explicit missing-route and missing-resource screens.
- Restore focus to a meaningful main heading/region after navigation without stealing focus on ordinary data refreshes.
- Keep the app shell navigable when a feature fails. Route-level boundaries need a useful retry/reset action.
- Authentication checks on the frontend improve UX; the backend must enforce access independently.
- Lazy-load heavy route features when measurement supports it. Handle loading and stale-chunk failure after deployment.
- Decide dirty-draft navigation behavior, including switching records and logout. Sensitive draft persistence requires explicit storage policy.
- Set useful page titles. Use document metadata/SSR strategies appropriate to the selected framework rather than assuming SPA routing solves SEO.

## 10. Styling and accessibility

Choose one primary styling approach: plain/CSS Modules, a token-based utility system or another documented system. Must keep colors, spacing, typography, radii and layout widths in consistent tokens. Domain facts and persisted content should not encode incidental CSS classes.

- Use responsive layout rather than fixed desktop coordinates. Test narrow screens, long text, translated text and browser zoom.
- Define hierarchy and spacing consistently; avoid arbitrary one-off values where an existing token works.
- Preserve visible keyboard focus, contrast and reduced-motion preferences.
- Use semantic buttons for actions and links for navigation. Set `type="button"` for non-submit buttons inside forms.
- Provide meaningful heading hierarchy, landmarks, skip navigation and accessible control names.
- Icons alone need accessible names. Decorative icons should be hidden from assistive technology.
- Dialogs require focus management, keyboard dismissal appropriate to the action and focus restoration.
- Announce important asynchronous status sparingly. Avoid noisy live regions for every streamed token.
- Scrolling preview/board areas need keyboard access and labels. Reorderable content needs an alternative to drag-only input.
- Tables require headers and an accessible mobile strategy. Do not destroy relationships solely to make a layout fit.
- Do not communicate errors or status only with color. Provide explanatory text.
- Bundle approved assets/fonts when privacy/offline policy requires it and preserve licenses.

Automated accessibility tests detect a subset of failures. Must supplement them with keyboard inspection and real browser checks; use representative screen-reader testing when the project's acceptance target requires it. Do not claim certification from a lint pass.

## 11. Streams, files and previews

### Long-running operations

Distinguish request-owned work from durable server jobs. Closing a progress panel may disconnect a stream without cancelling a durable job; the UI must explain this.

- Represent persisted job IDs, stage/status and terminal outcomes explicitly.
- Reconnect using the server's event cursor/replay contract. Deduplicate replayed events.
- Parse streamed bytes incrementally; UTF-8 characters and event frames can span reads. Bound buffer/event sizes and validate event shapes.
- Close streams on unmount, identity changes, cancellation and lock. Reconnect with bounded backoff and authoritative status checks.
- A closed connection without a terminal event is not success. Polling fallback should reconcile with persisted server state.
- Give cancellation a visible acknowledgement. Partial results must be labeled as partial.

### Downloads/uploads/previews

- Check upload type/size for fast feedback; backend limits and validation remain mandatory.
- Use safe download names and revoke blob URLs after use. Abort obsolete previews and release renderer resources.
- Preview the actual exported artifact when exact pagination matters. A responsive HTML approximation cannot prove PDF parity.
- Bundle workers locally where required. Verify worker MIME types, proxy headers, production base paths and font loading.
- Never inject untrusted HTML directly. Use an approved sanitizer/inert format and a restricted iframe when the use case requires HTML previews.
- Make previews usable with text alternatives or semantic output. Canvas alone must not be the sole route to essential information.

## 12. Security and privacy

Must treat browser data and code as user-visible. Frontend environment values, source maps and static assets cannot hold private server credentials. Authorization and business constraints belong on the server.

- Default to secure server-managed cookies for browser sessions when appropriate; align CSRF defenses, SameSite, credentials and origins with the deployment.
- Do not persist tokens/private records in local storage by habit. If offline storage is required, document encryption, key management, logout and compromise limits.
- Escape text by default; validate URL schemes before creating user-controlled links. Trusted Types/CSP may be part of a defense strategy, not a substitute for safe rendering.
- Keep telemetry/external fonts/scripts off unless explicitly permitted by the product's privacy policy. Review new dependencies for runtime network behavior.
- Never log private drafts, tokens, provider prompts or full API responses to the console/error service.
- Lock/logout/account change must cancel private work, close streams, clear private query/store state, discard sensitive view state and release preview objects.
- Guard against an old in-flight response repopulating cleared caches. Use scoped keys plus session/workspace generations and cancellation.
- Enforce production security headers in the actual host/proxy and test handled error responses too.
- Explain export/delete boundaries accurately: downloaded files, user backups and provider copies may remain outside the application.

The source repository's audit found automatic session expiry did not advance its workspace epoch. New projects should test expiry, explicit logout/lock and deletion independently; clearing browser state alone cannot revoke held server transactions or streams.

## 13. Performance and observability

Measure before adding memoization, virtualization or a new store. Use representative production builds/devices and record what improved.

- Split large optional features and avoid importing heavyweight libraries into the root bundle.
- Avoid request waterfalls and repeated full-list reads when paginated/aggregated APIs exist.
- Keep server pagination for unbounded data. Virtualization addresses DOM cost, not unbounded backend reads.
- Use `useMemo`/`useCallback` for a measured cost or required identity contract, not everywhere.
- Reduce preview requests through debouncing and cancellation; release memory-heavy PDFs/canvases when inactive.
- Use approved structured error metadata, build version and correlation IDs to diagnose failures without private content.
- Error reporting must obey consent and retention policy. Do not add third-party reporting merely because a library offers it.

## 14. Testing and delivery

| Layer | Verify |
|---|---|
| Pure unit | Transformations, validation, ordering, date/money formatting |
| Component | User interactions, error/empty/loading states, labels and draft preservation |
| Contract | Generated drift and adapters against schema-shaped responses |
| Browser integration | Real routing, proxy, storage, focus and rendering |
| Production smoke | Built assets, deep links, security headers, worker MIME and outages |

Default to Vitest and Testing Library for React behavior and Playwright for important browser journeys. Name tests after outcomes. Prefer role/name queries and realistic user events. Do not assert private hook implementation details or create snapshots of entire pages as the primary quality check.

Mock unavailable services at defined boundaries. A mocked model response proves UI/control behavior, not live model compatibility. Browser tests involving downloads/renderers must inspect actual artifacts when those are acceptance requirements.

Use disposable synthetic accounts/stores and isolate ports/processes. Tests must not read a user's personal database or invoke paid/external services implicitly. Clean up only resources created by the test.

Must pin the package-manager version, commit its lockfile, use frozen installs in CI and document supported Node releases. Keep lint, strict types, tests, contract drift and production build as separate visible gates. Add security audits and targeted browser/release checks according to change scope.

Build once and validate the artifact served by the real production proxy. Developer-server success does not prove production worker assets, CSP, cookies or fallback routing. Report unavailable environments explicitly.

## 15. Implementation and review checklists

### New-project setup

- [ ] Adoption record complete; essential workflows and deployment scope selected.
- [ ] Runtime/package manager pinned; lockfile and `.env.example` contain no secrets.
- [ ] Strict TypeScript, hook linting, formatting and quality commands configured.
- [ ] App shell, routes, error recovery, skip link and focus behavior implemented.
- [ ] Shared transport, contract generation, error policy and query scope defined.
- [ ] UI tokens and accessible primitives selected without unnecessary dependencies.
- [ ] One real end-to-end vertical slice passes under a production build.
- [ ] README documents setup, required backend contract, checks and known limits.

### Feature workflow

1. Define the user journey, API dependencies, failure states and acceptance evidence.
2. Confirm the contract; regenerate types after backend changes.
3. Add domain adapters/query keys, then pure transformations and UI state.
4. Build accessible components with recovery and draft preservation.
5. Verify the relevant interactions and real browser/runtime boundaries.
6. Review privacy, cleanup, conflicts, cache invalidation and production behavior.
7. Record exact checks and unresolved environment limitations.

### Review questions

- [ ] Is each value owned by one clear state source?
- [ ] Are effects necessary and cleaned up, and are late responses harmless?
- [ ] Are requests typed, scoped, cancellable and bounded in retries?
- [ ] Does failure preserve user work and offer an accurate recovery action?
- [ ] Are destructive actions, conflicts and unsaved work handled explicitly?
- [ ] Can a keyboard user complete the main journey?
- [ ] Are sensitive data, generated types and server authorization boundaries respected?
- [ ] Are test claims limited to the environments and artifacts actually exercised?

Anti-patterns to reject: page-level duplicated fetch policy, copied API interfaces, global state for every field, derived-state effects, index keys in editable lists, swallowed failures returning empty data, autosave overwriting newer revisions, endless retries, sensitive console logging, untrusted HTML injection and claiming preview/export parity without real artifact evidence.
