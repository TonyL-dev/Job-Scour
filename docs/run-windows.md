# Run the completed local app on Windows

Phases 0–6 are implemented. The broader blueprint still lists later enhancements. This is a local single-owner application; public/multi-user deployment, OCR, external reminder delivery, automatic encrypted backups and later differentiators are outside this release. Hosted CI, physical clean-OS certification, Windows Word and live Codex container authentication remain unverified. See IMPLEMENTATION_STATUS.md for acceptance evidence.

## 1. Check prerequisites

Open PowerShell and run:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
python --version
node --version
pnpm --version
```

Required: 64-bit Python 3.12+, Node 24.x, pnpm 11.19.0. If pnpm is missing, run `npm install -g pnpm@11.19.0`. Install the required Python/Node versions if needed, then reopen PowerShell. Git is needed for development/hooks, not to run the application. During the 2026-10-08 guidance session, the Codex terminal resolved Python 3.14.8, Node 24.19.0, pnpm 11.19.0 and native Codex CLI 0.160.1. A separate terminal must also resolve the executables on its own PATH.

## 2. Prepare dependencies and storage

From the repository root:

```powershell
python scripts/tasks.py setup
python scripts/tasks.py renderer-setup
python scripts/tasks.py migrate
python scripts/tasks.py doctor
```

Stop if a command fails and resolve its error before continuing. Setup downloads locked dependencies; renderer-setup downloads the matching Chromium. Migrate upgrades the configured database; it does not reset existing records. Back up an existing workspace before upgrading. Doctor validates storage and renders synthetic PDF content without AI. Default configuration needs no .env file. Backend settings can be customized using backend/.env.example, but never overwrite an existing .env blindly.

## 3. Start both services

Keep this first PowerShell window open:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
python scripts/tasks.py backend
```

