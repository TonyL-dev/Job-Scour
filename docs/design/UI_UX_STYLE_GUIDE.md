# UI/UX style specification — Clean workspace 1.0

Updated 2026-10-25. This is the reusable, implementation-aligned specification for the application's Apple-inspired visual style. It describes the result to reproduce, not just a design process or a mood board. A future website can use a different product name, content, framework and navigation structure while retaining this visual language.

Start with the [working reference site](ui-starter/index.html). Its `tokens.css` and `foundation.css` are synchronized copies of the application's actual styles, not approximate examples. Open `index.html` locally or serve the folder with any static server. No package installation, external fonts, CDN, account or backend is required.

Use the [Apple website analysis](apple-website-ui-analysis.md) for observations and sources, the [clean UI process](../coding-practices/CLEAN_UI_DESIGN_PROCESS.md) for project workflow, and [component maintenance](../developer/UI_COMPONENTS.md) for React-specific behavior. The original product blueprint and earlier design proposals remain historical references. This specification governs the current visual implementation.

## 1. The style in one brief

**Purpose:** create a clear place to read, choose and work. Content has the strongest visual presence. Controls are predictable and carefully grouped. The style should feel calm, precise, useful and approachable.

The recognizable ingredients are:

- A `#F5F5F7` canvas with white foreground surfaces.
- Near-black headings, readable gray supporting text and selective blue actions.
- System sans-serif typography with a consistent size/weight hierarchy.
- Filled pill-shaped primary actions, outlined secondary actions and text-like utilities.
- Neutral segmented selectors with a dark selected segment.
- Borderless rounded panels, separated by background contrast and space.
- Clear field boundaries and visible keyboard focus even when the surrounding panels are visually quiet.
- Larger gaps between tasks than between controls within a task.
- Short instructions, accurate state feedback and progressive disclosure of occasional detail.

The intended result is recognizable from its hierarchy and proportions. Merely applying blue to existing buttons does not reproduce it. Neither does making every panel enormous or every label faint.

## 2. What to copy into a new project

Copy all files in `ui-starter/` together. The portable CSS works with semantic HTML and can also be imported into React, Vue or another framework.

| File | Responsibility | Treatment in a new project |
|---|---|---|
| `tokens.css` | All core colors, type, spacing, radii, motion and sizing decisions | Copy first; make deliberate product-specific changes here |
| `foundation.css` | Base elements and reusable visual patterns | Preserve the visual contracts while adapting component markup |
| `site.css` | Example marketing/reference-page composition | Replace with the new site's own layout CSS |
| `index.html` | Demonstrates sections, actions, fields, tabs, feedback and a table | Replace example content; retain useful structure |
| `ui.js` | Accessible reference tabs/disclosure and a page-only demo save | Replace demo save with real behavior; port interaction semantics |
| `manifest.json` | Style version and hashes of synchronized CSS | Reference provenance; regenerate if maintaining a derived kit |

Import order is important:

```html
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="foundation.css">
<link rel="stylesheet" href="your-site-layout.css">
```

Do not paste the original application's career/resume APIs, secrets, local owner assumptions, version pins or privacy configuration into a new website. Visual reuse is independent of its business and security architecture. Keep an adoption record containing the new audience, key tasks, content sensitivity, supported devices, framework, accessibility target and any deliberate departures from this guide.

## 3. Canonical tokens

The following block is generated from `frontend/src/styles/tokens.css`. In this repository, edit the source tokens and run `python scripts/ui_style.py sync`; do not manually update this block or the starter copies separately. `python scripts/ui_style.py check` detects drift and checks eleven principal contrast pairs. The ordinary repository `check` also runs it.

<!-- ui-tokens:start -->

