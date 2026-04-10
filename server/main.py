"""FastAPI entry point."""

import logging
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from routes.books import router as books_router
from routes.todo  import router as todo_router
from routes.queue import router as queue_router
from routes.ui    import router as ui_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

logger = logging.getLogger("eink")


class _RequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        ms = (time.monotonic() - start) * 1000
        logger.info("%s %s %d %.0fms", request.method, request.url.path,
                    response.status_code, ms)
        return response


app = FastAPI(title="E-ink Reader Server", docs_url="/docs")
app.add_middleware(_RequestLogger)

app.include_router(books_router)
app.include_router(todo_router)
app.include_router(queue_router)
app.include_router(ui_router)
