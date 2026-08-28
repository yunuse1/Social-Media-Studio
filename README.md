# Social Media Studio

A FastAPI backend for ingesting a post, generating platform-specific variants, reviewing them, scheduling approved variants, and publishing through swappable social-platform adapters. It also includes an optional LLM content-generation layer that produces structured variants before the existing deterministic validation and human-approval workflow.

## What is implemented

- Post ingestion with SQLite persistence
- Deterministic X, LinkedIn, and Telegram variants
- Optional structured LLM generation through `/ai/generate`
- LLM output grounded to the supplied source content
- Pydantic validation of structured AI output
- Platform constraint validation: length, hashtag count, and tone
- Human review workflow: draft → approved/rejected → published
- `SocialPublisher` adapter interface
- Mock X and LinkedIn publishers
- Real Telegram Bot API publisher
- Durable SQLite-backed publish jobs
- Background scheduler that survives API process restarts because scheduled jobs are persisted in SQLite
- Idempotent publishing using a unique `idempotency_key`
- Publish history and job inspection endpoints
- AI token-usage and configurable cost estimation

## Architecture

```text
Client / Postman
       |
       v
    FastAPI
       |
       +--> /ai/generate --> LLM --> structured variants
       |                              |
       |                              v
       +------------------------> constraint validator
                                      |
                                      v
                                human approval
                                      |
                                      v
       +--> SQLite: posts / variants / publish_jobs / publish_history
                                      |
                                      v
                               Scheduler Worker
                                      |
                                      v
                                SocialPublisher
                              /       |        \
                         Mock X   Mock LinkedIn  Telegram
```

The LLM is deliberately optional. The existing deterministic generator and publishing pipeline remain available, so an AI-provider failure does not replace the capstone's core reliability path.

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

## AI configuration

Set the following values in `.env` if you want to use the optional LLM endpoint:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_INPUT_COST_PER_MILLION=...
OPENAI_OUTPUT_COST_PER_MILLION=...
```

The model name and pricing are intentionally configured by environment variables rather than hard-coded, so the project does not assume a particular provider price or model availability.

### AI endpoint

`POST /ai/generate`

```json
{
  "title": "AI in Backend Engineering",
  "content": "A source article about reliable backend engineering..."
}
```

The response contains one structured variant for X, LinkedIn, and Telegram plus model/token/cost metadata. The generated text is validated against the same platform constraint engine used by the rest of the application.

## Demo flow

1. `POST /posts/ingest` with a title and content.
2. Optionally call `POST /ai/generate` to create AI-assisted platform variants from the same source content.
3. `GET /posts/{post_id}/variants` and select a variant.
4. `PATCH /variants/{variant_id}/status?new_status=approved`.
5. `POST /publish/schedule` with an idempotency key and a future `scheduled_at`.
6. The durable worker claims the job when it becomes due.
7. `GET /publish/jobs` shows scheduled/processing/completed jobs.
8. `GET /publish/history` shows the final delivery record.

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

The test suite covers platform constraint/tone enforcement, review gating, idempotency, durable scheduling, worker processing, adapter contracts, and the AI generator contract without making a real LLM API call.

## Known limitations

- The scheduler is an in-process worker backed by durable SQLite state; for multi-instance production deployment, a shared database plus a distributed job-claim mechanism would be appropriate.
- Telegram requires valid bot credentials and a reachable chat for a real external delivery.
- X and LinkedIn are intentionally mock adapters for the capstone's adapter abstraction demonstration.
- AI-generated variants are returned by `/ai/generate` but are not automatically published; human approval remains a separate explicit step.