```css
/* Clean workspace style 1.0.0. Portable: no network assets or product-specific values. */
:root {
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-body: 1.0625rem;
  --font-small: .875rem;
  --font-caption: .75rem;
  --font-hero: clamp(2rem, 5vw, 3.5rem);
  --font-page: clamp(2rem, 4vw, 2.5rem);
  --font-section: clamp(1.375rem, 2vw, 1.5rem);
  --font-subheading: 1.25rem;
  --weight-regular: 400;
  --weight-medium: 500;
  --weight-semibold: 600;
  --line-body: 1.5;
  --line-heading: 1.1;
  --tracking-heading: -.025em;

  --color-bg: #f5f5f7;
  --color-surface: #ffffff;
  --color-surface-muted: #e8e8ed;
  --color-sidebar: #fbfbfd;
  --color-text: #1d1d1f;
  --color-text-muted: #6e6e73;
  --color-border: #dedee3;
  --color-control-border: #86868b;
  --color-action: #0071e3;
  --color-action-hover: #0068d1;
  --color-link: #0066cc;
  --color-link-hover: #004f9f;
  --color-focus: #0066cc;
  --color-selected: #1d1d1f;
  --color-on-selected: #ffffff;
  --color-info-bg: #edf4ff;
  --color-danger: #ac2424;
  --color-danger-bg: #fff0f0;
  --color-warning: #704900;
  --color-warning-bg: #fff4d9;
  --color-success: #287339;

  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;
  --space-24: 96px;

  --radius-control: 12px;
  --radius-panel: 24px;
  --radius-feature: 28px;
  --radius-pill: 999px;
  --control-height: 44px;
  --action-gap: 16px;
  --panel-padding: 32px;
  --page-gutter: 48px;
  --width-content: 1120px;
  --width-reading: 680px;
  --width-form: 760px;
  --motion-fast: 160ms;
  --motion-panel: 240ms;
  --ease-standard: cubic-bezier(.2, 0, .2, 1);
  --shadow-overlay: 0 12px 40px #00000014;
}

@media (max-width: 800px) {
  :root { --page-gutter: 24px; --panel-padding: 24px; }
}

@media (max-width: 480px) {
  :root { --page-gutter: 16px; --panel-padding: 20px; }
}
```

<!-- ui-tokens:end -->

Use tokens through semantic names rather than copying a hex value into every component. Product-specific layout can add tokens when a value has a reusable role. Keep experimental one-off values out of the foundation until the pattern has earned reuse.

## 4. Color roles and contrast

| Role | Required usage |
|---|---|
| Canvas | `--color-bg`; the quiet surrounding workspace |
| Surface | `--color-surface`; a coherent foreground task or content group |
| Muted surface | `--color-surface-muted`; segmented tracks, preview surroundings and occasional grouped regions |
| Main text | `--color-text`; headings, entered values and important labels |
| Secondary text | `--color-text-muted`; supporting copy, metadata and hints, never disabled-looking essential instructions |
| Primary action | `--color-action`; one next commitment in an active task region |
| Links | `--color-link`; navigation and lower-emphasis actions on light surfaces |
| Selection | `--color-selected` + `--color-on-selected`; the active segment of a mutually exclusive view |
| Field boundary | `--color-control-border`; recognizable input/control edges |
| Structural separator | `--color-border`; noninteractive dividers, not a substitute for the stronger field boundary |
| Error/warning/success | Dedicated semantic tokens plus a written explanation |

The primary fill and link color are intentionally separate: `#0071E3` and `#0066CC`. White on the primary fill passes the 4.5:1 normal-text threshold. Muted text remains readable on both white and the canvas. Recompute contrast after brand customization; a palette swatch by itself cannot establish contrast in the final component.

Keep the interface mostly neutral. Use photography, document previews, charts or user content to supply additional color when they serve the task. Do not give each navigation group a decorative accent. A red operation should mean a destructive consequence or error, not merely an alternative button.

No full dark theme ships with this specification. The dark selected segment is a component state, not dark mode. A future dark theme requires its own semantic pairs, images, boundaries, focus states and validation.

## 5. Typography and text rhythm

Use the system font stack in the token file. A Mac can use its native system UI font; Windows normally uses Segoe UI. Preserve the hierarchy and geometry across platforms while accepting differences in glyph widths and wrapping. No downloaded Apple fonts are required.

| Role | Specification | Usage |
|---|---|---|
| Website hero | 32–56 px (`--font-hero`), weight 600, approximately 1.1 line height | One introductory statement on a marketing/reference page |
| App page title | 32–40 px (`--font-page`), weight 600, 1.1 line height | One h1 identifying the current working context |
| Section title | 22–24 px, weight 600, 1.2 line height | A major content/task group |
| Subheading | 20 px, weight 600, 1.3 line height | A record group or a subordinate task |
| Body/intro | 17 px, weight 400, 1.5 line height | Approximately 25.5 px line boxes |
| Field values | 16 px, weight 400, 1.5 line height | Inputs/selects; comfortable entry and narrow-screen readability |
| Labels/buttons/hints | 14 px; 400 or 500 by role | Operational text, action labels, supporting instructions |
| Caption | 12 px | Low-priority metadata only; not essential errors or form instructions |

