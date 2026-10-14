# Foundations technical design

Date: 2026-10-06. Status: initial design recorded before Phase 0 implementation, under the user's direct instruction to implement Phase 0. The older design-only handoff in PROJECT.md remains historical context; this document does not imply separate design approval. Later-phase entities below are planned, not implemented.

## Boundaries and service interfaces

HTTP routers validate requests and delegate to services. Repositories alone execute database operations. Shared infrastructure provides configuration, sessions, and value contracts without importing domains. Services exchange validated data, not ORM objects. Authentication resolves an owner before domain operations.

| Module | Responsibility and public operations | Permitted service dependencies |
|---|---|---|
| auth | Resolve local identity; later register users, authenticate, end sessions, change passcode, and enforce inactivity lock. | None |
| settings | Read/update privacy preferences; manage endpoints and model profiles; resolve task assignments. It stores configuration, not network calls. | None |
| career | Create, update, list, and retire career records; link evidence; resolve source facts for an owner; export a career snapshot. | None |
| jobs | Store job descriptions; save/read structured analyses and match snapshots. Analysis orchestration belongs to AI. | None |
| rendering | Render a document with a supplied template; print identical HTML to PDF; measure pages; extract text for parseability checks. | None |
| resumes | Manage templates and documents; save immutable versions; restore by creating a version; duplicate; change locks; request preview/export. | career, rendering |
| ats | Normalize aliases; score supplied job requirements against supplied resume text; persist/read reports. | rendering |
| ai | Resolve models, invoke the gateway, validate provenance, manage prompts, run/cancel pipelines, publish progress, and store suggestions. | settings, career, jobs, resumes, ats |
| importers | Extract uploaded text; request structured extraction; stage review; commit only user-approved records. | ai, career |
| applications | Manage applications, events, and follow-ups; obtain chosen job and immutable resume-version references. | jobs, resumes |

This table is the dependency diagram: each arrow points from a caller to a listed dependency. Leaves are auth/settings/career/jobs/rendering; resumes and ats depend only on leaves; ai depends on leaves and resumes/ats; importers depends on ai/career; applications depends on jobs/resumes. There are no reverse arrows or cycles. Unlisted calls are prohibited. In particular, jobs/resumes/settings must never invoke ai, career must never invoke resumes, rendering must never invoke career, and ats must never invoke ai. Routers in every module must never make LLM calls. Only ai owns LLM network traffic. The blueprint names nine backend domains despite referring to ten; the tenth implemented foundational module is health, exposing liveness/readiness through its service and repository, with no domain dependencies.

## Canonical Resume Document

The following contract is designed here and implemented in Phase 1. All objects reject unknown fields. Text is plain Unicode text, never HTML; IDs are UUIDs; ordered arrays define order. Optional means nullable or omitted with the default stated below.

| Object | Fields, types, requirements, meaning |
|---|---|
| Document | schema_version: required positive integer, initially 1; header: required Header; sections: required array of Section; metadata: required Metadata. |
| Header | name: required nonempty string; email, phone, location: optional strings, default null; links: array of Link, default empty. Identity fields are copied from user-confirmed career/profile data and are excluded from AI patch contracts. |
| Link | label: required nonempty string; url: required HTTP(S) URL. |
| Section | key: required UUID stable across versions; type: required SectionType; title: required nonempty string; visible: boolean default true; locked: boolean default false; items: required ordered Item array. |
| Item | key: required UUID; text: required nonempty string; origin: required user or ai; source_refs: required SourceRef array; locked: boolean default false; facts: optional DisplayFacts, default null. |
| DisplayFacts | employer, title, institution, degree, location: optional strings default null; start_date, end_date: optional ISO dates default null; current: boolean default false. Values are populated from source records; generated patches cannot change these fields. |
| SourceRef | entity_type: required CareerEntityType; entity_id: required UUID. Duplicate references are rejected. |
| Metadata | template_id: required UUID; target_page_limit: integer 1–10 default 2; job_description_id: optional UUID default null; style_overrides: required StyleOverrides, default empty object. |
| StyleOverrides | Optional font_family: bundled font identifier; font_size_pt: decimal 9–14; line_height: decimal 1–2; margin_mm: decimal 10–30; accent_color: six-digit hex color; section_spacing_mm: decimal 0–15. Omitted fields inherit template defaults. Templates may narrow these bounds. |