Open a second PowerShell window:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
python scripts/tasks.py frontend
```

Open http://127.0.0.1:5173. The overview should show Backend connected. Readiness is http://127.0.0.1:8000/api/health and API documentation is http://127.0.0.1:8000/docs. Keep both terminals open while using the app. These commands run the development UI against the real backend; they do not require Docker or a local model server.

## 4. Configure AI only if wanted

Use the installed native Codex CLI, authenticated on the same Windows account as the backend:

```powershell
codex --version
codex login status
```

If not signed in, run `codex login` and complete ChatGPT sign-in. If Codex is unavailable, follow the official CLI installation instructions: https://learn.chatgpt.com/docs/codex/cli. The adapter requires a native codex.exe on Windows, not merely a .cmd shim. If it is not discoverable, set STONKS_CODEX_CLI to the installed codex.exe's full path in the backend terminal, then restart the backend. Never copy OAuth credentials into this project.

In AI settings, review the sharing consent, check it only if you agree, and click Use Codex for AI tasks. This assigns the nine supported chat tasks and tests connectivity. Keyword matching needs no embedding model. Manual career entry/import parsing/editing/export/ATS/tracking work without AI. Consent allows the supplied job text/career facts to be processed remotely by OpenAI; account access/limits are determined by Codex.

## 5. Optional encrypted original/PNG storage

Parsing without retaining originals requires no private-file key. Retained originals and custom PNG assets require a backend APP_UPLOAD_KEY (or existing APP_ENCRYPTION_KEY fallback). Reuse the original key if data already exists. For a new workspace with no configured private-file key, run in the backend terminal before starting the backend:

```powershell
if (-not $env:APP_UPLOAD_KEY -and -not $env:APP_ENCRYPTION_KEY) {
    $env:APP_UPLOAD_KEY = [Environment]::GetEnvironmentVariable('APP_UPLOAD_KEY', 'User')
    if (-not $env:APP_UPLOAD_KEY) {
        $env:APP_UPLOAD_KEY = python -c "import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
        [Environment]::SetEnvironmentVariable('APP_UPLOAD_KEY', $env:APP_UPLOAD_KEY, 'User')
    }
}
```

This stores a reusable key in your Windows user environment without printing it. Restart the backend; subsequent new terminals inherit it. Keep a secure separate backup and never regenerate/change it while retaining encrypted files. These helpers read process environment variables; merely adding APP_UPLOAD_KEY to backend/.env does not configure them. This key protects private file bytes only; it does not encrypt all extracted text or the whole database. See README optional SQLCipher/field-encryption sections for those separate choices.

## 6. First product workflow

1. Import a text PDF/DOCX locally, review candidates and parent links, then commit approved facts; or enter them in Career library.
2. Build and save a master using library sources. Inspect the actual PDF; optionally choose the gold-standard master.
3. Save a job description in Job analysis; analyze it after AI setup.
4. Generate & review a tailored resume. Review sources/rejections, save a separate version, and inspect/download PDF or DOCX from history.
5. Generate/review a cover letter from the saved analysis and selected evidence; save an immutable version.
6. Track the application with exact submitted resume/letter versions and a follow-up date.
7. Use Strengthen profile, Prompt playground or Custom templates as needed; preferences/templates remain separate from stored career facts.
8. Configure a passcode in Privacy if desired and use JSON/ZIP export for backups. A passcode is not database encryption.

## 7. Stop, restart and maintain

Press Ctrl+C in both service terminals to stop. On normal subsequent launches, only repeat the two service-start commands. After a source upgrade, back up first and rerun setup, renderer-setup, migrate and doctor. Optional developer validation is `python scripts/tasks.py check`; acceptance already passed in the implementation session.

Default native data is backend/resume-tailor.db. Privacy export provides portable workspace artifacts; encrypted file envelopes still require your separate key. Copying the raw SQLite file should be done with the backend stopped, including applicable encryption salt/key handling. Downloads/backups/provider copies are outside delete-all. Keep loopback defaults; do not expose local mode as a public server.

If preview returns 503, rerun renderer-setup and doctor. If ports 5173/8000 are busy, identify the listener before stopping anything; README describes port/proxy configuration. If Codex cannot be found, fix the backend's native executable path. If private storage reports a key error, restore its original key rather than deleting data or generating another key. Use the matching command's terminal error for other failures.

## Docker alternative

The stock Docker stack supports local manual/PDF/ATS/history/tracker/privacy workflows but has no bundled Codex CLI/login. Native and Docker use different stores by default. From the root with Docker Desktop running:

```powershell
docker compose up --build --wait
```

Open http://127.0.0.1:5173. Stop with `docker compose down`, which preserves its database volumes. Avoid `down --volumes` unless you intend to erase that stack's data. Do not start native and Docker on the same ports simultaneously. Retained uploads/assets require explicit private-key forwarding via a Compose override; the stock Compose file does not forward APP_UPLOAD_KEY automatically.

## Current running installation — 2026-10-08

The native app was installed, its existing SQLite file backed up to .validation/startup-backups/20261008-162506, migrated and started. Doctor and real browser/synthetic PDF.js checks passed. An unrelated Docker stack occupies default ports, so use **http://127.0.0.1:5180**, with API on **http://127.0.0.1:8010**. Those native services were intentionally left running. The original Docker stack was preserved.

A new private-file key is persisted in the Windows user environment and loaded into the backend; its value was not logged. Keep that key for future retained uploads/assets. Codex is signed in, but this workspace has no AI configuration or sharing consent, so AI remains off until explicit consent/configuration. Existing career records were not edited and no AI calls were made by startup verification.

For future restarts on these alternate ports, use this backend terminal:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
$env:APP_API_PORT = '8010'
$env:APP_FRONTEND_ORIGINS = '["http://127.0.0.1:5180","http://localhost:5180"]'
$env:APP_UPLOAD_KEY = [Environment]::GetEnvironmentVariable('APP_UPLOAD_KEY', 'User')
python scripts/tasks.py backend
```

And this frontend terminal:

```powershell
Set-Location 'D:\DUM-E\Stonks V2'
$env:API_PROXY_TARGET = 'http://127.0.0.1:8010'
pnpm --dir frontend dev --port 5180
```

Do not run duplicate instances while the current services are listening. Current process information is in .validation/application-running.json; runtime browser evidence is in .validation/application-smoke-evidence.json. This startup verification did not rerun the complete development test suite; its previous acceptance results remain recorded separately.
