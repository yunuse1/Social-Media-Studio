from fastapi import FastAPI, HTTPException, status, Query
from contextlib import asynccontextmanager
from typing import List, Optional

from app.database import init_db, get_db
from app.models import (
    PostIngestRequest, PostResponse, 
    VariantResponse, VariantStatus, 
    ScheduleRequest, PublishHistoryResponse
)
from app.services.generator import generate_platform_variants
from app.services.validator import validate_variant_constraints, ValidationError
from app.services.scheduler import execute_publish

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Social Media Studio API",
    description="Multi-platform campaign publishing system with durable scheduling and idempotency guarantees.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Social Media Studio"}

@app.post("/posts/ingest", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Posts"])
def ingest_post(payload: PostIngestRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO posts (title, content, source_url) VALUES (?, ?, ?)",
        (payload.title, payload.content, payload.source_url)
    )
    post_id = cursor.lastrowid
    
    variants = generate_platform_variants(payload.title, payload.content)
    for platform, variant_text in variants.items():
        cursor.execute(
            "INSERT INTO variants (post_id, platform, content, status) VALUES (?, ?, ?, 'draft')",
            (post_id, platform, variant_text)
        )
    
    conn.commit()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()
    
    return dict(post)

@app.post("/variants/validate", tags=["Variants"])
def validate_custom_variant(platform: str, content: str):
    try:
        validate_variant_constraints(platform, content)
        return {"valid": True, "platform": platform, "length": len(content)}
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "ConstraintViolation", "message": str(e)}
        )

@app.get("/posts/{post_id}/variants", response_model=List[VariantResponse], tags=["Variants"])
def list_variants_by_post(post_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM variants WHERE post_id = ?", (post_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.patch("/variants/{variant_id}/status", response_model=VariantResponse, tags=["Review Workflow"])
def update_variant_status(variant_id: int, new_status: VariantStatus):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
    variant = cursor.fetchone()
    
    if not variant:
        conn.close()
        raise HTTPException(status_code=404, detail="Variant not found")

    cursor.execute("UPDATE variants SET status = ? WHERE id = ?", (new_status.value, variant_id))
    conn.commit()
    
    cursor.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

@app.post("/publish/schedule", tags=["Publishing"])
async def schedule_or_publish(payload: ScheduleRequest):
    try:
        result = await execute_publish(
            variant_id=payload.variant_id, 
            idempotency_key=payload.idempotency_key
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"error": str(e)})
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": str(e)})
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": str(e)})

@app.get("/publish/history", response_model=List[PublishHistoryResponse], tags=["Publishing"])
def get_publish_history():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM publish_history ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]