SectionType is summary, experience, projects, skills, education, certifications, volunteer, awards, publications, custom. CareerEntityType is experience, achievement, project, education, course, skill, certification, volunteer_experience, award, publication, custom_entry. Each section permits its matching records; summary may cite any career type; experience/project bullets must cite achievements linked to that parent. Custom sections use the same Item contract, not arbitrary executable payloads. Adding a section type requires registry/template support, schema update, migration if existing shapes change, and regenerating API types.

SourceRef shape and a nonempty array for AI items are schema validations. Existence, ownership, compatible type/parent, and active status require repository-backed service validation: a schema alone cannot prove database existence. AI items without references fail validation before persistence. User text without references is allowed as a manual draft and marked unverified by a derived validation report, never treated as sourced AI content. References do not prove semantic truth; numerical/skill checks and later verifier stages remain necessary. Historical snapshots retain resolved display facts and reference IDs when a record is retired; new generation cannot use retired facts. Changed source text triggers revalidation rather than silently rewriting a snapshot.

Locks live only inside versioned section/item JSON, not in a section_locks table. A section lock covers all descendants; an item lock protects that item. Lock changes create a new version. AI patch validators compare locked values byte-for-byte and reject changes; schema validation alone cannot enforce temporal invariants. Keys must be unique across a document.

StyleOverrides is a presentation envelope in metadata, never an item field. Content rewriting accepts only text and references. A renderer merges allowlisted overrides over template defaults; generated text has no CSS capability. Persisted schema_version drives sequential pure migrations on read, using copies; old versions remain unchanged. Unknown future versions fail with an actionable incompatibility error. Saving an upgraded snapshot creates a new version. The renderer produces one escaped, sandboxed HTML string used for both iframe preview and Chromium PDF; bundled fonts, asset versions, print geometry, and rendering engine version are controlled. Fonts finish loading before printing; external requests and template scripts are blocked.

## Relational entity catalogue

Notation: ! is NOT NULL, ? is nullable. UUID is portable SQLAlchemy Uuid; text means Unicode Text; string is bounded Unicode; date is Date; timestamp is UTC DateTime (SQLite normalization occurs in repository conversions); decimal is Numeric; JSON is SQLAlchemy JSON. Every table has id UUID! primary key, user_id UUID! indexed, created_at timestamp!, updated_at timestamp!. Except users, user_id references users.id. users.user_id self-references users.id and equals id (explicit ownership exception, not a second identity). All owner-bound relations use composite foreign keys (user_id, related_id) to a unique (user_id, id) target, preventing cross-owner links. Global seeds are copied to each owner so no nullable-owner bypass exists. Optional foreign keys preserve owner matching when set.

