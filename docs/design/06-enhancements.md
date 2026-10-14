# Phase 6 enhancement design

The Phase 6 implementation follows PROJECT.md's ordered acceptance checklist. Its deployment remains one local owner and one backend process. Server authentication, automatic encrypted backups, OCR, arbitrary template execution, external reminder delivery and the section 7 differentiators remain outside this phase.

| Domain | Responsibility | Business dependencies |
| --- | --- | --- |
| importers | Parse bounded PDF/DOCX uploads locally, stage evidence and review, atomically commit approved new records | career services, settings configuration, ai extraction |
| profile | Ask questions against a captured active source; prepare only user-supplied answers; confirm under revision control | career services, settings configuration, ai questions |
| cover_letters | Persist generation/review state and independent immutable letter versions; export historical snapshots | career services, jobs analysis, settings configuration, ai writer/verifier, rendering |
| prompt_management | Immutable bounded preferences, synthetic comparison reports and explicit activation/reset | settings configuration, ai evaluation |
| templates | Immutable presentation revisions, safe HTML/CSS and encrypted sanitized PNG assets | database-free rendering and shared content/value schemas |
| applications | Preserve the exact submitted letter version alongside the exact resume version | cover_letters version reads, existing jobs/resumes services |

HTTP routers adapt typed requests and responses. Services hold domain rules; repositories alone execute SQL and return detached DTOs. Pure schema, prompt-digest, validation and rendering functions do not create business dependency cycles. Settings resolution reads the active owner-scoped prompt preference through its repository; digest/preference helpers are pure. Only ai calls the model gateway or launches Codex.

## Import lifecycle

The JSON upload envelope fits the existing 4 MiB ASGI/Nginx write limit: file bytes are limited to 2 MiB before base64 encoding. A separate Python worker receives bytes through stdin, with isolated Python configuration and a minimal non-secret environment; two parsers may run and each has a 15-second deadline. PDF limits are 30 pages; DOCX limits are 256 archive members and 8 MiB expansion. Extracted text is limited to 200,000 characters and 500 fragments. Pending reviews are limited to ten.

The parser never executes document macros/actions, resolves XML entities, fetches relationships or extracts archive members to disk. Signatures, paths, duplicate members, active content and declared resource bounds are checked. Image-only/password-protected documents fail with recovery guidance. These controls bound work; they do not claim an OS memory sandbox or universal parsing of arbitrary documents.

Parsing state is persisted before starting the worker. Cancellation kills its registered process and blocks late results; startup marks interrupted parsing failed. Spawn admission rechecks the workspace epoch before registering the child. Originals are memory-only by default. Explicit retention encrypts original bytes in the database outside the web root, using APP_UPLOAD_KEY or APP_ENCRYPTION_KEY; missing/wrong keys and tampering fail closed. Filenames never select storage paths. Discard clears original bytes and staged text. Retained originals have a separate owner/passcode-checked download/delete action. Complete JSON export retains encrypted originals with an explicit base64 envelope; no storage key is exported.

Optional extraction uses a closed nullable staging schema compatible with Codex strict JSON. Exact fragment excerpts and literal factual values are checked; missing fields remain visible for user correction. Reviewed parent choices map temporary candidate references to new UUIDs, or explicitly select existing active records. Commit reserves the review revision and writes the entire accepted graph in one transaction through career services. Conditional source writes hold existing parent revisions without changing timestamps. Failed relationships/validation roll back the whole graph; successful replay returns original saved IDs. Duplicate hints never merge existing records.

## Profile and letter evidence

Profile questions are bare bounded questions, with no numeric suggestions or appended annotations. The user can skip, answer unknown or supply qualitative facts. Preparing wording deterministically appends supplied answers to the selected source; it does not ask a model to fill factual gaps. Confirmation uses both review revision and current career revision, with an atomic career update and preserved confirmation history. Source changes/retirement invalidate review. Immutable resumes remain unchanged.

Letters capture an exact saved job analysis, selected owner-valid source context, optional resume version and user-confirmed contact/recipient fields. Career paragraphs require cited source records, conservative deterministic claim checks and separate semantic verification. Rejected outputs remain visible. User-edited paragraphs have user origin and retain active references; user confirmation is not independent semantic verification. AI acceptance checks exact proposals and current factual context again and holds source/ancestor revisions through commit. Master resumes and older letters are preserved.

Letter saves are append-only and revision-controlled. Application links point to exact letter versions; edits/restores never reinterpret a submitted artifact. Queued/running operations fail explicitly after restart. Cancellation kills model work through the existing gateway; privacy changes cancel work and revoke its database epoch so late responses cannot create results. Historical exports render stored wording after source retirement.

## Prompt and template versions

Custom preferences expose supported tone/focus choices, not editable guardrails or schemas. Packaged prompts and custom versions remain immutable. Synthetic evaluation compares captured baseline/candidate configurations on two differing explicit metrics and an instruction-injection case, with applicable source/schema checks. Activation needs a passing report for the exact prompt/base/task and current task/verifier configuration plus an expected-active-version check. Reset selects the packaged prompt without deleting custom versions/reports. Captured profiles carry preference digests into new run provenance and analysis cache fingerprints; activation cannot change older runs.

Phase 6 prompt v1 is preserved; v2 is active after fresh native Codex evaluation exposed ambiguous import headings and question suffixes. Original failed outputs remain validation evidence. The evaluation corpus is deliberately small and synthetic: passing it is not proof of arbitrary semantic truth or all future model configurations.

Custom templates use fixed header/sections placeholders, allowlisted inert wrapper tags and bounded CSS. Template literals cannot inject career text or executable template expressions. CSS imports, URLs, scripts, unsafe attributes, hidden/absolute positioning and unsupported selectors are refused. Saving measures an actual synthetic Chromium PDF and stores extraction, reading-order and page findings alongside contrast/heading findings; the editor shows these before use. Full document ATS inspection remains separate. Custom templates are never advertised as unconditionally ATS-safe.

Assets are non-interlaced RGB/RGBA PNGs up to 256 KiB and 1024 pixels per side, with CRC/decompressed-size/filter checks; ancillary metadata is removed and animation is refused. At most four assets are selected per template and the owner library is capped at 100. Mandatory AES-GCM encryption binds each asset to its owner and UUID. Resume Document v1 gains an optional immutable template snapshot with encrypted asset copies; existing built-in IDs continue to work. Old versions therefore retain presentation after edits/retirement. Rendering is database-free, validates the snapshot, blocks external/file requests and caches only the full rendered artifact hash behind privacy epochs.

## DOCX presentation

DOCX uses a separate bounded OOXML exporter with headings, paragraphs, real bullets, hyperlinks, Unicode, stored display facts and embedded bundled Noto fonts. IDs, source references, prompts and rejected suggestions are omitted. It changes no snapshot or protection flag. Only user-clicked hyperlinks are external relationships; no remote template/image/font is embedded.

Pagination depends on the word processor. Style-only custom templates using canonical placeholders map to the exporter; custom HTML/CSS/assets receive an explicit refusal. Actual PDF page counts never establish DOCX pagination or arbitrary design fidelity. Visual validation and the supported word-processor/environment matrix are recorded separately in IMPLEMENTATION_STATUS.md.
