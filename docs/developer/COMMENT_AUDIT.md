# Application comment audit — 2026-10-26

Added 80 explanatory comment lines across 29 application source files. This is a targeted maintainability review of backend service/repository boundaries, shared infrastructure and frontend asynchronous workflows. It does not certify every line or remediate security findings. Existing working-tree changes were preserved.

## Explanations added

| Area | What the comments explain |
|---|---|
| Resume editing | In-flight save responses preserve newer draft edits; autosave requires a first save and stops after errors; library writes and document saves are separate; source revisions can make a draft dirty without changing its JSON. |
| Resume persistence/review | Conditional version writes arbitrate concurrent saves; snapshots can join a caller's transaction; AI origin cannot bypass review; employer/title/date facts are rebuilt from stored evidence. |
| Generation/progress | Protected items keep their positions; initial item budgets are estimates followed by actual PDF measurements; persisted workers outlive SSE readers; browser polling supplements progress events. |
| AI/jobs | Admission counts waiters and active inference; stale endpoint configurations reject subsequent calls; strict schemas preserve nullable types; CLI tool activity invalidates otherwise structured output; cached posting analyses still match current career evidence. |
| Import/profile/letters/prompts | Import-local parent keys resolve in dependency order; profile facts come from user answers; letter acceptance retries resolve exact saved versions; prompt activation requires evaluation against the current configuration. |
| Privacy/infrastructure | Commit locks close the epoch-check/commit race; delete rebinds only its own transaction; chunk limits apply before parsing; assets authenticate owner/identity; field encryption requires complete offline conversion. |
| Rendering/ATS/tracker | Late renders cannot repopulate an invalidated cache; adjacent headings group without global deduplication; DOCX refuses unmappable browser layouts; ATS checks extraction order; applications retain submitted version identities. |
| Frontend streams/previews | Streaming decoding preserves split characters/frames; PDF tasks belong to individual effects; lock polling evicts private queries. |

Comments describe intent, invariants, transaction ownership and non-obvious lifecycle behavior. Straightforward CRUD, self-explanatory controls and already documented code were left alone. No generated API files, dependencies, schemas, templates, CSS or product strings were edited by this audit.

The existing automatic session-expiry revocation gap is called out beside `LockState.unlocked`; its evidence and remediation backlog remain in [the security audit](../release/security-audit-2026-10-09.md). Explicit lock/delete revocation and automatic token expiry must not be described as equivalent. Other historical acceptance/security limits remain unchanged.

## Verification

Before/after source snapshots and an audit-only diff are in ignored `.validation/comment-audit-20261026/`. All 22 edited Python files retain identical ASTs and non-comment tokens. All seven edited TypeScript/TSX files emit identical JavaScript with comments removed. These comparisons use the working tree immediately before this audit, including earlier uncommitted work.

The full `python scripts/tasks.py check` result is recorded in [IMPLEMENTATION_STATUS.md](../../IMPLEMENTATION_STATUS.md). No additional tests were written for comments, and no service restart, personal-store access or live model call was needed. Docker, hosted CI and live provider compatibility are separate checks and were not rerun for this audit.