Keep headings compact, with `-.025em` tracking for the main hierarchy. Do not apply tight headline tracking to inputs or body paragraphs. Use sentence case for titles and controls; small eyebrows may be uppercase, without wide decorative letter spacing.

Default reading width is 680 px. Introductory copy should usually be one or two short sentences. Use a single visual type family; a document preview may use its document-specific fonts because it is the artifact, not app chrome. Never restyle exported documents accidentally by changing global application typography.

## 6. Spacing rules

The scale is 4, 8, 12, 16, 20, 24, 32, 40, 48, 64 and 96 px. These values are project decisions inspired by the research, not a claim that Apple's entire website follows this exact scale.

| Relationship | Default |
|---|---|
| Label → control | 8 px |
| Closely related metadata | 4–8 px |
| Related action targets | 16 px |
| Field groups / paragraph group → actions | 24 px |
| Panel interior | 32 px desktop; 24 px at ≤800; 20 px at ≤480 |
| Separate foreground panels | 32 px |
| App page header → content | 40 px desktop; 32 px narrow |
| Major website sections | 64 px vertical padding; 48 px narrow |
| Website hero | Up to 96 px top padding when the content warrants it |

A panel title and its fields belong together. A source editor and a document download are different tasks: separate them spatially, even if both contain buttons. Use layout `gap` rather than literal spaces, arbitrary `<br>` tags or a global `button + button` margin rule.

Do not increase all spacing indiscriminately. The goal is readable groups, not maximum page height. Remove repeated headings or redundant controls before adding more blank space. Long operational forms can remain compact inside the shared rhythm.

## 7. Widths, grids and responsive behavior

Two composition templates are supported:

**Website/reference page:** a centered `.page-width` container with a 1120 px maximum content width and responsive side gutters. Use a centered hero when there is a single introductory message. Use left-aligned headings and copy for reading, features and forms. A two-column feature grid becomes one column at 800 px.

**Application workspace:** a 224 px desktop sidebar and a content region. Standard main content has a 1216 px outer maximum including 48 px gutters, leaving 1120 px usable content. The document workspace can grow to an 1800 px outer maximum. Its editor/preview grid has a 32 px gap and a minimum 360 px preview column before the single-column mode takes over.

| Breakpoint | Application change | Portable/reference change |
|---|---|---|
| >1150 px | Editor and actual preview side by side | Composition can remain two columns |
| ≤1150 px | Editor/review grids use one column; Studio offers Edit/Preview selection | No universal site change required |
| ≤800 px | Sidebar becomes a labeled modal navigation drawer; forms/diffs become one column | Gutters 24 px, panels 24 px, reference grids one column |
| ≤480 px | Gutters 16 px, panels 20 px, action groups may distribute full available width | Same token changes; controls wrap intentionally |

Use `minmax(0, 1fr)` and `min-width: 0` on flexible content. Preserve wrapping for long names, errors and user text. A PDF, data table or board can have its own labeled scroll container. The whole page must not scroll horizontally at 320 px because of an oversized field or button.

Avoid fixed card heights for editable content. Fixed/minimum heights are acceptable for a small set of reference/marketing cards when the text is controlled and zoom does not clip it. Do not center-align long forms or long paragraphs to imitate the homepage hero.

## 8. Surfaces, corners and elevation

- Standard task panels: white, 24 px corners, no resting shadow and no decorative outline.
- Large editorial/feature cards: 28 px corners.
- Fields and small content regions: 12 px corners.
- Actions and segmented selectors: pill radius 999 px.
- Fieldsets, dividers and tables: a restrained 1 px structural separator.
- Modal/overlay surfaces: the defined overlay shadow, plus a readable backdrop when modal.
- Danger panel: an explicit danger boundary and explanatory text.

A new panel means a new coherent content/task group. It does not mean every item needs another white rounded rectangle. Inside a panel, use subheadings, whitespace and fine separators. Resting shadows should not be layered under every card, field and button.

