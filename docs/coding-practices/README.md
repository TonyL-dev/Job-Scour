# Reusable coding practices

These guides are starting standards for new projects, derived from this application's useful patterns and lessons. They describe recommended practice; they are not a claim that every recommendation is already implemented here.

- [Frontend coding practices](FRONTEND_CODING_PRACTICES.md): React, TypeScript, application structure, state, API integration, UI, accessibility, testing and delivery.
- [Backend coding practices](BACKEND_CODING_PRACTICES.md): Python, FastAPI, domain boundaries, contracts, persistence, concurrency, security, background work and operations.

Both guides can be copied independently. Read both when building a full-stack application. Examples use a generic `projects` domain and are illustrative, not additions to this application's API.

For a source-linked explanation of this repository's actual implementation, read the [developer handbook](../developer/README.md), [backend guide](../developer/BACKEND.md) and [frontend guide](../developer/FRONTEND.md). To turn these standards into a new project's concrete architecture/onboarding documentation, copy and complete the [project architecture template](../developer/PROJECT_ARCHITECTURE_TEMPLATE.md). Its proposed layout is explicitly separate from the current application's layout.

## How to adopt these guides

1. Copy the relevant guide into the new repository's `docs/coding-practices/` directory.
2. Complete its project adoption record before implementation. Choose actual versions, deployment scope, data sensitivity and supported environments; do not treat this repository's pins as universal defaults.
3. Reference the adopted guides from the repository's `AGENTS.md` and contributor documentation. Put enforceable checks in the formatter, linter, compiler, migration checks and CI.
4. Build one vertical slice: migrate storage, implement a use case, export its contract, integrate the UI and verify a real user journey.
5. Record justified deviations in a decision log. Update the guides when decisions change; preserve important compatibility and verification limitations.

Suggested `AGENTS.md` wording:

```markdown
Read docs/coding-practices/FRONTEND_CODING_PRACTICES.md and
docs/coding-practices/BACKEND_CODING_PRACTICES.md before changes.
Follow the completed project adoption records and documented exceptions.
Regenerate API artifacts after contract changes; do not edit generated files.
Run the checks relevant to the change and report their actual scope/results.
Preserve ownership, authorization, concurrency and privacy boundaries.
```

## Interpretation

**Must** marks an adopted requirement. **Default** marks the preferred starting choice, which can be changed with a recorded reason. **Conditional** practices apply only when the feature or deployment requires them. None of these documents requires adding optional features, frameworks or infrastructure to an otherwise small project.

For this repository, existing instructions take precedence. Its runtime requirements remain Python 3.12+, Node 24.x and pnpm 11.19.0. No runtime refactoring, dependency changes or deployment are part of creating these guides. The known automatic-session-expiry revocation issue and renderer/parser containment gaps remain unresolved; see the [security audit](../release/security-audit-2026-10-09.md).
