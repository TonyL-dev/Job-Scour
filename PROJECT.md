\# AI Resume Tailoring App: Implementation Blueprint



\*\*Stack:\*\* Python backend, TypeScript/React frontend, local LLM (LM Studio)



\---



\## 0. Guiding Principles (give these to the developer first)



These four rules drive most of the decisions below. Breaking any of them causes problems later.



1\. \*\*Content and presentation are separate.\*\* A resume is two things: structured content (JSON-like data) and a template that controls layout and style. The AI only edits content and never touches formatting. That's how layout, fonts, and visual identity stay intact.

2\. \*\*Every AI-generated statement must trace back to the career database.\*\* Each bullet, summary sentence, and listed skill links to the source record IDs it came from. If something has no source, it gets flagged or rejected. This is how "never fabricate" is enforced by the system rather than just requested in a prompt.

3\. \*\*Use deterministic code first and the LLM second.\*\* Page fitting, keyword matching, ATS scoring, and validation should be regular code wherever possible. Use the LLM for understanding and rewriting text, not for counting or measuring.

4\. \*\*Local-first and private by default.\*\* The app runs on the user's machine, the LLM is local, and no data leaves the machine unless the user explicitly sets that up.



\---



\## 1. Recommended Technology Stack



\### Frontend (TypeScript / React)

| Concern | Recommendation |

|---|---|

| Build tool | Vite + React + TypeScript (strict mode) |

| Routing | React Router or TanStack Router |

| Server state | TanStack Query (caching, retries, background refetch) |

| Local UI state | Zustand (editor state, panel layout) |

| Forms \& validation | React Hook Form + Zod |

| UI components | Tailwind CSS + shadcn/ui (Radix primitives, accessible) |

| Rich text editing | TipTap, used for bullet and summary editing |

| Drag-and-drop reorder | dnd-kit, for sections, bullets and experiences |

| Diff view | A text diff library, e.g. `diff` or `react-diff-viewer-continued` |

| Resume preview | The same HTML/CSS template the backend uses for PDFs, rendered in a sandboxed iframe |

| API types | TypeScript client auto-generated from the backend's OpenAPI schema (e.g. `openapi-typescript` / `orval`) so the two sides never drift |

| Streaming | Server-Sent Events (SSE) to show AI progress live |

| Testing | Vitest + React Testing Library; Playwright for end-to-end |



\### Backend (Python)

| Concern | Recommendation |

|---|---|

| Language | Python 3.12+ |

| Web framework | FastAPI (async, auto OpenAPI docs, Pydantic integration) |

| Data validation | Pydantic v2, which also defines the JSON schemas the LLM must follow |

| ORM \& migrations | SQLAlchemy 2.0 + Alembic |

| Database | PostgreSQL for multi-user/server; SQLite for single-user desktop mode (support both through SQLAlchemy) |

| Vector search | pgvector (Postgres) or sqlite-vec (SQLite) to rank career items by relevance |

| Embeddings | Local embedding model through Ollama (e.g. `nomic-embed-text`) or sentence-transformers |

| Background jobs | ARQ or Dramatiq with Redis in server mode; a simple in-process async task queue in desktop mode |

| LLM client | OpenAI-compatible HTTP client (`httpx` or the `openai` SDK pointed at a local base URL). Ollama and LM Studio both expose OpenAI-compatible endpoints |

| Structured LLM output | JSON-schema-constrained output (Ollama's `format`, LM Studio's `response\_format`), validated with Pydantic and retried on failure. The `instructor` library helps here |

| Prompt templating | Jinja2 |

| NLP utilities | spaCy (lemmatization, noun phrases), rapidfuzz (fuzzy keyword matching), tiktoken or the model's tokenizer for token counts |

| Resume import | PyMuPDF or pdfplumber for PDF; python-docx for DOCX |

| PDF generation | Playwright (headless Chromium) printing HTML/CSS. WeasyPrint is a lighter alternative |

| DOCX export (later) | python-docx / docxtpl |

| Auth (multi-user mode) | Argon2 password hashing, httpOnly session cookies, optional TOTP |

| Encryption | `cryptography` (Fernet/AES-GCM) for field-level encryption; SQLCipher for encrypted SQLite |

| Testing | pytest, pytest-asyncio, httpx test client, factory-boy |

| Quality | Ruff (lint + format), mypy or pyright (type checking) |



\### Infrastructure

\- Docker Compose for server mode: `frontend` (Nginx serving the built React app), `backend` (FastAPI via Uvicorn), `postgres`, `redis`. Ollama or LM Studio runs on the host and is reached at `host.docker.internal`.

\- Optional future desktop packaging: Tauri or Electron wrapping the frontend, with the Python backend bundled as a sidecar (PyInstaller).



\---



\## 2. System Architecture



\### High-level components

```

\[React SPA]  ──REST + SSE──>  \[FastAPI API layer]

&#x20;                                  │

&#x20;        ┌─────────────────────────┼──────────────────────────┐

&#x20;        │                         │                          │

&#x20;\[Domain services]        \[AI Orchestration]          \[Rendering service]

&#x20;career DB, resumes,      pipelines, prompt registry,  HTML templates → PDF,

&#x20;applications, versions   model router, validators     page-count measurement

&#x20;        │                         │                          │

&#x20;   \[Database + vectors]   \[LLM Gateway] ──HTTP──> Ollama / LM Studio

&#x20;                                  │

&#x20;                           \[Job queue / workers]

```



\### Backend module layout (tell the developer to organize by domain)

\- \*\*auth\*\*: users, sessions, passcode/local mode

\- \*\*career\*\*: experiences, achievements, projects, education, skills, certifications, volunteer work, awards, publications

\- \*\*resumes\*\*: templates, master resumes, resume documents, versions, section locks

\- \*\*jobs\*\*: job descriptions, job analyses, match analyses

\- \*\*ai\*\*: LLM gateway, model router, prompt registry, pipelines, validators, truthfulness checker

\- \*\*ats\*\*: keyword engine, scoring rules, suggestion generator

\- \*\*rendering\*\*: template engine, PDF generation, page measurement, text-extraction check

\- \*\*applications\*\*: tracker, stages, follow-ups, analytics

\- \*\*importers\*\*: PDF/DOCX parsing and LLM-assisted extraction into the career database

\- \*\*settings\*\*: LLM endpoints, model profiles, task-to-model assignments, privacy settings



Each module has three layers: \*\*router\*\* (HTTP only), \*\*service\*\* (business logic), and \*\*repository\*\* (database access). Routers never call the LLM directly; they go through the ai module.



\### The core data contract: the "Resume Document"

Define one canonical, versioned schema (Pydantic on the backend, generated TypeScript types on the frontend) that represents a resume's content:

\- Header (name, contact info, links)

\- Ordered list of sections. Each section has a type (summary, experience, projects, skills, education, etc.), a title, a visibility flag, a lock flag, and items.

\- Each item has its display text plus `source\_refs`: the IDs of the career database records it came from.

\- Metadata: template ID, style overrides, target page limit (default 2), the job it was tailored for.



Templates read this document and produce HTML. The frontend preview and the PDF use \*\*exactly the same template output\*\*, so the preview always matches the download.



\### Long-running AI work

Resume generation can take 30 seconds to several minutes on local hardware. The flow:

1\. The frontend starts a "generation run" and gets back a run ID immediately.

2\. A background worker runs the pipeline stages.

3\. The frontend subscribes to an SSE stream for that run and shows stage-by-stage progress ("Analyzing job… Ranking experiences… Rewriting bullets 3/12…").

4\. Runs can be cancelled, and partial results are kept.



\---



\## 3. Database Schema Design



Describe these entities to the developer. All tables get `id` (UUID), `user\_id` (owner, for row-level isolation), `created\_at`, and `updated\_at`. Where marked, add soft delete (`deleted\_at`).



\### Users \& settings

\- \*\*users\*\*: email, password hash (multi-user mode only), display name, mode flags

\- \*\*user\_settings\*\*: default template, default page limit, privacy toggles (store prompt logs, telemetry off), locale and date format



\### Career knowledge base

\- \*\*experiences\*\*: company, job title, location, employment type, start date, end date or "current", description, industry, ordering hint, soft delete

\- \*\*achievements\*\*: belongs to an experience \*or\* a project. Text, category (responsibility / achievement / impact), metric fields (metric value, unit, metric description such as "reduced latency 40%"), "verified by user" flag, importance rating from the user. \*\*This is the most important table.\*\* Every resume bullet traces back to records here.

\- \*\*projects\*\*: name, description, role, URL, dates, challenges solved, results; optional link to an experience

\- \*\*education\*\*: institution, degree, field, dates, GPA (optional), honors

\- \*\*courses\*\*: belongs to education; name, description

\- \*\*skills\*\*: name, category (language / framework / tool / soft skill / domain), proficiency, years of use, last used date, aliases (e.g. "JS", "ECMAScript")

\- \*\*skill\_evidence\*\*: links a skill to the experiences, projects, or achievements where it was used. This lets the AI prove a skill is real and say where it came from.

\- \*\*certifications\*\*: name, issuer, issue date, expiry date, credential ID, URL

\- \*\*volunteer\_experiences\*\*: same shape as experiences, simplified

\- \*\*awards\*\*: title, issuer, date, description

\- \*\*publications\*\*: title, venue, date, URL, co-authors

\- \*\*custom\_entries\*\*: a flexible type plus JSON payload for anything that doesn't fit the categories above (speaking engagements, patents, etc.)

\- \*\*embeddings\*\*: entity type, entity ID, model name, vector, content hash (to know when to re-embed)



\### Resumes \& templates

\- \*\*templates\*\*: name, HTML/CSS template body (or reference to a built-in template), ATS-safe flag, supported section types, default styles (fonts, sizes, margins, colors)

\- \*\*master\_resumes\*\*: name, template ID, "gold standard" flag, current version ID

\- \*\*resume\_documents\*\*: title, kind (master / tailored), template ID, linked job description ID, parent document ID (what it was derived or duplicated from), current version ID

\- \*\*resume\_versions\*\*: document ID, version number, full content snapshot (the Resume Document JSON), style overrides, created by (user / AI / restore), change summary, generation run ID, page count at save time

\- \*\*section\_locks\*\*: document ID, section key or item key, locked flag. Can also live inside the content JSON; pick one place and stick to it.



\### Jobs \& analysis

\- \*\*job\_descriptions\*\*: company, title, location, URL, raw text, source, date captured

\- \*\*job\_analyses\*\*: job description ID, model used, prompt version, structured result (required skills, preferred skills, technologies, years of experience, seniority, responsibilities, company values, keywords with weights, industry terms)

\- \*\*match\_analyses\*\*: job analysis ID, resume/career snapshot reference, matched items with scores, missing keywords, strengths, suggested emphasis areas, overall match score



\### AI operations

\- \*\*llm\_endpoints\*\*: name, provider type (Ollama / LM Studio / generic OpenAI-compatible), base URL, encrypted API key if any, "is local" flag

\- \*\*model\_profiles\*\*: endpoint ID, model name, context window, temperature, top-p, max output tokens, JSON-mode support flag

\- \*\*task\_model\_assignments\*\*: task name (job analysis, ranking, rewriting, summary, verification, grammar, cover letter, etc.) mapped to a model profile ID

\- \*\*prompt\_templates\*\*: key (e.g. `rewrite\_experience\_bullets`), description, task type

\- \*\*prompt\_versions\*\*: template ID, version, system text, user text, output schema reference, active flag, author (system / user), notes

\- \*\*generation\_runs\*\*: run type, status (queued / running / succeeded / failed / cancelled), input references, models and prompt versions used, stage timings, token counts, error info

\- \*\*generation\_suggestions\*\*: run ID, target (section/item), original text, proposed text, source refs, verification status (supported / unsupported / needs review), user decision (pending / accepted / rejected / edited)



\### ATS

\- \*\*ats\_reports\*\*: resume version ID, job analysis ID, overall score, keyword match percentage, sub-scores (keywords, formatting, structure, readability, length, action verbs, quantification), individual findings with severity and suggestions

\- \*\*keyword\_aliases\*\*: canonical term and its synonyms (e.g. "Kubernetes" ↔ "K8s"). Ship a seeded global list and allow user additions.



\### Application tracker

\- \*\*applications\*\*: company, position, job description ID, resume version ID used, cover letter ID, date applied, source/channel, current stage, outcome, salary info (optional), notes

\- \*\*application\_events\*\*: application ID, event type (applied / recruiter screen / interview / offer / rejection / follow-up), date, notes

