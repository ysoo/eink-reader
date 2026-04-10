"""
Device delivery queue.

The queue is stored in Blob Storage as queue.json — a JSON array of items:
  [{"type": "book", "name": "...", "url": "..."}, ...]

The Pico polls GET /api/queue, downloads each item, then calls
POST /api/queue/ack to clear the queue.
"""

import json
import logging
from fastapi import APIRouter

import storage

router = APIRouter(prefix="/api/queue")
logger = logging.getLogger("eink.queue")

_BLOB = "queue.json"


def _read() -> list[dict]:
    try:
        return json.loads(storage.download(_BLOB))
    except Exception:
        return []


def _write(items: list[dict]) -> None:
    storage.upload(_BLOB, json.dumps(items).encode(), content_type="application/json")


def enqueue(item: dict) -> None:
    """Add *item* to the queue (called by other routes, not the Pico)."""
    items = _read()
    deduped = any(i.get("name") == item.get("name") for i in items)
    items = [i for i in items if i.get("name") != item.get("name")]
    items.append(item)
    _write(items)
    logger.info("enqueue: %s %s%s", item.get("type"), item.get("name"),
                " (replaced duplicate)" if deduped else "")


@router.get("")
def get_queue():
    return _read()


@router.get("/ack")
@router.post("/ack")
def ack_queue():
    """Clear all pending items after the Pico has downloaded them."""
    items = _read()
    _write([])
    logger.info("queue ack: cleared %d items", len(items))
    return {"ok": True}