Example: an experience group has one employer/title/date header, its editable summary/duties and local item actions. Repeating the same employer heading above every duty adds noise. The implementation groups consecutive items for presentation while preserving their stored order, source references and independent controls.

## 9. Action hierarchy and buttons

| Variant | Appearance | Appropriate uses |
|---|---|---|
| Primary | Blue fill, white text, pill | Save a document, submit a confirmed task, begin the principal workflow |
| Secondary | Transparent fill, 1 px blue border, blue text, pill | Supporting export, alternative next step, adding a substantial item |
| Ghost | Transparent boundary and fill, blue text | Edit details, small utilities, reorder operations |
| Danger | Red text, transparent resting boundary; light red hover | Delete, retire or discard, with existing risk-appropriate safeguards |

Default minimum target is 44 × 44 px. Buttons have 14 px text and 10 px vertical / 21 px horizontal padding. Height may grow when a long label wraps. Do not shrink a label until it fits an arbitrary fixed width. Primary and secondary actions share geometry; visual emphasis comes from fill/border/text treatment.

One visually dominant action per active task region is the default. Aim for two or three visible document-level choices. Keep frequent Add/Edit/Accept/Reject and cancellation discoverable. Put occasional operations in an explicitly labeled disclosure such as More version actions. Do not hide validation warnings, protection state, consent or cancellation just to achieve a small button count.

Hover changes color/background subtly. Keyboard focus uses a 3 px blue outline with 4 px offset. Disabled buttons use native disabled semantics, reduced opacity and an explanation when the prerequisite is not obvious. Loading controls name the operation, such as Saving…, and prevent duplicate submission without falsely claiming success.

Use links for navigation and buttons for actions. An `<a class="button ...">` retains link semantics while presenting a prominent navigation action. A ghost action is still a button when it performs an operation. Inside forms, specify `type="button"` for utilities and cancellation so they do not submit accidentally.

## 10. Action groups and document toolbars

```html
<div class="actions">
  <button class="button button-primary" type="submit">Save changes</button>
  <button class="button button-secondary" type="button">Export PDF</button>
  <button class="button button-ghost" type="button">Cancel</button>
</div>
```

The group owns the 16 px gaps. Do not add per-button left margins. On narrow screens, wrapping should preserve meaningful order and adequate targets. A destructive utility should not be wedged between two ordinary navigation links.

The document toolbar contains truthful save state and document-level save/download actions. Its location does not change between Content and Appearance views. Existing save-and-download behavior must remain explicit. Historical export controls must identify the selected saved version rather than silently exporting the current draft.

## 11. Forms and field states

Use a persistent visible label. Placeholder text is a hint, not a label. Required/optional status must be understandable without color. Default field values are 16 px with 11 px vertical / 14 px horizontal padding and a 1 px field border; ordinary input height is approximately 48 px, above the 44 px minimum. Textareas begin at 112 px and grow vertically.

```html
<label for="project-name">Project name
  <input id="project-name" name="name" required aria-describedby="project-name-hint">
</label>
<p id="project-name-hint" class="helper-text">Choose a name you will recognize.</p>

<label for="contact-email">Email address
  <input id="contact-email" type="email" aria-invalid="true"
         aria-describedby="contact-email-error">
</label>
<p class="field-error" id="contact-email-error">Enter an address such as name@example.com.</p>
```

Keep errors specific and close to the field. Retain entered data after a failed save. Do not invent a successful state while a request is pending. Date constraints, source validity, concurrency conflicts and permissions remain enforced by the application; the style layer cannot replace validation.

Checkbox labels provide a 44 px-tall clickable row around a 20 px checkbox. Use a fieldset/legend for related choices. Avoid converting checkboxes into switches unless the semantics and immediate-save behavior actually match a switch.

## 12. Navigation and selection

Desktop sidebar navigation groups user tasks and retains visible destination names. The selected destination uses a neutral surface and stronger text. The mobile trigger says Navigation and opens a native modal dialog with a title, close action, keyboard containment and Escape dismissal. Closing restores focus; choosing a route focuses main content. Do not rely on hover-only navigation.

