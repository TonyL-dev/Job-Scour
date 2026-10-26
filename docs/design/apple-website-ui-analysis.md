# Apple website UI analysis

Inspected 2026-10-25: [Apple homepage](https://www.apple.com/), [Mac](https://www.apple.com/mac/) and [iPhone](https://www.apple.com/iphone/).

This is an inspection of the actual website, supplementing the earlier Phase 7 plan's Human Interface Guidelines research. Findings combine screenshots, read-only DOM/computed-style measurements and Apple's linked production CSS. Browser measurements came from a narrow embedded viewport, approximately 477 CSS px including its scrollbar. Desktop headline/button specifications below come from responsive CSS, not a newly captured full desktop screenshot. Locale prompts and campaign content vary; these are examples, not a universal Apple design specification.

Private evidence is in ignored `.validation/apple-ui-20261025/`. No career data was sent to Apple. The page inspection transmits ordinary browser requests only.

## 1. What creates the overall feel

The website foregrounds one product or topic at a time. A short heading establishes the subject, a short supporting line gives the benefit, and a small action group supplies the next step. Product photography carries much of the visual expression. The surrounding interface remains quiet.

The strongest reusable characteristics are clear hierarchy, deliberate grouping, constrained color, confident typography and consistent alignment. Removing detail indiscriminately would miss the point: Apple still provides extensive comparison, purchasing and legal information, but places it at different levels of the page.

For a resume application, content and preview should carry that emphasis. The most important work should be visible before settings and infrequent utilities.

## 2. Colors

| Observed color | Where it appears | Effect |
|---|---|---|
| `#FFFFFF` | Light surfaces, feature cards, text on filled blue controls | Clean foreground and clear separation from gray sections |
| `#F5F5F7` | Alternate sections, footer background, light text on dark hero sections | Very light neutral canvas without a strongly colored tint |
| `#1D1D1F` | Main text and dark selected segment | Near-black emphasis with a slightly softer appearance than pure black |
| `#000000` | Dark campaign imagery/background regions | Strong contrast between promotional sections |
| `#6E6E73` | Secondary navigation/submenu typography in inspected styles | Lower-priority text hierarchy |
| `#86868B` | Muted dark-theme callouts in homepage CSS | Secondary information on dark sections |
| `#0071E3` | Filled primary button background | A clear action accent |
| `#0066CC` | Links and outlined button text/border on light surfaces | A quieter navigational/supporting action |
| `#2997FF` | Links/outlined action accents in dark hero context | A brighter blue chosen for a dark surface |
| `#E8E8ED` | Mac category-control track | Groups related choices without separate outlined buttons |

The important relationship is neutral surfaces + dark text + selective accent. Product imagery supplies additional color without turning every control into a different accent. Dark sections are composed individually; the site is not simply alternating an app-wide dark-mode toggle.

Application translation: use one accent family for primary actions, selection and links. Reserve status colors for meaningful success, warning and error states. Check each text/background pair; copying an Apple gray into a different background does not establish accessible contrast.

Source: live computed styles on the pages above and Apple's [homepage foundation CSS](https://www.apple.com/v/homepage/a/styles/main.built.css), [homepage composition CSS](https://www.apple.com/v/homepage/a/styles/homepage.built.css).

## 3. Typography

The inspected CSS declares **SF Pro Display** for prominent headings and **SF Pro Text** for navigation, body copy and buttons. Fallbacks include Helvetica Neue, Helvetica, Arial and sans-serif. These are declared font stacks; font rendering also depends on the browser and loaded resources.

### Measured and source-verified examples

| Element | Large/default CSS | Medium CSS | Narrow CSS / observed value |
|---|---|---|---|
| Homepage hero headline | 56 px, weight 600, approximately 60 px line height | 48 px, approximately 52 px line height | 32 px, weight 600, 36 px line height |
| Homepage supporting line | 28 px, weight 400, 32 px line height | 24 px, 28 px line height | 19 px, weight 400, 23 px line height |
| Homepage hero button text | 17 px above the narrow breakpoint | Same hero rule applies above 734 px | 14 px, approximately 18 px line height |
| Mac page title | Not separately measured at desktop | Not separately measured | 40 px / 44 px, weight 600 |
| iPhone page title | Not separately measured at desktop | Not separately measured | 48 px / approximately 52 px |
| Mac section heading | Not separately measured at desktop | Not separately measured | 32 px / 36 px, weight 600 |
| Mac product name | Not separately measured at desktop | Not separately measured | 21 px / 25 px, weight 600 |
| Mac feature-card label/body | Not separately measured at desktop | Not separately measured | 14 px / approximately 18 px; label weight 600 |
| Default body context | — | — | 17 px / 25 px, weight 400 |

The homepage headline breakpoints in the inspected stylesheet are 1068 px and 734 px. They are page-specific responsive rules, not a required breakpoint system for this app.

Typography creates hierarchy through size and weight rather than many font families. Headline line heights are relatively tight; ordinary body text has more room. Tracking changes with size: the 56 px homepage headline uses `-.005em`, while its 32 px variant uses `.002em`. This is not a blanket instruction to tighten every label.

Application translation: use the installed local system font stack, 16 px body text, 28–32 px page titles, 20–24 px section headings and 14 px secondary text. Keep resume-document typography independent. Do not download or redistribute Apple's font files to imitate the website.

Source: [homepage foundation CSS](https://www.apple.com/v/homepage/a/styles/main.built.css) and live Mac/iPhone computed styles.

## 4. Spacing and layout

Apple uses multiple spacing scales at once. Closely related text and actions form a compact unit, while topics and sections have much larger separation.

| Inspected example | Observed value | Interpretation |
|---|---|---|
| Homepage headline → supporting line | 6 px default; 4 px narrow rule | These lines belong together |
| Supporting line → action group | 17 px default; 16 px medium; 11 px narrow | Actions remain attached to the message |
| Between paired homepage actions | 17 px default; 14 px narrow | Each action has its own target and breathing room |
| Homepage tile gutters | 12 px in the measured narrow layout | Separates full campaign regions without heavy borders |
| Mac feature-card text inset | 24 px on narrow cards | Text never touches card edges |
| Mac feature-card label → copy area | Copy wrapper adds 8 px top padding | A tighter internal hierarchy than the space between cards |
| Mac section heading side inset | Approximately 30 px in the inspected narrow layout | Shared alignment axis for section titles |
| Mac feature-card width | 260 px in the narrow gallery | The next card can peek into view and suggest continuation |
| iPhone lineup section | 112 px top padding in the sampled narrow state | Major sections have substantial separation |
| iPhone incentive section | 112 px top and bottom padding in the sampled narrow state | A section is a distinct topic, not another tightly stacked form field |

The website is not uniformly spacious: its global navigation and legal footer are dense. It gives space according to content purpose. Nor is everything centered: homepage campaign messages are centered, while category titles and product/card text are often left-aligned.

Application translation: 8–12 px within action groups, 16–24 px within panels, 24–32 px between groups and 32–48 px between major workspace sections. These are recommended app values, not Apple measurements. Marketing-scale 112 px section padding would make a working editor unnecessarily long.

Source: [homepage composition CSS](https://www.apple.com/v/homepage/a/styles/homepage.built.css), Mac/iPhone live geometry.

## 5. Buttons and action hierarchy

The inspected homepage pairs a filled action with a quieter outlined action. The first hero's Learn more action is filled blue while Buy is outlined; the iPhone product page can order Buy before Learn more. A button's emphasis therefore follows the context rather than a universal verb-to-style mapping.

Narrow homepage examples:

- Primary background `#0071E3`, white text.
- Secondary transparent background, 1 px blue outline, blue text.
- 14 px label, approximately 18 px line height.
- Computed padding 8 px vertically and 15 px horizontally, plus the 1 px border: 36 px measured total height.
- `border-radius: 980px`, producing a pill shape.
- Two actions separated by a 14 px gap.

Desktop hero CSS uses 17 px labels, approximately 20 px line height and larger padding, yielding a roughly 44 px control. Other contexts have their own sizes. The stylesheet also supplies an 8 px-radius block-button variant, so Apple does not use pills for every control.

The recurring composition is a small, clear choice set. Text links remain visibly lighter than buttons. An outline or a pill radius alone cannot fix too many competing actions.

Application translation: one filled Save action, a quieter export action, and a labeled disclosure for rare operations. Keep frequent Add experience, Accept/Reject, cancellation and protection status discoverable. Prefer 44 px interaction targets even where Apple's narrow marketing button example measures 36 px.

Source: [homepage foundation CSS](https://www.apple.com/v/homepage/a/styles/main.built.css), [composition CSS](https://www.apple.com/v/homepage/a/styles/homepage.built.css) and live button measurements.

## 6. Surfaces, cards, borders and depth

The sampled Mac benefit cards are white against a light neutral section. They have a **28 px radius**, **24 px internal text insets** and **no box shadow in their resting computed style**. Much of their separation comes from background contrast and space.

That differs from placing a visible outlined rectangle around every item. Large corners help large editorial/image cards feel approachable; small form fields need their own proportions. The site also uses flat full-width regions rather than forcing every section into a rounded card.

Application translation: choose 12–16 px workspace panels and 8–10 px controls as practical starting points. Reduce nested card outlines. Keep a clearly visible field boundary and focus state; do not sacrifice usability to make a field look borderless.

## 7. Navigation, segmented controls and disclosure

The narrow global navigation shows the brand, search, shopping bag and menu. Its measured height is 48 px. Desktop header CSS uses 44 px item heights and a maximum 1024 px navigation content container, including horizontal padding.

The Mac product filter is a single rounded track, not four independently outlined buttons:

- Track background `#E8E8ED`.
- Track padding 4 px.
- Pill radius 999 px.
- Dark selected indicator `#1D1D1F`.
- Approximately 36 px tab height in the sample, with 16 px horizontal text padding.
- A moving indicator expresses the selected category.

The Mac page also uses accordions to reveal related-device details. This keeps a large information set readable without displaying every paragraph at once.

Application translation: Content/Appearance is a coherent segmented choice. Primary navigation should be grouped around user tasks. Menus and disclosures should hold occasional configuration; warnings, save state and required consent stay visible where needed.

Source: [Mac page](https://www.apple.com/mac/) and [global header CSS](https://www.apple.com/api-www/global-elements/global-header/v1/assets/globalheader.css).

## 8. Imagery, copy and motion

Product imagery is large, carefully cropped and often isolated against a quiet background. Text generally has a dedicated space instead of being scattered over busy images. At narrow widths, galleries retain substantial product/card sizes and expose a neighboring item rather than shrinking every item into a tiny grid.

Copy is brief at the top level and becomes detailed as the visitor moves into comparison, disclosure and footnotes. Specific section headings help users predict the content below them.

Source-verified motion examples include a Mac feature-card transform transition of **0.3 seconds** with `cubic-bezier(0, 0, 0.5, 1)` and a category indicator position/width transition of **0.32 seconds ease-out**. Header CSS includes 0.24-second menu transitions. These describe selected CSS rules; this inspection is not a full animation/performance or accessibility audit.

Application translation: the resume preview can be the main visual. Avoid decorative stock imagery in the working editor. Use plain task labels and short guidance. Keep optional interaction transitions around 120–180 ms, respect reduced motion, and never delay saving/review feedback for an animation.

## 9. Concrete implications for this application

| Current problem | Apple-derived principle | Application decision |
|---|---|---|
| Buttons appear clumped together | A small action group with distinct visual roles | Explicit primary/secondary/ghost/danger variants and real layout gaps |
| Too many settings compete with editing | Content has a clear first level; detail can be disclosed | Content-first Studio, Appearance tab, advanced settings disclosures |
| Every item feels like another form | Consistent alignment and restrained surface treatment | Fewer nested outlines, clear experience grouping and contextual tools |
| Many equally prominent navigation destinations | Separate global/category/detail navigation | Task groups and a narrow-screen drawer |
| The page feels visually busy | Neutrals carry the interface; accent indicates purpose | Neutral shell, one blue family, meaningful status colors |
| App typography feels inconsistent | One coordinated family with a deliberate size/weight hierarchy | System UI stack and shared page/section/body scales |
| Preview becomes buried on small screens | Recompose the layout for the available width | Edit/Preview switching with mounted draft state |

The design target is a clear editing workspace with Apple's restraint. Marketing features such as large campaign imagery, dramatic dark sections and long scroll narratives serve a different task and should be adapted selectively.

## 10. Reusable inspection method

1. Choose a homepage, a category page and a detailed workflow page.
2. Capture the page at identified viewport sizes and wait for meaningful content to load.
3. Record computed styles for visible headings, copy, controls, surfaces and navigation.
4. Read responsive CSS before describing desktop values that were not measured live.
5. Measure gaps and insets; do not assume every site uses an 8 px grid.
6. Compare visual emphasis to the action's importance and frequency.
7. Separate observed values, interpretation and project recommendations.
8. Validate the adaptation on real populated app screens, with keyboard, long content, narrow layouts and error states.

Continue with the [clean UI process](../coding-practices/CLEAN_UI_DESIGN_PROCESS.md), [Phase 7 plan](07-ui-refinement-plan.md) and [UI implementation guidance](../developer/UI_COMPONENTS.md).
