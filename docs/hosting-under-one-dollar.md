# Hosting within $1/month

Planning date: 2026-10-09 (America/Toronto). Status: proposal only. No implementation, deployment, account creation, personal-data migration or model calls are authorized by this plan. Audience is awaiting clarification; recommendations below distinguish personal access from a public product.

## Feasibility and budget definition

Yes: $0/month in hosting-provider charges is feasible for personal access or a public, browser-first product. A dependable public service that retains the current full backend, cloud persistence and operator-funded AI cannot be promised at $1/month. Free tiers have limits and can change. Use $0 services rather than a paid plan whose first bill happens to be less than $1.

The budget assumes provider-supplied hostnames, no paid domain, no purchased AI credits and no paid email/SMS service. An existing ChatGPT plan is an existing expense, not a newly free AI service. If the cap includes that subscription, newly incurred electricity, internet or hardware, the personal-host route must account for those too. A $1 alert is not a billing cutoff. Require free-only plans and refuse paid fallback; outage or reduced functionality is preferable to exceeding the cap.

## Current product constraints

The accepted Phase 0-6 product has FastAPI/SQLAlchemy/Alembic, twelve career categories, immutable resume/letter/template versions, durable local runs, source checking, private assets, actual Chromium PDF fitting and PDF.js preview, semantic DOCX, ATS heuristics, imports and tracker/calendar. Preserve these accepted workflows in the local edition.

It is a single-owner application. `backend/app/auth/service.py` resolves a fixed local owner and refuses server mode; `backend/app/main.py` restricts hosts in local mode. Passcode/epoch protections do not constitute public multi-user authentication. The existing Compose credentials and ingress are local-development settings. Merely changing bind addresses or disabling guards is not a hosting solution.

Codex runs as a native child process in `ai/codex.py`, with explicit consent and isolated capabilities. It cannot execute inside a static browser page. Stock containers lack CLI/login, and live authenticated Codex container compatibility remains unverified. No credentials may be shipped into frontend bundles or scraped from CLI storage.

## Route A: full product for personal remote access

Recommended if the product serves only its owner. Keep data, FastAPI, Chromium and native Codex on the existing Windows computer. Serve a production React build and same-origin `/api` through a loopback proxy, then publish that proxy only to the owner's private Tailscale network using Serve HTTPS. A provider hostname avoids domain registration. Devices need Tailscale. Do not enable public Funnel.

Tailscale's current Personal plan is $0, supports up to six users and is for non-commercial use. This deployment still has exactly one application owner; the network's user allowance does not create separate product workspaces. Restrict access to the owner's identity/devices. The computer must be awake, connected and running; this is remote access to self-hosted software, not independent cloud hosting.

Ordered implementation milestones:

1. Add an opt-in private-access deployment profile and production static/API proxy. Preserve the existing 5180/8010 installation and unrelated Docker stack. Do not expose Vite or the raw API publicly. Keep backend loopback host enforcement; the proxy supplies an allowed backend Host while preserving the browser's real Origin.
2. Configure the exact private HTTPS frontend origin, owner-only network policy, trusted proxy boundary and secure session cookies. Never trust client-supplied identity/forwarding headers. Retain local passcode, bounded unlock attempts, no-store responses, CSP, 4 MiB writes, SSE cancellation and privacy epochs. Fail closed if the configured private-access boundary is absent.
3. Add documented Windows start/restart supervision under the same owner as CLI authentication. Keep private-file/storage keys in backend-only configuration. AI remains off until the existing explicit sharing-consent setup. No cloud AI relay is necessary.
4. Add consistent encrypted backup/restore procedures for the database, immutable assets and required sidecars, with recovery keys kept separately. Use SQLite backup facilities or quiesce writes; copying a live file without WAL handling is insufficient. Use existing local storage, with a separate-device copy where available. Automatic backup support is new work, not an existing accepted feature.
5. Verify real second-device HTTPS access, denied unauthorized access, cookies/origins, PDF.js, actual PDF/DOCX, SSE reconnect/cancel, lock/delete races, outage/restart and restore from synthetic data. Run check/audit/e2e/fresh-install for runtime release changes, api if contracts change, and report live AI checks separately with synthetic fixtures and explicit consent.

Acceptance: full accepted functionality is available from authorized devices without any hosting subscription. Loss of power/network produces a clear unavailable state. No public ingress or personal-data transfer to a new cloud store occurs.

## Route B: public browser-first edition

Recommended if anyone should be able to use the site without the owner subsidizing their compute or data. Host public application code on Cloudflare Pages Free at a `pages.dev` hostname. Store career data and immutable documents locally in the user's browser; publish no private records/assets as static files. Cloudflare serves the site's own packaged assets; retain no third-party runtime scripts/fonts, analytics or external asset URLs. The edge hosting choice is an explicit new distribution proposal relative to the original local-only architecture.

This is a substantial additional edition, not a deployment toggle. The initial public release would have narrower functionality than the accepted local product. It needs no cloud account/workspace database. It cannot provide cloud sync, phone access to another device's records, guaranteed persistence or full current PDF fitting by default.

Ordered implementation milestones:

