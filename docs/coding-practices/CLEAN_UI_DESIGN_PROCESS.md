# Clean UI design process

For reproducing this application's current style, start with the [UI/UX style specification](../design/UI_UX_STYLE_GUIDE.md) and [copyable reference site](../design/ui-starter/index.html). Those define exact adopted values and examples.

A reusable method for designing calm, understandable applications. Copy this guide into a future project and fill in its adoption record. It is a process document, not an installed skill or a requirement to use a particular framework. For its application here, see the [Phase 7 UI plan](../design/07-ui-refinement-plan.md).

## 1. Start with an explicit brief

Complete this before drawing screens:

| Decision | Project answer |
|---|---|
| Audience and experience level | Who uses the product, and how often? |
| Three most important tasks | What must people accomplish without help? |
| Devices and input methods | Desktop, narrow screen, touch, keyboard, assistive technology |
| Tone | Three concrete qualities, such as calm, precise, approachable |
| Data and safety constraints | What may never be hidden, lost or sent externally? |
| Existing behavior to preserve | URLs, persistence, undo, permissions, exports, integrations |
| Scope and exclusions | Which screens change, and which features do not? |
| Success measures | Task completion, wrong turns, time, error recovery, accessibility |
| Visual reference and rationale | Which principle is useful from each reference? |

Translate adjectives into decisions. “Clean” can mean fewer competing actions, stronger grouping and consistent alignment. “Minimal” must not mean unlabeled icons or missing instructions. A recognizable style comes from repeated rules, not copying branding.

## 2. Audit before polishing

Inventory routes, reusable patterns, actions and states. Inspect both source and actual screens; distinguish observed code from measured behavior. Use synthetic or approved non-sensitive data.

For each screen record:

```text
Screen / route:
User's goal:
Primary action:
Frequent secondary actions:
Infrequent actions:
Dangerous actions and consequences:
Inputs and prerequisite information:
Loading / empty / error / saving / conflict / success states:
Narrow-screen and keyboard problems:
Baseline screenshot and task observations:
Proposed change and expected benefit:
```

Count competing action groups and note accidental wrapping. Look for equal visual weight on unequal actions, repeated borders, excessive nesting, inconsistent labels and controls too far from the content they affect. Measure realistic long text and populated screens, not only attractive empty states.

## 3. Design the workflow and hierarchy

Write the shortest understandable path from user intent to outcome. Group navigation around user concepts rather than internal modules. Keep the current location visible and preserve important deep links.

Assign each action a role:

| Role | Presentation default |
|---|---|
| Next meaningful commitment | One filled primary action in the current task region |
| Common supporting action | Quiet secondary control near the relevant content |
| Infrequent utility | Labeled menu or progressive disclosure |
| Navigation | Link or navigation item rather than a submit-looking button |
| Destructive action | Separate grouping, clear consequence and appropriate recovery/confirmation |

Hide infrequent complexity, not the next step, warnings, save state or permission requirements. When a validation error occurs inside collapsed content, reveal it and direct focus appropriately. Menus reduce visual density but add discovery cost; verify that tradeoff with task testing.

## 4. Wireframe before styling

Draw low-detail layouts for a common desktop size and a narrow screen. Include the title, primary action, main content, contextual tools and feedback. Decide reading order and focus order together.

Start with the hardest useful screen, usually an editor, review flow or data-heavy view. If the design only works on a landing page, the design system is not ready. Show an error and a busy state in the wireframe. Check that changing panels does not imply losing work.

## 5. Define a small token system

Choose a spacing scale, typography hierarchy, semantic colors, control sizes, radii, elevation and motion rules. Start with a small set and expand only for a documented need.

Example starting points: a 4 px spacing base; 12–16 px gaps between related controls; 24–32 px between groups; 16 px body text; 44 px interactive targets; one accent color. These are defaults to evaluate, not universal rules. Large empty margins cannot compensate for crowded action rows.

Use semantic color names for text, background, border, focus, selection and status. Check actual foreground/background combinations in every state. Keep essential text readable; do not make secondary information so faint that it disappears. Prefer system or bundled licensed fonts and local icons when privacy/offline use matters.

## 6. Build components with behavior, not just appearance

