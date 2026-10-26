# UI components and maintenance — style 1.0.0

The canonical [UI/UX style specification](../design/UI_UX_STYLE_GUIDE.md) defines the exact visual contract and the [portable reference site](../design/ui-starter/index.html) demonstrates it. Use those when reproducing the style in another project. This document describes the application components.

Phase 7 keeps the existing React/TypeScript/CSS stack. App presentation uses [tokens](../../frontend/src/styles/tokens.css), [portable foundation](../../frontend/src/styles/foundation.css), [application layout styles](../../frontend/src/styles.css), [shared controls](../../frontend/src/components/ui/Controls.tsx) and [navigation](../../frontend/src/components/Navigation.tsx). Resume-rendering templates remain separate.

## Component contracts

| Component / pattern | Usage |
|---|---|
| `Button` | Pill geometry with 44px minimum targets. Default outlined secondary; explicit primary, ghost or danger variant. Native props and submit behavior are retained. Specify `type="button"` inside forms for non-submit actions. |
| `ActionGroup` | Flex layout with 16px gaps and narrow-screen wrapping. Group related actions only; separate distinct tasks. |
| `PageHeader` | 32–40px page title, optional eyebrow/description and optional trailing content. Keep existing accessible titles and deep links stable. |
| `StatusNotice` | Polite status by default; error uses alert semantics and error color. Success must not use the error treatment. |
| `Disclosure` | Native details/summary with ordinary tab navigation and Escape/focus return. This is not an ARIA menu. Use for occasional operations, not essential progress, consent or warnings. |
| `Tabs` | Neutral pill track and dark selected segment. Arrow/Home/End navigation, selected/tab/panel relationships and mounted hidden panels. Local drafts survive tab switches. Keep parent mutation/state ownership unchanged. |
| Native field pattern | Wrapping label, consistent input/select/textarea styles, visible required/optional text. Preserve labels and error association. Checkbox labels provide a larger clickable target. |
| Navigation dialog | Native modal dialog supplies focus containment and Escape behavior. Close returns to trigger; route navigation focuses main content. Desktop sidebar is grouped by user task. |

Examples:

```tsx
<ActionGroup>
  <Button variant="primary" disabled={saving} onClick={save}>Save changes</Button>
  <Button onClick={cancel}>Cancel</Button>
</ActionGroup>
<Disclosure title="More version actions">
  <ActionGroup><Button onClick={duplicate}>Duplicate</Button></ActionGroup>
</Disclosure>
```

Resume Studio keeps save/download outside both editor tabs, displays the actual mutation/dirty state, and switches Edit/Preview at narrow widths without unmounting either. Appearance controls change document metadata through the existing handlers. Consecutive items for the same sourced experience share a factual header; keys, order, source references and item locks remain independent. Source-detail forms open beside their selected group and save through the original career mutation. History's More version actions preserves restore and duplicate semantics. Native dialogs/disclosures were chosen over a new dependency; do not add partial ARIA menu semantics to ordinary disclosure content.

## Verification recipe

Run component keyboard/state tests plus the existing domain tests. The synthetic e2e harness covers tabs, drawer Escape/focus, mounted drafts, actual PDF preview, multiple viewport widths and every route's overflow/screenshots. A 640 CSS px viewport is a reflow approximation for a 1280 px browser at 200% zoom, not proof of actual browser zoom or screen-reader interoperability. Retain participant usability and manual accessibility limits in the implementation record.

Before changing shared selectors, review populated forms, long record labels, disabled/loading/error states, the application board, and narrow PDF previews. No remote fonts, icons, telemetry or CDN assets. Do not infer a successful data save from a visual state change; use the existing mutation result.

For future projects, copy the [clean UI process](../coding-practices/CLEAN_UI_DESIGN_PROCESS.md), complete its brief, then build components appropriate to that project. The current component code is an example rather than a universal requirement.

## Visual source and synchronization

`styles/tokens.css` is the primitive/semantic token source. `styles/foundation.css` supplies portable typography, panels, actions, fields, segmented controls, disclosures, notices, tables and accessibility fallbacks. `styles.css` imports both and owns product layout: navigation, Studio, real PDF frame and tracker. Route-level task panels combine the portable `panel` class with existing feature classes.

There is no global adjacent-button margin workaround. Related actions use ActionGroup; form footers separate editing from commitment. White panels are borderless by default, while fields retain a stronger visible boundary. Overlay elevation is reserved for dialogs.

Run `python scripts/ui_style.py sync` after changing reusable styles. It refreshes the portable starter CSS, manifest and the style guide's generated token block. `python scripts/ui_style.py check` verifies drift and eleven contrast pairs; it runs as part of `tasks.py check`. `tasks.py e2e` additionally runs the standalone reference's keyboard/draft/target/viewport checks after the product workflows. The browser example needs the existing backend Playwright environment; the distributed HTML/CSS/JS itself has no package dependency.