| Table | Additional columns and foreign keys | Constraints / relationships |
|---|---|---|
| users | email string?, password_hash text?, display_name string!, mode string! | Unique normalized email when nonnull; mode local/server; user_id=id. One user has many owned records. |
| user_settings | default_template_id UUID? → templates; default_page_limit integer!; store_prompt_logs boolean!; telemetry_enabled boolean!; locale string!; date_format string! | Unique user_id; page limit 1–10; telemetry false and prompt logs false by default. |
| experiences | company string!, job_title string!, location string?, employment_type string!, start_date date!, end_date date?, current boolean!, description text!, industry string?, ordering_hint integer!, deleted_at timestamp? | Dates ordered; current implies no end; soft delete. One experience has many achievements/projects. |
| achievements | experience_id UUID? → experiences; project_id UUID? → projects; text text!; category string!; metric_value decimal?; metric_unit string?; metric_description text?; verified_by_user boolean!; importance integer!; deleted_at timestamp? | Exactly one parent via XOR check; importance 1–5; parent indexes. Many achievements per parent. |
| projects | experience_id UUID? → experiences; name string!, description text!, role string?, url string?, start_date date?, end_date date?, challenges_solved text!, results text!, deleted_at timestamp? | Dates ordered; optional experience; soft delete. |
| education | institution string!, degree string!, field string?, start_date date?, end_date date?, gpa decimal?, honors text?, deleted_at timestamp? | One education has many courses; dates ordered. |
| courses | education_id UUID! → education; name string!, description text!, deleted_at timestamp? | Parent index. |
| skills | name string!, normalized_name string!, category string!, proficiency string?, years_of_use decimal?, last_used_date date?, aliases JSON!, deleted_at timestamp? | Unique owner/normalized_name; years nonnegative; aliases string array. |
| skill_evidence | skill_id UUID! → skills; experience_id UUID? → experiences; project_id UUID? → projects; achievement_id UUID? → achievements | Exactly one evidence target; unique skill/target per target kind; many-to-many via explicit links. |
| certifications | name string!, issuer string!, issue_date date?, expiry_date date?, credential_id string?, url string?, deleted_at timestamp? | Expiry after issue if present. |
| volunteer_experiences | organization string!, title string!, location string?, start_date date?, end_date date?, current boolean!, description text!, deleted_at timestamp? | Current/end-date consistency. |
| awards | title string!, issuer string?, date date?, description text!, deleted_at timestamp? | Owned source. |
| publications | title string!, venue string?, date date?, url string?, co_authors JSON!, deleted_at timestamp? | Co-authors string array. |
| custom_entries | entry_type string!, payload JSON!, deleted_at timestamp? | Entry type: speaking, patent, other; payload is validated inert JSON. |
| embeddings | entity_type string!, entity_id UUID!, model_name string!, vector JSON!, content_hash string! | Unique owner/type/id/model; source relation validated through career registry; vector finite float array with model dimension. Dialect-specific vector companion index described below. |
| templates | name string!, builtin_key string?, html_body text?, css_body text?, ats_safe boolean!, supported_section_types JSON!, default_styles JSON!, asset_version string! | Exactly built-in key or HTML/CSS source; unique owner/name; arrays/styles validated. |
| master_resumes | document_id UUID! → resume_documents; name string!, template_id UUID! → templates; gold_standard boolean!, current_version_id UUID? → resume_versions | Unique document; at most one gold standard per owner via partial index. Metadata specialization for a master document; version pointer mirrors document transactionally. |
| resume_documents | title string!, kind string!, template_id UUID! → templates; job_description_id UUID? → job_descriptions; parent_document_id UUID? → resume_documents; current_version_id UUID? → resume_versions; deleted_at timestamp? | Master/tailored; parent cannot equal self; current version must belong to document. One document has many versions. |
| resume_versions | document_id UUID! → resume_documents; version_number integer!; content_snapshot JSON!; style_overrides JSON!; created_by string!; change_summary text!; generation_run_id UUID? → generation_runs; page_count integer?; content_hash string! | Unique owner/document/version; positive version/page count; immutable snapshots. Overrides mirror snapshot metadata, validated equal. Hash indexed by document. |
| section_locks | No table: section key, item key, locked flag stored in content_snapshot. | Single source of truth; intentionally replaces listed entity. |
| job_descriptions | company string?, title string?, location string?, url string?, raw_text text!, source string!, date_captured timestamp!; deleted_at timestamp? | Source pasted/imported/manual/browser; one job has many analyses. |
| job_analyses | job_description_id UUID! → job_descriptions; model_used string!; prompt_version_id UUID! → prompt_versions; structured_result JSON!; input_hash string! | Index job/input hash/model/prompt version; result contains required/preferred skills, technologies, experience years, seniority, responsibilities, values, weighted keywords, industry terms. |
| match_analyses | job_analysis_id UUID! → job_analyses; resume_version_id UUID? → resume_versions; career_snapshot JSON?; matched_items JSON!; missing_keywords JSON!; strengths JSON!; emphasis_areas JSON!; overall_match_score decimal! | Exactly resume version or career snapshot; score 0–100. |
| llm_endpoints | name string!, provider_type string!, base_url string!, encrypted_api_key text?, is_local boolean!, remote_consent_at timestamp? | Unique owner/name; locality computed/validated rather than trusting caller; remote requires recorded consent. |
| model_profiles | endpoint_id UUID! → llm_endpoints; model_name string!, context_window integer!, temperature decimal!, top_p decimal!, max_output_tokens integer!, json_mode_supported boolean! | Unique owner/endpoint/model; positive token counts; temperature 0–2, top_p >0 and ≤1. |
| task_model_assignments | task_name string!, model_profile_id UUID! → model_profiles | Unique owner/task_name. |
| prompt_templates | key string!, description text!, task_type string! | Unique owner/key; one template has many versions. |
| prompt_versions | template_id UUID! → prompt_templates; version integer!; system_text text!, user_text text!, output_schema_ref string!, active boolean!, author string!, notes text! | Unique template/version; one active per owner/template using partial index; positive version. |
| generation_runs | run_type string!, status string!, input_refs JSON!, models_used JSON!, prompt_versions_used JSON!, stage_timings JSON!, token_counts JSON!, error_info JSON? | Index owner/status/created_at; token counts nonnegative; JSON refs validated for owner. |
| generation_suggestions | run_id UUID! → generation_runs; document_id UUID! → resume_documents; section_key UUID!; item_key UUID?; original_text text!, proposed_text text!, source_refs JSON!; verification_status string!; user_decision string! | Index run/decision; same provenance requirements as AI Item. |
| ats_reports | resume_version_id UUID! → resume_versions; job_analysis_id UUID! → job_analyses; overall_score decimal!, keyword_match_percentage decimal!, sub_scores JSON!, findings JSON! | Scores 0–100; index version/analysis; findings severity info/warning/error, target keys and suggestions. |
| keyword_aliases | canonical_term string!, normalized_term string!, synonyms JSON! | Unique owner/normalized_term; seed copies per owner. |
| applications | company string!, position string!, job_description_id UUID? → job_descriptions; resume_version_id UUID? → resume_versions; cover_letter_id UUID? → cover_letters; date_applied date?, source string!, current_stage string!, outcome string?, salary_info JSON?, notes text! | Index owner/stage and owner/date_applied; many applications may use one immutable resume version. |
| application_events | application_id UUID! → applications; event_type string!, date timestamp!, notes text! | Index application/date; one application has many events. |
| follow_ups | application_id UUID! → applications; due_date timestamp!, done boolean!, note text! | Index owner/done/due_date; one application has many reminders. |
| cover_letters | job_id UUID! → job_descriptions; version integer!; content text!; source_refs JSON! | Positive version; unique owner/job/version; provenance validated. |
| interview_prep_sets | job_id UUID! → job_descriptions; questions JSON!, star_answers JSON! | Answers include source refs; versioned inert structured JSON. |
| linkedin_drafts | headline text!, about text!, experience_rewrites JSON!, source_refs JSON! | All generated statements require source refs. |
| audit_log | action string!, entity_type string!, entity_id UUID?, timestamp timestamp! | Index owner/timestamp; no content or credentials. |
| files | path text!, mime_type string!, size integer!, hash string!, encrypted boolean! | Unique owner/path; nonnegative size; private storage paths only. |

