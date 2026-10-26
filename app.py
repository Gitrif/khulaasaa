"""
Application entrypoint alias for uvicorn (app:app).
Re-exports the FastAPI app from main.py.
"""
from main import app

__all__ = ["app"]
