# Phase 7 implementation record

Implementation authorized 2026-10-22. This record supplements the preserved plan and tracks evidence rather than claiming participant testing from automation.

## Baseline and action inventory

The baseline is the pre-redesign synthetic SQLCipher/Chromium workflow. Its screenshots cover structured experience, generation, narrow preview, history, templates and applications. Personal stores are excluded. Desktop shell and Studio wireframes are in the Phase 7 plan; the narrow reference is navigation drawer → document toolbar → Edit/Preview switch → preserved content panel. No representative tester timing baseline is available.

| Route | Preserved actions and states | Implemented placement |
|---|---|---|
| / | Connection/retry, enter career, open resumes | Task cards, secondary connection panel |
| /career/:kind | All categories, add/edit/save/cancel/retire, validation/loading/error/empty | Category navigation, record cards, focused form |
| /imports | Upload/retention, select, optional AI extraction, candidates, review/commit/discard/delete original/cancel | Upload, saved list, review action groups |
| /profile | Select evidence/review, questions/cancel, answers/prepare/confirm/discard | Evidence, saved list, review cards |
| /resumes | Select/new, autosave, manual save/download, details/gold, appearance, all section/item/source/lock controls | Document toolbar, content/appearance tabs, contextual actions and preview |
| /jobs | Save/select/analyze/cancel/new, matching/mode, results | Setup and analysis panels |
| /generate | Inputs, generate/cancel/reconnect, decisions/edit/bulk review, scope/locks/regenerate, save review/commit/download | Stage indicator, review cards, advanced regeneration and commit panel |
| /history | Filters/select/compare, PDF/DOCX, restore/duplicate, ATS/editor/source/track links | Version selection, export and version action groups |
| /applications | Filter, board/table, edit/new/save, events, follow-ups, exact downloads/links | Board cards, details form, exact artifact controls |
| /letters | Context/sources/generate/cancel, run/review/keep/save, version/restore/edit/export/track | Context, review, version cards |
| /templates | Select/copy, style/HTML/CSS/assets, preview/save/duplicate/retire | Presentation and advanced details, measured preview |
| /settings/ai | Consent/default setup, detect, endpoints/profiles/assign/test, registry | Default setup, explicit advanced disclosure |
| /prompts | Packaged/saved, fork/save, evaluate/cancel/report/activate/reset | Preference task, optional reference, review |
| /privacy | Passcode/lock, encryption status, exports, typed deletion | Separate protection/export/danger panels |

All routes retain their URLs, query parameters and hash targets. All pages retain loading/error/empty feedback and domain validations. WorkspaceGate retains unlock/retry/lock clearing. No model requests, persistence contracts or generated types are changed by presentation work.

## Validation status

Native engineering acceptance completed 2026-10-25. Milestones 7A–7E are implemented; 7F automated native gates passed, with the external/manual acceptance limits below.

- Final `python scripts/tasks.py check` passed: Ruff lint/format (154 files), strict mypy (119 source files), 86 backend tests, generated API/type drift, ESLint, strict TypeScript, 25 frontend tests and production Vite build.
- Final expanded `e2e` passed A/D/E/F, 6A–6F, structured experience and Phase 7 tabs/navigation/responsiveness against disposable SQLCipher storage, actual Chromium/PDF.js and synthetic model responses. No page errors or external requests. Studio was checked at 320/390/768/1280/1440 CSS px; all other routes at 390/1440. Keyboard tab switching, Escape/focus return and Edit/Preview draft preservation passed. A 640px viewport is only a reflow approximation for 200% zoom.
- Final `fresh-install` passed with new dependency environments: production browser UI, keyboard, actual PDF/ATS, outage/restart. Existing host OS; no clean-OS certification or Docker/Nginx claim.
- Final `audit` passed Python and pnpm with no known vulnerabilities. TLS verification remained enabled using process-local certifi CA paths.
- Native runtime: Python 3.14.8, Node 24.21.0, pnpm 11.19.0, Playwright 1.63.0 / Chromium 153.0.8010.12. No new Python 3.12 or PostgreSQL compatibility run was made for this UI release.
- Visually inspected populated Studio desktop/narrow screenshots, overview, narrow settings and forced-colors output. Eight principal token contrast pairs passed their text/control thresholds; evidence `.validation/phase7-contrast.json`. Screenshot presence alone is not full accessibility certification.
- The first integrated check caught formatting under the wrong Ruff configuration and was corrected. Earlier expanded browser runs failed on 5-second letter-PDF and local-parser assertions and then hit Windows temporary-file cleanup locks. The final bounded expectations respect the existing parser timeout/polling and actual render latency; earlier runs remain failures.