\- \*\*follow\_ups\*\*: application ID, due date, done flag, note



\### Future-feature tables

\- \*\*cover\_letters\*\*: content, job ID, version

\- \*\*interview\_prep\_sets\*\*: job ID, questions, STAR answers with source refs

\- \*\*linkedin\_drafts\*\*: headline, about, experience rewrites

\- \*\*audit\_log\*\*: user ID, action, entity, timestamp (no sensitive content)

\- \*\*files\*\*: stored uploads (original resumes) with path, MIME type, size, hash, encryption flag



\### Indexing notes

\- Index `user\_id` on every table.

\- Index applications by stage and date for the tracker.

\- Use a vector index on embeddings.

\- Store a content hash on each resume version for quick "did anything change" checks.



\---



\## 4. AI Integration Strategy



\### 4.1 LLM Gateway

A single internal service that every AI call goes through. Its responsibilities:

\- Talk to any OpenAI-compatible endpoint. Ollama and LM Studio both qualify, and native Ollama API support can be added as a fallback.

\- Look up which model profile to use for a given task (the \*\*model router\*\*).

\- Count tokens before sending and refuse or trim if the request would exceed the model's context window.

\- Ask for structured JSON output when the model supports it. Validate against the Pydantic schema. If validation fails, retry up to N times with the validation error included in the retry prompt. Then fail gracefully.

\- Support streaming for user-visible text.

\- Enforce timeouts and cancellation, and limit concurrency (local GPUs can handle only one or two concurrent requests).

\- Run a health check: list available models from the endpoint so the settings UI can show a dropdown, and test connectivity.

\- Log metadata (model, tokens, latency). Log prompts and responses only if the user opts in.



\### 4.2 Model routing (defaults the user can change)

| Task | Model size | Temperature |

|---|---|---|

| Job description analysis | Large | 0.1–0.2 |

| Relevance re-ranking | Medium/large | 0.0–0.2 |

| Bullet and summary rewriting | Large | 0.4–0.6 |

| Truthfulness verification | Large (or a different model from the writer) | 0.0 |

| Grammar / polish | Small | 0.2 |

| Formatting / length condensing | Small/medium | 0.3 |

| Resume import extraction | Large | 0.0–0.1 |



Include an onboarding "detected models" screen with recommended pairings, e.g. a 7–14B instruct model for rewriting and a 3–4B model for grammar. Make it clear that output quality depends heavily on model size.



\### 4.3 The generation pipeline (multi-stage, not one giant prompt)

Local models have small context windows and get worse with long prompts, so the work is split into focused steps:



1\. \*\*Job analysis.\*\* Send the job description to the analysis model and get back a structured JobAnalysis (skills split into required and preferred, keywords with importance weights, seniority level, years of experience, responsibilities, values). Normalize keywords against the alias table. Cache the result per job description.

2\. \*\*Candidate retrieval (deterministic plus embeddings).\*\* Embed the job's requirements. Score every career item (experiences, achievements, projects, skills) by vector similarity, keyword overlap, recency, and user-assigned importance. Keep the top K.

3\. \*\*LLM re-rank and selection.\*\* Give the model the job analysis plus short summaries of the top candidates (not the whole database). It returns a ranked selection with reasons. Then apply a \*\*budget\*\*: how many experiences and bullets fit within two pages for this template (estimated from template metrics). Locked sections are kept exactly as they are.

4\. \*\*Section-by-section rewriting.\*\* One call per section, or per experience entry. Each call receives only the relevant job keywords, the source achievements for that entry (with their IDs), the writing rules, and the target number of bullets. It returns bullets, and each bullet must list the `source\_refs` it used.

5\. \*\*Summary and skills generation.\*\* The summary is written last, from the selected content. The skills section is assembled \*\*mostly deterministically\*\*: only skills that exist in the database, ordered by relevance to the job and grouped the way the master resume groups them.

6\. \*\*Verification (truthfulness guard).\*\* Described in 4.5.

7\. \*\*Assembly and page fitting.\*\* Insert the content into the master resume's structure and template, render, and measure page count. If it's over two pages, use the fitting loop in 4.6.

8\. \*\*ATS scoring.\*\* Run the ATS engine (section 6) against the result.

9\. \*\*Present as suggestions.\*\* Every change is stored as a suggestion the user can accept or reject. Nothing silently overwrites the master resume.



\### 4.4 Prompt engineering system

\- \*\*Prompt registry.\*\* Every prompt is a versioned template stored in the database and seeded from files in the repo. Each one has a system part, a user part, variables, and a linked output schema.

\- \*\*Layered prompt structure\*\* for every call:

&#x20; 1. \*\*Non-overridable guardrail block\*\*, always added by the system: never invent employers, titles, dates, metrics, skills or certifications; only use the provided source facts; cite source IDs; don't inflate seniority or scope; if a fact isn't available, leave it out.

&#x20; 2. \*\*Task block\*\*: what to do in this specific step.

&#x20; 3. \*\*Style block\*\*, which users can customize: tone, action-verb preferences, wording rules, banned phrases ("results-driven", "team player", etc.).

&#x20; 4. \*\*Context block\*\*: the job analysis excerpt and source facts, delimited and labeled as data rather than instructions.

&#x20; 5. \*\*Output schema block\*\*.

\- \*\*Advanced users\*\* can fork any prompt, edit the task and style blocks, test it against a sample job in a "prompt playground", compare outputs side by side, and roll back. They \*\*cannot\*\* remove the guardrail block.

\- \*\*Prompt evaluation set.\*\* Keep a folder of 10–20 sample career profiles and job descriptions with expected properties: no unsupported claims, required keywords covered, page count ≤ 2. Re-run it whenever prompts or default models change. This is the regression test suite for AI quality.



\### 4.5 Truthfulness enforcement (multiple layers)

1\. \*\*Provenance required.\*\* Any generated bullet without valid `source\_refs` that point to the user's own records is rejected automatically.

2\. \*\*Fact checks in code:\*\*

&#x20;  - Every number or percentage in the output must appear in the cited source records.

&#x20;  - Every technology or skill named must exist in the user's skills table or in the cited source text (alias-aware).

&#x20;  - Company names, titles, and dates are never written by the LLM; they come straight from the database.

3\. \*\*LLM verifier pass.\*\* A separate call at temperature 0 compares each rewritten bullet with its sources and labels it \*supported\*, \*partially supported\*, or \*unsupported\*, with a reason.

4\. \*\*UI surfacing.\*\* Unsupported or partial items are highlighted in the editor with a warning and the source shown, and they're excluded by default unless the user accepts them.

5\. \*\*"Missing keyword" handling.\*\* If the job asks for something the user doesn't have, the AI \*\*never adds it\*\*. It appears in the match analysis as a gap with a suggestion such as "If you have Next.js experience, add it to your career database."



\### 4.6 Two-page fitting loop

1\. Estimate the budget before rewriting (roughly lines per page for the template, characters per line).

2\. After rendering, measure the real page count with the headless browser.

3\. If it's over the limit, apply steps in order and re-measure after each:

&#x20;  - Drop the lowest-relevance unlocked bullets.

&#x20;  - Drop the lowest-relevance older experiences or projects (or collapse them into a short "Earlier experience" line, if the template supports it).

&#x20;  - Ask the small model to condense the longest bullets ("shorten to ≤ N characters, keep metric and keywords").

&#x20;  - As a last resort, apply small layout adjustments the user allows (spacing, font-size step within template-defined limits).

4\. If it's well under the limit, optionally bring back the next-most-relevant items.

5\. Also avoid awkward results like a single orphan line on page 2. Add a check for minimum fill on the last page.



\### 4.7 Context window management

\- Store the context length on each model profile, and budget tokens for each call (system + context + expected output + safety margin).

\- Never send the full career database. Send only retrieved, relevant items, summarized if needed.

\- Long job descriptions: strip boilerplate (EEO statements, benefits) before analysis, or chunk the text and merge the results.

\- Cache job analyses and embeddings. Re-embed a career item only when its content hash changes.



\### 4.8 Partial regeneration and instructions

\- Users can select a section, an item, or several bullets and give an instruction ("make this more senior", "improve these three bullets", "shorten to fit"). This sends a focused request with only that scope and its sources, so it's fast and cheap.

\- Provide quick-action presets (Rewrite summary, Quantify, More concise, More senior, More technical, Fit to 2 pages) plus a free-text instruction box.

\- Locked items are never sent for modification; they're only included as read-only context.



\---



\## 5. User Flows



\### Flow A: Onboarding

1\. Choose a mode: Local single-user (default) or multi-user server.

2\. Connect the LLM: auto-detect Ollama (`localhost:11434`) and LM Studio (`localhost:1234`), list models, run a test prompt, and assign models to tasks using recommended defaults.

3\. Privacy screen: explain that data stays local; set an optional app passcode and optional database encryption.

4\. Build the career database: either import an existing resume or start from scratch.



\### Flow B: Import an existing resume

1\. Upload PDF or DOCX.

2\. Extract text (and layout hints).

3\. The LLM extracts structured records (experiences, achievements, skills, etc.) into a \*\*review screen\*\*. Nothing is saved until the user confirms.

4\. The user fixes or merges records, adds extra achievements and metrics, and links skills to experiences.

5\. The user picks the template closest to their current design (or customizes one): fonts, colors, section order, margins, headings. This becomes the master resume, marked as the gold standard.



\### Flow C: Grow the career database

\- Dedicated pages per category, with inline add and edit.

\- A "Strengthen my profile" helper: the AI asks follow-up questions about vague achievements ("How many users? What percentage improvement?"). The user answers, and the answers become new verified facts. \*\*The AI asks; the user supplies the facts.\*\*

\- A completeness meter, e.g. "4 of 9 achievements have measurable metrics."



\### Flow D: Tailor a resume (the main flow)

1\. Click \*\*New tailored resume\*\*.

2\. Select the master resume (defaults to the gold standard).

3\. Paste the job description and optionally enter the company, title, and URL. The app auto-detects these where it can.

4\. \*\*Job analysis screen\*\*: extracted requirements, keywords, seniority, and the match analysis (matched experiences, gaps, strengths, emphasis areas). The user can adjust keyword importance or untick keywords before generating.

5\. \*\*Generate\*\*: live progress over SSE.

6\. \*\*Review screen\*\*: split view. Left is the original or master, right is the tailored version. Changes are highlighted as diffs, each with accept, reject, or edit. A warning badge marks anything unverified. The ATS score panel sits on the side.

7\. The user locks, edits, or regenerates sections as needed; the preview updates live and shows the page count.

8\. \*\*Save version\*\* → \*\*Download PDF\*\* (with a page-count and ATS readiness check first).

9\. Prompt: "Track this application?" This creates a tracker entry already linked to the resume version and job.



\### Flow E: History and versions

\- A resume library filterable by company, title, date, and status.

\- Open any version, compare any two versions (content diff), restore an older one (this creates a new version, so history stays intact), or duplicate it as a starting point for a similar job.



\### Flow F: Application tracking

\- Kanban board (Saved → Applied → Screen → Interview → Offer / Rejected) plus a table view.

\- Each card shows company, role, resume version, dates, next follow-up, and notes.

\- Dashboard: follow-ups due, response rates by resume version, stages reached.



\---



\## 6. ATS Optimization System



Build it mostly in deterministic Python, with the LLM used only to write the explanatory suggestions.



| Check | How it works |

|---|---|

| Keyword match % | Weighted: required keywords count more than preferred ones. Matching uses normalization (lowercase, lemmatize, aliases, fuzzy match) against the resume's plain text. Report matched, missing, and partial (e.g. "React" present but "Next.js" requested). |

| Missing keywords | Each missing keyword is checked against the career database. If the user \*has\* it but it isn't on the resume, the app suggests adding it. If they don't, it's marked as a skill gap and never inserted. |

| Keyword stuffing | Count each keyword's occurrences and density per section, and flag anything over a threshold or repeated within one bullet. |

| Formatting | Template-level flags: multi-column layout, tables, images or icons, text in headers/footers, non-standard fonts. ATS-safe templates are labeled. |

| Parseability | Extract text from the \*\*generated PDF\*\* and confirm the reading order, section headings, contact info and dates come out correctly. This catches template problems. |

| Section structure | Standard headings present (Experience, Education, Skills); consistent date formats; reverse-chronological order. |

| Readability | Bullet length (aim for about 1–2 lines), sentence complexity score, passive voice detection. |

| Length | Page count ≤ limit; flag a mostly empty last page. |

