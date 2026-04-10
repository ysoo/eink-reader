"""
Book routes:
  POST /api/books/upload          — accept epub or txt, convert, store in Blob
  GET  /api/books                 — list available books
  DELETE /api/books/{name}        — delete a book
  POST /api/books/{name}/queue    — add book to the device delivery queue
  GET  /api/books/jobs/{job_id}   — check upload job status
"""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from epub_converter import extract_text
from formatter import format_book, PAGE_SIZE
import storage
from routes.queue import enqueue

router = APIRouter(prefix="/api/books")
logger = logging.getLogger("eink.books")

# In-memory job store — sufficient for a single-instance personal server.
_jobs: dict[str, dict] = {}


def _process_upload(job_id: str, data: bytes, filename: str) -> None:
    try:
        name = os.path.splitext(filename)[0]
        ext  = os.path.splitext(filename)[1].lower()
        logger.info("upload started: %s (%d bytes)", filename, len(data))
        if ext == ".epub":
            raw_text, title, author = extract_text(data)
        else:
            raw_text = data.decode("utf-8", errors="replace")
            title, author = name, ""
        bin_data = format_book(raw_text, title=title, author=author)
        storage.upload(f"books/{name}.bin", bin_data)
        pages = len(bin_data) // PAGE_SIZE - 1
        logger.info("upload done: %s.bin, %d pages", name, pages)
        _jobs[job_id] = {"status": "done", "name": f"{name}.bin", "pages": pages}
    except Exception as e:
        logger.exception("upload failed: %s", filename)
        _jobs[job_id] = {"status": "error", "error": str(e)}


@router.post("/upload")
async def upload_book(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".epub", ".txt"):
        raise HTTPException(status_code=400, detail="Only .epub and .txt files are supported.")

    data = await file.read()
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(_process_upload, job_id, data, file.filename)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("")
def list_books():
    blobs = storage.list_books()
    return [b[len("books/"):] for b in blobs]


@router.delete("/{name}")
def delete_book(name: str):
    try:
        storage.delete(f"books/{name}")
    except Exception:
        raise HTTPException(status_code=404, detail="Book not found.")
    logger.info("book deleted: %s", name)
    return {"deleted": name}


@router.post("/{name}/queue")
def queue_book(name: str):
    blob_name = f"books/{name}"
    try:
        url = storage.sas_url(blob_name)
    except Exception:
        raise HTTPException(status_code=404, detail="Book not found in storage.")
    enqueue({"type": "book", "name": name, "url": url})
    logger.info("book queued: %s", name)
    return {"queued": name}
