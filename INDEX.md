# Social Media Studio — Final Deliverables Index

This index collects the final capstone deliverables and supporting evidence in one place.

| Deliverable | Purpose |
|---|---|
| [README.md](README.md) | Project overview, architecture, setup, demo flow, AI evaluation, transparency, and limitations |
| [capstone.yaml](capstone.yaml) | Grader manifest with run, seed, test, base URL, and acceptance endpoints |
| [EVIDENCE.md](EVIDENCE.md) | Acceptance probes, real Telegram delivery, Swagger screenshots, and AI evaluation evidence |
| [BUILDLOG.md](BUILDLOG.md) | Implementation/build history and verification notes |
| [.env.example](.env.example) | Required environment variable template |
| [evaluation/eval_cases.json](evaluation/eval_cases.json) | Reproducible AI evaluation inputs |
| [evaluation/evaluate_ai.py](evaluation/evaluate_ai.py) | Deterministic AI evaluation script |
| [tests/](tests/) | Automated unit and acceptance tests |
| [screenshot/](screenshot/) | Final Swagger and Telegram delivery screenshots |

## Core workflow

`ingest → generate variants → validate → human approval → schedule → worker → publish → history`

## AI workflow

`source content → Gemini → structured variants → deterministic validation → human approval`

## Final verification

- Full local test suite: passed
- Gemini evaluation: **5/5 cases passed (100%)**
- Real Telegram delivery: verified end-to-end
- X and LinkedIn: intentionally mocked adapters
