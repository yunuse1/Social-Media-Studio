# Build Log

## Capstone completion pass

- Reviewed the repository against the current Social Media Studio brief.
- Added a durable `publish_jobs` SQLite table with a unique idempotency key and indexed due-job lookup.
- Added an in-process background worker that polls persisted jobs and resumes them after API restart.
- Changed `/publish/schedule` so future `scheduled_at` values create durable jobs instead of publishing immediately.
- Preserved immediate publishing when `scheduled_at` is omitted or already due.
- Kept the publish-history idempotency guard before adapter calls.
- Added platform tone constraints alongside length and hashtag constraints.
- Added validator tests and acceptance evidence documentation.
- Added a complete README with architecture, local setup, demo flow, idempotency explanation, and known limitations.

## Verification note

The final local acceptance run should be performed with the repository checked out at the latest commit. Record the actual terminal/Swagger outputs and screenshots in the submission evidence rather than claiming a test was run when it was not.
