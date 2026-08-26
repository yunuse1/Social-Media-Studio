# Social Media Studio

A FastAPI backend for ingesting a post, generating platform variants, reviewing them, scheduling approved variants, and publishing through swappable social-platform adapters.

## What is implemented

- Post ingestion with SQLite persistence
- Deterministic X, LinkedIn, and Telegram variants
- Platform constraint validation: length, hashtag count, and tone
- Human review workflow: draft → approved/rejected → published
- `SocialPublisher` adapter interface
- Mock X and LinkedIn publishers
- Real Telegram Bot API publisher
- Durable SQLite-backed publish jobs
- Background scheduler that survives API process restarts because scheduled jobs are persisted in SQLite
- Idempotent publishing using a unique `idempotency_key`
- Publish history and job inspection endpoints

## Architecture

```text
Client
  |
  v
FastAPI
  |
  +--> SQLite: posts / variants / publish_jobs / publish_history
  |
  +--> Generator --> platform variants --> review/approval
  |
  +--> Scheduler Worker --> SocialPublisher
                              |-- Mock X
                              |-- Mock LinkedIn
                              `-- Telegram Bot API
```

## Run locally

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

uvicorn app.main:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs`.

## Demo flow

1. `POST /posts/ingest` with a title and content.
2. `GET /posts/{post_id}/variants` and select a variant.
3. `PATCH /variants/{variant_id}/status?new_status=approved`.
4. `POST /publish/schedule` with an idempotency key and a future `scheduled_at`.
5. The durable worker claims the job when it becomes due.
6. `GET /publish/jobs` shows scheduled/processing/completed jobs.
7. `GET /publish/history` shows the final delivery record.

For an immediate publish, omit `scheduled_at`.

## Idempotency and restart safety

Every publish job has a unique idempotency key persisted in SQLite. The worker checks `publish_history` before calling an adapter, so a retry or process restart cannot intentionally create a second publish for the same key. Scheduled jobs remain in `publish_jobs` while the API process is down and are picked up after restart.

## Telegram

Set the values in `.env` before using the Telegram adapter:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Mock adapters require no external credentials.

## Tests

```bash
pytest -q
```

The test suite includes platform constraint and tone enforcement. The acceptance probes documented in `EVIDENCE.md` cover the end-to-end scheduling, approval, idempotency, and adapter-swap scenarios.

## Known limitations

- The scheduler is an in-process worker backed by durable SQLite state; for multi-instance production deployment, a shared database plus a distributed job-claim mechanism would be appropriate.
- Telegram requires valid bot credentials and a reachable chat for a real external delivery.
- X and LinkedIn are intentionally mock adapters for the capstone's adapter abstraction demonstration.
