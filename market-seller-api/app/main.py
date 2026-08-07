from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.db import init_db
from app.routers import billing, extract, monitors, signup, usage


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > self.max_bytes:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Marketplace Seller API", version="0.2.0", lifespan=lifespan)
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_size_bytes)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(signup.router)
app.include_router(extract.router)
app.include_router(usage.router)
app.include_router(monitors.router)
app.include_router(billing.router)