| Action verbs | Check the first word of each bullet against a categorized action-verb list; flag weak openers ("Responsible for", "Helped with") and repeated verbs. |

| Quantification | Detect numbers, percentages, currency, and time savings; report the share of bullets that are quantified and point to unquantified bullets whose source has a metric available. |



\*\*Output\*\*: an overall score, sub-scores, and a prioritized list of actionable findings, each linked to the place in the editor it refers to, e.g. \*"The job requests Next.js; your database shows Next.js use at Acme Corp, but this resume only mentions React. Consider adding it to the Acme bullet about the dashboard rebuild."\*



Make sure the score is presented as guidance, not as a real ATS's verdict. Real ATS systems differ from vendor to vendor.



\---



\## 7. Feature Prioritization



\### MVP (must have)

1\. Local single-user mode with an optional passcode

2\. LLM endpoint configuration (Ollama and LM Studio), model listing, per-task model assignment, temperature setting

3\. Career database CRUD (create, edit, delete) for all core categories, with achievements as atomic records and skill evidence linking

4\. Two or three built-in ATS-safe templates with customizable fonts, colors, spacing and section order

5\. Master resume creation (manual) and gold standard flag

6\. Job description input, job analysis, and match analysis

7\. Full generation pipeline with provenance and truthfulness verification

8\. Review editor: side-by-side view, accept/reject, manual edits, section locks, partial regeneration with presets

9\. Two-page fitting loop

10\. Basic ATS report (keywords, missing keywords, action verbs, quantification, length)

11\. PDF export that matches the preview exactly

12\. Version history: list, restore, duplicate

13\. Simple application tracker (list view, stages, notes, linked resume version)

14\. Full data export (JSON) and delete-all



\### Phase 2 (high value)

\- Resume import from PDF/DOCX with a review screen

\- "Strengthen my profile" interview helper

\- Cover letter generator (same truthfulness rules)

\- Version-to-version diff view, kanban tracker, follow-up reminders

\- Prompt management UI and playground for advanced users

\- Full ATS report (stuffing, parseability check, readability, structure)

\- DOCX export

\- Custom template editor / importing a user's own HTML/CSS design



\### Phase 3 (differentiators)

\- Interview preparation: likely questions, STAR answers built from career records with citations, technical questions from the job description

\- Company research summary. This requires a web lookup, so it should be opt-in and clearly labeled as leaving the machine, or work only from text the user pastes in.

\- LinkedIn optimization (headline, about, experiences)

\- Resume analytics: most-requested skills across saved jobs, interview conversion by resume version, which experiences show up in successful applications

\- Skill gap analysis with learning paths and suggested portfolio projects

\- Browser extension to capture job descriptions from job boards

\- Multi-user server mode with full auth

\- Desktop app packaging (Tauri)



\---



\## 8. Security \& Privacy



\### Data protection

\- \*\*Local by default\*\*: the default LLM endpoint allowlist is `localhost` / `127.0.0.1` / the LAN only. Adding a remote or cloud endpoint triggers an explicit warning that resume data will be sent to that server, and that endpoint gets a visible "remote" badge.

\- \*\*Encryption at rest\*\*:

&#x20; - SQLite mode: SQLCipher, with a key derived from the user's passcode (Argon2id).

&#x20; - Postgres mode: disk/volume encryption plus field-level encryption for the most sensitive fields (contact info, raw job descriptions, uploaded files, stored API keys).

\- \*\*Uploaded files\*\* are stored outside the web root, encrypted, and served only through authenticated endpoints. Delete the original upload after import if the user chooses.

\- \*\*No telemetry\*\* by default, and no third-party scripts or CDNs in the frontend (bundle everything).

\- \*\*Logging\*\*: never log resume content, job descriptions, or prompts by default. Prompt/response logging is opt-in and auto-expires. Logs pass through a PII-redaction filter.

\- \*\*Data control\*\*: one-click full export (JSON plus PDFs), per-item delete, and "delete everything" that actually removes data, including embeddings and caches.

\- \*\*Backups\*\*: optional encrypted local backup file.



\### Application security

\- \*\*Local mode\*\*: bind the backend to `127.0.0.1` only, with an optional passcode lock screen and auto-lock after inactivity.

\- \*\*Server mode\*\*: Argon2id password hashing, httpOnly + Secure + SameSite session cookies, CSRF protection, rate limiting on login, optional TOTP 2FA, account lockout.

\- \*\*Authorization\*\*: every query is scoped to the owner's user ID in the repository layer, and tests confirm that one user can't read another's data.

\- \*\*Input validation\*\*: Pydantic on every request; size limits on uploads and job description text; file-type validation by content, not just extension.

\- \*\*PDF parsing safety\*\*: parse in a sandboxed worker with time and memory limits.

\- \*\*Template rendering safety\*\*: user-edited templates are sandboxed (Jinja2 sandbox environment, no external resource loading in headless Chromium, no JavaScript in templates). The frontend preview uses a sandboxed iframe.

\- \*\*XSS\*\*: sanitize any rich text before rendering; never render LLM output as raw HTML.

\- \*\*Prompt injection\*\*: job descriptions are untrusted input (someone could paste "ignore previous instructions…"). Delimit them clearly as data, never let LLM output trigger actions or tool calls, validate all output against schemas, and rely on the code-based fact checks rather than trusting the model.

\- \*\*Dependency hygiene\*\*: pin dependencies, run `pip-audit` and `npm audit` in CI, and use Dependabot or Renovate.

\- \*\*CORS\*\*: allow only the frontend origin.

\- \*\*Secrets\*\*: environment variables / a secret store for server secrets; stored LLM API keys are encrypted.



\---



\## 9. Development Roadmap



Give each phase to the developer with its \*\*definition of done\*\*.



\### Phase 0: Foundations (about 1 week)

\- Monorepo with `/backend` and `/frontend`, Docker Compose, Makefile or task runner, pre-commit hooks, CI (lint, type-check, tests).

\- FastAPI skeleton, settings management, database plus Alembic, health endpoint.

\- React skeleton with routing, layout shell, TanStack Query, and the generated API client pipeline.

\- \*\*Done when\*\*: `docker compose up` brings up the full stack, CI is green, and the frontend calls a typed backend endpoint.



\### Phase 1: Career database and templates (1–2 weeks)

\- All career entity models, APIs, and UI pages; achievements with metrics; skill evidence links.

\- Resume Document schema; two ATS-safe templates; rendering service; live preview; PDF export with page counting.

\- Manually built master resume with section ordering and style options.

\- \*\*Done when\*\*: a user can enter their full history, build a master resume, and download a PDF that's identical to the preview.



\### Phase 2: LLM gateway and job analysis (1–2 weeks)

\- Endpoint and model settings UI, auto-detection, connectivity test, task-to-model assignment.

\- Gateway with structured output, validation retries, token budgeting, streaming, cancellation.

\- Prompt registry seeded from files; prompt evaluation harness.

\- Job description input → job analysis → match analysis (embeddings plus keyword engine).

\- \*\*Done when\*\*: pasting a job description gives a stable, schema-valid analysis on at least two different local models, and the evaluation suite runs.



\### Phase 3: Generation pipeline and review editor (2–3 weeks)

\- Retrieval, ranking, selection with budget, section rewriting with provenance, verifier, assembly, page-fitting loop.

\- Background job runs with SSE progress.

\- Review editor: side-by-side diff, accept/reject/edit, locks, partial regeneration with presets and free-text instructions, live page count.

\- \*\*Done when\*\*: on the evaluation set, the output is ≤ 2 pages, has zero unsupported claims after verification, uses the master template unchanged, and the user can accept or reject each change.



\### Phase 4: ATS, versions, tracker (1–2 weeks)

\- ATS engine and report panel with clickable findings.

\- Versioning: auto-save versions, history, restore, duplicate.

\- Application tracker linked to resume versions.

\- Data export/delete; passcode lock; encryption at rest.

\- \*\*Done when\*\*: the MVP list in section 7 is complete and end-to-end Playwright tests cover Flows A, D, E and F.



\### Phase 5: Hardening and release (1 week)

\- Performance work (caching, concurrency limits), error states, empty states, accessibility pass (keyboard navigation, screen-reader labels, contrast).

\- Security review against section 8; dependency audit.

\- User docs: model recommendations, hardware expectations, privacy explanation.

\- \*\*Done when\*\*: a fresh install works on a clean machine following only the README.



\### Phase 6+: Phase 2 and Phase 3 features from section 7, in that order.



\---



\## 10. Technical Challenges \& Solutions



| Challenge | Solution |

|---|---|

| \*\*Preserving an uploaded resume's exact design.\*\* Arbitrary PDFs can't be reliably reproduced. | Be upfront about this in the product. Rebuild the design as an HTML/CSS template (choose the closest built-in one and customize it, or have a template editor). For DOCX uploads, a later option is to edit the user's own DOCX in place by treating it as a template with placeholders. |

| \*\*Local models produce invalid JSON\*\* | Schema-constrained decoding where available, Pydantic validation, retries that include the error message, simpler schemas for small models, and a fallback "repair" pass. |

| \*\*Hallucinated facts\*\* | Provenance requirements, code-based number and skill checks, a verifier model, UI flags, and facts like names/titles/dates inserted from the database rather than written by the AI. |

| \*\*Small context windows\*\* | Split the pipeline into stages, retrieve only relevant items, process one section per call, budget tokens, cache job analyses. |

| \*\*Slow generation on consumer hardware\*\* | Background jobs, streaming progress, per-section regeneration, caching, smaller models for minor tasks, a concurrency limit of 1–2 against the local server. |

| \*\*Inconsistent quality between models\*\* | The prompt evaluation set, a recommended models list, per-model prompt variants if needed, and an "output quality depends on the model" note in settings. |

| \*\*Accurate page counting\*\* | Measure the actual rendered PDF with the same engine used for export, not estimates. Use estimates only for the initial budget. |

| \*\*Preview and PDF don't match\*\* | One template source, rendered by one engine family (Chromium for both, via iframe and Playwright). Bundle the fonts locally. |

| \*\*Keyword matching misses\*\* ("JS" vs "JavaScript", "CI/CD" vs "continuous integration") | Alias dictionary plus lemmatization plus fuzzy matching plus embedding similarity for partial matches. |

| \*\*Keyword stuffing versus coverage\*\* | Density caps in the ATS engine, prompt rules (each keyword at most once or twice, only where the source supports it), and a stuffing finding in the report. |

| \*\*Prompt injection through job descriptions\*\* | Treat the job description as data, no tool access for the LLM, schema validation, and code-based checks that don't depend on model obedience. |

| \*\*Schema evolution of the Resume Document\*\* | Store a schema version in every snapshot and write migration functions that upgrade old snapshots when they're loaded. |

| \*\*Frontend and backend types drifting apart\*\* | Generate the TypeScript client from OpenAPI in CI and fail the build if it's out of date. |



\---



\## 11. Production Best Practices



\- \*\*Type safety end to end\*\*: strict TypeScript, Pydantic everywhere, mypy/pyright in CI, a generated API client.

\- \*\*Testing pyramid\*\*:

&#x20; - Unit tests for the ATS engine, fact checks, page-fitting logic, keyword normalization (these are deterministic and should be thoroughly tested).

&#x20; - Integration tests for APIs, with a \*\*fake LLM\*\* that returns recorded responses so tests are fast and repeatable.

&#x20; - The AI evaluation suite, run on demand and before releases against real local models.

&#x20; - Playwright end-to-end tests for the main flows.

\- \*\*Idempotent, observable jobs\*\*: every generation run records its inputs, model and prompt versions, and stage timings, so any output can be explained and reproduced.

\- \*\*Immutable versions\*\*: resume versions are never overwritten. Restoring creates a new version.

\- \*\*Feature flags\*\* for Phase 2 and 3 features.

\- \*\*Accessibility and UX\*\*: keyboard-friendly editor, clear loading/empty/error states, undo for accept/reject, autosave with a "saved" indicator.

\- \*\*Documentation\*\*: an architecture decision record (ADR) for each major choice, an API reference from OpenAPI, a prompt changelog, and a user privacy page.

\- \*\*Code conventions\*\*: one domain per module, routers kept thin, services hold the logic, no LLM calls outside the AI module, no database calls outside repositories.

\- \*\*Configuration\*\*: everything environment-specific (ports, database URL, LLM defaults) comes from settings, with good defaults for local mode.



\---



\## 12. Instructions for Handing This to a Developer



1\. Give them sections 0, 2 and 3 first and ask for a written \*\*technical design document\*\* (module list, Resume Document schema in prose, entity list) for your review \*\*before\*\* they write any code.

