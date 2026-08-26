import sqlite3
from typing import Dict, Any
from app.database import get_db
from app.adapters import get_publisher
from app.adapters.base import PublishResult

async def execute_publish(variant_id: int, idempotency_key: str) -> Dict[str, Any]:
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM publish_history WHERE idempotency_key = ?",
        (idempotency_key,)
    )
    existing_record = cursor.fetchone()
    if existing_record:
        conn.close()
        return {
            "status": "already_processed",
            "message": "This operation was performed before (Idempotent response).",
            "data": dict(existing_record)
        }

    cursor.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
    variant = cursor.fetchone()
    if not variant:
        conn.close()
        raise ValueError(f"Variant {variant_id} not found.")

    if variant["status"] != "approved":
        conn.close()
        raise PermissionError(f"Variant not approved (status='{variant['status']}'). Please approve first.")

    platform = variant["platform"]
    content = variant["content"]

    publisher = get_publisher(platform)
    publish_res: PublishResult = await publisher.publish(content=content, idempotency_key=idempotency_key)

    try:
        if publish_res.success:
            cursor.execute("""
                INSERT INTO publish_history (variant_id, platform, idempotency_key, status, live_post_id)
                VALUES (?, ?, ?, 'published', ?)
            """, (variant_id, platform, idempotency_key, publish_res.post_id))
            
            cursor.execute("UPDATE variants SET status = 'published' WHERE id = ?", (variant_id,))
            conn.commit()
            
            return {
                "status": "success",
                "platform": platform,
                "post_id": publish_res.post_id,
                "url": publish_res.url,
                "message": publish_res.message
            }
        else:
            cursor.execute("""
                INSERT INTO publish_history (variant_id, platform, idempotency_key, status, error_message)
                VALUES (?, ?, ?, 'failed', ?)
            """, (variant_id, platform, idempotency_key, publish_res.message))
            conn.commit()
            
            return {
                "status": "failed",
                "platform": platform,
                "message": publish_res.message
            }
    finally:
        conn.close()