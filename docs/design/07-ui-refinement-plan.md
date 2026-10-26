# Phase 7 proposal: a calmer, clearer interface

Prepared 2026-10-22. Status: planning only; no UI implementation or visual acceptance is claimed. This user-requested UI phase is proposed next after completed Phase 6, ahead of the remaining section 7 differentiators. The original PROJECT.md blueprint remains intact.

Implementation was subsequently authorized. See [implementation record](07-ui-implementation.md) and [direct Apple website analysis](apple-website-ui-analysis.md). The proposal below is preserved; implementation does not itself establish release acceptance.

## 1. Outcome and design direction

Make the application feel like a focused desktop productivity tool: generous spacing, clear typography, quiet surfaces, predictable controls and one obvious next action. Interpret “Apple feel” through clarity, restraint and consistency. Use a neutral light workspace, white content surfaces, dark readable text and one restrained blue accent. Keep the product's own name and identity. Avoid decorative glass, oversized hero headings, excessive shadows and animation that competes with editing.

The reusable method is in [Clean UI design process](../coding-practices/CLEAN_UI_DESIGN_PROCESS.md). This plan applies that method to this repository.

## 2. Current evidence and scope

This is a source-based audit, not a new inspection of the running application. Capture synthetic-data screenshots and measure usability in 7A before treating these findings as visual measurements.

| Source | Observed structure | Proposed response |
|---|---|---|
| [styles.css](../../frontend/src/styles.css) | Global filled button styling; shared wrapping action rows; mixed serif headings and system body text; literal spacing/color values | Explicit button hierarchy, semantic tokens and task-specific layouts |
| [App.tsx](../../frontend/src/App.tsx) | Fourteen equally ranked navigation links; overview foregrounds connection details | Group navigation by task; foreground saved work and next actions |
| [ResumePage.tsx](../../frontend/src/ResumePage.tsx) | Style settings, section movement/removal, item movement/removal, locks and source selection compete within the editor | Stable document toolbar, content-first sections and contextual secondary controls |
| [ExperienceForm.tsx](../../frontend/src/ExperienceForm.tsx) | Repeated remove-duty controls and form actions | Quiet row actions; distinct form footer; retain explicit library-save explanation |
| [GenerationPage.tsx](../../frontend/src/GenerationPage.tsx) | Setup, progress, suggestions, regeneration and commit actions share one long screen | Stage-oriented presentation with persistent progress and review status |
| [HistoryPage.tsx](../../frontend/src/HistoryPage.tsx) | Download, restore, duplicate and tracking actions compete | Selected-version context with grouped export and separate version operations |
| [AISettingsPage.tsx](../../frontend/src/AISettingsPage.tsx) | Endpoint/profile/assignment/registry controls coexist | Guided default setup and clearly labeled advanced configuration |

The frontend currently uses React, TypeScript and ordinary CSS. Tailwind/shadcn and other libraries in the original blueprint are not installed requirements. Start with the existing stack; do not bundle a framework migration into the redesign.

Included: application shell, all existing routes, reusable controls, responsive layouts, accessibility, copy and state presentation. Excluded: new differentiator features, backend/domain redesign, altered AI behavior, resume/PDF template redesign, deployment and automatic security remediation. The known expiry-revocation and renderer/parser containment findings remain tracked separately.

## 3. Proposed design system

These are project starting values, subject to contrast checks and browser review, not Apple specifications.

| Foundation | Starting specification |
|---|---|
| Spacing | 4, 8, 12, 16, 24, 32, 48 px tokens; 8–12 within related action groups, 24 between groups, 32 between major sections |
| Page gutters | 32 px desktop, 24 tablet, 16 narrow screens; editor can use a wider content container |
| Typography | Existing local system font stack throughout app chrome; body 16 px/1.5, secondary text 14 px, section headings 20–24 px, page titles 28–32 px; reserve 12 px for nonessential metadata |
| Surfaces | Neutral workspace such as #f5f5f7; white primary surfaces; near-black text such as #1d1d1f; validate muted text, borders and accent pairings |
| Accent | One blue family for primary actions, selected states and links; separate semantic success/warning/error tokens with text labels |
| Controls | Default 44 px minimum interactive height; icon target 44 × 44 px; 8–10 px control radius and 12–16 px panel radius |
| Depth | Fine separators and whitespace first; restrained shadow for elevated menus/dialogs only |
| Motion | Optional 120–180 ms state transitions; respect reduced motion; no animation needed to understand state |

Use semantic names such as `--color-text-muted`, `--space-6`, `--control-height` and `--radius-panel`. Do not change document-rendering fonts or templates when changing app typography. Fonts/icons remain local; use available system fonts without downloading Apple font assets.

### Button and action rules