Segmented choices share one `#E8E8ED` track with 4 px internal padding and a dark selected segment. Use this pattern for a small set of mutually exclusive views such as Content/Appearance, not unrelated operations such as Save/Delete/Export.

Actual tabs require tablist/tab/tabpanel relationships, selected state, roving tab stops, arrow keys and Home/End. Keep draft-owning panels mounted when hiding them. A group of `aria-pressed` buttons is a valid alternative for layout toggles such as Edit/Preview; it should not claim tab semantics unless it implements them.

## 13. Disclosure, menus and dialogs

The application uses native `details`/`summary` for occasional actions and supporting material. It remains in document flow, with normal Tab navigation. Escape closes the disclosure and returns focus to the summary. This is deliberately not an ARIA menu; do not add `role="menu"` to ordinary buttons without the corresponding keyboard behavior.

When opening a modal, provide an accessible title, sensible initial focus, background isolation, an obvious close path and restored focus. Prefer platform/native behavior or a proven accessible primitive over a visually attractive but incomplete custom overlay. Confirmations must describe the actual consequence. Do not add confirmation dialogs to routine reversible actions solely for visual consistency.

## 14. Feedback and asynchronous work

| State | Presentation and behavior |
|---|---|
| Loading | A short named status; retain relevant context |
| Empty | Explain what belongs here and provide one useful next step |
| Busy mutation | State what is happening and block duplicate submission |
| Saved | Show success only after persistence confirms it |
| Unsaved | Preserve the draft and make the pending state clear |
| Conflict | Explain the conflict and a safe recovery path; retain input |
| Recoverable error | Explain what failed and offer retry where appropriate |
| Long-running task | Visible progress/cancellation; reconnect and partial results where implemented |
| Locked workspace | Clear private content through the existing privacy barrier, then present unlock |

Use polite status announcements for ordinary progress/success. Use alerts for failures requiring attention. Do not color success red or announce every animation/frame as an alert. Pair status colors with words. No fake progress percentages or arbitrary success timers.

The starter's save is explicitly a local demonstration. Replace it with real persistence and errors in a production application. A polished status label is not proof of a completed write.

## 15. Lists, tables, boards and document previews

Collection rows should look like content choices rather than a wall of outlined pills. Use text alignment, whitespace and a fine separator; reveal a meaningful hover/focus treatment. Keep the entire target keyboard reachable.

Tables use left alignment, 16 px cell padding, readable column headings and horizontal separators. Wide tables belong in a labeled, keyboard-focusable region that can scroll independently. A board can use neutral columns and white item cards, while retaining a keyboard/table alternative.

A real document preview is a separate visual surface. Its white paper and typography belong to the document. Surround it with a muted neutral frame; keep page count, updating/error state and export meaning clear. A CSS drawing of a page in the reference starter is only an illustration, not a replacement for this app's actual Chromium/PDF.js output.

## 16. Copy, imagery and icons

Lead with a concrete subject or task. Prefer Save changes, Add experience and Open resumes over generic Go, Continue or Submit when the more specific label helps. Explain technical details only when they affect a user decision. Keep source, privacy and export limitations that matter to the workflow.

Use images when they explain the product or content. In a working editor, the artifact itself is often the most useful visual. Do not add decorative stock photos, gradients or illustrations merely to fill space. Images should have a clear crop/aspect-ratio policy and appropriate alt text; decorative images have empty alt text.

Use a small coherent local icon set if icons help recognition. Match stroke/size and preserve accessible names. Visible text remains preferable for unfamiliar actions. Neither Apple logos nor its icon/font files are required to reproduce the style.

## 17. Motion and accessibility

Use 160 ms transitions for ordinary color/state changes and up to 240 ms for panel-level presentation. Animate only properties that help explain a change. The current foundation does not add elaborate entrance, scroll or parallax animation. It disables motion under `prefers-reduced-motion` and retains explicit boundaries/focus in forced-colors mode.

Maintain a 320 CSS px reflow check, keyboard operation, visible focus, accessible labels, programmatically associated field errors, meaningful heading order and truthful status semantics. Normal text targets 4.5:1 contrast and applicable control boundaries/focus 3:1. The product's 44 px target exceeds the WCAG 2.2 minimum pointer criterion; specific exceptions and other criteria still require review. [WCAG 2.2](https://www.w3.org/TR/WCAG22/)

