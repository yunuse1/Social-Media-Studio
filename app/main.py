import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, status

from app.ai_models import AIGenerateRequest
from app.database import get_db, init_db
from app.models import PostIngestRequest, PostResponse, PublishHistoryResponse, ScheduleRequest, VariantResponse, VariantStatus
from app.services.ai_generator import generate_ai_variants
from app.services.generator import generate_platform_variants
from app.services.scheduler import enqueue_publish, execute_publish, scheduler_worker
from app.services.validator import ValidationError, validate_variant_constraints
from dotenv import load_dotenv

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop_event = asyncio.Event()
    worker = asyncio.create_task(scheduler_worker(stop_event))
    app.state.scheduler_stop_event = stop_event
    app.state.scheduler_task = worker
    try:
        yield
    finally:
        stop_event.set()
        await worker


app = FastAPI(
    title="Social Media Studio API",
    description="Multi-platform campaign publishing with durable scheduling, idempotency, and optional AI-assisted content generation.",
    version="1.2.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "Social Media Studio", "scheduler": "running"}


@app.post("/posts/ingest", response_model=PostResponse, status_code=status.HTTP_201_CREATED, tags=["Posts"])
def ingest_post(payload: PostIngestRequest):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (title, content, source_url) VALUES (?, ?, ?)", (payload.title, payload.content, payload.source_url))
    post_id = cursor.lastrowid
    for platform, variant_text in generate_platform_variants(payload.title, payload.content).items():
        cursor.execute("INSERT INTO variants (post_id, platform, content, status) VALUES (?, ?, ?, 'draft')", (post_id, platform, variant_text))
    conn.commit()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()
    conn.close()
    return dict(post)


@app.post("/ai/generate", tags=["AI"])
def generate_ai_content(payload: AIGenerateRequest):
    try:
        result = generate_ai_variants(payload.title, payload.content)
        return result.model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"error": "AIConfigurationError", "message": str(exc)})
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"error": "AIOutputValidationError", "message": str(exc)})
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": "AIProviderError", "message": str(exc)})


@app.post("/variants/validate", tags=["Variants"])
def validate_custom_variant(platform: str, content: str, tone: str | None = None):
    try:
        validate_variant_constraints(platform, content, tone)
        return {"valid": True, "platform": platform, "length": len(content), "tone": tone}
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail={"error": "ConstraintViolation", "message": str(exc)})


@app.get("/posts/{post_id}/variants", response_model=List[VariantResponse], tags=["Variants"])
def list_variants_by_post(post_id: int):
    conn = get_db()
    rows = conn.execute("SELECT * FROM variants WHERE post_id = ?", (post_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.patch("/variants/{variant_id}/status", response_model=VariantResponse, tags=["Review Workflow"])
def update_variant_status(variant_id: int, new_status: VariantStatus):
    conn = get_db()
    variant = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    if not variant:
        conn.close()
        raise HTTPException(status_code=404, detail="Variant not found")
    conn.execute("UPDATE variants SET status = ? WHERE id = ?", (new_status.value, variant_id))
    conn.commit()
    updated = conn.execute("SELECT * FROM variants WHERE id = ?", (variant_id,)).fetchone()
    conn.close()
    return dict(updated)


@app.post("/publish/schedule", tags=["Publishing"])
async def schedule_or_publish(payload: ScheduleRequest):
    # Explicit scheduled_at means "create a durable job". Immediate publishing
    # is available by omitting scheduled_at entirely.
    if payload.scheduled_at is not None:
        scheduled_at = payload.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        try:
            return enqueue_publish(payload.variant_id, payload.idempotency_key, scheduled_at)
        except Exception as exc:
            raise HTTPException(status_code=400, detail={"error": str(exc)})

    try:
        return await execute_publish(payload.variant_id, payload.idempotency_key)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"error": str(exc)})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"error": str(exc)})
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"error": str(exc)})


@app.get("/publish/jobs", tags=["Publishing"])
def get_publish_jobs():
    conn = get_db()
    rows = conn.execute("SELECT * FROM publish_jobs ORDER BY scheduled_at ASC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/publish/history", response_model=List[PublishHistoryResponse], tags=["Publishing"])
def get_publish_history():
    conn = get_db()
    rows = conn.execute("SELECT * FROM publish_history ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]