- One visually dominant action per active task region. The page header and an active dialog should not compete; dialog actions belong to the dialog.
- Primary: filled accent for the next meaningful commitment, such as Save resume or Generate suggestions. Secondary: quiet outlined/tonal treatment. Tertiary: text/ghost treatment for infrequent utilities. Destructive: separate labeled action with risk-appropriate confirmation.
- Aim for no more than three visible actions in a document-level group. Put infrequent Duplicate/Restore operations in a labeled More actions menu. This is a project heuristic, not a universal accessibility rule.
- Keep frequent editing and safety actions discoverable: Add experience, Accept/Reject, lock status, Cancel generation and unsaved/conflict warnings must not disappear into overflow.
- Use 8–12 px gaps inside groups and a larger separation between unrelated groups. Do not rely on literal spaces between buttons. On narrow screens deliberately stack groups or use a menu instead of accidental wrapping.
- Icon-only buttons need accessible names, visible focus and tooltips available on keyboard focus. Never expose essential actions only on hover.
- Disabled actions have nearby explanations when the prerequisite is unclear. Async actions show progress and prevent duplicate submission without blocking unrelated navigation unnecessarily.

## 4. Navigation and screen proposals

Keep current URLs and bookmarked query/hash links working. Reorganize navigation without changing API contracts.

| Navigation group | Existing destinations |
|---|---|
| Home | Overview, redesigned around resume/workflow entry points |
| Career | Career library, Import resume, Strengthen profile |
| Documents | Resumes, Cover letters, History & ATS, Custom templates |
| Opportunities | Job analysis, Generate & review, Applications |
| Settings | AI settings, Prompt playground, Privacy |

Show group hierarchy on desktop with a quiet sidebar. On narrow screens use a labeled navigation drawer with active-page context, Escape/close behavior and focus return. All destinations remain reachable without hover. Settings can sit lower in the shell, but lock/privacy access remains easy to find.

### Resume Studio: first complete slice

Desktop layout proposal:

```text
Navigation | Resume title            Save status    [Save resume] [Export] [More]
           | Content     Appearance
           | Section outline / editor              Actual PDF preview
           | Experience                            Page count / preview status
           | Company · Title · Dates
           | Summary and duties
           | [Add experience]                      Warnings when applicable
```

For new documents, Save resume creates the first saved version. Afterward show accurate autosave states: Saving, Saved, Unsaved changes, Save failed or Conflict. A manual save remains available. Export must clearly describe whether it saves current changes or downloads a specific saved version; preserve current save-and-download semantics and exact historical exports.

Content is the default editor view. Appearance contains template, font, margins and spacing. Group experience text under its stored company/title/dates; place Edit details on that group. Keep protection state visible next to the relevant content. Move infrequent removal and ordering operations into accessible contextual controls, with keyboard reordering preserved. Expand the section containing a validation error or a linked ATS finding.

At narrow widths, switch between Edit and Preview using labeled tabs that preserve the draft and preview state; do not force the entire PDF below a very long editor. Avoid remounting state-owning editors when hiding panels. Sticky toolbars must not cover focused fields, warnings or the on-screen keyboard.

### Remaining screens

| Screen | Primary improvement | Important behavior to retain |
|---|---|---|
| Overview | Continue/open saved work and clear start actions; connection details become secondary | First-use guidance and actionable connection errors |
| Career / Import / Profile | Category hierarchy, concise rows, focused editing/review panels | Parent relationships, staged import confirmation, user-supplied facts and cancellation |
| Jobs / Generation | Setup → progress → review → save as visible workflow stages | Reconnectable runs, partial results, explicit AI consent, evidence, unsupported warnings and revision checks |
| History / ATS | Version list, selected version context, compare and grouped export | Immutable versions, restore as a new version, heuristic score wording and source/editor links |
| Applications | Clear stage headings, compact cards, focused application details | Exact document links, keyboard alternatives and local-date follow-ups |
| Letters | Focused draft/review/export layout consistent with resumes | Independent immutable letter versions and evidence verification |
| Templates | Separate appearance controls from advanced template editing | Real measured validation and unsupported DOCX explanations |
| AI / Prompts / Privacy | Clear task sections, advanced details on demand, separated dangerous actions | Explicit consent, exact evaluation gates, lock/export/delete barriers and accurate provider capabilities |

## 5. Ordered implementation milestones

Each milestone depends on the preceding gate. Estimates are rough focused engineering days, not a delivery commitment; baseline findings can change them.

| Milestone | Work and deliverable | Exit gate | Estimate |
|---|---|---|---|
| 7A — Baseline and interaction design | Inventory every route/action/state; capture synthetic desktop/narrow screenshots; measure task paths; create Resume Studio and shell wireframes | All existing actions mapped to proposed locations; reference layouts and baseline metrics recorded | 1–2 days |
| 7B — Tokens and components | Build tokens, Button, ActionGroup, PageHeader, Field, StatusNotice, disclosure, menu and dialog patterns with state examples | Keyboard/contrast/state review passes; no remote assets; explicit component API documented | 2–3 days |
| 7C — Shell and Resume Studio | Deliver grouped navigation and complete content/appearance/editor/preview slice | Real save/autosave/conflict/reload/export, structured experience and PDF.js workflows pass in synthetic environment | 3–5 days |
| 7D — Core workflows | Migrate Career, Import, Profile, Jobs, Generation and History/ATS | Existing actions remain reachable; review, cancel, source and lock semantics pass | 3–5 days |
| 7E — Remaining screens | Migrate Applications, Letters, Templates, AI settings, Prompts, Privacy and all empty/error/locked states | Route/state checklist complete; dialogs, long content and narrow navigation verified | 2–4 days |
| 7F — Usability and release acceptance | Compare baseline tasks, refine, run regression and production browser checks; finish reusable examples | Measurable acceptance below and documented residual issues | 2–3 days |