Automated contrast and interaction checks are bounded evidence. They do not establish full screen-reader interoperability or representative usability. Actually inspect long content, focus visibility, zoom, narrow layouts, error recovery and dialogs. Never use visually hidden content as an authorization or privacy control.

## 18. Step-by-step workflow for another website

1. Complete the product brief and define three to five real tasks.
2. Copy the starter kit; keep the original token names and import order initially.
3. Choose the website container or application-shell composition. Adapt navigation to the new information architecture.
4. Design the hardest useful screen before polishing the homepage.
5. Assign a clear primary action to each task region; list utilities and destructive operations separately.
6. Build structure with semantic HTML and the shared field/panel/action patterns.
7. Replace sample content and local demo handlers. Implement actual data, validation, permissions and recovery.
8. Apply consistent tokens to every screen and every state, including empty/error/busy/disabled/conflict views.
9. Inspect desktop and narrow screenshots side by side. Fix accidental wrapping, repeated decoration and hierarchy problems.
10. Keyboard-test navigation, tabs, disclosures, dialogs and full task completion. Check actual zoom and assistive technology where required.
11. Run contrast, overflow, interaction, persistence and release checks appropriate to the project.
12. Record decisions, exceptions, screenshots and unresolved checks. Update the adopted specification when the system changes.

Do not replace the new project's architecture with this application's backend simply to reuse its style. Keep content and presentation separate and select the framework/storage/deployment appropriate to the new product.

## 19. Copyable implementation prompt

Use this prompt with the guide and the starter folder attached or accessible:

```text
Build [website/application purpose] for [audience] using the attached
UI_UX_STYLE_GUIDE.md and ui-starter visual kit, style version 1.0.0.

Keep tokens.css and foundation.css as the visual starting point. Reproduce
their typography, colors, spacing, pill actions, dark selected segments,
borderless rounded panels, readable fields and focus treatment. Use a system
font stack and local assets. Do not approximate the style with arbitrary
colors, multiple font families, excessive card outlines or resting shadows.

Primary tasks: [three to five tasks].
Pages: [required pages].
Content/assets: [available content and licensed local assets].
Framework: [chosen stack or ask for a suitable choice].
Data/privacy requirements: [requirements].
Deployment and supported devices: [requirements].

Adapt information architecture and content to this product. Use clear action
hierarchy and deliberate groups. Keep ordinary text at 17px, fields at 16px,
buttons/labels at 14px, 44px minimum targets and the documented breakpoints.
Keep errors, loading, empty, saved, conflict and disabled states coherent.
Do not ship the starter's fake page-only save as production persistence.

Verify populated desktop/narrow screens, 320px reflow, keyboard/focus,
contrast, error recovery and actual user workflows. Show screenshots and
report only checks actually performed. Document deliberate deviations.
```

Fill in the bracketed fields. This prompt is a starting brief, not a guarantee of identical output from every generator. For close reproduction, provide the actual CSS kit and a screenshot of the reference in addition to this document.

## 20. Review checklist and change policy

Before accepting a new screen:

- Its purpose and next action are clear without reading a long introduction.
- Typography follows the hierarchy; long text has a reasonable reading width.
- Primary/secondary/utility actions are visually distinct and spatially grouped.
- The spacing between unrelated tasks is larger than gaps within a group.
- Panels group content meaningfully; their nesting and repeated headings are necessary.
- Fields have visible labels, readable values, focus and useful error messages.
- Narrow layouts preserve functionality, drafts and a sensible reading order.
- Long text, large data sets, empty/error/busy/conflict states and disabled prerequisites were inspected.
- Keyboard users can complete the workflow and recover focus after overlays.
- The final site uses the adopted tokens and shared foundation instead of drifting page-specific copies.
- Product behavior, data safety and privacy have their own implementation and verification.

The application source tokens/foundation are canonical for this repository. `sync` copies them into the starter, refreshes this guide's token block and writes hashes to the manifest. `check` verifies those artifacts. Update the style version deliberately when changing its reusable contract. Preserve the Apple research as observations; edit this specification when the adopted design changes.

The Phase 7 [implementation record](07-ui-implementation.md) and root IMPLEMENTATION_STATUS.md hold actual verification results. A style guide describes expectations; it does not establish that every accessibility, usability or deployment gate passed.
