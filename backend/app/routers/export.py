import logging
from fastapi import APIRouter, Request
from fastapi.responses import Response, JSONResponse

from app.exporters.drawio import arch_result_to_drawio_xml
from app.exporters.mermaid_export import arch_result_to_mermaid
from app.models.schemas import DrawioExportRequest, ErrorResponse, ErrorCode
from app.services.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/export/drawio")
@limiter.limit("30/minute")
async def export_drawio(request: Request, body: DrawioExportRequest) -> Response:
    try:
        xml_content = arch_result_to_drawio_xml(body.result)
        return Response(
            content=xml_content,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="architecture.drawio"'},
        )
    except Exception as exc:
        logger.exception("drawio export error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Export failed. Please try again.",
                code=ErrorCode.generation_failed,
            ).model_dump(),
        )


@router.post("/export/mermaid")
@limiter.limit("30/minute")
async def export_mermaid(request: Request, body: DrawioExportRequest) -> Response:
    try:
        mmd = arch_result_to_mermaid(body.result)
        return Response(
            content=mmd,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="architecture.mmd"'},
        )
    except Exception as exc:
        logger.exception("mermaid export error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Export failed. Please try again.",
                code=ErrorCode.generation_failed,
            ).model_dump(),
        )
