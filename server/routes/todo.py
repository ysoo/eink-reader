"""
Todo routes:
  GET    /api/todo            — return todo list as JSON (for dashboard)
  POST   /api/todo            — replace todo list (from dashboard)
  POST   /api/todo/braindump  — freeform text → Azure OpenAI → structured todos
  POST   /api/todo/sync       — receive device todo.txt, merge, store
"""

import json
import logging
import os
import time
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import storage
from routes.queue import enqueue

router = APIRouter(prefix="/api/todo")
logger = logging.getLogger("eink.todo")

_BLOB       = "todo_sync.txt"
_MAX_ITEMS  = 60
_MAX_TEXT   = 43


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _read_items() -> list[dict]:
    """Load todo items from Blob Storage. Returns [] if not found."""
    try:
        raw = storage.download(_BLOB).decode()
        items = []
        for line in raw.splitlines():
            if "|" in line:
                status, text = line.split("|", 1)
                items.append({"text": text.strip(), "done": status == "1"})
        return items
    except Exception:
        return []


def _write_items(items: list[dict]) -> None:
    lines = [
        "{flag}|{text}".format(flag="1" if i["done"] else "0", text=i["text"][:_MAX_TEXT])
        for i in items[:_MAX_ITEMS]
    ]
    storage.upload(_BLOB, "\n".join(lines).encode(), content_type="text/plain")


def _merge(server_items: list[dict], device_lines: list[str]) -> list[dict]:
    """
    Merge device todo.txt lines into the server list.
    Server is authoritative for text and order; device wins for done status.
    """
    device_done = {}
    for line in device_lines:
        if "|" in line:
            status, text = line.split("|", 1)
            device_done[text.strip()] = (status == "1")

    return [
        {"text": item["text"], "done": device_done.get(item["text"], item["done"])}
        for item in server_items
    ]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("")
def get_todo():
    return _read_items()


class TodoList(BaseModel):
    items: list[dict]

@router.post("")
def set_todo(body: TodoList):
    _write_items(body.items)
    return {"ok": True, "count": len(body.items)}


class BrainDump(BaseModel):
    text: str

@router.post("/braindump")
def braindump(body: BrainDump):
    logger.info("braindump: %d chars received", len(body.text))
    t0 = time.monotonic()
    items = _call_openai(body.text)
    logger.info("openai call took %.0fms, %d items", (time.monotonic() - t0) * 1000, len(items))
    _write_items(items)
    enqueue({"type": "todo", "name": "todo_sync.txt", "url": storage.sas_url(_BLOB)})
    return {"items": items}


@router.post("/queue")
def queue_todo():
    """Queue the current todo list for device delivery."""
    enqueue({"type": "todo", "name": "todo_sync.txt", "url": storage.sas_url(_BLOB)})
    logger.info("todo queued")
    return {"ok": True}


@router.post("/sync")
async def sync_from_device(request: Request):
    raw = await request.body()
    device_lines = raw.decode("utf-8", errors="replace").splitlines()
    server_items = _read_items()
    merged = _merge(server_items, device_lines)
    _write_items(merged)
    logger.info("todo sync: device sent %d lines, merged to %d items",
                len(device_lines), len(merged))
    return {"ok": True, "count": len(merged)}


# ---------------------------------------------------------------------------
# Azure OpenAI
# ---------------------------------------------------------------------------

def _call_openai(brain_dump: str) -> list[dict]:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_KEY"],
        api_version="2024-02-01",
    )
    system = (
        "Convert the following brain dump into a concise todo list. "
        "One item per line. Max 43 characters per item. "
        "Return only the list, no numbering, no extra text."
    )
    resp = client.chat.completions.create(
        model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": brain_dump},
        ],
        max_tokens=512,
        temperature=0.3,
    )
    lines = resp.choices[0].message.content.strip().splitlines()
    return [
        {"text": line.strip()[:_MAX_TEXT], "done": False}
        for line in lines
        if line.strip()
    ][:_MAX_ITEMS]
