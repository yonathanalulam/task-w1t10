# Developer Rulebook v2

This file is the repo-local engineering rulebook for `slopmachine` projects.

## Scope

- Treat the current working directory as the project.
- Ignore parent-directory workflow files unless the user explicitly asks you to use them.
- Do not treat workflow research, session exports, or sibling directories as hidden implementation instructions.

## Working Style

- Operate like a strong senior engineer.
- Read the code before making assumptions.
- Work in meaningful vertical slices.
- Do not call work complete while it is still shaky.
- Reuse and extend shared cross-cutting patterns instead of inventing incompatible local ones.

## Verification Rules

- During ordinary iteration, prefer the fastest meaningful local verification for the changed area.
- Prefer targeted unit, integration, module, route-family, or platform-appropriate local UI/E2E checks over broad reruns.
- Do not rerun full Dockerized startup and the full test suite on every small change.
- The broad owner-run project-standard verification path should be used sparingly, with a target budget of at most 3 times across the whole workflow cycle.
- If you run a Docker-based verification command sequence, end it with `docker compose down` unless containers must remain up.

Every project must expose:

- one primary documented command to launch or run the application in its selected stack
- one primary documented command to run the full supported test suite
- follow the original prompt and existing repository first; use the defaults below only when they do not already specify the platform or stack

For web backend/fullstack projects, those are usually:

- `docker compose up --build`
- `./run_tests.sh`

For mobile, desktop, CLI, library, or other non-web projects, use the selected stack's appropriate commands instead, but keep them to one clear documented launch command and one clear documented full-test command.

## Testing Rules

- Tests must be real and tied to actual behavior.
- Do not mock APIs for integration testing.
- Use real HTTP requests against the actual running service surface for integration evidence.
- For UI-bearing work, use the selected stack's local UI/E2E tool on affected flows and inspect screenshots or equivalent artifacts when practical.

Selected-stack defaults:

- follow the original prompt and existing repository first; use the defaults below only when they do not already specify the platform or stack
- web frontend/fullstack: Playwright for browser E2E/UI verification when applicable
- mobile: Expo + React Native + TypeScript by default, with Jest plus React Native Testing Library for local tests and a platform-appropriate mobile UI/E2E tool when the flow needs it
- desktop: Electron + Vite + TypeScript by default, with a project-standard local test runner plus Playwright's Electron support or another platform-appropriate desktop UI/E2E tool when the flow needs it

## Documentation Rules

- Keep `README.md` and any codebase-local docs accurate.
- The README must explain what the project is, what it does, how to run it, and how to test it.
- The README must stand on its own for basic codebase use.

## Secret And Runtime Rules

- Do not create or keep `.env` files anywhere in the repo.
- Do not rely on `.env`, `.env.local`, `.env.example`, or similar files for project startup.
- Do not hardcode secrets.
- If runtime env-file format is required, generate it ephemerally and do not commit or package it.

Selected-stack secret/config defaults:

- follow the original prompt and existing repository first; use the defaults below only when they do not already specify the platform or stack
- web Dockerized services: use Docker/runtime-provided variables, never committed env files
- mobile apps: do not bundle real secrets into the client; use app config only for non-secret public configuration and keep real secrets server-side or in platform-appropriate secure storage when user/device secrets must be stored at runtime
- desktop apps: keep sensitive values in main-process/runtime configuration or platform-appropriate secure storage, and do not expose them to the renderer by default

## Product Integrity Rules

- Do not leave placeholder, setup, debug, or demo content in product-facing UI.
- If a real user-facing or admin-facing surface is required, build that surface instead of bypassing it with API shortcuts.
- Treat missing real surfaces as incomplete implementation.

## Rulebook Files

- Do not edit `AGENTS.md` or other workflow/rulebook files unless explicitly asked.
