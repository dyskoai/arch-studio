from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ─── Core domain types ────────────────────────────────────────────────────────

class Tier(str, Enum):
    entry  = "entry"
    light  = "light"
    medium = "medium"
    heavy  = "heavy"

class Pattern(str, Enum):
    single_agent_router    = "single-agent-router"
    multi_agent_supervisor = "multi-agent-supervisor"


class ArchNode(BaseModel):
    id:        str  = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    label:     str  = Field(..., min_length=2, max_length=40)
    tier:      Tier
    layer:     int  = Field(..., ge=0, le=10)
    role:      str  = Field(..., max_length=200)
    rationale: str  = Field(default="", max_length=200)
    primary:   str  = Field(default="", max_length=100)
    secondary: str  = Field(default="", max_length=100)


class ArchEdge(BaseModel):
    from_node: str = Field(..., alias="from")
    to_node:   str = Field(..., alias="to")
    label:     str = Field(default="", max_length=50)
    model_config = {"populate_by_name": True}


class ArchResult(BaseModel):
    pattern:       Pattern
    title:         str  = Field(..., min_length=4, max_length=60)
    justification: str  = Field(..., max_length=500)
    nodes:         list[ArchNode]
    edges:         list[ArchEdge]


# ─── Phase 1 — Refine ─────────────────────────────────────────────────────────

class RefineRequest(BaseModel):
    rough_input: str = Field(..., min_length=5, max_length=500)

    @field_validator("rough_input")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class RefineResponse(BaseModel):
    refined_spec: str   # Polished 2–4 sentence problem spec
    word_count:   int


# ─── Phase 2 — Generate ───────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    refined_spec: str = Field(..., min_length=20, max_length=1000)

    @field_validator("refined_spec")
    @classmethod
    def strip(cls, v: str) -> str:
        return v.strip()


class PipelineTimings(BaseModel):
    router_ms:    int
    architect_ms: int
    validator_ms: int
    total_ms:     int


class GenerateMeta(BaseModel):
    pattern:  Pattern
    stages:   PipelineTimings
    repaired: bool


class GenerateResponse(BaseModel):
    result: ArchResult
    meta:   GenerateMeta


# ─── Export ───────────────────────────────────────────────────────────────────

class DrawioExportRequest(BaseModel):
    result: ArchResult


# ─── Errors ───────────────────────────────────────────────────────────────────

class ErrorCode(str, Enum):
    rate_limited      = "RATE_LIMITED"
    invalid_input     = "INVALID_INPUT"
    refine_failed     = "REFINE_FAILED"
    generation_failed = "GENERATION_FAILED"

class ErrorResponse(BaseModel):
    error: str
    code:  ErrorCode
