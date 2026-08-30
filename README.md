# Social Media Studio

A backend service for turning one source post into platform-specific social content, reviewing the generated variants, scheduling approved content, and publishing through swappable platform adapters.

**Built for:** backend engineers and content teams who need a reliable API workflow around social-media content generation rather than an AI-only text generator.

The project combines deterministic backend logic with an optional Gemini generation layer. AI output is treated as untrusted input: it is structured, validated, checked against platform constraints, and requires human approval before publishing.

## What it does

- Ingests source posts and stores them in SQLite
- Generates deterministic X, LinkedIn, and Telegram variants
- Optionally generates platform-specific variants with Gemini via `POST /ai/generate`
- Grounds AI generation in the supplied source content
- Validates structured AI output with Pydantic
- Enforces platform constraints such as length, hashtag count, and tone
- Supports human review: `draft → approved/rejected → published`
- Uses a `SocialPublisher` adapter interface
- Provides mock X and LinkedIn publishers
- Provides a real Telegram Bot API publisher
- Persists publish jobs in SQLite
- Runs scheduled jobs through a background worker
- Uses idempotency keys to make publishing retry-safe
- Exposes publish history and job inspection endpoints
- Records AI token usage and configurable cost estimates

## Architecture

```text
                         Client / Postman
                                |
                                v
                             FastAPI
                                |
              +-----------------+------------------+
              |                                    |
              v                                    v
        /posts/ingest                         /ai/generate
              |                                    |
              v                                    v
          SQLite DB <-------------------------- Gemini
              |                                    |
              |                             structured variants
              |                                    |
              +-------------------------> deterministic validator
                                                   |
                                                   v
                                             human approval
                                                   |
                                                   v
                                        publish job in SQLite
                                                   |
                                                   v
                                           Scheduler Worker
                                                   |
                                                   v
                                          SocialPublisher
                                      /        |          \
                                   Mock X  Mock LinkedIn  Telegram
```

The LLM is deliberately optional. The deterministic generator and publishing pipeline remain usable when the AI provider is unavailable.

## Requirements

- Python 3.11+ recommended
- `pip`
- No external database is required for local development; SQLite is used by default
- Gemini API access is optional. Mock publishers do not require social-platform credentials.

## Run locally

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

If PowerShell blocks script activation, run the equivalent activation command from Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then open Swagger UI at:

`http://127.0.0.1:8000/docs`

For the grader manifest, use:

```bash
uvicorn app.main:app --port 8000
```

Optional sample data can be created with:

```bash
python -m app.seed
```

## Gemini configuration

Copy `.env.example` to `.env` and set:

```text
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_INPUT_COST_PER_MILLION=0
GEMINI_OUTPUT_COST_PER_MILLION=0
```

The model and pricing are environment variables rather than hard-coded application values.

### AI endpoint

`POST /ai/generate`

Example request:

```json
{
  "title": "AI in Backend Engineering",
  "content": "Reliable backend systems need validation, persistence, testing, and safe failure handling."
}
```

The response contains structured variants for X, LinkedIn, and Telegram together with model/token/cost metadata. The generated content then passes through the same deterministic constraint engine used by the rest of the application.

## End-to-end usage

A reviewer can reproduce the main workflow in Swagger UI or Postman:

1. **Ingest a source post** with `POST /posts/ingest`.
2. **Generate variants** with `POST /ai/generate` (or use the deterministic path without Gemini).
3. **Inspect variants** with `GET /posts/{post_id}/variants`.
4. **Approve a variant** with `PATCH /variants/{variant_id}/status?new_status=approved`.
5. **Schedule publishing** with `POST /publish/schedule` and a unique idempotency key.
6. **Let the worker process the due job.**
7. **Inspect jobs** with `GET /publish/jobs`.
8. **Inspect delivery history** with `GET /publish/history`.

For immediate publishing, omit `scheduled_at` where supported by the endpoint contract.

### Telegram publishing

For real Telegram delivery, configure:

```text
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

X and LinkedIn use mock adapters in this capstone so the adapter architecture can be demonstrated without requiring third-party production credentials.

## v2 Evaluation Results

Five representative source-content cases were generated with the real Gemini integration and evaluated with the deterministic evaluator in `evaluation/evaluate_ai.py`.

| Metric | Result |
|---|---:|
| Evaluation cases | **5** |
| Cases passed | **5/5** |
| Overall pass rate | **100%** |
| Three variants per case | **5/5** |
| All supported platforms present | **5/5** |
| Structured fields valid | **5/5** |
| Platform constraints valid | **5/5** |
| Source content present | **5/5** |

The evaluation intentionally measures deterministic structural and platform constraints instead of inventing an automated semantic-quality score. Writing quality, factual accuracy, and hallucination risk still require human review.

Evaluation inputs are stored in `evaluation/eval_cases.json`; the evaluator is `evaluation/evaluate_ai.py`. Generated `evaluation/eval_results.json` is local evaluation output and is not required in the repository.

## Tests

Run the automated test suite with:

```bash
pytest -q
```

The tests cover platform constraint and tone enforcement, review gating, idempotency, durable scheduling, worker processing, publisher adapter contracts, and the Gemini generator contract without making a real LLM API call.

## Reliability and safety decisions

### Human approval before publishing

AI-generated content never goes directly from generation to publishing. A variant must pass deterministic validation and then be explicitly approved. This keeps the model out of the final authorization step.

### Idempotent publishing

Every publish job has a unique idempotency key persisted in SQLite. Before an adapter is called, the worker checks publish history for the same key. This makes retries and process restarts safer and prevents an intentional duplicate publish for the same job key.

### Restart-safe scheduling

Scheduled jobs are persisted rather than kept only in process memory. If the API process restarts, pending jobs remain in SQLite and can be picked up by the worker.

## Known limitations

- The scheduler is an in-process worker backed by durable SQLite state. A multi-instance production deployment would need a shared database and distributed job claiming.
- Telegram requires valid bot credentials and a reachable chat for real delivery.
- X and LinkedIn are mock adapters in this capstone; real production API integrations are not implemented.
- AI-generated variants are not automatically published; human approval is intentionally required.
- Automated AI evaluation checks deterministic structure and platform constraints. Semantic quality, factual accuracy, and hallucination detection are not fully automated.
- SQLite is appropriate for this capstone and local deployment, but a production-scale system would likely use a server database and stronger operational observability.

## Demo

The required demo is a live end-to-end walkthrough rather than a slide presentation. It demonstrates source ingestion, AI generation, validation, human approval, scheduling/background processing, and publish history.

The recording also explains:

- **Design decision:** AI generation is optional and sits behind deterministic validation and human approval, so the core workflow does not depend on successful LLM output.
- **Limitation:** the scheduler is an in-process worker with SQLite, which is restart-safe for a single instance but is not a distributed production job system.

The final submission should use an **unlisted YouTube link** for the 3–5 minute recording.

## AI Transparency Disclosure

Gemini was used for the optional platform-specific content generation step exposed by `/ai/generate`. The surrounding application logic—source ingestion, database persistence, Pydantic schemas, deterministic platform constraints, human approval, scheduling, worker processing, idempotency, publish history, and the `SocialPublisher` adapter contract—remains application logic rather than model-generated authorization.

AI output is treated as untrusted input: it is structured, validated against the source content, checked against platform constraints, and still requires human approval before publishing.

## Project structure

```text
app/                    # FastAPI application and domain logic
evaluation/             # v2 evaluation cases and deterministic evaluator
tests/                  # automated tests
.env.example            # environment variable template
requirements.txt        # Python dependencies
```
