import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.adapters import get_publisher
from app.adapters.base import PublishResult
from app.database import get_db


async def execute_publish(variant_id: int, idempotency_key: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publish_history WHERE idempotency_key = ?", (idempotency_key,))
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {"status": "already_processed", "data": dict(existing)}

    cursor.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
    variant = cursor.fetchone()
    if not variant:
        conn.close()
        raise ValueError(f"Variant {variant_id} not found.")
    if variant["status"] != "approved":
        conn.close()
        raise PermissionError(f"Variant not approved (status='{variant['status']}'). Please approve first.")

    try:
        publisher = get_publisher(variant["platform"])
        result: PublishResult = await publisher.publish(
            content=variant["content"], idempotency_key=idempotency_key
        )
        if result.success:
            cursor.execute(
                "INSERT INTO publish_history (variant_id, platform, idempotency_key, status, live_post_id) VALUES (?, ?, ?, 'published', ?)",
                (variant_id, variant["platform"], idempotency_key, result.post_id),
            )
            cursor.execute("UPDATE variants SET status = 'published' WHERE id = ?", (variant_id,))
            conn.commit()
            return {"status": "success", "platform": variant["platform"], "post_id": result.post_id, "url": result.url, "message": result.message}

        cursor.execute(
            "INSERT INTO publish_history (variant_id, platform, idempotency_key, status, error_message) VALUES (?, ?, ?, 'failed', ?)",
            (variant_id, variant["platform"], idempotency_key, result.message),
        )
        conn.commit()
        return {"status": "failed", "platform": variant["platform"], "message": result.message}
    finally:
        conn.close()


def enqueue_publish(variant_id: int, idempotency_key: str, scheduled_at: datetime) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM publish_jobs WHERE idempotency_key = ?", (idempotency_key,))
        existing = cursor.fetchone()
        if existing:
            return {"status": "already_scheduled", "job": dict(existing)}

        cursor.execute(
            "INSERT INTO publish_jobs (variant_id, idempotency_key, scheduled_at) VALUES (?, ?, ?)",
            (variant_id, idempotency_key, scheduled_at.astimezone(timezone.utc).isoformat()),
        )
        conn.commit()
        cursor.execute("SELECT * FROM publish_jobs WHERE id = ?", (cursor.lastrowid,))
        return {"status": "scheduled", "job": dict(cursor.fetchone())}
    finally:
        conn.close()


def _claim_due_job() -> Optional[Dict[str, Any]]:
    conn = get_db()
    cursor = conn.cursor()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            "SELECT * FROM publish_jobs WHERE status = 'scheduled' AND scheduled_at <= ? ORDER BY scheduled_at LIMIT 1",
            (now,),
        )
        job = cursor.fetchone()
        if not job:
            return None
        cursor.execute(
            "UPDATE publish_jobs SET status = 'processing', attempts = attempts + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'scheduled'",
            (job["id"],),
        )
        conn.commit()
        return dict(job)
    finally:
        conn.close()


async def process_due_jobs() -> int:
    processed = 0
    while True:
        job = _claim_due_job()
        if not job:
            break
        try:
            result = await execute_publish(job["variant_id"], job["idempotency_key"])
            conn = get_db()
            conn.execute(
                "UPDATE publish_jobs SET status = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                ("completed" if result["status"] in {"success", "already_processed"} else "failed", result.get("message"), job["id"]),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            conn = get_db()
            conn.execute(
                "UPDATE publish_jobs SET status = 'scheduled', last_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(exc), job["id"]),
            )
            conn.commit()
            conn.close()
        processed += 1
    return processed


async def scheduler_worker(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        await process_due_jobs()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass
