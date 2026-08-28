# Acceptance Evidence

This file records the acceptance scenarios and the final AI verification evidence for the Social Media Studio capstone.

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

## Probe 6 — Real Gemini generation

The optional AI endpoint was manually verified through FastAPI's `/ai/generate` endpoint with the configured Gemini environment variables.

Verified model:

```text
GEMINI_MODEL=gemini-3.1-flash-lite
```

A successful request returned HTTP **202** and produced exactly three structured variants:

- X
- LinkedIn
- Telegram

The successful response included:

```text
Input tokens: 177
Output tokens: 207
Model: gemini-3.1-flash-lite
Estimated cost: 0 USD
```

The zero cost is the value configured in the local cost-tracking environment variables, not a provider-pricing claim.

## Probe 7 — V2 AI evaluation

Five representative cases were generated using the real Gemini integration and evaluated with `evaluation/evaluate_ai.py`.

| Metric | Result |
|---|---:|
| Evaluation cases | 5 |
| Cases passed | **5/5** |
| Overall pass rate | **100%** |
| Exactly three variants | 5/5 |
| All supported platforms present | 5/5 |
| Structured fields valid | 5/5 |
| Platform constraints valid | 5/5 |
| Source content present | 5/5 |

Case results:

```text
PASS backend-ai
PASS product-launch
PASS technical-update
PASS engineering-practice
PASS remote-collaboration
```

The evaluator intentionally measures deterministic structural and platform constraints. It does not claim to automatically measure semantic quality or hallucination risk.

## Reproducibility

Evaluation inputs are committed in:

```text
evaluation/eval_cases.json
```

The evaluator is:

```text
evaluation/evaluate_ai.py
```

`evaluation/eval_results.json` is generated locally from live model calls and is intentionally not required in the repository.

## Submission checklist

- [x] README with architecture, run steps, demo flow, AI configuration, evaluation results, and limitations
- [x] `.env.example`
- [x] SQLite persistence
- [x] durable scheduled jobs
- [x] idempotency key persistence
- [x] review gate
- [x] platform constraints
- [x] mock X/LinkedIn adapters
- [x] real Telegram adapter
- [x] Gemini AI generation
- [x] Gemini-focused unit tests
- [x] five-case AI evaluation
- [x] evidence plan
- [ ] Attach terminal/Swagger screenshots from a final local acceptance run

## Limitations

- The scheduler is an in-process worker backed by durable SQLite state; multi-instance production deployment would need a shared database plus distributed job claiming.
- X and LinkedIn are mock adapters for the capstone's adapter abstraction demonstration.
- Telegram requires valid bot credentials and a reachable chat for real delivery.
- AI-generated variants are not automatically published; human approval remains an explicit step.
- Automated AI evaluation checks deterministic constraints; semantic quality and hallucination detection still require human review.
