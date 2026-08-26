# Acceptance Evidence

This file records the acceptance scenarios to run locally before submission.

## Probe 1 — Constraint enforcement

1. Call `POST /variants/validate` for X with content over 280 characters.
2. Expected: HTTP 400 with `ConstraintViolation`.
3. Repeat with more than 3 hashtags.
4. Expected: HTTP 400.
5. For LinkedIn, pass `tone=casual`.
6. Expected: HTTP 400 because LinkedIn allows professional/neutral tone in this implementation.

## Probe 2 — Review gate

1. Ingest a post.
2. Select a generated variant while it is still `draft`.
3. Call `/publish/schedule` without approving it.
4. Expected: HTTP 403 and no publish-history row.
5. Set the variant to `approved`.
6. Schedule it again with a new idempotency key.
7. Expected: job is accepted and later becomes `completed`.

## Probe 3 — Idempotency

1. Approve a variant.
2. Publish it with `idempotency_key=demo-key-1`.
3. Repeat the exact publish request with the same key.
4. Expected: `already_processed`; no second `publish_history` row.

## Probe 4 — Durable scheduling

1. Approve a variant.
2. Schedule it for at least two minutes in the future.
3. Verify `/publish/jobs` contains the job with `status=scheduled`.
4. Stop the API process before the due time.
5. Restart the API.
6. Expected: the persisted job remains in SQLite and the worker claims it after its due time.

## Probe 5 — Adapter swap

The API resolves publishers through the `SocialPublisher` interface. X and LinkedIn use mock implementations while Telegram uses the real Bot API implementation. Switching the platform changes the adapter without changing the scheduler contract.

## Submission checklist

- [x] README with architecture, run steps, demo flow, and limitations
- [x] `.env.example`
- [x] SQLite persistence
- [x] durable scheduled jobs
- [x] idempotency key persistence
- [x] review gate
- [x] platform constraints
- [x] mock X/LinkedIn adapters
- [x] real Telegram adapter
- [x] test suite
- [x] evidence plan
- [ ] Attach terminal/Swagger screenshots from a final local acceptance run
