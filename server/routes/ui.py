"""Serves the static web dashboard."""

from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")


@router.get("/")
def dashboard():
    return FileResponse(os.path.join(_STATIC, "index.html"))