2\. Build strictly in the Phase 0 → 5 order. Don't let them start the AI pipeline before rendering and PDF export work. Page fitting and preview accuracy depend on it.

3\. Require the \*\*prompt evaluation set\*\* in Phase 2. It's your objective measure of whether the AI follows the "never fabricate" and "two pages" rules.

4\. At the end of each phase, check against its "done when" criteria, ideally with a demo that uses your own real career data.

5\. Make clear that these three rules are \*\*non-negotiable\*\*: AI output must cite its sources; names, titles and dates come from the database; nothing leaves the machine unless the user explicitly configures a remote endpoint.



\---





\# Developer Handoff #1 — Foundations Brief \& Design Document Request



\*\*Project:\*\* AI Resume Tailoring App

\*\*Stack (fixed, not open for debate):\*\* Python backend (FastAPI), TypeScript/React frontend, local LLM via Ollama / LM Studio

\*\*Your deliverable for this step:\*\* a written Technical Design Document. \*\*No code yet.\*\*



\## How to read this packet



This packet contains only what you need to design the foundations: the guiding principles, the system architecture, and the data model. Technology choices, AI pipeline details, ATS rules, user flows, security requirements, and the phase roadmap all exist and will be handed to you once the design document is approved. Don't start on them, and don't start on the AI pipeline at all — it comes later and depends on decisions made here.



If anything in here is ambiguous or you think it's wrong, say so in the design document rather than silently choosing a different path.



\---



\## Section 0 — Guiding Principles



These four rules drive most of the decisions below. Breaking any of them causes problems later. Every choice in your design document must be consistent with them, and I will review the document against them.



1\. \*\*Content and presentation are separate.\*\* A resume is two things: structured content (JSON-like data) and a template that controls layout and style. The AI only ever edits content; it never touches formatting. That's how layout, fonts, and visual identity stay intact.

2\. \*\*Every AI-generated statement must trace back to the career database.\*\* Each bullet, summary sentence, and listed skill links to the source record IDs it came from. If something has no source, it gets flagged or rejected. This is how "never fabricate" is enforced by the system rather than just requested in a prompt.

3\. \*\*Use deterministic code first and the LLM second.\*\* Page fitting, keyword matching, ATS scoring, and validation should be regular code wherever possible. The LLM is for understanding and rewriting text — not for counting or measuring.

4\. \*\*Local-first and private by default.\*\* The app runs on the user's machine, the LLM is local, and no data leaves the machine unless the user explicitly configures that.



\---



\## Section 2 — System Architecture



\### High-level components



```

\[React SPA]  --REST + SSE-->  \[FastAPI API layer]

&#x20;                                  |

&#x20;        +-------------------------+--------------------------+

&#x20;        |                         |                          |

&#x20;\[Domain services]        \[AI Orchestration]          \[Rendering service]

&#x20;career DB, resumes,      pipelines, prompt registry,  HTML templates -> PDF,

&#x20;applications, versions   model router, validators     page-count measurement

&#x20;        |                         |                          |

&#x20;   \[Database + vectors]   \[LLM Gateway] --HTTP--> Ollama / LM Studio

&#x20;                                  |

&#x20;                           \[Job queue / workers]

```



\### Backend module layout (organize by domain, not by layer)



\- \*\*auth\*\* — users, sessions, passcode / local mode

\- \*\*career\*\* — experiences, achievements, projects, education, skills, certifications, volunteer work, awards, publications

\- \*\*resumes\*\* — templates, master resumes, resume documents, versions, section locks

\- \*\*jobs\*\* — job descriptions, job analyses, match analyses

\- \*\*ai\*\* — LLM gateway, model router, prompt registry, pipelines, validators, truthfulness checker

\- \*\*ats\*\* — keyword engine, scoring rules, suggestion generator

\- \*\*rendering\*\* — template engine, PDF generation, page measurement, text-extraction check

\- \*\*applications\*\* — tracker, stages, follow-ups, analytics

\- \*\*importers\*\* — PDF/DOCX parsing and LLM-assisted extraction into the career database

\- \*\*settings\*\* — LLM endpoints, model profiles, task-to-model assignments, privacy settings



Each module has three layers: \*\*router\*\* (HTTP only), \*\*service\*\* (business logic), \*\*repository\*\* (database access).

Hard rules: routers never call the LLM directly — they go through the `ai` module; no database access outside repositories; no LLM calls outside `ai`.



\### The core data contract: the "Resume Document"



Define one canonical, versioned schema (Pydantic on the backend, generated TypeScript types on the frontend) representing a resume's content:



\- \*\*Header\*\* — name, contact info, links

\- \*\*Sections\*\* — an ordered list. Each section has a type (summary, experience, projects, skills, education, etc.), a title, a visibility flag, a lock flag, and items.

\- \*\*Items\*\* — each has its display text plus `source\_refs`: the IDs of the career database records it came from.

\- \*\*Metadata\*\* — template ID, style overrides, target page limit (default 2), the job it was tailored for.



Templates read this document and produce HTML. The frontend preview and the PDF must use \*\*exactly the same template output\*\*, so the preview always matches the download.



\### Long-running AI work



Resume generation can take 30 seconds to several minutes on local hardware. The flow:



1\. The frontend starts a "generation run" and immediately receives a run ID.

2\. A background worker executes the pipeline stages.

3\. The frontend subscribes to an SSE stream for that run and shows stage-by-stage progress ("Analyzing job… Ranking experiences… Rewriting bullets 3/12…").

4\. Runs can be cancelled, and partial results are kept.



\---



\## Section 3 — Database Schema Design



All tables get `id` (UUID), `user\_id` (owner, for row-level isolation), `created\_at`, and `updated\_at`. Add soft delete (`deleted\_at`) where marked.



\### Users \& settings

\- \*\*users\*\* — email, password hash (multi-user mode only), display name, mode flags

\- \*\*user\_settings\*\* — default template, default page limit, privacy toggles (store prompt logs, telemetry off), locale and date format



\### Career knowledge base

\- \*\*experiences\*\* — company, job title, location, employment type, start date, end date or "current", description, industry, ordering hint, \*soft delete\*

\- \*\*achievements\*\* — belongs to an experience \*or\* a project. Text, category (responsibility / achievement / impact), metric fields (metric value, unit, metric description such as "reduced latency 40%"), "verified by user" flag, user importance rating. \*\*This is the most important table — every resume bullet traces back to records here.\*\*

\- \*\*projects\*\* — name, description, role, URL, dates, challenges solved, results; optional link to an experience

\- \*\*education\*\* — institution, degree, field, dates, GPA (optional), honors

\- \*\*courses\*\* — belongs to education; name, description

\- \*\*skills\*\* — name, category (language / framework / tool / soft skill / domain), proficiency, years of use, last used date, aliases (e.g. "JS", "ECMAScript")

\- \*\*skill\_evidence\*\* — links a skill to the experiences, projects, or achievements where it was used. Lets the AI prove a skill is real and say where it came from.

\- \*\*certifications\*\* — name, issuer, issue date, expiry date, credential ID, URL

\- \*\*volunteer\_experiences\*\* — same shape as experiences, simplified

\- \*\*awards\*\* — title, issuer, date, description

\- \*\*publications\*\* — title, venue, date, URL, co-authors

\- \*\*custom\_entries\*\* — flexible type plus JSON payload for anything outside the categories above (speaking engagements, patents, etc.)

\- \*\*embeddings\*\* — entity type, entity ID, model name, vector, content hash (to know when to re-embed)



\### Resumes \& templates

\- \*\*templates\*\* — name, HTML/CSS template body (or reference to a built-in template), ATS-safe flag, supported section types, default styles (fonts, sizes, margins, colors)

\- \*\*master\_resumes\*\* — name, template ID, "gold standard" flag, current version ID

\- \*\*resume\_documents\*\* — title, kind (master / tailored), template ID, linked job description ID, parent document ID (what it was derived or duplicated from), current version ID

\- \*\*resume\_versions\*\* — document ID, version number, full content snapshot (the Resume Document JSON), style overrides, created by (user / AI / restore), change summary, generation run ID, page count at save time

\- \*\*section\_locks\*\* — document ID, section key or item key, locked flag. May instead live inside the content JSON — \*\*pick one place and justify it in the design document.\*\*



\### Jobs \& analysis

\- \*\*job\_descriptions\*\* — company, title, location, URL, raw text, source, date captured

\- \*\*job\_analyses\*\* — job description ID, model used, prompt version, structured result (required skills, preferred skills, technologies, years of experience, seniority, responsibilities, company values, keywords with weights, industry terms)

\- \*\*match\_analyses\*\* — job analysis ID, resume/career snapshot reference, matched items with scores, missing keywords, strengths, suggested emphasis areas, overall match score



\### AI operations

\- \*\*llm\_endpoints\*\* — name, provider type (Ollama / LM Studio / generic OpenAI-compatible), base URL, encrypted API key if any, "is local" flag

\- \*\*model\_profiles\*\* — endpoint ID, model name, context window, temperature, top-p, max output tokens, JSON-mode support flag

\- \*\*task\_model\_assignments\*\* — task name (job analysis, ranking, rewriting, summary, verification, grammar, cover letter, etc.) mapped to a model profile ID

\- \*\*prompt\_templates\*\* — key (e.g. `rewrite\_experience\_bullets`), description, task type

\- \*\*prompt\_versions\*\* — template ID, version, system text, user text, output schema reference, active flag, author (system / user), notes

\- \*\*generation\_runs\*\* — run type, status (queued / running / succeeded / failed / cancelled), input references, models and prompt versions used, stage timings, token counts, error info

\- \*\*generation\_suggestions\*\* — run ID, target (section/item), original text, proposed text, source refs, verification status (supported / unsupported / needs review), user decision (pending / accepted / rejected / edited)



\### ATS

\- \*\*ats\_reports\*\* — resume version ID, job analysis ID, overall score, keyword match percentage, sub-scores (keywords, formatting, structure, readability, length, action verbs, quantification), individual findings with severity and suggestions

\- \*\*keyword\_aliases\*\* — canonical term and its synonyms (e.g. "Kubernetes" / "K8s"). Ship a seeded global list; allow user additions.



\### Application tracker

\- \*\*applications\*\* — company, position, job description ID, resume version ID used, cover letter ID, date applied, source/channel, current stage, outcome, salary info (optional), notes

\- \*\*application\_events\*\* — application ID, event type (applied / recruiter screen / interview / offer / rejection / follow-up), date, notes

\- \*\*follow\_ups\*\* — application ID, due date, done flag, note



\### Future-feature tables (design for them now, build later)

\- \*\*cover\_letters\*\* — content, job ID, version

\- \*\*interview\_prep\_sets\*\* — job ID, questions, STAR answers with source refs

\- \*\*linkedin\_drafts\*\* — headline, about, experience rewrites

\- \*\*audit\_log\*\* — user ID, action, entity, timestamp (no sensitive content)

\- \*\*files\*\* — stored uploads (original resumes) with path, MIME type, size, hash, encryption flag



\### Indexing notes

\- Index `user\_id` on every table.

\- Index applications by stage and date for the tracker.

\- Use a vector index on embeddings.

\- Store a content hash on each resume version for quick "did anything change" checks.



\---



\## Your Deliverable: Technical Design Document



Write it in markdown, in the repository at `/docs/design/01-foundations.md`. Prose and tables only — \*\*no implementation code.\*\* Short, precise schema sketches in prose or table form are expected; working code is not. Aim for something I can read in 30–45 minutes.



\### Required contents



\*\*1. Module list\*\* — for each of the ten backend modules above:

\- Its responsibility in one or two sentences.

\- The public interface its service layer exposes (operation names and what they do, in prose — no signatures required, but be concrete).

\- Which other modules it depends on, and which it must never call.

\- A dependency diagram or table showing call direction, demonstrating there are no cycles.



\*\*2. Resume Document schema, in prose\*\*

\- Every field, its type, whether it's required, and what it means.

\- How section types are modelled, and how a new section type gets added later.

\- How `source\_refs` are represented and validated — what a valid reference is, and what happens when an item has none.

\- How locks are represented, plus your decision on the section-locks question above (separate table vs. inside the content JSON) with the reason.

\- Your schema-versioning and migration strategy: where the version number lives, and how an old snapshot is upgraded when loaded.

\- How style overrides interact with template defaults.



\*\*3. Entity list\*\*

\- Every table, its columns with types and nullability, and its primary and foreign keys.

