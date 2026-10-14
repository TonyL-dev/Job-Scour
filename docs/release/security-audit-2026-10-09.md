# Application security audit — 2026-10-09

Repository: Stonks V2. Assessment of the accepted Phase 0–6 local application, its current native deployment, the Codex integration and the proposed sub-$1 hosting approaches. Date uses America/Toronto.

## Executive assessment

**The present loopback-only installation has a substantially smaller remote attack surface than a public website. It is not ready to expose directly to the internet or share as a multi-user server.** Knowing the owner's public IP is not enough to connect to these loopback listeners. Conversely, turning on port forwarding, binding to all interfaces, or placing an unauthenticated public tunnel in front of the application could make private data accessible with little effort. No operating-system exploit would be needed to use an exposed, unlocked API.

**I did not find or demonstrate a working remote-code-execution exploit or a way to take over the computer through a public IP. This is not proof that none exists.** One privacy revocation bug was reproduced: automatic session expiration does not invalidate existing database sessions or existing generation event streams. Several important hardening gaps were also found, particularly the unsandboxed Chromium renderer and parser subprocess privileges.

**The Codex adapter makes several sound defensive choices. Its normal remote connection uses the CLI's authenticated HTTPS/secure-WebSocket transport, rather than an inbound connection to the owner's computer.** It disables model tools, removes application secrets from the child environment, ignores user configuration/rules and validates structured output. However, the native CLI still runs under the backend's OS account and needs its own authentication credentials. Read-only mode is not an assurance that the whole CLI cannot read local files; retrospective event rejection cannot undo a tool action if one ever happens. Transport encryption also does not mean that OpenAI cannot process the supplied career facts.

Recommended posture: retain loopback-only access; enable a strong passcode and deliberately configure storage encryption; fix session-expiration revocation; harden document/render processing; then validate an owner-only private HTTPS deployment. Do not publish this local API as a public SaaS backend.

## Method, scope and limitations

Performed:

- Reviewed the repository's project/status/architecture/decisions, previous release review and hosting proposal. Inspected HTTP middleware, fixed-owner authentication, privacy sessions/epochs, repositories, encryption, imports, custom templates/assets, rendering/export, frontend, Compose, Dockerfiles, task runner and CI, with deeper attention to security boundaries.
- Read local listener metadata for the four application-related ports and Windows firewall profile enablement. Made a read-only request to native `/api/privacy/status` and a HEAD request to the development UI; no career records were retrieved.
- Ran disposable synthetic probes using a fresh migrated SQLite database and TestClient. Demonstrated expiry behavior, host/origin checks, default unlocked access, cookie behavior at the ASGI boundary and endpoint schema acceptance. No hostile network destinations were contacted.
- Ran `python scripts/tasks.py check` and `python scripts/tasks.py audit`. Existing tests use synthetic fixtures; no inference was requested by this audit.
- Checked official OpenAI, Playwright and Tailscale documentation for transport, authentication, sandbox and network claims.

Not performed: independent third-party penetration testing; remote public-IP scanning; router/NAT/UPnP/tunnel inventory; exhaustive firewall rule review; packet interception or TLS certificate validation of a live Codex inference; credential contents/account privacy settings inspection; memory-corruption exploit development; destructive or load testing; broad fuzzing; OS/container vulnerability scans; new hosted/Docker/ARM tests; full browser e2e/fresh-install reruns. No security plugin was installed or used. This report is a targeted source audit with limited reproducible dynamic checks, not a certification or a vendor security-scan result.

Application code, configuration, running services and personal data were not changed. Build/check commands refreshed normal generated build outputs. Only audit evidence/documentation was added. No commits, remotes, account creation, publication or model calls occurred.

Evidence: ignored `.validation/security-audit-20261009.py` and `.validation/security-audit-20261009.json`. The script preserves SHA-256 hashes of eight key reviewed source/config files. There are no commits yet, so these hashes identify that part of the reviewed state. The temporary database/canary directory was removed automatically. Historical Phase 6 evidence remains separate from new checks.

## Current deployment observations

