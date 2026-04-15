import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.routers import refine, generate, export
from app.services.ratelimit import limiter

settings = get_settings()

app = FastAPI(
    title="Architecture Studio API",
    version="3.0.1",
    docs_url="/docs" if settings.env != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(refine.router)
app.include_router(generate.router)
app.include_router(export.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "3.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.env == "development",
    )