All foreign keys default RESTRICT on deletion. Full owner deletion is an explicit child-first transaction plus files/cache cleanup. Soft delete applies to career source records, resume_documents, and job_descriptions; references survive retirement for historical audit. Embeddings for retired sources are removed and new retrieval excludes retired records. Evidence targeting retired records is inactive by derivation. Users/endpoints/models/prompts referenced by historical runs cannot be hard-deleted independently; retirement can be added when those screens are implemented. UUID generation and UTC timestamp defaults are application-side for portability. Circular version-pointer foreign keys are nullable at creation and filled transactionally after inserting the first version; migrations split creation/constraint steps where required.

## Enum catalogue

| Field family | Closed values |
|---|---|
| user mode | local, server |
| employment_type | full_time, part_time, contract, internship, freelance, other |
| achievement category | responsibility, achievement, impact |
| skill category | language, framework, tool, soft_skill, domain |
| proficiency | beginner, intermediate, advanced, expert (nullable) |
| custom entry type | speaking, patent, other |
| document kind | master, tailored |
| version created_by | user, ai, restore |
| endpoint provider_type | ollama, lm_studio, openai_compatible |
| task_name / task_type | job_analysis, ranking, rewriting, summary, verification, grammar, condensing, import_extraction, cover_letter, interview_prep, linkedin |
| prompt author | system, user |
| run_type | tailoring, job_analysis, partial_regeneration, import, cover_letter, interview_prep, linkedin |
| run status | queued, running, succeeded, failed, cancelled |
| suggestion verification_status | supported, unsupported, needs_review (partially supported verifier results map to needs_review) |
| suggestion user_decision | pending, accepted, rejected, edited |
| application stage | saved, applied, screen, interview, offer, rejected, withdrawn |
| application outcome | accepted, rejected, withdrawn, no_response (nullable until final) |
| application source | direct, referral, job_board, recruiter, other |
| event_type | saved, applied, recruiter_screen, interview, offer, rejection, follow_up, withdrawal |
| analysis seniority | internship, entry, mid, senior, lead, executive, unspecified |
| ATS severity | info, warning, error |
| audit action | create, update, retire, delete, export, login, logout, restore |
| audit entity_type | All table names in the catalogue except audit_log; also session |