\- Relationship cardinalities, plus how you model the achievements "belongs to an experience \*\*or\*\* a project" case and why.

\- Which tables get soft delete, and what happens to references to a soft-deleted record (especially a `source\_ref` pointing at one).

\- Indexes and uniqueness constraints.

\- How SQLite (single-user desktop) and PostgreSQL (multi-user server) are both supported from one model layer, including the vector-search difference between the two.

\- Enum values for every status/type/category field named above.



\*\*4. Key design decisions\*\* — a short ADR-style entry for each significant choice: the decision, the alternatives considered, and why you chose as you did. At minimum cover the section-locks placement, schema versioning, the achievements polymorphic link, the dual-database approach, and how preview and PDF are guaranteed to use identical template output.



\*\*5. Open questions and risks\*\* — anything you need me to decide, anything in this brief you think is wrong, anything you consider risky. Be blunt; this is the cheapest moment to raise it.



\### Explicitly out of scope for this document

Prompt text, the AI pipeline stages, ATS scoring formulas, UI screen designs, deployment details, and the build roadmap. They're already specified and will be handed over once this document is approved.



\### Acceptance criteria



I'll approve the document when:



\- \[ ] Every one of the ten modules has a responsibility, an interface, and its dependencies, with no dependency cycles.

\- \[ ] The Resume Document schema is complete enough that frontend and backend could be built against it independently without further questions.

\- \[ ] Provenance (`source\_refs`) is enforceable from the schema alone — I can see how an unsourced bullet gets caught by the system, not by a prompt.

\- \[ ] Every entity in Section 3 appears, with columns, keys, and enum values; nothing is listed as "TBD".

\- \[ ] Content and presentation are visibly separate — nothing in the content schema encodes layout or styling.

\- \[ ] Schema versioning and the migration path are specified.

\- \[ ] Both SQLite and PostgreSQL are addressed from one model layer.

\- \[ ] Design decisions are justified, not just asserted.

\- \[ ] There is no implementation code in the document.



\### Non-negotiables (enforced in review at every stage)



1\. AI output must cite its sources.

2\. Names, titles, and dates come from the database — never written by the LLM.

3\. Nothing leaves the machine unless the user explicitly configures a remote endpoint.



\*\* RULES BEFORE ENDING A SESSION \*\*
Update the following files or create them if they don't exist:
AGENTS.md

ARCHITECTURE.md

IMPLEMENTATION\_STATUS.md

DECISIONS.md

SKILLS.md

---

## Implementation session — 2026-10-06

The current user explicitly authorized Phase 0 implementation. The historical design-only handoff above was addressed by writing `docs/design/01-foundations.md` before code; this session then implemented the requested foundation.

Phase 0 now has `/backend` and `/frontend`, FastAPI settings and health endpoints, SQLAlchemy plus the initial Alembic identity migration, React routing/layout with TanStack Query, a generated typed API client with drift detection, Docker Compose for frontend/backend/PostgreSQL/Redis, a cross-platform task runner, installed pre-commit hooks, and GitHub Actions checks/audits/Compose smoke validation. Dependencies are locked; no AI endpoint is contacted by this phase.

Local lint, formatting, strict Python/TypeScript checks, 4 backend tests, 3 React tests, API drift checks, and the production build passed. Dependency audits found no known vulnerabilities. A real browser verified the running frontend's typed backend connection, navigation, route reload, and responsive layout.

The locked backend also installed and passed tests/type checks on Python 3.12.14. An isolated native PostgreSQL 18 instance verified migrations, schema drift, persistence, and API readiness; this does not claim Docker/PostgreSQL 17 image validation.

Docker is not installed on this machine. Docker startup and hosted CI are still unverified, so Phase 0's complete definition of done is not claimed. See `IMPLEMENTATION_STATUS.md` for evidence and outstanding acceptance checks, and `README.md` for startup commands. Phase 1 features have not been started.

Session-ending rule completed: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md all created or updated. Original blueprint requirements above remain unchanged; append factual session records when continuing.

## Phase 1 implementation session — 2026-10-06

The user explicitly requested Phase 1 implementation and completion of RULES BEFORE ENDING A SESSION. The original blueprint and design-only handoff above are preserved as historical requirements.

Phase 1 now implements all career record/evidence categories, owner-scoped CRUD/UI, achievement metrics and verification, skills/evidence links, Resume Document v1, two ATS-safe templates, escaped shared HTML, embedded OFL Noto fonts, Chromium PDF rendering and actual page counting, locally bundled PDF.js preview, manual master editing with section/item ordering and style controls, gold standard selection, and append-only snapshots with optimistic save conflicts. Phase 2 AI settings/gateway/jobs/embeddings, Phase 3 generation/fitting, and Phase 4 history/ATS/tracker/privacy controls are not implemented.

Native check suite passed: strict lint/format/types, 10 backend tests, 6 frontend tests, generated API drift, and production build. Both templates passed real PDF geometry/drawing-command/text parity checks. Real browser validation entered synthetic career history and linked metrics/skills/evidence, built/reordered/styled/saved a master, previewed actual PDF pages, downloaded the matching PDF, reloaded persisted data, and checked mobile layout. Final PDF.js desktop/mobile screenshots were visually inspected; runtime made no external requests. Dependency audits found no known vulnerabilities. Python 3.12 compatibility and isolated native PostgreSQL 18 migrations/domain/PDF checks passed.

Docker runtime and hosted CI remain unverified because Docker is unavailable and the repository has not been published. Local-only identity is explicit; server domain routes are disabled until authentication exists. No real career data, AI calls, telemetry, commits, remote, or publication were involved.

Session-ending requirement completed: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md were updated with implementation scope, decisions, evidence, setup, and remaining checks. See README.md for the Phase 1 workflow and renderer setup.

## Phase 2 implementation session — 2026-10-07

The user authorized implementation of section 9's Phase 2 and explicitly required RULES BEFORE ENDING A SESSION. Section 7's later enhancement phase labels do not replace the implementation roadmap. The original blueprint/design-only handoff remain preserved.

Phase 2 implementation now includes AI endpoint/model/settings screens, local detection and connection tests, task routing, consent/disable controls and environment-backed keys, the ai-only structured streaming gateway with conservative budgeting/retries/timeouts/cancellation, immutable prompt registry/seeding and evaluation harness, job entry and cached evidenced analysis, and current-career retrieval with embeddings/weighted keywords/aliases, source IDs, gaps, coverage, and emphasis. Contracts were regenerated and an explicit Alembic migration adds the new owner-scoped tables. Manual masters/locks/rendering remain Phase 1 behavior; resume generation/fitting/review remain Phase 3, and ATS/history/tracker/full privacy controls remain Phase 4.

Final ordinary check suite passed: 17 backend tests, 12 frontend tests, strict lint/format/types, regenerated API drift checks, and production build. Python 3.12 and isolated native PostgreSQL 18 checks passed. Two local chat models produced stable schema-valid/evidenced results; the ten-pair suite exposed small-model failures and Devstral's explicit-metadata omission. Prompt v1 is preserved, v2 is active, and extraction 2.1 parses only narrow, explicit posting metadata. Fresh seniority retests and final replay of all twenty real Devstral outputs pass; original failed reports remain and the replay is not called a fresh complete final-version model run.

Real browser setup and full analysis passed using Devstral plus actual Nomic vectors from an existing CPU server. It verified sourced rankings/gaps, cache reuse/reload, cancellation, desktop/mobile layout, and zero external page requests/errors. Mobile navigation wraps correctly. LM Studio's own Nomic loader still crashes locally; generic vector retrieval was verified through the temporary native embedding endpoint, without claiming the loader was repaired. Detailed configurations/failures/evidence are in IMPLEMENTATION_STATUS.md. Qwen2.5's validation model completed downloading in the daemon, was checksum verified, and remains outside product source. No real career data was used.

RULES BEFORE ENDING A SESSION completed: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md are all updated. Temporary browser, backend, frontend and model services were stopped; the isolated PostgreSQL cluster was stopped. The original blueprint is unchanged, Docker/hosted CI are still unverified, and no commits, remotes, or publication were requested. Phase 3 generation/fitting/review remains the next implementation phase.



## Phase 3 implementation session — 2026-10-07

The current user authorized section 9's Phase 3 generation pipeline/review editor and explicitly required RULES BEFORE ENDING A SESSION. The original blueprint and historical handoff above remain unchanged.

Phase 3 now implements persisted owner-scoped generation runs/suggestions; a bounded background local worker with SSE, reconnect/reload, explicit cancellation and interruption recovery; job/retrieval reuse; ranked selection with initial budgets; focused source-citing rewriting, deterministic skill assembly/order, selected-evidence summary; code claim checks plus a separate temperature-zero verifier; actual-PDF page fitting; protected-content enforcement; and `/generate` review with side-by-side changes, accept/reject/edit, source warnings, persisted decisions/locks, partial scopes/presets/instructions, live PDF page counts, and separate immutable tailored saves/downloads. ATS scoring/history/tracker/full privacy controls remain Phase 4.

Generation prompts v1 are preserved and v2 clarifies aliases/full-source verification after real-model over-rejection. Native controls and live model quality are recorded separately in IMPLEMENTATION_STATUS.md. Protected content may prevent fitting; the app reports that rather than changing locks. Sparse-final-page warnings use extracted text length and need visual review. The local worker supports one backend process; authenticated server workers remain future work.

RULES BEFORE ENDING A SESSION: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md, and PROJECT.md are updated for this session. Final validation evidence and any remaining environment/model limits are recorded in IMPLEMENTATION_STATUS.md. Docker and hosted CI require their own environments. No commit, remote, or publication was requested.

Phase 3 final refinements: factual context excludes ranking/review metadata, exact stored metrics support Quantify, signed/percentage numbers retain meaning, accepted AI proposals recheck current rules, protected visible education can support summary, hidden sources do not populate summary, and Fit saves retain a two-page target. Generation v3 preserves v1/v2 and adds an explicit structured-metric verifier example. Final evidence is recorded in IMPLEMENTATION_STATUS.md with original failures/retests distinguished.

## Codex steering during Phase 3 — 2026-10-07

The user explicitly requested Codex instead of their local LLM. Phase 3 remains the session objective and is implemented with Codex as the default setup/evaluation provider. The installed CLI's ChatGPT login supports all six text tasks through the ai-only boundary, with explicit sharing consent, isolated schema-constrained ephemeral calls, bounded process cancellation, current-source validation and immutable tailored saves. Embeddings default off, so keyword matching needs no local server. Optional previous providers remain available; existing settings are not silently migrated or consented.

Codex controls sampling/output length; this does not claim temperature-zero Codex verification or a fixed resolved model for default. Generation v3, facts.v1, claim checks 3.2 and the original blueprint remain preserved. Native Codex connection, stored-metric generation and browser setup/generation/reconnect/review/PDF/mobile/cancellation passed. Final corpus/compatibility evidence and Docker/CI limits are in IMPLEMENTATION_STATUS.md. Phase 4 ATS/history/tracker/authentication/full privacy controls remain future work. RULES BEFORE ENDING A SESSION has been completed for AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md and PROJECT.md. No commit, remote or publication was requested.

Verification guidance follow-up — 2026-10-07: the user asked how to verify Docker and hosted CI. Repository inspection confirmed no Docker command or configured Git remote. Provided concrete stack/health/schema/PDF/persistence and GitHub Actions instructions. No installation, commit, push or publication was requested/performed, and verification remains outstanding. Container Codex CLI/authentication is separate from current Compose smoke checks. All six session documents were updated; original blueprint preserved.


## Phase 4 implementation session — 2026-10-07

The user explicitly requested section 9's Phase 4 and completion of RULES BEFORE ENDING A SESSION. The original blueprint and historical design-only handoff above remain unchanged.

Phase 4 now implements deterministic ATS reports against exact saved versions and analyses, with sourced missing terms/gaps, English heuristics, actual PDF text/order/contact/facts/page checks and clickable findings; autosave/no-op deduplication and immutable history/compare/restore/duplicate with lineage; manual master/tailored editing with user-origin changes and current checks on retained AI content; application table/board, exact submitted-version PDFs, stages/events/revisions/notes/follow-ups and response-stage summaries; local passcode/cookie/inactivity/restart controls; complete JSON and JSON/all-version-PDF ZIP export; typed delete-all and epoch revocation of pending writes/SSE. Saved generation runs retain their original version through later edits and commit/download replay.

