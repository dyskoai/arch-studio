import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agents.refiner import run_refiner
from app.models.schemas import RefineRequest, RefineResponse, ErrorResponse, ErrorCode
from app.services.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refine", response_model=RefineResponse)
@limiter.limit("20/minute")   # generous — refiner is fast/cheap
async def refine(request: Request, body: RefineRequest) -> RefineResponse:
    try:
        refined_spec = await run_refiner(body.rough_input)
        if not refined_spec:
            raise ValueError("Refiner returned empty output")
        return RefineResponse(
            refined_spec=refined_spec,
            word_count=len(refined_spec.split()),
        )
    except Exception as exc:
        logger.exception("Refine error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Failed to refine your input. Please try again.",
                code=ErrorCode.refine_failed,
            ).model_dump(),
        )