1. Introduce a typed workspace interface separating React workflows from HTTP transport, leaving the current FastAPI adapter intact. Map every current endpoint/invariant to browser support, local companion support or an explicitly unavailable capability. Preserve generated API types; new portable document contracts must be generated/validated rather than edited by hand.
2. Implement versioned IndexedDB repositories, schema migrations, transactional parent remapping, immutable snapshots and optimistic revisions for career/manual resumes/history/tracker first. Port source membership, locks and deterministic matching checks with shared fixtures. A client implementation protects the user's workflow; it is not trusted server authorization.
3. Design encrypted browser workspace/asset storage with a user-derived key, password-based KDF, authenticated encryption, unique nonces and fail-closed unlock. Clear application caches/key references on lock, and guard late operations with epochs. Document that JavaScript cannot guarantee memory zeroization, XSS can access unlocked data, and a lost password/cleared browser store can lose records. Request persistent storage where supported, measure quota and require explicit portable encrypted backup/download and tested restore. Browser storage is not a backup.
4. Add local manual editing, template rendering and semantic DOCX. Initially offer browser print-to-PDF with an honest pagination limitation. It does not replace actual Chromium measurements, PDF extraction ATS or fit acceptance. For full measured export/import/AI, retain a separately installed local companion using the existing backend.
5. Build companion pairing as a separate security milestone: explicit user start/approval, short-lived credentials, exact origin allowlist, loopback-only API, no arbitrary commands, and no credential exposure. Test HTTPS-to-local browser permission/private-network/CORS/CSP behavior on named supported browsers; do not assume fetch to localhost works everywhere. If pairing is blocked, fall back to opening the local app or explicit file exchange. Preserve all evidence checks at the companion before saving AI output. Mobile users without a companion get the supported manual edition.
6. Add AI only through the owner's own local companion/provider configuration, with consent and existing source verification. No operator-funded inference or shared ChatGPT credential. The browser edition's companion transport delegates inference to ai; it does not introduce a second LLM endpoint caller. Expose unavailable/limit states clearly. Do not advertise free unlimited AI.
7. Add Pages SPA fallback, security/privacy headers, bundled assets and no secret/data files in the upload allowlist. Inspect artifact sizes; the current per-file Pages limit is 25 MiB. Use free-only hosting with no paid Functions/R2 fallback. Test browser migrations/quota/cleared storage, injection, encrypted backup restore, cross-tab revisions, late writes after lock/delete, mobile, actual exports and CSP. Retain existing check/audit/e2e/fresh-install gates and add a real Pages browser check before claiming hosted compatibility.

Acceptance: the public site is usable for the declared manual workflows at $0 owner hosting cost, with transparent local persistence and backup warnings. Full current feature parity is a later measured milestone; users needing it keep the native edition/companion. No accounts or separate-user cloud authentication are falsely claimed.

## Route C: free cloud VM, conditional alternative

Oracle currently documents Always Free A1 capacity equivalent to 2 OCPUs/12 GB RAM, 200 GB combined boot/block storage and five volume backups. Capacity can be unavailable, and idle instances may be reclaimed. Do not use older 4 OCPU/24 GB tutorials or manufacture load to evade reclamation. This can host a personal prototype independent of the owner's PC, but it is not an availability guarantee.

Before choosing it: prove actual free allocation in the home region without upgrading to paid billing; validate locked Python/Node/Chromium/SQLCipher/Codex availability on ARM; use an isolated synthetic store. Prefer native Linux service supervision for Codex rather than claiming untested stock-container authentication. Retain one backend process and persistent encrypted assets. Use private owner-only access for a personal deployment. Independent encrypted off-VM backups and a tested rebuild are mandatory; provider backups alone are not sufficient recovery design.

A public full-backend edition additionally needs real owner/session authentication, CSRF protection, strict trusted-proxy/host/origin configuration, tenant isolation for caches/keys/files/runs, owner-scoped epochs, per-user quotas/fair queueing and key/account recovery. Do not map multiple users to LOCAL_OWNER or expose native Codex execution to public requests. Those changes and AI funding require their own design and validation before launch. Free capacity alone does not solve them.

Render Free is unsuitable for the present durable store: web filesystems are ephemeral, persistent disks require paid services and free Postgres expires after 30 days. Free static/edge hosting alone does not supply this product's existing native Python/Chromium/CLI runtime.

## Cost and decision gate

| Route | Owner hosting bill target | Main tradeoff |
|---|---:|---|
| A: personal PC + private HTTPS | $0/month | PC uptime, personal-use eligibility, existing electricity/internet/AI expenses |
| B: public browser-first Pages | $0/month | New storage/export work; initial feature limits; no automatic cloud sync or subsidized AI |
| C: Always Free cloud VM | $0 within verified allocation | Capacity/reclamation, ARM compatibility, security and recovery work |

Choose A for personal full-feature access, B for a public zero-subsidy product, C only if free-tier availability risk is acceptable. Audience and whether $1 covers only incremental hosting remain open. No route has been selected or deployed.

## Official sources checked on 2026-10-09

- [Tailscale pricing and personal-use eligibility](https://tailscale.com/pricing)
- [Tailscale Serve HTTPS/private network and identity behavior](https://tailscale.com/docs/features/tailscale-serve)
- [Cloudflare Pages pricing](https://www.cloudflare.com/en-ca/developer-platform/products/pages/)
- [Pages build/file limits](https://developers.cloudflare.com/pages/platform/limits/)
- [Oracle Always Free allocation, capacity, reclamation and backups](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Render Free persistence and expiration limits](https://render.com/docs/free)
- [OpenAI authentication, billing modes and public execution guidance](https://learn.chatgpt.com/docs/auth)
- [OpenAI plan usage and credit limits](https://learn.chatgpt.com/docs/pricing)

These sources establish provider offerings, not deployed-product compatibility or future pricing. Existing Phase 6 test evidence is historical; this planning session ran no product checks and changed no runtime code.

Security follow-up (2026-10-09): see docs/release/security-audit-2026-10-09.md. The reproduced expiry revocation gap and renderer/parser isolation require remediation and target-environment verification before treating private remote access as ready. No route is deployed or security-certified.
