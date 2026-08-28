import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import main
from app.adapters import get_publisher
from app.database import get_db, init_db
from app.services.scheduler import enqueue_publish, process_due_jobs


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "acceptance.sqlite3"
    monkeypatch.setattr("app.database.DB_FILE", str(db_file))
    import sqlite3

    def test_get_db():
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr("app.database.get_db", test_get_db)
    monkeypatch.setattr("app.services.scheduler.get_db", test_get_db)
    init_db()
    with TestClient(main.app) as test_client:
        yield test_client


def create_approved_variant(client):
    response = client.post(
        "/posts/ingest",
        json={
            "title": "Acceptance test post",
            "content": "This is sufficiently long content for the acceptance test.",
            "source_url": "https://example.com/test",
        },
    )
    assert response.status_code == 201
    post_id = response.json()["id"]
    variants = client.get(f"/posts/{post_id}/variants")
    assert variants.status_code == 200
    variant_id = variants.json()[0]["id"]
    approved = client.patch(f"/variants/{variant_id}/status?new_status=approved")
    assert approved.status_code == 200
    return variant_id


def test_review_gate_blocks_unapproved_publish(client):
    response = client.post(
        "/posts/ingest",
        json={
            "title": "Review gate test",
            "content": "This content is long enough for the review gate test.",
        },
    )
    variant_id = client.get(f"/posts/{response.json()['id']}/variants").json()[0]["id"]
    publish = client.post(
        "/publish/schedule",
        json={"variant_id": variant_id, "idempotency_key": "review-gate-001"},
    )
    assert publish.status_code == 403


def test_idempotency_prevents_duplicate_publish(client):
    variant_id = create_approved_variant(client)
    payload = {"variant_id": variant_id, "idempotency_key": "idem-test-001"}
    first = client.post("/publish/schedule", json=payload)
    second = client.post("/publish/schedule", json=payload)
    assert first.status_code == 200
    assert first.json()["status"] == "success"
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"
    history = client.get("/publish/history")
    assert history.status_code == 200
    assert len([x for x in history.json() if x["idempotency_key"] == "idem-test-001"]) == 1


def test_scheduling_persists_future_job(client):
    variant_id = create_approved_variant(client)
    scheduled_at = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
    response = client.post(
        "/publish/schedule",
        json={
            "variant_id": variant_id,
            "scheduled_at": scheduled_at,
            "idempotency_key": "schedule-test-001",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"
    jobs = client.get("/publish/jobs").json()
    job = next(job for job in jobs if job["idempotency_key"] == "schedule-test-001")
    assert job["status"] == "scheduled"
    assert job["variant_id"] == variant_id


def test_due_job_is_processed_by_worker(client):
    variant_id = create_approved_variant(client)

    # The API intentionally publishes immediately for past timestamps.
    # To test the worker itself, enqueue a future job first, then move its
    # persisted schedule into the past and let the worker claim it.
    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    result = enqueue_publish(variant_id, "worker-test-001", scheduled_at)
    assert result["status"] == "scheduled"

    conn = get_db()
    conn.execute(
        "UPDATE publish_jobs SET scheduled_at = ? WHERE idempotency_key = ?",
        ((datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(), "worker-test-001"),
    )
    conn.commit()
    conn.close()

    processed = asyncio.run(process_due_jobs())
    assert processed >= 1
    jobs = client.get("/publish/jobs").json()
    job = next(job for job in jobs if job["idempotency_key"] == "worker-test-001")
    assert job["status"] == "completed"


def test_adapter_swap_contract():
    x = get_publisher("x")
    linkedin = get_publisher("linkedin")
    telegram = get_publisher("telegram")
    assert x.__class__.__name__ == "MockXPublisher"
    assert linkedin.__class__.__name__ == "MockLinkedInPublisher"
    assert telegram.__class__.__name__ == "TelegramPublisher"