Optional complete SQLite encryption uses SQLCipher and an Argon2id-derived backend storage passphrase plus a paired salt file. Non-destructive offline conversion verifies a new encrypted copy and retains plaintext originals for user-managed handling. Optional AES-GCM descriptive-field/JSON encryption and blind skill indexes support SQLite/PostgreSQL; metadata remains queryable in field-only mode, and PostgreSQL disk/volume encryption is an operator responsibility. Keys never enter settings exports/model children. Startup fails closed on missing/wrong keys/tampering/unconverted fields. Passcode lock and storage unlock are separate documented mechanisms. No process-memory/key-recovery/server-authentication guarantee is claimed.

Validation uses disposable synthetic data. Playwright covers A/D/E/F with real Chromium/PDF.js and SQLCipher but synthetic model responses; this is not a new live-model quality evaluation. Exact final checks, compatibility/container evidence and remaining deployment limits are recorded in IMPLEMENTATION_STATUS.md. Phase 5 hardening/release remains next; importers and other enhancement-catalogue features remain future work. No personal database was migrated or sent to models.

RULES BEFORE ENDING A SESSION: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md and PROJECT.md are all updated; the original blueprint is preserved. No commit, remote or publication was requested.


Phase 4 final verification — 2026-10-07: native check passed (43 backend/17 frontend tests, strict lint/types/contracts/build); final Playwright A/D/E/F passed with actual PDF/SQLCipher and synthetic model responses; Python 3.12 focused tests and PostgreSQL 18 workflows passed; clean dependency audits passed. Docker became available and final isolated builds/health/Alembic/Linux Phase 4 tests/Nginx/PostgreSQL 17 PDF/ATS/tracker/privacy smoke passed. Hosted CI and live Codex container account authentication remain unverified. Validation services/volumes and the started native cluster were stopped/removed; unrelated stacks and the personal store were preserved. All six session files are updated, PROJECT.md's blueprint is retained, and no commit/remote/publication was requested or performed.


## Phase 5 implementation session — 2026-10-07

The user explicitly authorized section 9 Phase 5 hardening/release and completion of RULES BEFORE ENDING A SESSION. The original blueprint and historical handoff are preserved above. Phase 5 implements bounded PDF caching with privacy invalidation, bounded AI waiters/render admission, request-size limits and production security headers/CSP, unbuffered SSE proxying, retry/loading/empty states, route recovery, keyboard skip/navigation/focus, accessible PDF/board scrolling, polled-lock query clearing and improved contrast. README now describes the current MVP, supported installation commands, Codex/provider choice, hardware estimates, storage/privacy limits, error recovery, upgrades and release verification. The section 8 review is saved in docs/release/security-review.md.

Fresh-install/doctor tasks provide repeatable synthetic installation evidence using explicit source allowlists/new dependencies/storage and production browser workflows. Container, hosted CI and live account authentication remain separate evidence categories. No personal database, keys or credentials are copied to fixtures or sent to models. New prompts, server authentication, imports and later enhancement phases are outside this phase. Exact executed checks/failures/limits are appended to IMPLEMENTATION_STATUS.md. No commit, remote or publication was requested.

RULES BEFORE ENDING A SESSION: AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md and PROJECT.md are maintained for this session. Final rules were reread and owned validation cleanup was verified before conclusion.


Phase 5 final acceptance — 2026-10-07: native check passed (48 backend/20 frontend tests, strict types/lint/drift/build), final A/D/E/F passed, audits found no known vulnerabilities, isolated README-only native installation/outage/restart passed, and no-cache Linux builds plus final healthy Nginx/PostgreSQL/PDF/privacy browser workflow and 13 Linux focused tests passed. Production .mjs MIME was corrected after a real PDF.js failure; API proxy errors also receive no-store. Source-only Docker contexts exclude local data/settings/evidence. Hosted CI, physical clean-OS certification and live Codex container login remain unverified. All six session documents and the original blueprint are maintained; final rules were reread. Owned validation stores/services/volumes are removed, unrelated services/personal data preserved, and no model calls, commits, remotes or publication occurred. Exact evidence is in IMPLEMENTATION_STATUS.md.


## Roadmap clarification - 2026-10-08

Section 9 explicitly includes Phase 6+: implement the section 7 high-value enhancement catalogue before differentiators, accounting for features already delivered in Phases 0-5. This session only clarified the roadmap; no Phase 6 implementation was requested or started. Original blueprint and validation limits are preserved.

## Phase 6 acceptance checklist - 2026-10-08

This checklist turns section 9's Phase 6+ direction into ordered milestones for the remaining section 7 high-value enhancements. It supplements the original blueprint without replacing it. Originally appended as planning, this checklist was subsequently authorized for implementation by the user. The checked requirements are now accepted against the requirement-to-evidence matrix in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md#phase-6-acceptance-evidence--2026-10-08). Named environment limits are explicitly recorded there; checked boxes do not imply untested hosted CI, Word or container account compatibility.

Implement 6A through 6F in order, then complete the shared regression and release gates in 6G. Each milestone can be reviewed independently, but completing one does not establish completion of the whole phase. Section 7 differentiators remain subsequent work: interview preparation/STAR drafts, company research, LinkedIn optimization, expanded analytics, learning paths, browser capture, multi-user authentication and desktop packaging. Automated encrypted backups also remain outside this checklist.

### Scope and acceptance evidence

- [x] Record a baseline against current code and tests before implementation. Version comparison, kanban tracking, stored follow-ups and deterministic ATS reports already exist; extend or verify them instead of rebuilding them under a new phase label.
- [x] For each accepted milestone, record the requirement, fixture or workflow, observed result, command/report location and environment in IMPLEMENTATION_STATUS.md. Separate automated controls, visual inspection and fresh model evaluations.
- [x] Use disposable synthetic stores and files for acceptance. Do not open, migrate or transmit personal career data during evaluation.
- [x] Keep the existing local single-owner deployment and server guards. New endpoints enforce ownership, origin/passcode controls and workspace epochs; client-supplied IDs never choose an owner.
- [x] Keep routers limited to HTTP adaptation, services responsible for business rules and repositories responsible for database access. Only ai may invoke a model; define new domain dependencies without cycles before adding them.
- [x] Preserve historical snapshots and prompts. Use Alembic for schema changes and generated OpenAPI/types for contract changes; no hand-edited generated types.

### 6A. PDF/DOCX resume import with staged review

Done when a user can import a supported document, correct and approve extracted records, then build a sourced manual master without changing existing records silently.

- [x] Accept text-bearing PDF and DOCX only. Validate file signatures as well as extensions/MIME types; reject malformed, password-protected and unsupported files with actionable errors. Image-only PDFs explain that OCR is not supported in this milestone.
- [x] Publish and enforce numeric upload, PDF page, DOCX expanded-size/member-count, extracted-text, processing-time and pending-import limits. Reconcile upload limits with the existing 4 MiB backend/proxy write limit; streaming or multipart uploads must not bypass limits.
- [x] Parse locally without executing macros, scripts, embedded objects or archive paths. Never fetch PDF links, DOCX external relationships or remote assets. Test forged extensions, archive traversal, excessive expansion, corrupt input and timeout cleanup.
- [x] Extract text before optional model assistance. Show what text will be shared; model extraction requires explicit provider configuration/consent and uses the ai gateway's bounded structured output and cancellation controls. Local parsing remains available without AI.
- [x] Stage typed candidate career records with source excerpts and PDF page or DOCX paragraph/table locators. Employers, titles, dates, skills and metrics must be supported by the uploaded text or explicitly supplied by the user; uncertain or missing values remain visible for correction.
- [x] Review supports edit, accept and reject for individual candidates, parent-child links and duplicate suggestions. Duplicate detection proposes actions but never merges, overwrites or retires existing facts automatically.
- [x] Commit only approved, schema-valid candidates through career services, with owner-valid relationships and an atomic revision check. Commit retries are idempotent; stale reviews and lock/delete races cannot create duplicates or late records.
- [x] Discarding or cancelling an import creates no career records. Reload/restart preserves completed review state or explicitly marks interrupted parsing as failed; it never implies unfinished extraction succeeded.
- [x] Store temporary uploads outside the web root with generated identifiers and encrypted bytes at rest, independently of optional database encryption. Fail closed if required storage keys are absent. Original filenames cannot choose paths; logs/URLs omit document content.
- [x] Default to deleting original uploads after commit/discard; any retention is an explicit choice with a delete action. Retained file reads enforce owner/passcode/epoch checks. Clear temporary files after errors, cancellation and startup recovery; export/delete-all covers staged imports and retained uploads with documented export contents.
- [x] Demonstrate text PDF and DOCX imports containing experiences, achievements/metrics, projects, education and skills, plus ambiguous dates and duplicates. Approved facts appear in career records and a manual master's actual PDF; rejected candidates do not.
- [x] Explain that content import does not reproduce arbitrary uploaded design, and that confirming an extraction is not independent verification of the original claim.

### 6B. Strengthen my profile helper

Done when targeted questions help the user add confirmed evidence without the model supplying missing facts.

- [x] Let the user select an active achievement/project/experience and review the exact source context before a consented AI request. Questions seek missing scope, outcomes, tools or measurements without suggesting an invented answer.
- [x] Permit skip, unknown and qualitative answers; a metric is optional. No guessed numbers, employers, dates, certifications or skills are persisted from questions or model proposals.
- [x] Show a proposed factual edit beside the current record and the user's answer, including separate metric value/unit fields where applicable. Only explicit user confirmation writes it through career services.
- [x] Recheck owner, active ancestry, record revision and workspace epoch before saving. Concurrent edits/retirement require refreshed review; retries cannot duplicate achievements or skill-evidence links.
- [x] Confirmed answers are recorded as user-supplied evidence and user confirmation, not model verification. Existing resume versions remain immutable; refreshed retrieval uses the changed factual snapshot.
- [x] Test refusal to answer, contradictory dates/metrics, unsupported model assertions, source retirement during a request, cancellation and lock/delete. A rejected or unanswered suggestion changes no career fact.
- [x] Keep this helper distinct from later interview preparation: Phase 6 collects facts; it does not generate STAR interview answers or learning plans.

### 6C. Sourced cover letter generation and review

Done when a saved job and selected career evidence produce a reviewable, separately versioned letter whose accepted AI claims are supported.

- [x] Add a cover-letter domain with router/service/repository boundaries and documented acyclic dependencies. Add explicit model task assignments and immutable prompt versions; existing settings are not silently assigned or consented.
- [x] Select a saved job/analysis and active career evidence, optionally linked to an exact resume version. User-confirmed recipient/contact fields and stored employer/title/date facts remain separate from AI prose.
- [x] Generate bounded structured paragraphs with source references and model/prompt/input provenance through ai. Job text is untrusted data; the model has no web, shell, apps or other tools.
- [x] Check numbers, source membership, technology/skill evidence and semantic support using the established conservative verification rules. Unsupported claims remain flagged and cannot be directly accepted as supported AI text.
- [x] Show accept/reject/edit and source evidence per proposed paragraph. Manual edits retain user origin and valid references for factual career claims; salutations and non-factual transition text need no fabricated career citation.
- [x] Recheck current evidence at acceptance, including changed/retired sources and older pending runs. Never insert a job requirement or inferred company claim as career evidence.
- [x] Save accepted letters as append-only versions with optimistic concurrency, history/restore and idempotent commit. Preserve the master resume and all prior letters; rejection/cancellation saves no accepted letter.
- [x] Link an application to the exact submitted cover-letter version alongside its exact resume version. Later edits cannot alter the submitted artifact or its download.
- [x] Provide actual locally rendered PDF preview/download, selectable text and documented length controls. Export/delete-all includes letter versions, provenance and pending runs; privacy revocation cancels work and blocks late results.
- [x] Evaluate synthetic cases for fabricated metrics/skills, injection, stale evidence, absent recipient information, failure/cancellation and a successful reviewed save. Record fresh Codex evaluation separately from mocked UI fixtures; do not claim temperature-zero Codex sampling.

### 6D. Prompt management UI and playground

Done when users can safely fork, evaluate, activate and roll back task/style customizations without changing immutable guardrails or historical runs.