| Observed item | Result | Meaning / limitation |
|---|---|---|
| Native backend 8010 and frontend 5180 | Listening on `127.0.0.1` | Direct remote clients cannot address these sockets through the machine's LAN/public IP. A local reverse proxy/tunnel could still provide a path; those were not exhaustively inventoried. |
| Existing Docker-facing ports 8000/5173 | Listening on `127.0.0.1` | Same direct reachability conclusion; unrelated stack was preserved. |
| Windows firewall Domain/Private/Public profiles | Enabled; default inbound setting reported `NotConfigured` | Enablement alone does not prove effective deny rules, correct edge/router configuration or absence of other services. |
| Native privacy status | `passcode_enabled=false`, `locked=false` | No application session secret is required by the currently running workspace. |
| Native field/database encryption status | Both false | Current product status does not claim field or full-file encryption. This is not a finding that Windows disk encryption is absent; disk encryption was not checked. |
| Native private-file encryption | Not established by status response | Prior startup notes record a private-file key, but this audit did not read the key or retained files. A private-file key alone does not encrypt career/extracted text. |
| HEAD `http://127.0.0.1:5180/` | 200; no CSP, nosniff or X-Frame-Options | Current development server differs from hardened production Nginx/preview configuration. |

These are point-in-time observations, not claims that settings can never change.

## What an IP address does and does not allow

An IP address is a network address, not a password or a grant of computer control. Public addresses can be discovered through ordinary network activity and automated scanning. Hiding an IP is not an adequate defense.

An attack needs a reachable service and a way to misuse it: missing authentication, stolen credentials, application vulnerabilities, a malicious file that the owner processes, or an OS/library flaw. There are different outcomes:

1. **Reading/changing application data:** possible through an exposed unlocked API without breaking into Windows.
2. **Consuming AI usage or freezing the app:** possible through authorized or inadequately protected expensive endpoints, without OS control.
3. **Executing code as the backend account:** would need a code-execution flaw, malicious trusted executable/dependency, or another local compromise. Same-account document processing increases the consequence of such a flaw.
4. **Administrator control:** is a further privilege boundary; code execution as a normal account does not automatically confer admin rights, but can still expose that user's accessible documents and credentials.

| Deployment | Practical assessment |
|---|---|
| Current loopback-only installation | Low direct internet reachability through these observed ports. Remaining concerns include local malware, other processes/users, browser attacks and files voluntarily imported. No numerical hacking probability can be honestly assigned. |
| Binding the backend to LAN/all interfaces | Other reachable clients may access it. Host headers can be supplied by non-browser clients; `TrustedHostMiddleware` is not remote authentication. Current startup settings do not forbid a broad bind in local mode. |
| Router port forwarding / public tunnel without access gate | Unsafe for this release. Making the unlocked API reachable makes data access straightforward; TLS would only encrypt the attacker's connection. |
| Owner-only private Tailscale Serve HTTPS | A sound candidate after hardening and real validation. WireGuard plus HTTPS protects transit; identity/device restrictions determine access. A compromised permitted device/account can still attack the app. Broad tailnet membership is not an owner-only policy. |
| Cloudflare public tunnel with Access | Conditional alternative requiring authenticated Access on every application/API path, no origin bypass, correct proxy trust and tests. A tunnel by itself supplies reachability, not authorization. Cloudflare-mediated HTTPS is not the same privacy boundary as peer-to-peer WireGuard. Not deployed or validated here. |
| Full backend on a cloud VM | A separate host may reduce exposure of the personal PC, but reachable API/storage/AI credentials on that VM still need real authentication and isolation. Cloud storage, free capacity and TLS do not supply those controls automatically. |
| Public static/browser-first edition | No owner PC needs to accept inbound app traffic if no companion is enabled. Risks move to XSS, malicious updates, browser storage, backup and companion pairing. This remains a proposal, not audited implemented functionality. |