Total planning range: 13–22 focused days, excluding user review delays. Finish the first slice before spreading incomplete component patterns across every page. A code review and screenshots at each gate make direction changes inexpensive; they do not imply this planning request authorizes implementation.

## 6. Implementation boundaries

Introduce shared presentation components under a proposed `frontend/src/components/ui/` directory and semantic styling under a proposed `frontend/src/styles/` directory. These directories are planned, not existing architecture claims. Keep domain-aware editor/review components separate from generic controls. Extract large page sections incrementally, keeping existing request/state ownership initially.

Migrate scoped page styles and remove superseded selectors as each route is completed. Avoid globally changing every button before pages have explicit variants. Do not hand-edit generated API types or add storage migrations for visual preferences. Persisted preferences, if later needed, require a separate contract decision. Keep backend routers/services/repositories and ai-only inference unchanged.

Do not introduce speculative autosave, silently write source facts, rewrite snapshots, or make UI hiding a security control. Preserve two-step experience persistence: saving library evidence and saving the resume draft are separate. Preserve epochs, lock behavior, consent, source validity and optimistic concurrency while reorganizing views.

## 7. Acceptance and verification

### Visual and usability criteria

- Inventory accounts for every existing route and action, including advanced and destructive operations.
- Each active task region has one clear primary action; document-level groups follow the three-action target or record a justified exception.
- All converted controls use shared variants/tokens. Related actions have intentional gaps, with no touching or accidental multi-line button clusters in reference screenshots.
- Review at 390, 768, 1280 and 1440 CSS px widths, plus 320 CSS px reflow and 200% zoom. No page-level horizontal scrolling; PDF/table/board regions may scroll within clearly labeled containers.
- Text contrast meets 4.5:1 for normal text and 3:1 for large text; required control boundaries/focus indicators meet applicable non-text contrast. Aim for 44 px controls; WCAG's 24 px minimum has specific exceptions and is not the product design target.
- Keyboard users can navigate, open/close menus/dialogs, reorder, review suggestions and return focus. Errors are associated with fields; saving/progress feedback is announced without excessive interruption. Reduced-motion and forced-colors checks pass.
- With synthetic fixtures, test five tasks: reopen a saved resume, add experience/save, change appearance/preview/export, review suggestions/save a tailored copy, and find/restore a version. Record completion, elapsed time, wrong turns and assistance before/after.
- Target at least 4 of 5 representative testers completing each task without assistance; no observed destructive misunderstanding or lost draft. Aim for 20% lower median completion time across the five tasks without worsening individual critical paths. With fewer testers, label findings preliminary; do not invent statistically significant results.

### Functional and release criteria

Run `python scripts/tasks.py check` and `python scripts/tasks.py e2e` after integrated changes. Use disposable synthetic storage and synthetic model responses; never personal data for screenshots or live model calls for visual tests. Cover first save, autosave failure/conflict, reload, exact-version export, locks, partial review, cancellation/reconnection and lock-driven clearing. Preserve existing A/D/E/F and Phase 6 workflows.

Review actual Chromium/PDF.js output and downloaded PDF/DOCX behavior when those interfaces are changed. Screenshot checks complement real interaction tests. Add focused tests for new menu/dialog/tab focus behavior and draft preservation rather than brittle CSS-value assertions. Do not claim visual usability from unit tests alone.

Run `audit` and `fresh-install` for the release gate; regenerate with `api` only if contracts change. Verify production Nginx/CSP/PDF worker behavior in Docker for the UI release, and hosted CI only in its own environment. Record browser/runtime versions and unavailable checks. Preserve the currently documented native Word, clean-OS, hosted CI and live Codex-container verification limits unless newly tested.

## 8. Risks and controls

| Risk | Control |
|---|---|
| Minimalism hides important features | Action inventory, visible frequent actions, task-based discoverability tests |
| New tabs/panels lose editing state | Keep state above panels; test switching, navigation, conflicts and interrupted saves |
| Global CSS causes broad regressions | Explicit variants and incremental scoped migration |
| “Apple feel” becomes faint text or decorative blur | Contrast gates, opaque defaults and real Windows browser review |
| Large page refactoring changes persistence | Separate presentation extraction from behavioral changes; keep mutation paths intact |
| Screenshots reveal career information | Synthetic fixtures only; no personal-store access |

## 9. References

Apple's [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines) and [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) inform the emphasis on clear hierarchy and consistent controls. This web application adopts those principles, not a claim of native macOS behavior.

Accessibility gates reference [WCAG 2.2](https://www.w3.org/TR/WCAG22/). The project-specific spacing, palette, action-count and usability targets above are proposed design decisions. Sources consulted 2026-10-22.