Status enums use portable strings plus CHECK constraints, avoiding native Postgres enums. JSON status/category fields use the same validated contracts. Date format is an allowlisted formatting pattern (ISO, US, day-first); MIME types, titles, units, venues, industries, keyword terms, model names, and error codes are free text rather than invented closed enums.

## Decisions and risks

| Decision | Alternatives and rationale |
|---|---|
| Snapshot locks | Separate lock table causes historical state ambiguity; embedded flags restore the actual lock state alongside content. |
| Sequential schema migrations | Editing old versions destroys reproducibility; upgrade copies and save a new immutable version instead. |
| Achievement parent XOR | Generic entity ID cannot enforce parent existence. Two nullable typed foreign keys plus exactly-one check support real relational integrity. Evidence uses the same pattern with three targets. |
| Portable relational base | SQLite for private desktop operation, PostgreSQL for server deployments; one SQLAlchemy model layer, explicit Alembic revisions, JSON and portable UUIDs. No runtime create_all. |
| Vector adapters | Keep portable embedding metadata; Phase 2 adds sqlite-vec virtual tables and pgvector columns/indexes through dialect-specific migrations. Vector dimension/model changes rebuild the matching adapter index. SQLAlchemy relationships never depend on those extension tables. Phase 0 installs neither extension. |
| One renderer | A separate frontend template invites drift. Backend-generated escaped HTML is the shared preview/PDF artifact, with print styles and geometry checked in Phase 1. |
| Monorepo and generated contract | A checked-in OpenAPI snapshot plus generated TypeScript lets CI detect drift without a live backend or database. |

The brief's ten-module count is inconsistent with its nine named domains; health resolves the count without inventing a product domain. Requiring provenance enforceability from a schema alone overstates what schemas can do: ownership/existence/semantic support necessarily use persisted facts and validators. Historical snapshots preserve display text, not proof that a once-cited fact remains current. Source revisions may eventually need dedicated immutable career-record history. The master metadata version pointer is redundant with resume_documents and must be checked in the same transaction; a later simplification can remove it with migration. SQLite is unencrypted in Phase 0, matching the roadmap's Phase 4 encryption milestone; no real career data is needed to exercise this scaffold. Server authentication is not implemented, so Compose exposes services only on loopback and is a local development stack. Docker, hosted CI, PostgreSQL runtime, and visual rendering checks require their respective execution environments; local checks must not be described as proof of these unavailable systems.
