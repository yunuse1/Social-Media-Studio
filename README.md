# Social Media Studio

A FastAPI backend for ingesting posts, generating platform-specific variants, reviewing them, scheduling approved variants, and publishing through swappable social-platform adapters. It also includes an optional Gemini content-generation layer that produces structured variants before deterministic validation and human approval.

## What is implemented

- Post ingestion with SQLite persistence
- Deterministic X, LinkedIn, and Telegram variants
- Optional structured Gemini generation through `/ai/generate`
- LLM output grounded to the supplied source content
- Pydantic validation of structured AI output
- Platform constraint validation: length, hashtag count, and tone
- Human review workflow: draft → approved/rejected → published
- `SocialPublisher` adapter interface
- Mock X and LinkedIn publishers
- Real Telegram Bot API publisher
- Durable SQLite-backed publish jobs
- Background scheduler with persisted jobs
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
       +--> /ai/generate --> Gemini --> structured variants
       |                            |
       |                            v
       +----------------------> constraint validator
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

The LLM is deliberately optional. The deterministic generator and publishing pipeline remain available, so an AI-provider failure does not replace the capstone's core reliability path.

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

For the grader manifest, the equivalent command is `uvicorn app.main:app --port 8000`; sample data can be created with `python -m app.seed`.

## AI configuration

Set the following values in `.env` to use Gemini:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_INPUT_COST_PER_MILLION=0
GEMINI_OUTPUT_COST_PER_MILLION=0
```

The model and pricing are configured through environment variables rather than hard-coded values.

### AI endpoint

`POST /ai/generate`

```json
{
  "title": "AI in Backend Engineering",
  "content": "A source article about reliable backend engineering..."
}
```

The response contains one structured variant for X, LinkedIn, and Telegram plus model/token/cost metadata. The generated text is passed through the same deterministic platform constraint engine used by the rest of the application.

## v2 Evaluation Results

Five representative source-content cases were generated with the real Gemini integration and evaluated with the deterministic evaluator in `evaluation/evaluate_ai.py`.

| Metric | Result |
|---|---:|
| Evaluation cases | **5** |
| Cases passed | **5/5** |
| Overall pass rate | **100%** |
| Three variants per case | 5/5 |
| All supported platforms present | 5/5 |
| Structured fields valid | 5/5 |
| Platform constraints valid | 5/5 |
| Source content present | 5/5 |

The evaluation intentionally reports deterministic structural and platform constraints rather than inventing an automated semantic-quality score. Writing quality, factual accuracy, and hallucination risk still require human review.

Evaluation inputs are stored in `evaluation/eval_cases.json`; the evaluator is `evaluation/evaluate_ai.py`. Generated `evaluation/eval_results.json` is local evaluation output and is not required in the repository.

## AI Transparency Disclosure

Gemini was used for the optional platform-specific content generation step exposed by `/ai/generate`. The application logic around source ingestion, database persistence, Pydantic schemas, deterministic platform constraints, human approval, scheduling, worker processing, idempotency, publish history, and the `SocialPublisher` adapter contract was implemented as application logic rather than delegated to the model. AI output is treated as untrusted input: it is structured, validated against the source content, checked against platform constraints, and still requires human approval before publishing.

## Demo flow

1. `POST /posts/ingest` with a title and content.
2. `POST /ai/generate` to create AI-assisted variants from the same source content.
3. `GET /posts/{post_id}/variants` and select a variant.
4. `PATCH /variants/{variant_id}/status?new_status=approved`.
5. `POST /publish/schedule` with an idempotency key and a future `scheduled_at`.
6. The durable worker claims the job when it becomes due.
7. `GET /publish/jobs` shows scheduled/processing/completed jobs.
8. `GET /publish/history` shows the final delivery record.

For an immediate publish, omit `scheduled_at`.

## Idempotency and restart safety

Every publish job has a unique idempotency key persisted in SQLite. The worker checks `publish_history` before calling an adapter, so a retry or process restart cannot intentionally create a second publish for the same key. Scheduled jobs remain persisted while the API process is down and are picked up after restart.

## Telegram

Set the following values in `.env` before using the Telegram adapter:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

Mock adapters require no external credentials.

## Tests

```bash
pytest -q
```

The test suite covers platform constraint/tone enforcement, review gating, idempotency, durable scheduling, worker processing, adapter contracts, and the Gemini AI generator contract without making a real LLM API call.

## Known Limitations

- The scheduler is an in-process worker backed by durable SQLite state; multi-instance production deployment would need a shared database plus distributed job claiming.
- Telegram requires valid bot credentials and a reachable chat for real delivery.
- X and LinkedIn are intentionally mock adapters for the capstone's adapter abstraction demonstration.
- AI-generated variants are not automatically published; human approval remains an explicit step.
- Automated AI evaluation checks deterministic constraints; semantic quality and hallucination detection are not fully automated.