- [x] Display packaged prompt versions as read-only and support owner-scoped forks with immutable versions, descriptions and changelogs. Saving a draft does not activate it.
- [x] Allow only supported task/style fields and validated variables. Guardrails, source-authority rules, schema, provider isolation and verification enforcement remain system-controlled; reject attempts to override them.
- [x] Validate missing/unknown variables and prompt/schema compatibility before testing or activation. Server validation remains authoritative even if the UI is bypassed.
- [x] Default playground inputs to synthetic fixtures. Personal source selection requires explicit action and sharing consent; show the selected data and destination before running.
- [x] Compare baseline and candidate outputs side by side with schema/evidence failures, provenance, timings and available usage metadata. A plausible output alone is not a passing evaluation.
- [x] Activation requires a recorded passing applicable synthetic evaluation and an explicit user action; failures remain visible. Support rollback by selecting a preserved version, never rewriting history.
- [x] Cache fingerprints and new runs include the exact active prompt digest. In-flight runs retain their captured version; changing activation cannot reinterpret saved output or bypass current acceptance checks.
- [x] Bound playground input, concurrency, time and output; support cancellation and lock/delete revocation. Export/delete includes custom prompt versions and any intentionally retained playground artifacts; do not enable content logging by default.
- [x] Prove guardrail tampering, injection, schema mismatch and stale activation fail safely; demonstrate fork/test/activate/rollback and unchanged historical generation provenance.

### 6E. DOCX resume and cover-letter export

Done when exact saved document versions export as editable DOCX with preserved factual content and documented layout limitations.

- [x] Export a selected immutable resume or cover-letter version with its title/version identified. Historical retired-source exports use stored facts; drafts/new saves still require current valid evidence.
- [x] Use semantic paragraphs, headings, lists and links with locally available/bundled fonts. Support Classic and Modern resume content, all supported section types, Unicode, dates and metrics, plus cover letters.
- [x] Include no macros, scripts, external templates, remote images or automatically fetched relationships. Do not embed career IDs, prompt text, rejected suggestions, secrets or unrelated source records in metadata/hidden content.
- [x] Keep content generation separate from DOCX presentation. Exporting changes no snapshot, protection flag, source reference or stored PDF; repeat export of a version preserves its content.
- [x] Label DOCX layout as editable and word-processor dependent. Chromium PDF page counts do not establish DOCX pagination or exact PDF visual parity.
- [x] Verify text, sequence, headings, hyperlinks and editable structure programmatically; visually inspect representative short/long/multipage documents in named supported word processors and record versions/platforms.
- [x] Check clipping, broken characters, orphan headings and missing content at normal margins. If a target word processor is unavailable, record it as unverified rather than claiming cross-editor compatibility.
- [x] Downloads enforce privacy/ownership/epoch checks and no-store headers, use safe filenames and bounded generation, and clear temporary artifacts on failure/cancellation. Privacy documentation explains that downloaded copies remain outside delete-all.

### 6F. Custom template editor and HTML/CSS import

Done when an owner can create a bounded, safe template, preview real PDFs, version it and reuse it without altering document content or older exports.

- [x] Define a documented declarative template contract with supported placeholders, section types, local assets and numeric layout/resource bounds. HTML/CSS import accepts this safe subset; arbitrary executable templates and exact reproduction of every design are unsupported.
- [x] Provide creation from a built-in copy, editing, validation, preview, immutable save/versioning, duplication and retirement. Built-in templates remain immutable; template changes never rewrite resume content.
- [x] Treat imports as untrusted. Reject scripts, event handlers, unsafe URL schemes, remote fonts/assets, CSS imports/network URLs, file reads, template code execution and unsupported constructs before rendering. Renderer isolation also blocks outbound requests and local-file access.
- [x] Allow only explicitly uploaded/validated local assets with encrypted private storage and bounded size/count/type. Prevent active SVG/embedded content and path traversal; asset IDs and owner checks determine access.
- [x] Bind each saved resume version to an immutable template revision and asset set, including a migration strategy for existing built-in IDs. Editing/retiring a template preserves old PDF/DOCX availability and exact generation-run downloads.
- [x] Include template/asset digests in render cache keys. Privacy events invalidate cached artifacts and late insertion; cache hits never bypass source/epoch checks.
- [x] Preview and PDF export use the same actual render artifact. Show page counts, overflow and fitting limits; protected content remains unchanged even when a new layout exceeds its target.
- [x] Run deterministic extraction/order/heading/contrast/layout checks and show findings before use. Label ATS safety as heuristic; decorative/multicolumn layouts must not receive an unconditional ATS-safe guarantee.
- [x] Document which custom template features map to DOCX. Unsupported mappings require a visible disclosed fallback or refusal; never silently claim preservation of arbitrary HTML/CSS in DOCX.
- [x] Test adversarial HTML/CSS/assets, no external renderer/browser requests, malformed placeholders, source retirement, oversize renders and missing assets. Visually inspect actual PDFs and PDF.js under Vite and production Nginx for representative custom templates.
- [x] Export/delete covers custom revisions/assets and preserves reference integrity while active. Keyboard editing, readable validation errors and recovery from invalid drafts work without losing the last saved valid version.

### 6G. Existing-feature coverage and final acceptance gates

Done when all prior milestones have evidence and the expanded product retains the completed Phase 0-5 guarantees.

- [x] Verify version-to-version compare, restore/duplicate, autosave conflicts, exact generation-run downloads, application board/table, stage events and saved follow-ups still work with old and new documents.
- [x] Provide an in-app view of upcoming/overdue follow-ups with due dates, completion and navigation to the application. Define date/timezone and restart behavior. Stored reminders do not imply background delivery while the app is closed; email/SMS/push sending remains outside scope.
- [x] Verify ATS stuffing, parseability/reading order, readability, structure and page findings against exact saved versions, including custom templates. Keep scores heuristic and missing job skills separate from career facts; the existing ATS implementation is regression coverage, not a new feature claim.
- [x] Add focused tests for new business invariants, owner/source isolation, stale revisions, atomic/idempotent commits, workspace lock/delete races and file/template boundaries. Exercise both SQLite and isolated PostgreSQL migrations/workflows without personal stores.
- [x] Regenerate contracts with `python scripts/tasks.py api` after changes. Run `python scripts/tasks.py check`, `audit`, `e2e` and `fresh-install`; record actual results and failures, not expected outcomes.
- [x] Extend disposable browser workflows for import-review-master-PDF, profile confirmation, cover-letter review/application linkage, prompt rollback, DOCX download and custom-template historical export. Use actual parsing, encryption and PDFs; label synthetic model fixtures explicitly.
- [x] Run fresh synthetic live-provider evaluations for each new AI task and changed active prompt through the product path. Document corpus, configured provider/model, repetitions, acceptance rates and rejected outputs. No accepted AI career claim may lack owner-valid supporting evidence; conservative rejection is not proof of arbitrary semantic truth.
- [x] Exercise keyboard navigation, focus recovery, screen-reader labels, narrow-screen review, empty/loading/error states, cancellation, reload and backend restart for every new flow. Inspect representative exported artifacts visually.
- [x] Extend JSON/ZIP export and typed delete-all to every new entity/file/run. Confirm no secrets appear in exports and no pending operation/cache can repopulate a locked/deleted workspace; original external downloads/provider copies remain outside deletion guarantees.
- [x] Update README setup/limits/privacy/troubleshooting, release security review and all six session documents. Describe unsupported OCR, layout fidelity, reminder delivery, provider behavior and key/storage requirements plainly.
- [x] Verify changed Docker/Nginx/runtime dependencies in isolated fresh builds and real production browser workflows. Hosted CI, physical clean-OS certification and live Codex container login remain explicitly unverified until tested in those environments; native or mocked checks cannot substitute.
- [x] Final acceptance records every required box with linked evidence or an explicitly agreed scope amendment. Do not call Phase 6 complete with required boxes silently deferred. No commits, remote creation, publication or external messages are implied by checklist completion.


## Phase 6 implementation progress - 2026-10-08

Interim record: the user authorized implementation of Phase 6 and session-ending maintenance on 2026-10-08. API/UI implementations for 6A-6F existed while acceptance was still in progress and boxes remained pending. All six required session documents received progress entries. This interim state is superseded by the final acceptance/evidence below; the original blueprint and planning history remain preserved.


## Phase 6 final acceptance — 2026-10-08

The user-authorized 6A-6G checklist above is implemented and accepted. The original blueprint and earlier planning/progress entries remain preserved as history. Import review, profile fact collection, sourced cover letters, evaluated prompt preferences, DOCX exports, custom template revisions and the in-app follow-up calendar now work within the documented local scope.

| Milestone | Acceptance evidence |
|---|---|
| 6A import | Real PDF/DOCX parsing, staged review/parent graphs, atomic career commit/replay, encrypted retention, cancellation/recovery and actual master PDF. |
| 6B profile | Explicit user answers/confirmation, stale source and pending cancellation/retirement/lock/delete tests; fresh question-task evaluation. |
| 6C letters | Supported review, immutable history/restore, exact application version, PDF/DOCX, unsupported-claim rejection and fresh writing-task evaluation. |
| 6D prompts | Read-only packaged prompts, immutable preferences, synthetic baseline/candidate reports, activation/rollback/reset and digest/configuration controls. |
| 6E DOCX | Semantic structure/content tests, historical exports and visually inspected short/long Classic/Modern/letter pages in Linux LibreOffice Writer 25.2.3. Windows Word remains unverified. |
| 6F templates | Safe HTML/CSS/PNG boundaries, encrypted immutable assets, actual measured saved findings, historical PDFs and native/Nginx PDF.js views. |
| 6G release | Final 81 backend/20 frontend check, audits, A/D/E/F/6A-6F browser, fresh installation/outage/restart, Python 3.12/Linux tests and real PostgreSQL 17/Nginx workflows. |

