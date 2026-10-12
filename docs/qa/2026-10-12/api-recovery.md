# API Recovery Slice

## Scope

- Owned files: `frontend/src/api.ts`, `frontend/src/api.test.ts`.
- Goal: prevent a hung API request or hung response body from leaving the UI busy indefinitely.
- Non-goals: provider settings, auth schema, retry behavior, deployment, and production data mutation.

## Behavior Change

- Every authenticated ledger API request now uses a combined `AbortController` with a 90 second timeout.
- The timeout covers both the initial `fetch()` and response body reading.
- Caller-supplied `AbortSignal` values remain supported by the internal request contract.
- Timeout failures return `ApiError` code `request_timeout` with Korean copy distinct from offline failures.
- Ordinary network failures still return `offline`.
- Server errors, correlation IDs, 401 handling, and supplied `Idempotency-Key` values remain unchanged.
- Mutating requests still do not retry automatically.

## Verification

- `npm test -- --run src/api.test.ts` from `frontend` passed: 11 tests.
- `npm run lint -- src/api.ts src/api.test.ts` from `frontend` passed.
- `npm run build` from `frontend` still fails outside this slice in `src/ledger-context.test.tsx` with existing `never` type errors for plan progress fields. The API files no longer report build errors after this change.

## Residual Risk

- The 90 second timeout is intentionally longer than the observed Render free cold-start window. A truly slow but valid request above that limit will surface a retryable timeout to the user.
- The underlying browser fetch/body stream is aborted through the same signal; fake never-settling response bodies in tests are guarded by a promise race so the UI path still resolves.