Tailscale describes its connections as end-to-end WireGuard encrypted and its coordination/relay visibility as metadata/encrypted traffic. That protects transport, not compromised endpoints or excessive access grants. [Tailscale security](https://tailscale.com/security). Serve exposes services within the private network and honors network access rules; public Funnel is a different feature and should remain disabled for the personal route. [Serve documentation](https://tailscale.com/docs/features/tailscale-serve).

## Findings and priorities

Severity is contextual priority, not a CVSS score or a claim of an available exploit. “Confirmed” denotes observed behavior; “conditional” requires the stated deployment/attacker prerequisites; “hardening” denotes an absent defense without a demonstrated exploit. No finding below has been remediated in this audit.

| ID | Priority | Classification | Finding |
|---|---|---|---|
| SA-01 | High before network/public exposure | Confirmed design; conditional attack | Fixed local owner and optional passcode cannot safely authenticate public/multi-user access. |
| SA-02 | High hardening priority | Confirmed configuration; exploit unproven | Chromium sandbox is not enabled; rendering runs with backend-account privileges. |
| SA-03 | Medium; potentially high exploit impact | Confirmed missing isolation; exploit unproven | Parser subprocess has no OS filesystem/network/memory boundary. |
| SA-04 | Medium | Reproduced privacy bug | Session expiry fails to revoke existing streams/database sessions. |
| SA-05 | Medium for sensitive local data | Observed configuration | Current workspace is unlocked and lacks configured field/full-database encryption. |
| SA-06 | Medium before remote use | Observed development configuration | Running UI lacks production browser security headers; dev server should not be published. |
| SA-07 | Medium before HTTPS proxy deployment | Reproduced ASGI behavior; deployment-dependent | Secure-cookie behavior depends on trusted scheme forwarding that is not defined by the current deployment. |
| SA-08 | Medium before untrusted users | Schema-confirmed; network exploit untested | Configurable HTTP providers lack a server-grade destination/SSRF policy. |
| SA-09 | Medium operational risk | Source-confirmed trust boundary | Codex isolation depends on the trusted native CLI/account; result-event rejection is retrospective. |
| SA-10 | Medium before network exposure | Source-confirmed capacity limits | Resource limits do not cover every denial-of-service path or fair per-user admission. |

### SA-01 — Current identity model must not be exposed publicly

Evidence: `backend/app/auth/service.py:local_owner`, `backend/app/privacy/service.py:45`, `backend/app/main.py:138`, `backend/app/core/config.py`, `compose.yaml`.

`local_owner` always resolves the application's fixed owner in local mode. `LockState.unlocked` returns true when there is no passcode. In a new synthetic store, unauthenticated export returned 200. With no Origin header, creating a disabled synthetic endpoint returned 201. The real native status also reports no passcode. Unexpected browser write Origins were rejected with 403; an evil Host returned 400. Those are useful controls, but CORS, Host and Origin headers do not authenticate a non-browser network client. Requests without Origin are intentionally accepted. No missing-Origin browser exploit was demonstrated.

Server-mode guards are a positive control; removing them is not an acceptable shortcut. Local mode does not enforce a loopback-only configured bind at startup. An external proxy can also make a loopback socket reachable while satisfying its Host restrictions. Stock Compose uses known local database credentials; they must not be reused for a cloud deployment.

Impact if misexposed: reading/exporting the owner workspace, modifying records/settings, data deletion or initiating consented model workflows. Initial passcode configuration on an unlocked exposed store could also let another caller set a passcode. This is application compromise, not demonstrated OS takeover.

Remediation: fail closed on unsafe local binds; introduce a dedicated private-access profile with an independently authenticated owner-only gateway and no bypass path; require strong passcode for remote access. For public access implement server sessions, CSRF protection, per-owner authorization and isolated files/caches/runs/epochs. Keep local development credentials local.

Acceptance: unauthenticated/incorrect-owner access cannot reach protected APIs through any proxy route; missing/forged identity headers fail; direct origin cannot bypass the gate; invalid local broad binds fail startup; public mode cannot resolve everyone to LOCAL_OWNER.

### SA-02 — Renderer omits Chromium sandboxing

Evidence: `backend/app/rendering/service.py:248` calls `playwright.chromium.launch()` without `chromium_sandbox=True`. Playwright documents the default as false. [Playwright BrowserType](https://playwright.dev/python/docs/api/class-browsertype).

The implementation does disable page JavaScript, sets offline mode, aborts routed requests, applies a restrictive document CSP, escapes content, validates custom templates/CSS and bounds sanitized PNGs. These materially reduce reachable behavior. They do not replace the OS sandbox that contains a compromised Chromium process. Launch also does not supply a minimal environment, so renderer children inherit the backend environment by default; secret stripping is present for Codex/parser, not this renderer.

A memory-safety flaw in rendering/layout/image/font handling would be more consequential when the browser runs without that containment. No malicious template/PNG was shown to execute code, and the audit did not demonstrate a Chromium vulnerability. On native Windows a compromise could operate with the backend account's accessible resources. Docker's non-root app user reduces impact within a container, but container defaults are not a substitute for a deliberately constrained render worker.

Remediation: enable and verify supported Chromium sandboxing, fail closed if unavailable for the selected profile, and consider a separate low-privilege renderer service with read-only filesystem, minimal environment, no network and CPU/memory/process limits. Do not silently fix launch failures with `--no-sandbox`.

Acceptance: actual launch/security checks on Windows/Linux confirm the intended sandbox; real PDF.js/PDF/template/font/PNG workflows still pass; a synthetic worker cannot read unrelated canary files or obtain backend keys. Test the deployed mechanism, not only expected launch arguments.

### SA-03 — Parser process isolation is incomplete

Evidence: `backend/app/importers/service.py:87`, `backend/app/importers/parser.py`.

Positive controls include Python `-I`, a minimal environment, two parser admissions, 15-second timeout, 2 MiB input, PDF page/action constraints, DOCX member/expansion limits, XML entity rejection, no archive extraction and generic errors. Retained originals are opt-in encrypted. Those are good defenses.

But `-I` is Python import/environment isolation, not an OS sandbox. There is no separate restricted OS account, filesystem allowlist, network deny rule or worker memory limit here. The same isolated-mode mechanism read a synthetic canary outside its working directory in the audit probe. That proves the mechanism lacks filesystem containment; it is not an exploit of the actual parser. Similarly, “the parser contains no network calls” is different from “the OS forbids the parser from networking.”

PDF decompression/extraction can allocate resources before page/text limits are checked. `communicate()` collects output before its length check, so that check is not a peak-memory ceiling. Native-library or future parser bugs could have backend-account impact. Python/pypdf behavior in this corpus did not demonstrate code execution.

Remediation: move parsing to a restricted worker with no secrets, no unrelated file access, blocked egress, OS memory/CPU/process limits and bounded streamed output. Consider Windows job objects/AppContainer or a proven equivalent and Linux container/cgroup/seccomp isolation. Continue all current content checks.

Acceptance: synthetic denied-file/denied-network/resource exhaustion tests demonstrate containment; actual PDF/DOCX import, cancellation and epoch revocation still pass on named supported platforms. Do not use harmful files on the personal store.

### SA-04 — Automatic expiry does not revoke in-flight access

Evidence: `backend/app/privacy/service.py:45`, `backend/app/core/workspace.py`, `backend/app/resumes/generation_service.py:842`, `backend/app/resumes/generation_router.py`, synthetic audit JSON.

Expiry removes session tokens and clears the PDF cache, but does not advance `WorkspaceBarrier.epoch` or cancel active work. Generation event streams check the workspace epoch, not token validity. Sessions already bound to the unchanged epoch can still execute and commit.

Reproduction: establish a synthetic passcode session; bind a database session and start the actual event generator with a mocked synthetic run lookup; expire the token; request privacy status. Status reports locked and a new export receives 423, but the epoch is unchanged. The already-open event generator subsequently emits a synthetic result, and the already-bound database session commits a synthetic update. The event/run content is mocked; the expiry, barrier and stream implementation are real. This is not a live Codex test.

Impact: the meaning of “locked after session expiry” is incomplete for an already authorized connection/operation. It does not let an arbitrary new unauthenticated request pass the lock. Explicit lock/passcode-change/delete already invalidate epochs and cancel work; that distinction must be preserved.

Remediation: define whether expiry revokes just one session or the whole workspace. For the existing single-owner policy, coordinate expiry with epoch invalidation/cancellation; add token-aware stream checks and a backend timer if revocation must occur without another request. A future multi-session design needs per-session revocation rather than surprising unrelated authorized sessions. Backend inactivity enforcement must not depend solely on a browser timer.

Acceptance: a held stream/pending transaction cannot emit private data/commit after automatic expiry; late render cannot refill caches; no client polling is required for the promised timeout; behavior with multiple sessions is documented/tested.

### SA-05 — Current passcode and database encryption are disabled

Evidence: native read-only privacy status; `backend/app/core/encryption.py`, `backend/app/core/cipher_database.py`, `backend/app/core/private_files.py`.

This is a configuration weakness, not a broken AES-GCM implementation. Without a passcode, any process able to reach the local API can use it. Without configured field/full-file encryption, copying a readable database can disclose stored career text, imports' extracted text, versions and other sensitive content. Actual database contents/ACLs and BitLocker status were not inspected. No claim is made that personal data is present or was leaked.

Passcode access and encryption at rest solve different problems. Scrypt hashes passcodes with a random salt and constant-time verification; they are not stored as plaintext. SQLCipher uses an Argon2id-derived key; AES-GCM private files bind owner/asset identity. Optional field encryption leaves queryable metadata. None of these controls protects an already compromised backend while it has the keys/unlocked data.

Remediation: enable a strong unique passcode; deliberately select field or full-store encryption and perform the documented offline backup/conversion/verification workflow. Confirm OS disk protection and file permissions. Protect keys separately from backups. Do not regenerate a key while retaining data encrypted with the original.

Additional integrity limitation: generic field encryption uses field/context AAD, rather than binding every ciphertext to a record/owner UUID. It is not a universal defense against an attacker with database-write access copying ciphertext between compatible fields. This was source-reviewed, not tested as a complete application attack. Use record-bound AAD in a future versioned migration if malicious database tampering is in scope; don't advertise encryption as protection against all rollback/swapping attacks.

Acceptance: documented wrong/missing-key and tamper failures, restart/unlock tests and successful restore from a synthetic encrypted backup. Confirm metadata/privacy scope accurately; downloaded JSON/PDF/DOCX copies remain plaintext.

### SA-06 — Current UI is a development deployment

Evidence: live UI HEAD check, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/nginx.conf`.

The running 5180 UI does not return CSP/nosniff/frame-protection headers. Hardened headers exist under Vite preview and Nginx, but are not applied to the current development server. Therefore historical production-header tests cannot be used to claim those headers are active in the native dev UI.

No XSS exploit was found: React escapes text, the audit search found no `dangerouslySetInnerHTML`/eval path, resume HTML is escaped and preview iframes have empty sandbox permissions. Lack of CSP removes defense in depth if an injection/dependency flaw emerges. Missing frame protection also permits framing of the development page where browser rules allow it. Browser localhost/private-network protections are browser-dependent, not a server security policy. This audit did not run a live browser exploit.

Remediation: serve a production build behind the hardened local proxy for remote access; avoid publishing Vite dev/preview as a permanent internet service. Keep same-origin APIs, locally packaged fonts/PDF.js and restrictive CSP; set HTTPS/HSTS only after a supported HTTPS deployment is established.

Acceptance: inspect actual served headers and iframe behavior in a real browser on the final URL, including API errors, SPA routes and PDF.js workers. A config file containing headers is insufficient.

### SA-07 — HTTPS proxy scheme/cookie trust needs a defined deployment contract

Evidence: `backend/app/privacy/router.py:10`, `frontend/nginx.conf:11`, synthetic probe.

Session cookies have HttpOnly and SameSite=Strict. Secure is set only when `request.url.scheme == 'https'`. In a plain HTTP ASGI TestClient scope, merely adding `X-Forwarded-Proto: https` did not create a Secure cookie. That is expected without trusted proxy handling and is not a demonstrated bypass of a deployed TLS proxy. Uvicorn can process trusted forwarding headers depending on its deployment settings; actual end-to-end behavior must be tested.

Current Nginx is HTTP-only and does not establish a trusted TLS-termination/scheme policy. Its forwarded Host can also conflict with local backend Host restrictions on a new remote hostname. Copying this setup under a public HTTPS URL may fail or issue cookies with weaker flags if operators work around restrictions incorrectly.

Remediation: define the one trusted proxy, preserve exact external Origin, deliberately normalize permitted backend Host, strip incoming forwarding/identity headers and forward a trustworthy HTTPS scheme. Enforce secure cookies in a remote-access profile instead of accepting downgrade. Do not trust forwarding headers from arbitrary direct clients.

Acceptance: browser cookies on the deployed HTTPS URL are Secure/HttpOnly/Strict; plain HTTP cannot receive/use sensitive sessions; spoofed forwarding headers from an untrusted peer have no effect; API has no bypass listener. No remote deployment was evaluated here.

### SA-08 — Configurable model destinations are not a public-server SSRF boundary

Evidence: `backend/app/settings/schemas.py:34`, `backend/app/ai/gateway.py:66`.

Optional HTTP providers accept loopback HTTP and explicitly consented remote HTTPS. Schema probes accepted consented HTTPS loopback, RFC1918 and link-local addresses. No request was sent to these targets. Non-loopback HTTPS, no URL credentials/query/fragment, disabled redirects and `trust_env=False` are positive controls. Standard HTTPX certificate verification remains enabled. There is no DNS-resolution/IP policy preventing private/metadata destinations, DNS changes or server-side probing by a settings user.

For the current trusted local owner, connecting to a local model server is intentional. In a public server, allowing untrusted users to choose endpoints could permit internal service probing or requests from the server network. TLS/certificate validity and endpoint path requirements constrain possible targets; the accepted URLs alone do not prove a cloud metadata leak. This concern applies to optional HTTP providers, not Codex's fixed provider marker.

Remediation for server mode: explicit provider/destination allowlist, validated/pinned resolution across requests, cloud metadata/internal range restrictions where appropriate, network egress rules and per-user secrets. Keep local-provider capabilities behind a separate trusted local profile.

Acceptance: a synthetic internal endpoint and DNS-changing fixture cannot be reached from an untrusted server settings user; required allowed providers still work; redirects/proxies cannot bypass the policy.

### SA-09 — Codex is a trusted native process, not a complete containment boundary

Evidence: `backend/app/ai/codex.py:17`, `:25`, `:72`, `:136`, `:161`, `:217`; detailed transport assessment below.

The executable is resolved from `STONKS_CODEX_CLI`/PATH and checked for existence (plus `.exe` on Windows); no signature/hash/version attestation is performed. Readiness checks required flags and ChatGPT login text. The child receives HOME/USERPROFILE/CODEX_HOME and authentication-related OS paths so it can authenticate, though application/API secrets are excluded. It runs as the backend OS account. Temporary working directories do not change OS identity or impose a read allowlist on the entire binary.

Shell/apps/plugins/web/memories/subagents are disabled; read-only and no-approval flags are supplied. These are significant model capability controls. OpenAI describes sandbox flags as restrictions on agent commands. They should not be interpreted as sandboxing every network/file operation of the CLI itself. Credential storage, native binary trust and same-account malware remain separate concerns. [OpenAI approvals/security](https://learn.chatgpt.com/docs/agent-approvals-security).

Tool-event rejection occurs after `run()` finishes and covers four named item types. It detects recognized unwanted output; it does not undo already executed actions, nor establish fail-closed coverage of every future event/tool type. Flags/config semantics may change between CLI releases. No tool escape was demonstrated. The existing mocked controls passed; no fresh inference/OS sandbox attestation occurred.

Remediation: use a trusted explicit CLI path and maintained compatible version; add compatibility tests for tool surfaces/event taxonomy, fail closed on unexpected security-relevant events and test restrictions on supported OSes. Consider a dedicated low-privilege AI helper with its own account/authentication and OS boundaries. Protect credential storage with user-only ACLs and OS credential store where supported. Never make this process an untrusted public execution service.

Acceptance: a synthetic disabled-tool attempt cannot read a canary/write/connect unexpectedly before result rejection; version/config changes cannot silently re-enable capabilities; process-tree timeout/cancel tests include descendants; keys/credentials never enter frontend/API/export/log content. These tests must avoid real secrets.

### SA-10 — Resource bounds do not establish network-scale resilience

Evidence: `backend/app/core/http.py`, `backend/app/ai/gateway.py:33`, `backend/app/rendering/service.py:230`, `backend/app/privacy/service.py:93`, `backend/app/privacy/service.py:54`.

Positive controls: 4 MiB ingress, bounded AI waiters/timeouts, two render slots, parser admissions/deadlines, bounded DOCX admission, bounded private PDF cache and unlock backoff. Remaining limits include no explicit body-read deadline in the ASGI receive loop, in-memory JSON/all-PDF ZIP export proportional to workspace size, no overall export quota, renderer memory/CPU constraints and no fair per-user quotas. Render semaphore wait limits admission wait, not all native process resource usage.

Unlock backoff is global and process-memory-only, so a reachable caller can cause temporary denial of unlock for the owner; restart resets backoff. Parallel attempts need their own consideration. Frontend 15-minute inactivity lock relies on pointer/key events and browser timers; sleeping/closed/throttled tabs are not server-side idle enforcement. Server 30-minute expiry limits new requests but has SA-04's in-flight gap.

No DoS stress test was run. These are capacity/availability gaps, not evidence of machine takeover. For owner-only access they are less exposed than in a public app.

Remediation: trusted gateway connection/body deadlines and rate limits, bounded streaming exports, OS resource budgets, fair admission and durable/session-aware abuse policy if server mode is built. Monitor health/resource metadata without logging private text. Use explicit busy/error states rather than unlimited work or unexpected paid fallback.

Acceptance: synthetic slow uploads, bounded export size, repeated expensive calls and bad unlock attempts cannot exhaust all service capacity or grow memory beyond documented limits; cancel releases capacity; owner recovery remains available.

## How secure is the Codex connection?

There are several distinct boundaries; treating them as one “secure connection” would hide important risks.

### 1. Browser to the application

Currently this is HTTP on loopback, not encrypted TLS. Remote observers cannot directly sniff loopback traffic through the LAN, but the local OS/process environment is trusted. A local compromise may inspect data before any encryption. For remote devices use authenticated private HTTPS; do not put plain HTTP career traffic onto a shared Wi-Fi/LAN. The proposed private network does not encrypt the local database or prevent an authorized client from exploiting the application.

### 2. Backend to local CLI

The backend starts Codex with a structured argument list (`create_subprocess_exec`), not shell-interpolated prompt text. The prompt goes through stdin; generated output is parsed as data, not executed as Python/shell/SQL. This is a meaningful defense against shell injection. Temporary schema/results are removed when the call finishes. CLI diagnostic/output reads are bounded and raw failures are suppressed. Schema validation happens again in the gateway. POSIX process groups and Windows `taskkill /T /F` are used for cancellation.

Application API keys/encryption keys are filtered from the Codex child environment, confirmed with synthetic sentinel values. This does not mean Codex has no credentials: it must access its own ChatGPT login. It also does not mean other same-account processes cannot inspect temporary files/memory or the OS user environment. Temporary result cleanup is not secure disk erasure; crash dumps, swap and provider-side copies are outside that promise.

### 3. CLI to OpenAI

The app forces the OpenAI provider and ChatGPT login mode while ignoring user configuration. The configured `https://chatgpt.com/codex` string is a provider marker; **the app does not post inference directly to that URL or pin every real CLI network destination.** The CLI owns authentication, HTTPS/secure-WebSocket transport and certificate handling. Official documentation describes shared CA handling for login, HTTPS requests and secure WebSocket connections. [OpenAI authentication](https://learn.chatgpt.com/docs/auth).

Assuming an authentic maintained CLI and uncompromised TLS trust configuration, this is a conventional authenticated encrypted connection against passive network observers. No certificate-verification bypass was found in the app's model boundary. Optional HTTPX providers also retain standard certificate verification, reject remote plaintext and disable redirect/proxy inheritance. I did not intercept or inspect a live Codex handshake, attest the installed binary or audit OpenAI's infrastructure. No TLS version/cipher, pinning or absolute man-in-the-middle immunity is claimed. A trusted corporate TLS interceptor or compromised root trust/endpoint has different visibility.

The normal inference path is outbound. It does not create a permanent inbound public-IP control channel to this backend. CLI interactive OAuth login can use a localhost callback; that is not the same as exposing the app to the internet. Account phishing, token theft or compromised local software remain possible independent of IP knowledge.

### 4. Data disclosure and credentials

Explicit AI configuration/consent is required and revalidated before inference admission. Codex receives selected job/career/import/letter context needed for a task, not automatic unrestricted database access. “Selected” still may include personally identifying/confidential facts; it is not anonymization. Disabling an endpoint prevents later stale calls, but cannot retract data already transmitted. Cancellation and local delete-all cannot erase provider copies.

Transport encryption protects data on its way to the provider; the provider can process that data. The audit did not inspect the account's retention, training, workspace or regional policies, so it cannot promise zero retention/no training for this particular account. ChatGPT sign-in and API-key sign-in use different applicable controls. [OpenAI authentication and data-handling boundary](https://learn.chatgpt.com/docs/auth).

Official documentation says Codex login can be cached in a plaintext `auth.json` or OS credential store. The application does not scrape/forward these tokens to an arbitrary provider, but a process with access to that storage may steal them. This audit did not read auth.json, tokens or credential-store contents, and cannot assert which storage mode/ACL is active. Protect the account with MFA and secure sessions; use supported OS credential storage/user-only permissions; never publish logs/auth caches or copy them into public images. [OpenAI login caching](https://learn.chatgpt.com/docs/auth).

### 5. Malicious prompts versus malicious programs

Prompt injection can influence text; it does not automatically execute a program. Here model tools are disabled, model output is schema-checked, source/numeric/vocabulary checks precede semantic verification, and saves recheck current source authority. Unsupported text should remain rejected or require sourced user review. These are positive controls against fabricated resumes and against turning job text into instructions.

However, instruction following and semantic verification are not proofs. Read-only permits reads under its configured policy; “approval never” means no prompts, not unlimited authority or a universal sandbox. A hypothetical capability/config regression could make post-run rejection too late for confidentiality. Do not treat prompt delimiters or a second verifier as substitutes for OS containment.

OpenAI explicitly advises against exposing Codex execution in untrusted/public environments. [OpenAI authentication guidance](https://learn.chatgpt.com/docs/auth). The public browser-first hosting plan should therefore keep AI in a separately approved local companion, not expose the owner's signed-in CLI to arbitrary visitors.

## Controls that held up in this review

- Source-reviewed loopback defaults plus actual loopback listeners; server-domain guards remain.
- Host rejection (400), untrusted write-Origin rejection (403), new-request rejection after passcode expiry (423), HttpOnly/Strict cookie flags and synthetic secret filtering.
- Parameterized SQLAlchemy repository queries and owner scoping in inspected paths; no direct string-interpolated user SQL found in the reviewed application query paths. This is not exhaustive SQL fuzzing or proof of multi-tenant authorization.
- Escaped template text, HttpUrl resume links, bounded inert custom HTML/CSS, sanitized restricted PNG encoding, sandboxed HTML iframe and packaged PDF.js/fonts. No model-to-eval/shell execution path was found.
- Optional authenticated encryption, missing/wrong-key fail-closed startup/reads, backup-before-conversion design and owner-bound asset AAD. At-rest enablement is separate from implementation availability.
- Explicit lock/delete/passcode changes revoke epochs/cancel operations, with real regression controls; the automatic-expiry exception is documented above.
- Non-root Docker app/frontend users and source-allowlisted image contexts, no published DB/Redis host ports. No claim of a hardened public container deployment or fresh container scan.
- API no-store/privacy headers and production CSP. These do not establish that current dev-page headers are hardened.

## Executed validation

| Check | Result |
|---|---|
| `python scripts/tasks.py check` | Passed: 81 backend tests, 20 frontend tests, Ruff lint/format, strict mypy/TypeScript, API artifact drift, ESLint and production build. One upstream Starlette/httpx deprecation warning. Existing tests pass despite SA-04 because they did not cover expiry's full stream/commit revocation. |
| Initial `python scripts/tasks.py audit` | Failed while pip-audit prepared/upgraded its temporary pip environment. This was not a successful vulnerability check. |
| Audit retest | Passed Python and Node audits: no known vulnerabilities reported. Set this command's SSL_CERT_FILE and REQUESTS_CA_BUNDLE to the installed certifi bundle; TLS verification remained enabled and no permanent settings changed. |
| Custom synthetic audit script | Passed execution and recorded the weak behaviors as well as positive controls; exit 0 means probes completed, not that every security condition is safe. |
| Actual current local posture | Listener/firewall metadata, privacy booleans and UI HEAD response inspected; no content/export/AI requests sent to the personal backend. |

Package advisory success does not cover logic bugs, malicious/supply-chain packages, native Chromium/CLI/OS advisories, mutable image base tags or GitHub Actions integrity. Dependency locks are valuable; Python requirements are pinned without a `--require-hashes` installation policy, and CI actions/images use tags rather than immutable digests/commit SHAs. Consider integrity pins, provenance and periodic controlled update/scan work. Do not freeze vulnerable binaries indefinitely to preserve a lock.

Full browser e2e, fresh-install, Docker/hosted compatibility and fresh live-provider evaluation were not rerun during this audit. Prior acceptance evidence is historical and is not a security certificate.

## Prioritized implementation backlog

1. **Keep public ingress closed.** Preserve existing ports/services; enable owner passcode through the UI and plan encryption through reviewed backup/offline conversion. Do not change privacy settings silently as part of an audit.
2. **Fix SA-04 with meaningful expiry tests.** Include held SSE and pending transactions, no-poll expiry, cache late insertion and multi-session policy. Preserve explicit lock/delete barriers.
3. **Isolate renderer/parser privileges.** Enable supported Chromium sandboxing; add restricted workers, minimal environments, filesystem/network/resource boundaries. Verify actual PDFs/imports/cancellation on supported OSes.
4. **Create and test a production private-access profile.** Owner-only identity/device policy, HTTPS, Secure cookies, strict proxy/origin/host contract, no bypass, production browser headers and documented recovery.
5. **Harden Codex trust and compatibility.** Explicit trusted binary/account, supported credential storage, capability/event compatibility and synthetic containment tests. Keep consent and ai-only inference. Do not relax sandbox controls to make a deployment work.
6. **Add resource/backup controls.** Bounded exports, read deadlines, worker budgets and tested independent encrypted backups. Preserve downloads/provider deletion limitations.
7. **Only then consider public/server work.** Real owner authentication/CSRF, tenant-scoped state/key/cache/worker isolation, SSRF policy, abuse limits and a separate AI cost/security design. A public browser-first edition needs its own XSS/storage/pairing audit before release.

For runtime fixes run check/audit/e2e/fresh-install as appropriate, regenerate API artifacts if contracts change, and verify real PDFs/browser/OS isolation and hosted environments separately. Acceptance should be based on observed deny behavior and invariants, not mock flags alone.

## Honest conclusion

The code contains meaningful privacy and safety work, and the currently observed loopback binds protect it from direct public-IP access through these sockets. The strongest immediate concern is not that an IP magically grants control of the PC: it is that a local-only identity model could be exposed through hosting changes, and that file/AI native processes still trust the backend OS account.

A carefully restricted private HTTPS deployment is feasible after the identified hardening and validation. A public tunnel to the current unlocked app is unsafe. A public multi-user backend or unrestricted signed-in Codex service is not supported by the present security design. No assertion of “unhackable,” zero risk, or an easy demonstrated PC-takeover exploit is justified by this audit.
