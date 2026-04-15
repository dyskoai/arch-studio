import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agents.runner import run_generate as run_pipeline
from app.models.schemas import (
    GenerateRequest, GenerateResponse, GenerateMeta,
    ErrorResponse, ErrorCode,
)
from app.services.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
@limiter.limit("10/minute")
async def generate(request: Request, body: GenerateRequest) -> GenerateResponse:
    try:
        pipeline_result = await run_pipeline(body.refined_spec)
        return GenerateResponse(
            result=pipeline_result["result"],
            meta=GenerateMeta(
                pattern=pipeline_result["pattern"],
                stages=pipeline_result["timings"],
                repaired=pipeline_result["repaired"],
            ),
        )
    except Exception as exc:
        logger.exception("Generate error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Architecture generation failed. Please try again.",
                code=ErrorCode.generation_failed,
            ).model_dump(),
        )