The detailed commands, environments, initial failures, original rejected model outputs, fresh retests and report locations are in [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md#phase-6-acceptance-evidence--2026-10-08). Fresh native Codex passed 18/18 baseline/candidate task outputs across all three new tasks and three synthetic fixtures. UI/container models are explicitly synthetic. Provider-managed sampling, configured default-model resolution and conservative semantic checks retain their documented limits.

Hosted CI, physical clean-OS certification, native Microsoft Word and live Codex container login remain unverified. OCR, arbitrary design fidelity, external reminder delivery, automatic encrypted backups, multi-user authentication and section 7 differentiators remain outside this accepted phase. No required feature is silently deferred.

RULES BEFORE ENDING A SESSION was reread from the original block. AGENTS.md, ARCHITECTURE.md, IMPLEMENTATION_STATUS.md, DECISIONS.md, SKILLS.md and PROJECT.md are updated with meaningful changes/evidence/limits. Owned validation services, network and volumes were removed; unrelated services and personal data were preserved. No commits, remotes, publication or external messages were requested/performed.


Run-guidance session — 2026-10-08: Phase 0–6 remains accepted and runnable locally, while later roadmap/server capabilities and recorded environment checks remain outside completion. Added docs/run-windows.md with setup, startup, AI consent, optional storage keys, first-use, shutdown/restart and Docker differences. No app launch, personal-data migration, model call, commit, remote or publication. RULES BEFORE ENDING A SESSION reread; all six session documents updated and blueprint retained.


Native launch session — 2026-10-08: user explicitly requested getting the application running. Native installation, pre-migration backup, migrations, real PDF doctor and browser verification completed. App is running at http://127.0.0.1:5180 with backend on 8010; unrelated Docker stack on defaults is preserved. Codex is signed in, but AI remains off pending explicit sharing consent. Current restart steps are in docs/run-windows.md. RULES BEFORE ENDING A SESSION reread; all six session documents updated and blueprint retained. No commits, remotes or publication; user-requested services remain running.

## Hosting within $1/month planning — 2026-10-09

The user requested a feasible implementation plan for $0 hosting or a maximum $1/month site budget. The plan is in docs/hosting-under-one-dollar.md. It distinguishes full-feature personal access using existing hardware/private HTTPS, a separate public browser-first edition with user-owned local compute/storage, and conditional Oracle Always Free hosting. Audience/budget boundaries remain open; no route is selected or implementation/deployment authorized by this planning session. The original blueprint, completed Phase 0-6 and verification limits remain unchanged. Provider facts are dated official research, not hosted compatibility evidence. No services, personal data, models, accounts, commits, remotes or publication changed. RULES BEFORE ENDING A SESSION reread; all six ending documents updated.

## Security audit — 2026-10-09

User requested a thorough security audit, especially IP exposure/computer takeover and Codex connection, saved separately in docs/release/security-audit-2026-10-09.md. It records current loopback/unlocked/unencrypted/dev-header posture, a reproduced session-expiry revocation bug, conditional public-exposure risks, Chromium/parser containment gaps, Codex transport/credential/capability boundaries and prioritized acceptance tests. No working RCE or PC takeover was demonstrated; this is targeted source/synthetic validation, not independent penetration-test certification. check passed 81 backend/20 frontend tests/all gates; audit retest passed using trusted certifi TLS after initial temporary pip preparation failure. No remediation, personal data/settings/service/model/account/commit/remote/publication changes. Hosted proposal remains undeployed. Original RULES BEFORE ENDING A SESSION reread; all six ending files updated, original blueprint preserved.


## Node PATH troubleshooting — 2026-10-13

User reported node unrecognized in an outside terminal. Codex process resolves bundled Node v24.19.0 at C:\Users\coolg\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe; this does not establish the outside terminal PATH. Guidance uses a temporary PowerShell PATH prepend and optional user PATH configuration. Bundled pnpm currently reports 11.25.0, whereas this repository requires 11.19.0; do not assume bundled pnpm meets the prerequisite. No runtime configuration, installations, services, personal data or model calls changed. Product checks were not rerun for this guidance-only session; previous environment limits remain. All six session documents maintained; original blueprint preserved.


Node follow-up — 2026-10-13: clarified bundled app runtime versus an independently installed Windows development runtime. Prior cache PATH advice is a temporary workaround; recommend standalone Node 24.x with installer PATH setup for regular outside-terminal use. No install/PATH mutation performed. OpenAI Docs skill consulted; bundle location is established by local dependency metadata, not a public cache stability guarantee.



## Reusable coding practices - 2026-10-13

User requested thorough reusable frontend and backend coding-practice .md files for future projects. Created docs/coding-practices/FRONTEND_CODING_PRACTICES.md, BACKEND_CODING_PRACTICES.md and README.md, linked from the root README. Guides include adoption records, structure/naming, examples, implementation workflows, safeguards and review/setup checklists. Recommendations are distinct from implemented features and known audit gaps. Original blueprint and ending rules are preserved; all six session files updated. Documentation-only work; no application code, contracts, dependencies, services, personal stores, model calls, commits, remotes or publication changed.


pnpm version guidance — 2026-10-13: user reported setup rejecting pnpm 12.11.2. Source inspection confirms scripts/tasks.py enforces exactly 11.19.0 and frontend/package.json pins the same release. Advise installing pnpm@11.19.0, verifying resolution/version, then rerunning setup; do not bypass the guard or change lockfiles to accommodate an unvalidated major version. If resolution remains wrong, inspect where.exe pnpm/Get-Command pnpm -All for PATH precedence. No installation, PATH mutation, application code/dependency change, service/data access or model call performed. Product checks not rerun for guidance-only work. Original ending rules reread, all six session documents updated and blueprint preserved.


pnpm pin rationale — 2026-10-13: 11.19.0 is the locked and validated installation/build baseline. Repository evidence establishes reproducibility and exact-version enforcement, not a demonstrated incompatibility or known defect in 12.11.2. A pnpm 12 upgrade would require an intentional toolchain/lockfile review and fresh checks/build/install evidence; none was requested or performed. No runtime/dependency/PATH/service/data changes or product tests. All six session documents maintained; original blueprint and ending rules preserved.


pnpm home guidance — 2026-10-13: inspected the user-specified Local/pnpm/bin launchers read-only; pnpm.cmd targets a native executable under Local/pnpm/global/v11, with sibling pnpx/pn launchers. npm global uninstall alone may not remove this separate installation. Verified installed self-update --help and official pnpm.io/cli/self-update; recommend explicit self-update 11.19.0 outside the project then verify, rather than deleting the pnpm home/store or changing project pins. No uninstall/update/PATH mutation executed; all six ending documents updated, rules reread and blueprint preserved.


Codex PATH diagnosis — 2026-10-13: user reported codex unrecognized in outside PowerShell while using port 5173. Read-only listeners confirm this is now native Vite/python on 5173/8000, not the old Docker stack; Docker daemon is unavailable. Codex process resolves native executable C:\Users\coolg\AppData\Local\OpenAI\Codex\bin\2e5e00daee91c61d\codex.exe and login status reports ChatGPT authentication. Advise setting STONKS_CODEX_CLI to that executable in the backend terminal, checking login status via full path and restarting backend; explicit in-app remote consent still required. Versioned app path can change after updates. No installation, PATH/environment mutation, service restart, data/AI-settings change or model call performed. Product tests not rerun for guidance. All six ending documents updated and original rules/blueprint preserved.


GitHub commit guidance - 2026-10-13: read-only Git inspection confirms an initialized repository on master with no commits and no remote. Explained initial local commit, empty GitHub repository, HTTPS remote and first push, with staged-file review and existing ignore rules. No staging, commit, branch/remote mutation, account change or publication executed. Product tests not rerun for guidance-only work; earlier validation limits remain. Original ending rules reread; all six session documents updated and blueprint preserved.


Pre-publication privacy review - 2026-10-13: inspected all 239 Git-eligible source/documentation files with credential/contact/path patterns and reviewed flagged examples without reading the personal database or environment credential contents. No recognized live credential signatures or real contact/resume records were identified; this bounded review is not an exhaustive secret-scan guarantee. Six root session documents contain the Windows username/local executable paths; docs/run-windows.md includes the local project path. The security audit and session history disclose point-in-time privacy settings and unresolved vulnerabilities. Email matches are synthetic examples; Compose includes a documented local development database password. Existing .gitignore excludes the actual backend/resume-tailor.db, .env files and .validation, but does not broadly exclude arbitrary exports/backups, alternate SQLite suffixes or SQLCipher salt sidecars. Recommend private GitHub visibility and redacting machine-specific details before public release. No redaction, ignore-rule change, staging, commit, remote, publication, service/data/model change or product test performed. Original ending rules/blueprint preserved; all six session documents updated.

## Docker startup recovery — 2026-10-15

User reported `docker compose up --build --wait` failing on the backend dependency. Actual backend logs showed psycopg unable to resolve `postgres` during Alembic startup; PostgreSQL and Redis were healthy. Recreated only backend/frontend using `docker compose up -d --force-recreate --wait backend frontend`, preserving existing database/Redis volumes and unrelated stacks. All four services became healthy; frontend HTTP 200 and `/api/health` status ok/database ready were verified. Recovery establishes successful current startup, not the underlying Docker DNS failure mechanism or full product/container AI compatibility. No application/configuration/dependency change, volume deletion, manual career-data access, model call, commit or publication. Full product checks were not rerun for operational recovery. All six session documents updated; original blueprint and prior validation limits preserved; original ending rules reread.

README Docker troubleshooting — 2026-10-15: documented backend dependency failure diagnosis with Compose status/logs and the verified backend/frontend force-recreation recovery for PostgreSQL hostname resolution failure. Explicitly preserves database/Redis volumes, retains standard build/start instructions, and distinguishes other startup errors. Documentation-only follow-up; inspected README placement/commands against the preceding successful recovery. No new service/data/model changes or product tests. All six session documents maintained; original ending rules and blueprint preserved.


## Saved resume diagnosis — 2026-10-15

Read-only inspection found the running Docker frontend/backend on loopback 5173/8000 using PostgreSQL in resume-tailor_postgres_data, with zero resume documents/versions. The separate native backend/resume-tailor.db contains one master and 76 immutable saved versions; latest saved timestamp is 2026-10-14 02:49:05 UTC (October 13, 10:49 p.m. America/Toronto). Counts and timestamps only were inspected, not resume content. Native services are not listening on 5180/8010. The empty Docker workspace does not establish deletion: native and Compose stores are separate. Resume studio also opens a blank new draft by default; use Saved resumes after opening the correct installation. Autosave begins only after the first explicit save. Existing alternate-port restart instructions are in docs/run-windows.md. No services, databases, settings, model calls or dependencies changed; no migration/transfer/commit/publication performed. Product checks were not rerun for this read-only diagnosis. Original ending rules reread and blueprint preserved; all six session documents updated.


## Native saved-work restart — 2026-10-15

User authorized starting the native installation to access saved work. Created a consistent SQLite backup in ignored .validation/native-restart-20261015/resume-tailor-before-start.db before launch. Native backend/frontend now run on loopback 8010/5180 with explicit existing SQLite path and frontend proxy; Docker services/volumes remain untouched. Proxied health reports database ready, frontend HTTP 200, and GET /api/resumes returns the existing master at version 76. Opened its direct editor URL in the Codex browser panel. Services intentionally remain running; no migrations, data transfer, resume edits or model calls performed. Full product/browser/PDF checks were not rerun for startup. A combined hidden-process launch command was blocked by automatic policy review; backup and ordinary task-runner launches succeeded separately. Original ending rules were reread in this conversation; all six session documents updated and blueprint preserved.


## README saved-work restart — 2026-10-15

README now puts the existing Windows native restart sequence before Docker: explicit existing SQLite path with missing-file check, loopback 8010 backend, 5180 frontend/proxy, reuse of the existing private-upload key, and Saved resumes selection/direct-URL bookmarking. It distinguishes first-time default-port setup from routine restarts and explains separate Docker persistence, first-save/autosave behavior and backups. PowerShell blocks parsed successfully; resolved database URL matches the existing store and save labels were checked against ResumePage.tsx. Documentation only: no application/data/service/dependency/model changes, no product-suite rerun, no commit/publication. All six ending documents updated; original ending rules and blueprint preserved.


## Developer onboarding handbook — 2026-10-15

User requested thorough backend/frontend explanations for developer onboarding and reuse in future projects. Added docs/developer/README.md, BACKEND.md, FRONTEND.md and PROJECT_ARCHITECTURE_TEMPLATE.md, linked from the main README, architecture index and coding-practice index. Covers actual organization/design principles, linked source paths, full-stack workflows, persistence/concurrency, state/forms/streams, privacy, tests, deployment and extension/review recipes. Proposed layouts remain explicitly separate from implemented code. Original blueprint and roadmap remain preserved; no product implementation or additional phase is claimed. Documentation links/anchors were checked; full product tests were not rerun. No services/personal data/models/dependencies/commits/remotes/publication changed. Original ending rules reread and all six session documents updated.

## Structured master experience — 2026-10-15

User requested company/title/start/end-or-present, a one-sentence summary and duty bullets in the master resume. Resume Studio now provides structured entry and shared source-detail editing, separate summary/duty items, conservative summary validation and paragraph/bullet rendering in HTML/PDF/DOCX. Company/title/dates remain stored facts; new entry text is library description evidence, while later resume text edits remain snapshot-only. Existing items default to duty presentation without migration; generation preserves summary roles and rejects invalid proposals. Immutable snapshots, source/lock/privacy checks and the original blueprint remain preserved. README and backend/frontend onboarding plus all six session documents are maintained; exact check/browser evidence and limits are in IMPLEMENTATION_STATUS.md. No personal store edits, live model calls, service deployment, dependency changes, commits, remotes or publication were performed. The original ending rules were reread.

Structured experience final validation — 2026-10-15: check passed 86 backend/23 frontend tests, lint/strict types/generated drift/build; audits and actual SQLCipher/Chromium/PDF.js browser workflows passed. Details and corrected intermediate failures are in IMPLEMENTATION_STATUS.md. No database migration, personal data/service change, live inference, dependency change or deployment. Restart native backend/refresh frontend or rebuild Docker to load the updated contract. All six session files updated; original ending rules reread and blueprint preserved.


## Saved-work port correction — 2026-10-16

User reported missing old template on 5173. Read-only counts found native SQLite has one master/80 versions and zero custom-template records/revisions/assets; Docker has zero resumes/custom templates. A separate custom template was not recovered or claimed. Created/preserved ignored .validation/native-restart-20261016/before-start.db via SQLite backup. Stopped only Compose frontend/backend (volumes and PostgreSQL/Redis preserved), then launched native backend/frontend on loopback 8000/5173 against the explicit existing SQLite path. Proxied health reports ready, UI HTTP 200, resume API returns version 80, custom-template API returns empty. Requested opening the saved master directly. README restart commands now use 5173/8000 and explain stopping Docker app services before native startup; run-windows guidance supersedes old alternate-port history. No migration, resume edit, model call, dependency change, commit or publication. Product suite and real PDF/browser rendering were not rerun; operational HTTP checks only. All six session documents updated, original ending rules reread and blueprint preserved.


## Experience editor visibility — 2026-10-16

Inspected the actual native resume editor in the in-app browser. The structured editor is present but collapsed behind Add experience. Opened that form and verified Company, Title, Start date, End date, Present, summary and duty controls in the live accessibility tree; screenshot confirms the visible date inputs. No code, resume/library data or settings changed; master remained at version 80. Product tests not rerun for UI navigation. All six ending documents maintained; original blueprint and ending rules preserved.