The initial audit found 11 Python and six Vite advisories. A later feed update also identified filelock/setuptools/virtualenv/pypdf and Zod/Undici findings. Resolved pins: pypdf 6.21.2, certifi 2026.10.19, filelock 4.2.1, setuptools 84.1.0, virtualenv 21.14.10; Vite 8.3.3, locked Zod 4.6.7 and Undici 8.12.3. Python pins derive from installed package metadata; pnpm generated its lock. `pip check` passed. These are maintenance updates, not a framework replacement.

Still unverified: representative five-person task testing and the 20% timing target, actual browser 200% zoom and screen-reader interoperability, Docker/Nginx production acceptance (daemon unavailable), hosted CI, clean OS, native Word and live Codex container login. Prior expiry-revocation and renderer/parser containment findings remain unresolved. Do not call all Phase 7 acceptance gates complete.

Successful harness services/stores were stopped/removed by their own cleanup. Automatic approval review blocked deletion of two failed-run disposable stores (`.validation/phase4-e2e-ck2_xzn7` and `.validation/phase4-e2e-wdeu4wye`) without a specific reason; they remain ignored. No personal-store reads/writes, live inference, deployment, commits, remotes or publication were performed.

## Apple-inspired refinement and reusable style — 2026-10-25

The follow-up request authorized aligning the actual application with the Apple website analysis and documenting enough detail to reproduce the style in future websites. The canonical specification is now [UI/UX style specification — Clean workspace 1.0](UI_UX_STYLE_GUIDE.md), with a [working, copyable reference site](ui-starter/index.html). The guide specifies exact tokens, markup patterns, action hierarchy, spacing and widths, typography, component states, responsive behavior, accessibility, writing, adoption steps and a reusable coding-agent prompt. It distinguishes observed Apple patterns from the application's deliberate adaptations.

The implementation uses the light gray canvas, white borderless panels, near-black system typography, selective blue pill actions, outlined supporting actions and neutral/dark segmented selection. Panel padding is 32px on desktop, then 24px/20px; page gutters are 48px, then 24px/16px; related actions use a 16px gap. Fields retain visible boundaries and keyboard focus. Overview cards prioritize the two main tasks, navigation is quieter, and contextual utilities move into deliberate groups and disclosures. Consecutive experience items share their stored factual company/title/date heading while retaining independent content, ordering, sources and locks. Editing source details appears beside that experience group.

`frontend/src/styles/tokens.css` and `foundation.css` are the canonical portable CSS. `scripts/ui_style.py sync` distributes exact copies into the reference kit, updates its hash manifest and regenerates the guide's token appendix. `check` rejects drift and checks eleven principal contrast pairs; the normal repository check includes it. The reference browser gate is part of `e2e` and verifies keyboard tabs, retained drafts, demo feedback, Escape/focus behavior, control heights, 320/390/768/1280/1440px reflow, zero page errors and zero remote requests. Forced-colors and reduced-motion screenshots supplement these checks; they do not establish full accessibility conformance.

The final product browser run passed A/D/E/F, Phase 6, structured experience and Phase 7 workflows with real SQLCipher, Chromium/PDF.js and synthetic model responses. The standalone reference browser run passed. Desktop overview/editor, narrow overview and reference/forced-colors screenshots were visually reviewed. The focused frontend suite now contains 26 passing tests, including factual heading grouping and cancellation without lost draft content. Final release-suite evidence follows in IMPLEMENTATION_STATUS.md. Earlier evidence and unresolved manual/platform/security limits above remain applicable. No new dependencies or API contracts were introduced by this follow-up.

The first follow-up fresh-install run failed strict TypeScript on the newly added regression test (missing required experience description and unsupported role-query `exact` options). The fixture now supplies the field and the queries use their default exact-name behavior; the corrected strict TypeScript run passed. The original failure log is retained in `.validation/ui-style-fresh-install-first-failure.log`. A fresh isolated rerun supplies the final installation result.

Final follow-up native gates passed: check (155 Ruff-formatted files, strict mypy 119 files, 86 backend/26 frontend tests, lint/types/contracts/build), audit (Python/pnpm: no known vulnerabilities), product and distributed-reference e2e, and corrected fresh-install (production UI/PDF/ATS/outage/restart). CSS/documented token/manifest consistency and eleven contrast pairs passed; 94 local links/assets passed. No new compatibility or manual usability claim is made beyond the explicit evidence above. All six session-ending documents record the results and preserve historical failures and blueprint.