Define a component matrix before migrating screens:

| Component | Required examples and behavior |
|---|---|
| Button / action group | Primary, secondary, tertiary, destructive, disabled, busy, keyboard focus, wrapping |
| Field | Label, hint, required/optional, error, disabled, long values |
| Menu / disclosure | Trigger name, open state, keyboard interaction, Escape, focus return |
| Dialog / drawer | Accessible title, initial focus, modal behavior, close path, scroll, restored focus |
| Status notice | Loading, empty, success, warning, recoverable error, retry |
| Tabs / navigation | Selected state, proper semantics, keyboard behavior, preserved panel state |

Prefer native controls where they meet the need. If a complex interaction requires an accessible library, evaluate it deliberately and record the dependency choice. Avoid custom widgets without keyboard and screen-reader behavior. Do not adopt a whole framework merely to get different corner radii.

## 7. Implement one complete slice

Migrate a representative workflow end to end: layout, components, states, responsiveness and tests. Keep business rules and persistence separate from visual components. Use stable identities and preserve draft state when panels move or hide.

Review that slice before copying the patterns. Migrate the remaining screens in small groups; remove obsolete styles instead of layering permanent overrides. Keep a route/action inventory so “simplification” cannot silently remove functionality.

## 8. Verify usability and accessibility

Use the same realistic tasks and fixtures before and after. Ask participants to complete the goal without telling them which controls to click. Record completion, time, wrong turns, assistance and errors; summarize observed problems rather than relying only on “looks nicer.” Small samples are directional evidence.

Check desktop/narrow layouts, long labels, large data sets, zoom and text enlargement. Keyboard-test the full flow and inspect focus after every menu/dialog closes. Review contrast, accessible names, error association, status announcements, reduced motion and forced colors. Automated checks are useful but cannot establish full accessibility or usability.

For a web project targeting WCAG 2.2 AA, normal text generally needs 4.5:1 contrast, large text 3:1, and applicable non-text controls 3:1. The minimum pointer target criterion is 24 × 24 CSS px with defined exceptions; a 44 px project target is more generous. Test reflow at 320 CSS px and distinguish genuinely two-dimensional regions from accidental page overflow. Consult the normative [WCAG 2.2 standard](https://www.w3.org/TR/WCAG22/) for exact criteria and exceptions.

## 9. Document and maintain the result

Keep these artifacts with the project:

1. Design brief and scope.
2. Route/action/state inventory and baseline evidence.
3. Desktop/narrow wireframes and selected visual direction.
4. Tokens and component examples with usage rules.
5. Before/after task observations and accessibility results.
6. Migration checklist, decisions, exceptions and unresolved checks.

Reusable review checklist:

- Can someone identify the page purpose and next action immediately?
- Are related controls close together and unrelated groups clearly separated?
- Are common actions visible and rare actions still discoverable?
- Do spacing, typography and component variants follow shared rules?
- Are labels explicit, errors actionable and saving status truthful?
- Can users recover from mistakes without losing work?
- Does the screen remain usable with keyboard, zoom and narrow layouts?
- Are loading, empty, error, conflict and success states designed?
- Has the actual workflow been tested, including persistence and exports?
- Are remaining limitations documented without overstating validation?

Suggested project instruction:

```text
Read the adopted UI design brief and component guidance before UI changes.
Use semantic tokens and shared controls. Preserve task, data and privacy behavior.
Verify realistic states, keyboard operation and narrow layouts.
Update the route/action inventory and record actual validation evidence.
```

## References and interpretation

Apple's [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines) and [button guidance](https://developer.apple.com/design/human-interface-guidelines/buttons) are useful references for hierarchy and consistency. Apply relevant principles to the target platform rather than importing native-platform assumptions into the web. The workflow and example token values in this guide are project recommendations, not quotations or official Apple requirements. References consulted 2026-10-22.

For a worked inspection example, read the [Apple website analysis](../design/apple-website-ui-analysis.md). It separates measured browser styles, responsive CSS, interpretations and application recommendations.

The process is intentionally general. The adopted style specification selects exact values (including 16px action gaps) and keeps its token block and reference CSS synchronized with the implementation. Copy the kit with the guide when asking another project or coding agent to reproduce the appearance.
