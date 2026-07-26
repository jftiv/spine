# Stack defaults

What to reach for when starting something new and nothing in the target repo dictates
otherwise. **An existing repo's choices always win** — consistency beats these defaults.

| Concern | Default | Notes |
|---|---|---|
| Frontend | TypeScript + React + Vite | strict TS, function components |
| Frontend server state | SWR (`useSWR`) | not `useEffect` + `useState`. TanStack Query only with a stated justification |
| Frontend client state | local state → context → Zustand | in that order of escalation |
| Frontend forms | plain controlled inputs; React Hook Form + Zod when form-heavy | RHF needs approval before adding |
| Backend (services, CLIs) | Go | stdlib-first |
| Backend (rich domain, MS stack) | C# / .NET | nullable on, warnings as errors |
| Database (new) | PostgreSQL | latest stable |
| Database (legacy) | MySQL | only when the system is already on it |
| Unit tests (TS) | Vitest | |
| Unit tests (Go) | stdlib `testing` + subtests | |
| Unit tests (C#) | xUnit | |
| E2E + visual regression | Playwright | the only browser automation tool |
| Observability | OpenTelemetry → OTLP collector | keeps the backend swappable |
| Containers | multi-stage, distroless/slim, non-root | pinned by digest for prod |

## Adding a dependency

Justify it. The bar: does the standard library or an existing dependency already do this
acceptably? Is it maintained? What does it pull in transitively? A dependency is a
permanent liability, and the second library that does the same job is worse than either
alone.

**Prefer the slim package that covers the need over the comprehensive one that covers
every need.** Weight and API surface are ongoing costs; capability you do not use is not
free. Choosing the larger option requires naming the specific capability the slim one
lacks — "more powerful" and "more popular" are not reasons. This is the rule behind
SWR-over-TanStack-Query above, and it generalizes.

Some dependencies are **approval-gated**: recommend them with the justification, then
wait for the user before adding. React Hook Form is one.

## Introducing a new language or framework to an existing repo

Don't, without an explicit conversation. One backend runtime per service, one test
runner per language, one browser automation tool per repo.
