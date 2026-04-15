# Intentiv Architecture Studio — Full-Stack PRD
**Version:** 3.0  
**Status:** Ready for Engineering  
**Scope:** Google ADK Python Multi-Agent Backend + Next.js Frontend  
**Key Change from v2:** Backend is fully rebuilt on Google ADK's multi-agent primitives. A new two-phase user flow adds a human-in-the-loop **Refiner** stage before the architecture pipeline runs.

---

## 1. What Changed and Why

### The new two-phase flow

v2 was a straight shot: user types → architecture comes out. That's fine for power users but fails for everyone else. The input quality is too sensitive — "order status agent" gives you garbage, but "an agent that connects to three backend systems and fetches statuses for multiple orders in parallel, returning a structured table with CSV export" gives you a great diagram.

The fix: **ask the user what they want in rough terms, have an AI refiner turn it into something precise, let them edit it, then run the pipeline.** This is the pattern from your example — the user submits a vague idea, the system returns a detailed spec, the user edits/approves, and *then* the heavy pipeline fires.

### Why ADK

ADK's `SequentialAgent` + `session.state` + `output_key` pattern is a perfect fit for this pipeline. Each agent writes its result to a named state key, the next agent reads it. Data contracts are enforced by prompts and Pydantic, not by custom plumbing. The ADK runner also handles the invocation context, so the FastAPI layer becomes thin — just session management and HTTP I/O.

### Claude models in ADK Python

The ADK Python docs specify using Claude through LiteLLM. The model string format is `litellm/anthropic/claude-sonnet-4-20250514`. This requires `ANTHROPIC_API_KEY` in the environment — LiteLLM picks it up automatically.

---

## 2. Complete User Flow

```
┌─────────────────────────────────────────────────────────┐
│  PHASE 1 — PROBLEM REFINEMENT (new)                     │
│                                                         │
│  1. User types a rough problem statement                │
│     "I want to build an order status agent for support" │
│                                                         │
│  2. Frontend POSTs to /refine                           │
│                                                         │
│  3. Refiner Agent (ADK LlmAgent, haiku) returns:        │
│     "Build an agent that connects across backend        │
│      systems and finds order status for multiple        │
│      orders together. Results should be a detailed      │
│      table with an option to download as CSV."          │
│                                                         │
│  4. Frontend renders the refined spec in an             │
│     editable textarea — user can tweak it               │
│                                                         │
│  5. User clicks "Generate Architecture" to approve      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE 2 — ARCHITECTURE PIPELINE (enhanced from v2)     │
│                                                         │
│  Frontend POSTs refined spec to /generate               │
│                                                         │
│  ADK SequentialAgent runs 3 sub-agents in order:        │
│                                                         │
│  ┌──────────────┐                                       │
│  │ Router Agent │  Classifies pattern + node hint       │
│  │  (haiku)     │  writes to state["classification"]    │
│  └──────┬───────┘                                       │
│         │                                               │
│  ┌──────▼───────┐                                       │
│  │Architect Agt │  Generates full node+edge graph       │
│  │  (sonnet)    │  writes to state["raw_architecture"]  │
│  └──────┬───────┘                                       │
│         │                                               │
│  ┌──────▼───────┐                                       │
│  │Validator Agt │  Deterministic Python graph repair    │
│  │  (no LLM)    │  writes to state["final_architecture"]│
│  └──────┬───────┘                                       │
│         │                                               │
│  FastAPI extracts state["final_architecture"]           │
│  Returns GenerateResponse to frontend                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
         Frontend renders diagram + export menu
```

---

## 3. Technical Stack

### Backend (Python)

| Layer | Choice | Reason |
|---|---|---|
| Agent Framework | `google-adk` (Python) | Native `SequentialAgent`, shared session state, ADK runner |
| Claude via ADK | `litellm/anthropic/claude-*` model strings | ADK Python uses LiteLLM as the Claude bridge |
| API Layer | FastAPI + uvicorn | Thin HTTP wrapper around ADK `Runner` |
| Session Store | ADK `InMemorySessionService` (dev) / Redis-backed (prod) | ADK manages session lifecycle |
| Data Validation | Pydantic v2 | Request/response schemas, JSON parsing |
| Rate Limiting | `slowapi` | IP-based sliding window |
| Dependency Mgmt | `uv` | Fast, lockfile-reproducible |
| Testing | `pytest` + `pytest-asyncio` | Async route + agent unit tests |
| Deployment | Railway or Cloud Run | Both support ADK; Cloud Run is ADK's native target |

### Frontend (Next.js) — unchanged from v2 except new Phase 1 screen

| Layer | Choice |
|---|---|
| Framework | Next.js 14 (App Router) + TypeScript |
| State | Zustand |
| Diagram | Custom SVG |
| Styling | Tailwind CSS |
| Deployment | Vercel |

### Environment Variables

**Backend (`.env`):**
```
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=http://localhost:3000,https://intentiv.ai
RATE_LIMIT_PER_MINUTE=10
ENV=development
```

**Frontend (`.env.local`):**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 4. Repository Structure

```
intentiv/
├── backend/
│   ├── main.py                         # FastAPI app, CORS, routers
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── .env.example
│   └── app/
│       ├── config.py                   # pydantic-settings
│       ├── routers/
│       │   ├── refine.py               # POST /refine  — Phase 1
│       │   ├── generate.py             # POST /generate — Phase 2 pipeline
│       │   └── export.py               # POST /export/drawio
│       ├── agents/
│       │   ├── refiner.py              # Phase 1: standalone LlmAgent
│       │   ├── router_agent.py         # Pipeline Stage 1: classifier
│       │   ├── architect_agent.py      # Pipeline Stage 2: architecture gen
│       │   ├── validator_agent.py      # Pipeline Stage 3: graph repair (CustomAgent)
│       │   └── pipeline.py             # SequentialAgent assembly + ADK Runner
│       ├── exporters/
│       │   └── drawio.py
│       ├── models/
│       │   └── schemas.py              # All Pydantic models
│       └── services/
│           └── ratelimit.py
│
└── frontend/
    ├── app/
    │   ├── page.tsx                    # Now routes to Phase1Screen or Phase2Screen
    │   └── layout.tsx
    ├── components/
    │   ├── phase1/
    │   │   ├── RoughInputPanel.tsx     # First textarea — rough problem
    │   │   └── RefinedSpecEditor.tsx   # Editable refined spec + approve button
    │   ├── results/                    # Unchanged from v2
    │   │   ├── ResultsLayout.tsx
    │   │   ├── DiagramCanvas.tsx
    │   │   ├── NodeInspector.tsx
    │   │   ├── PatternBadge.tsx
    │   │   ├── StatRow.tsx
    │   │   └── ExportMenu.tsx
    │   └── shared/
    │       ├── LoadingScreen.tsx
    │       └── TopBar.tsx
    ├── lib/
    │   ├── api.ts                      # refineSpec(), generateArchitecture(), exportDrawio()
    │   ├── exporters/                  # svg.ts, mermaid.ts, json.ts — unchanged
    │   ├── layout.ts
    │   ├── tierConfig.ts
    │   └── types.ts
    ├── store/
    │   └── useArchStore.ts             # New: roughInput, refinedSpec, phase states
    └── styles/
        └── globals.css
```

---

## 5. Pydantic Schemas (`backend/app/models/schemas.py`)

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ─── Core domain types ────────────────────────────────────────────────────────

class Tier(str, Enum):
    entry  = "entry"
    lite   = "lite"
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
```

---

## 6. Configuration (`backend/app/config.py`)

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key:     str
    allowed_origins:       str  = "http://localhost:3000"
    rate_limit_per_minute: int  = 10
    env:                   str  = "development"

    # ADK model strings — LiteLLM bridge for Claude in ADK Python
    refiner_model:   str = "litellm/anthropic/claude-haiku-4-5-20251001"
    router_model:    str = "litellm/anthropic/claude-haiku-4-5-20251001"
    architect_model: str = "litellm/anthropic/claude-sonnet-4-20250514"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## 7. Phase 1 — Refiner Agent (`backend/app/agents/refiner.py`)

This agent runs **standalone** (not inside the pipeline `SequentialAgent`). It is a single `LlmAgent` invoked directly by the `/refine` route via an ADK `Runner`.

**Purpose:** Transform a vague problem description into a precise, opinionated spec that makes a great architecture prompt — exactly like the example in the product brief.

**Model:** `claude-haiku-4-5` (fast, cheap — this is a single-turn expansion, not deep reasoning)

```python
import os
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.config import get_settings

REFINER_INSTRUCTION = """You are a senior AI product architect who turns rough, vague problem 
descriptions into precise, actionable agent system specifications.

When the user gives you a rough idea, return a refined specification that:
1. Specifies what data sources or backend systems the agent connects to
2. Describes what the agent does with multiple inputs (parallel? sequential?)  
3. States exactly what the output format should be (table, report, action, etc.)
4. Mentions any specific features like export options, filtering, or user controls

Rules:
- Output ONLY the refined specification text. No headers, no lists, no labels.
- 2–4 sentences maximum. Be specific and opinionated.
- Use present tense ("Build an agent that...", "The system should...")
- Do not mention architecture patterns, tiers, or implementation details

Example input: "order status agent for support"
Example output: "Build an agent that connects across backend order management, 
warehouse, and shipping systems to retrieve real-time status for multiple orders 
simultaneously. The agent should aggregate results into a structured table showing 
order ID, current status, last update, and estimated delivery, with a one-click 
option to download the results as a CSV file."
"""


def build_refiner_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="refiner_agent",
        model=settings.refiner_model,
        instruction=REFINER_INSTRUCTION,
        # No output_key — we read the runner's final event text directly
    )


async def run_refiner(rough_input: str) -> str:
    """
    Runs the refiner agent standalone and returns the refined spec text.
    Creates a fresh session for each call — stateless by design.
    """
    os.environ["ANTHROPIC_API_KEY"] = get_settings().anthropic_api_key

    session_service = InMemorySessionService()
    agent = build_refiner_agent()
    runner = Runner(
        agent=agent,
        app_name="intentiv_refiner",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="intentiv_refiner",
        user_id="api_user",
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=rough_input)],
    )

    refined_text = ""
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Collect the final agent response text
        if event.is_final_response() and event.content and event.content.parts:
            refined_text = "".join(
                part.text for part in event.content.parts if hasattr(part, "text")
            )

    return refined_text.strip()
```

---

## 8. Phase 2 — Architecture Pipeline

### 8.1 Router Agent (`backend/app/agents/router_agent.py`)

The first sub-agent in the `SequentialAgent`. Classifies the pattern and writes to `session.state["classification"]` via `output_key`.

**Model:** `claude-haiku-4-5` — fast triage, no deep reasoning needed  
**ADK primitive used:** `LlmAgent` with `output_key="classification"`

```python
from google.adk.agents import LlmAgent
from app.config import get_settings

ROUTER_INSTRUCTION = """You are an AI architecture classifier. Read the problem specification 
and output ONLY valid JSON — no markdown, no preamble.

Schema:
{
  "pattern": "single-agent-router" | "multi-agent-supervisor",
  "confidence": "high" | "medium" | "low",
  "reasoning": "one internal sentence explaining the choice",
  "node_count_hint": 7
}

Classification rules:
- single-agent-router: One router dispatches to bounded, deterministic tools.
  Signals: "route to", "classify and forward", "look up", "fetch from",
  sequential steps, API calls, no cross-agent collaboration. node_count_hint: 5–8.
- multi-agent-supervisor: A supervisor coordinates multiple agents in parallel
  or iteratively. Signals: "multiple specialists", "parallel processing",
  "maker/checker", "different personas", "cross-review", "iterative refinement".
  node_count_hint: 8–14.

Output ONLY the JSON object. Nothing else."""


def build_router_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="router_agent",
        model=settings.router_model,
        instruction=ROUTER_INSTRUCTION,
        output_key="classification",   # writes JSON string to session.state["classification"]
    )
```

### 8.2 Architect Agent (`backend/app/agents/architect_agent.py`)

The second sub-agent. Reads `session.state["classification"]` (injected via `{classification}` in its instruction template) and generates the full architecture.

**Model:** `claude-sonnet-4` — deep reasoning, structured JSON output  
**ADK primitive used:** `LlmAgent` with `output_key="raw_architecture"`

```python
from google.adk.agents import LlmAgent
from app.config import get_settings

ARCHITECT_INSTRUCTION = """You are a senior AI systems architect. Generate a precise, 
production-grade agentic architecture blueprint based on the problem spec below.

Classification from router (use this — do not re-derive):
{classification}

Respond ONLY with valid JSON. No markdown fences, no preamble. Raw JSON only.

JSON Schema:
{
  "pattern": "<same pattern as classification>",
  "title": "Descriptive System Title (4-6 words)",
  "justification": "Exactly 2 sentences explaining why this pattern fits.",
  "nodes": [
    {
      "id": "snake_case_unique_id",
      "label": "Node Name (2-4 words)",
      "tier": "entry" | "lite" | "medium" | "heavy",
      "layer": 0,
      "role": "One sentence: what this node does.",
      "rationale": "One sentence: why this tier.",
      "primary": "Primary deployment (e.g., Managed Cloud API)",
      "secondary": "Fallback (e.g., Self-Hosted Open-Weights)"
    }
  ],
  "edges": [
    { "from": "node_id", "to": "node_id", "label": "2-4 word data flow" }
  ]
}

LAYER RULES:
- Layer 0: Exactly one "User Input" node. tier=entry. Omit primary/secondary.
- Layer 1: Lite router (single-agent-router) OR Heavy supervisor (multi-agent-supervisor).
- Layer 2: Specialist medium-tier worker agents for domain tasks.
- Layer 3: QA/eval (heavy), external tool integrations, APIs.
- Layer 4: Exactly one "Output / Response" node. tier=entry. Omit primary/secondary.

TIER RULES:
- entry: ONLY user input and final output nodes.
- lite: Routers, classifiers, dispatchers. Fast, cheap. No deep reasoning.
- medium: Specialist workers — drafting, extraction, research, analysis.
- heavy: Orchestrators directing other agents. Any QA/eval/verification node.

EDGE RULES:
- Data flows: L0 → L1 → L2 → L3 → L4. Back-edges (QA → worker) encouraged.
- Every node must appear in at least one edge.
- All "from" and "to" must exactly match node IDs.

Output only the JSON object."""


def build_architect_agent() -> LlmAgent:
    settings = get_settings()
    return LlmAgent(
        name="architect_agent",
        model=settings.architect_model,
        instruction=ARCHITECT_INSTRUCTION,
        output_key="raw_architecture",   # writes to session.state["raw_architecture"]
    )
```

**How state injection works:** ADK automatically resolves `{classification}` in the instruction string by reading `session.state["classification"]` — the value written by the `router_agent` in the previous sequential step.

### 8.3 Validator Agent (`backend/app/agents/validator_agent.py`)

The third sub-agent. A `CustomAgent` — no LLM involved. Reads `session.state["raw_architecture"]`, runs deterministic graph repair, writes to `session.state["final_architecture"]`.

**ADK primitive used:** `BaseAgent` subclass with custom `_run_async_impl`

```python
import json
import copy
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types as genai_types


class ValidatorAgent(BaseAgent):
    """
    Deterministic graph validator — no LLM.
    Reads session.state["raw_architecture"], repairs issues,
    writes session.state["final_architecture"] and session.state["repaired"].
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw_json = ctx.session.state.get("raw_architecture", "")

        try:
            raw = json.loads(raw_json)
        except json.JSONDecodeError:
            # If architect output is malformed JSON, emit an error event
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text="VALIDATOR_ERROR: could not parse raw_architecture")]
                ),
                actions=EventActions(escalate=True),  # stops the pipeline
            )
            return

        repaired, issues = self._repair(raw)

        # Write results to shared session state
        ctx.session.state["final_architecture"] = json.dumps(repaired)
        ctx.session.state["repaired"] = len(issues) > 0
        ctx.session.state["validator_issues"] = [i["type"] for i in issues]

        summary = f"Validation complete. Issues found and repaired: {len(issues)}"
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=summary)]
            ),
        )

    # ── Repair logic ──────────────────────────────────────────────────────────

    def _repair(self, raw: dict) -> tuple[dict, list[dict]]:
        result = copy.deepcopy(raw)
        issues: list[dict] = []

        result, issues = self._fix_duplicate_ids(result, issues)
        result, issues = self._fix_missing_output(result, issues)
        result, issues = self._fix_bad_edge_targets(result, issues)
        result, issues = self._fix_isolated_nodes(result, issues)
        result, issues = self._fix_wrong_tier(result, issues)

        return result, issues

    def _fix_duplicate_ids(self, result: dict, issues: list) -> tuple[dict, list]:
        seen: set[str] = set()
        id_remap: dict[str, str] = {}
        new_nodes = []
        for node in result.get("nodes", []):
            if node["id"] in seen:
                new_id = f"{node['id']}_2"
                id_remap[node["id"]] = new_id
                node = {**node, "id": new_id}
                issues.append({"type": "duplicate_id", "node_id": node["id"]})
            seen.add(node["id"])
            new_nodes.append(node)
        result["nodes"] = new_nodes
        result["edges"] = [
            {**e, "from": id_remap.get(e["from"], e["from"]),
                  "to":   id_remap.get(e["to"],   e["to"])}
            for e in result.get("edges", [])
        ]
        return result, issues

    def _fix_missing_output(self, result: dict, issues: list) -> tuple[dict, list]:
        if not any(n.get("layer") == 4 for n in result.get("nodes", [])):
            issues.append({"type": "missing_output"})
            output_node = {
                "id": "output_response", "label": "Output / Response",
                "tier": "entry", "layer": 4,
                "role": "Delivers the final result to the user.",
                "rationale": "", "primary": "", "secondary": "",
            }
            result["nodes"].append(output_node)
            # Wire the last non-output node to it
            predecessor = self._nearest_predecessor(result["nodes"], target_layer=4)
            if predecessor:
                result["edges"].append({
                    "from": predecessor["id"],
                    "to": "output_response",
                    "label": "final response",
                })
        return result, issues

    def _fix_bad_edge_targets(self, result: dict, issues: list) -> tuple[dict, list]:
        node_ids = {n["id"] for n in result.get("nodes", [])}
        valid = []
        for e in result.get("edges", []):
            if e["from"] not in node_ids or e["to"] not in node_ids:
                issues.append({"type": "missing_edge_target",
                               "from": e["from"], "to": e["to"]})
            else:
                valid.append(e)
        result["edges"] = valid
        return result, issues

    def _fix_isolated_nodes(self, result: dict, issues: list) -> tuple[dict, list]:
        connected = {e["from"] for e in result["edges"]} | {e["to"] for e in result["edges"]}
        for node in result["nodes"]:
            if node["id"] not in connected:
                pred = self._nearest_predecessor(result["nodes"], target_layer=node["layer"],
                                                  exclude=node["id"])
                issues.append({"type": "isolated_node", "node_id": node["id"]})
                if pred:
                    result["edges"].append({
                        "from": pred["id"], "to": node["id"], "label": "task data"
                    })
        return result, issues

    def _fix_wrong_tier(self, result: dict, issues: list) -> tuple[dict, list]:
        for node in result["nodes"]:
            if node.get("tier") == "entry" and node.get("layer") not in (0, 4):
                node["tier"] = "medium"
                issues.append({"type": "wrong_tier", "node_id": node["id"]})
        return result, issues

    def _nearest_predecessor(
        self, nodes: list[dict], target_layer: int, exclude: str | None = None
    ) -> dict | None:
        candidates = [
            n for n in nodes
            if n.get("layer", 99) < target_layer and n.get("id") != exclude
        ]
        return max(candidates, key=lambda n: n.get("layer", 0), default=None)


def build_validator_agent() -> ValidatorAgent:
    return ValidatorAgent(
        name="validator_agent",
        description="Deterministic graph validator — repairs structural issues in architecture JSON.",
    )
```

### 8.4 Pipeline Assembly (`backend/app/agents/pipeline.py`)

Assembles the three agents into an ADK `SequentialAgent` and exposes a `run_pipeline()` async function for the route handler to call.

```python
import json
import os
import time
from typing import Any

from google.adk.agents import SequentialAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.agents.router_agent import build_router_agent
from app.agents.architect_agent import build_architect_agent
from app.agents.validator_agent import build_validator_agent
from app.config import get_settings
from app.models.schemas import ArchResult, Pattern, PipelineTimings


def build_pipeline() -> SequentialAgent:
    """
    Assembles the three-stage pipeline as a SequentialAgent.
    
    Data flow via session.state:
      router_agent     → state["classification"]    (JSON string)
      architect_agent  → state["raw_architecture"]  (JSON string, reads {classification})
      validator_agent  → state["final_architecture"] (JSON string)
                       → state["repaired"]           (bool)
                       → state["validator_issues"]   (list[str])
    """
    return SequentialAgent(
        name="architecture_pipeline",
        description="Three-stage pipeline: classify pattern → generate architecture → validate graph",
        sub_agents=[
            build_router_agent(),
            build_architect_agent(),
            build_validator_agent(),
        ],
    )


async def run_pipeline(refined_spec: str) -> dict[str, Any]:
    """
    Runs the architecture pipeline for a given refined spec.
    Returns a dict with the ArchResult, timings, and repair flag.
    """
    os.environ["ANTHROPIC_API_KEY"] = get_settings().anthropic_api_key

    session_service = InMemorySessionService()
    pipeline = build_pipeline()
    runner = Runner(
        agent=pipeline,
        app_name="intentiv_pipeline",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="intentiv_pipeline",
        user_id="api_user",
    )

    user_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=refined_spec)],
    )

    t_start = time.monotonic()
    timings: dict[str, float] = {
        "router_start": 0.0,
        "architect_start": 0.0,
        "validator_start": 0.0,
    }

    # Run the SequentialAgent — events stream as each sub-agent completes
    async for event in runner.run_async(
        user_id="api_user",
        session_id=session.id,
        new_message=user_message,
    ):
        # Track timing milestones from agent author labels
        author = getattr(event, "author", "")
        now = time.monotonic()
        if author == "router_agent" and timings["router_start"] == 0.0:
            timings["router_start"] = now
        elif author == "architect_agent" and timings["architect_start"] == 0.0:
            timings["architect_start"] = now
        elif author == "validator_agent" and timings["validator_start"] == 0.0:
            timings["validator_start"] = now

    t_end = time.monotonic()

    # Read final results from shared session state
    final_state = session.state
    final_arch_json = final_state.get("final_architecture", "")
    repaired = bool(final_state.get("repaired", False))

    if not final_arch_json:
        raise ValueError("Pipeline completed but final_architecture is empty")

    arch_data = json.loads(final_arch_json)

    # Normalise edge aliases (from/from_node)
    for edge in arch_data.get("edges", []):
        if "from" not in edge and "from_node" in edge:
            edge["from"] = edge.pop("from_node")
        if "to" not in edge and "to_node" in edge:
            edge["to"] = edge.pop("to_node")

    arch_result = ArchResult.model_validate(arch_data)

    # Approximate per-stage timings from milestone markers
    total_ms = int((t_end - t_start) * 1000)
    router_ms    = max(0, int((timings["architect_start"] - t_start) * 1000))
    architect_ms = max(0, int((timings["validator_start"] - timings["architect_start"]) * 1000))
    validator_ms = max(0, int((t_end - timings["validator_start"]) * 1000))

    return {
        "result": arch_result,
        "pattern": arch_result.pattern,
        "timings": PipelineTimings(
            router_ms=router_ms,
            architect_ms=architect_ms,
            validator_ms=validator_ms,
            total_ms=total_ms,
        ),
        "repaired": repaired,
    }
```

---

## 9. Route Handlers

### 9.1 Refine Route (`backend/app/routers/refine.py`)

```python
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agents.refiner import run_refiner
from app.models.schemas import (
    RefineRequest, RefineResponse, ErrorResponse, ErrorCode
)
from app.services.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/refine", response_model=RefineResponse)
@limiter.limit("20/minute")   # More generous — this is cheap haiku
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
```

### 9.2 Generate Route (`backend/app/routers/generate.py`)

```python
import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.agents.pipeline import run_pipeline
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
```

---

## 10. FastAPI App (`backend/main.py`)

```python
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
    title="Intentiv Architecture Studio API",
    version="3.0.0",
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
        port=8000,
        reload=settings.env == "development",
    )
```

---

## 11. Dependencies (`backend/pyproject.toml`)

```toml
[project]
name = "intentiv-backend"
version = "3.0.0"
requires-python = ">=3.12"
dependencies = [
    "google-adk>=0.5.0",        # ADK Python — SequentialAgent, LlmAgent, BaseAgent, Runner
    "litellm>=1.50.0",           # Claude model bridge for ADK Python
    "anthropic>=0.40.0",         # LiteLLM calls this under the hood
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "slowapi>=0.1.9",
    "redis>=5.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.7.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Install and run:**
```bash
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

---

## 12. Frontend Changes

### 12.1 Updated Zustand Store (`frontend/store/useArchStore.ts`)

Two new phases added to the existing store. The existing `result`, `meta`, and diagram states are unchanged.

```typescript
import { create } from "zustand";
import { ArchResult, GenerateResponse } from "@/lib/types";
import { refineSpec, generateArchitecture } from "@/lib/api";

type Screen =
  | "rough_input"      // Phase 1a: user types rough problem
  | "refining"         // Phase 1b: loading — refiner running
  | "refined_review"   // Phase 1c: user reviews/edits refined spec
  | "generating"       // Phase 2a: loading — pipeline running
  | "results";         // Phase 2b: diagram ready

interface ArchStore {
  // Phase 1
  screen:       Screen;
  roughInput:   string;
  refinedSpec:  string;
  setRoughInput:  (v: string) => void;
  setRefinedSpec: (v: string) => void;
  refine:       () => Promise<void>;

  // Phase 2
  result:       ArchResult | null;
  meta:         GenerateResponse["meta"] | null;
  error:        string;
  generate:     () => Promise<void>;

  // Diagram interaction
  hoveredNodeId:  string | null;
  selectedNodeId: string | null;
  setHoveredNodeId:  (id: string | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  activeNodeId: () => string | null;

  // Export
  showExportMenu: boolean;
  setShowExportMenu: (v: boolean) => void;
  copied: boolean;
  setCopied: (v: boolean) => void;

  reset: () => void;
}

export const useArchStore = create<ArchStore>((set, get) => ({
  screen: "rough_input",
  roughInput: "",
  refinedSpec: "",
  setRoughInput:  (roughInput)  => set({ roughInput }),
  setRefinedSpec: (refinedSpec) => set({ refinedSpec }),

  refine: async () => {
    const { roughInput } = get();
    if (!roughInput.trim() || roughInput.length < 5) return;
    set({ screen: "refining", error: "" });
    try {
      const data = await refineSpec(roughInput);
      set({ refinedSpec: data.refined_spec, screen: "refined_review" });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Refinement failed.";
      set({ error: msg, screen: "rough_input" });
    }
  },

  result: null,
  meta: null,
  error: "",

  generate: async () => {
    const { refinedSpec } = get();
    if (!refinedSpec.trim() || refinedSpec.length < 20) return;
    set({ screen: "generating", error: "", result: null });
    try {
      const data = await generateArchitecture(refinedSpec);
      set({ result: data.result, meta: data.meta, screen: "results" });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Generation failed.";
      set({ error: msg, screen: "refined_review" });
    }
  },

  hoveredNodeId: null,
  selectedNodeId: null,
  setHoveredNodeId: (id) => set({ hoveredNodeId: id }),
  setSelectedNodeId: (id) => set(s => ({
    selectedNodeId: s.selectedNodeId === id ? null : id,
  })),
  activeNodeId: () => get().selectedNodeId ?? get().hoveredNodeId,

  showExportMenu: false,
  setShowExportMenu: (v) => set({ showExportMenu: v }),
  copied: false,
  setCopied: (v) => set({ copied: v }),

  reset: () => set({
    screen: "rough_input", roughInput: "", refinedSpec: "",
    result: null, meta: null, error: "",
    selectedNodeId: null, hoveredNodeId: null,
  }),
}));
```

### 12.2 Updated API Client (`frontend/lib/api.ts`)

```typescript
import type {
  ArchResult, GenerateResponse, RefineResponse,
  GenerateErrorResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    throw Object.assign(new Error(err.error ?? "Request failed"), {
      code: err.code,
      status: res.status,
    });
  }
  return res.json() as Promise<T>;
}

// Phase 1
export async function refineSpec(roughInput: string): Promise<RefineResponse> {
  return post<RefineResponse>("/refine", { rough_input: roughInput });
}

// Phase 2
export async function generateArchitecture(
  refinedSpec: string
): Promise<GenerateResponse> {
  return post<GenerateResponse>("/generate", { refined_spec: refinedSpec });
}

// Export
export async function exportDrawio(result: ArchResult): Promise<Blob> {
  const res = await fetch(`${BASE}/export/drawio`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result }),
  });
  if (!res.ok) throw new Error("draw.io export failed");
  return res.blob();
}
```

### 12.3 Updated TypeScript Types (`frontend/lib/types.ts`)

Add the two new Phase 1 types; all Phase 2 types from v2 are unchanged.

```typescript
// Phase 1 (new)
export interface RefineRequest  { rough_input: string; }
export interface RefineResponse { refined_spec: string; word_count: number; }

// Phase 2 (unchanged from v2)
export type Tier    = "entry" | "lite" | "medium" | "heavy";
export type Pattern = "single-agent-router" | "multi-agent-supervisor";

export interface ArchNode {
  id: string; label: string; tier: Tier; layer: number;
  role: string; rationale: string; primary: string; secondary: string;
}
export interface ArchEdge { from: string; to: string; label: string; }
export interface ArchResult {
  pattern: Pattern; title: string; justification: string;
  nodes: ArchNode[]; edges: ArchEdge[];
}
export interface PipelineTimings {
  router_ms: number; architect_ms: number;
  validator_ms: number; total_ms: number;
}
export interface GenerateMeta {
  pattern: Pattern; stages: PipelineTimings; repaired: boolean;
}
export interface GenerateResponse { result: ArchResult; meta: GenerateMeta; }
export interface GenerateErrorResponse {
  error: string;
  code: "RATE_LIMITED" | "INVALID_INPUT" | "REFINE_FAILED" | "GENERATION_FAILED";
}
```

---

## 13. Frontend Screen Specifications (Phase 1 — new screens)

### 13.1 `rough_input` Screen — `RoughInputPanel.tsx`

**Purpose:** Capture a vague, low-effort problem description. This screen should feel conversational, not like a form.

**Elements:**
- Brand label: `INTENTIV · ARCHITECTURE STUDIO`
- H1: `What are you building?`
- Subhead: `Describe it roughly. We'll make it precise.`
- 3 examples as pill buttons (pre-fill the textarea on click):
  - `"Order status for support"`
  - `"Customer support triage"`
  - `"Code review pipeline"`
- Textarea: 3 rows, max 500 chars, placeholder: `"Describe the problem in plain language. Don't overthink it."`
- Button: `REFINE MY IDEA →` — disabled when input < 5 chars
- Character counter: bottom-right of textarea
- Error box (conditional)
- On submit: `store.refine()` fires → screen transitions to `refining`

### 13.2 `refining` Loading Screen

Same loading animation as the existing loading screen (dot grid + progress bar).

**Loading messages specific to this step:**
```
"reading your idea"
"sharpening the problem statement"
"adding specifics"
"almost ready to review"
```

### 13.3 `refined_review` Screen — `RefinedSpecEditor.tsx`

**Purpose:** Show the AI-refined spec in a textarea the user can freely edit, then approve it to trigger Phase 2.

**Elements:**
- Top label: `AI-REFINED SPECIFICATION` (9px, teal, letterSpacing 3)
- Subtle info line: `Review and edit before generating. This is what the architecture will be based on.`
- **Editable textarea** — populated with `store.refinedSpec`, large, no max length restriction, full width, DM Mono, dark bg
- Word count indicator: bottom-left
- Two buttons, right-aligned:
  - `← START OVER` — calls `store.reset()`
  - `GENERATE ARCHITECTURE →` (primary, teal) — calls `store.generate()`
- Error box (conditional — shown if Phase 2 fails but user is back on this screen)

**Key UX decision:** The textarea must be fully editable. The user should feel in control of what goes to the pipeline. The refined text is a starting point, not a contract.

### 13.4 `generating` Loading Screen

Same animation as `refining` but with pipeline-specific messages:
```
"parsing problem topology"
"classifying agent pattern"
"assigning weight classes"
"resolving node dependencies"
"wiring the architecture"
"rendering blueprint"
```

### 13.5 `results` Screen

Unchanged from v2. The top bar `← NEW` button calls `store.reset()` which returns to `rough_input`.

---

## 14. Tests (`backend/tests/`)

### 14.1 Validator unit tests (`tests/test_validator.py`)

```python
import json
import pytest
from app.agents.validator_agent import ValidatorAgent


def _raw(nodes, edges, pattern="single-agent-router"):
    return {
        "pattern": pattern,
        "title": "Test System",
        "justification": "Test. Test.",
        "nodes": nodes,
        "edges": edges,
    }

BASE_NODES = [
    {"id": "user_input", "label": "User Input", "tier": "entry", "layer": 0,
     "role": "Entry", "rationale": "", "primary": "", "secondary": ""},
    {"id": "router",     "label": "Router",     "tier": "lite",  "layer": 1,
     "role": "Routes",  "rationale": "Fast", "primary": "Cloud", "secondary": "OSS"},
    {"id": "output_response", "label": "Output", "tier": "entry", "layer": 4,
     "role": "Exit", "rationale": "", "primary": "", "secondary": ""},
]
BASE_EDGES = [
    {"from": "user_input", "to": "router",          "label": "query"},
    {"from": "router",     "to": "output_response", "label": "result"},
]

agent = ValidatorAgent(name="test_validator", description="test")


def test_valid_graph_no_issues():
    raw = _raw(BASE_NODES, BASE_EDGES)
    repaired, issues = agent._repair(raw)
    assert issues == []


def test_missing_output_node_added():
    nodes = [n for n in BASE_NODES if n["layer"] != 4]
    raw = _raw(nodes, BASE_EDGES[:1])
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "missing_output" for i in issues)
    assert any(n["layer"] == 4 for n in repaired["nodes"])


def test_bad_edge_target_removed():
    bad_edges = BASE_EDGES + [{"from": "router", "to": "ghost_node", "label": "x"}]
    raw = _raw(BASE_NODES, bad_edges)
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "missing_edge_target" for i in issues)
    assert all(e["to"] != "ghost_node" for e in repaired["edges"])


def test_isolated_node_wired():
    orphan = {"id": "orphan", "label": "Orphan", "tier": "medium", "layer": 2,
              "role": "Does stuff", "rationale": "m", "primary": "C", "secondary": "O"}
    raw = _raw(BASE_NODES + [orphan], BASE_EDGES)
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "isolated_node" for i in issues)
    assert any(e["to"] == "orphan" for e in repaired["edges"])


def test_entry_at_wrong_layer_demoted():
    bad = {"id": "bad_entry", "label": "Bad", "tier": "entry", "layer": 2,
           "role": "Wrong", "rationale": "", "primary": "", "secondary": ""}
    extra_edge = {"from": "router", "to": "bad_entry", "label": "data"}
    raw = _raw(BASE_NODES + [bad], BASE_EDGES + [extra_edge])
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "wrong_tier" for i in issues)
    node = next(n for n in repaired["nodes"] if n["id"] == "bad_entry")
    assert node["tier"] == "medium"


def test_duplicate_ids_renamed():
    dup_router = {**BASE_NODES[1]}  # duplicate router
    raw = _raw(BASE_NODES + [dup_router], BASE_EDGES)
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "duplicate_id" for i in issues)
    ids = [n["id"] for n in repaired["nodes"]]
    assert len(ids) == len(set(ids))
```

### 14.2 Route integration tests (`tests/test_routes.py`)

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app

MOCK_REFINED_SPEC = "Build an agent that connects to three backend systems to retrieve order status for multiple orders simultaneously, returning results in a structured table with CSV export capability."

MOCK_PIPELINE_RESULT = {
    "result": {
        "pattern": "single-agent-router",
        "title": "Order Status Agent",
        "justification": "Bounded routing. Direct dispatch.",
        "nodes": [
            {"id": "user_input", "label": "User Input", "tier": "entry", "layer": 0,
             "role": "Entry", "rationale": "", "primary": "", "secondary": ""},
            {"id": "router", "label": "Intent Router", "tier": "lite", "layer": 1,
             "role": "Routes", "rationale": "Fast", "primary": "Cloud", "secondary": "OSS"},
            {"id": "output_response", "label": "Output", "tier": "entry", "layer": 4,
             "role": "Exit", "rationale": "", "primary": "", "secondary": ""},
        ],
        "edges": [
            {"from": "user_input", "to": "router", "label": "query"},
            {"from": "router", "to": "output_response", "label": "result"},
        ],
    },
    "pattern": "single-agent-router",
    "timings": {"router_ms": 200, "architect_ms": 2000, "validator_ms": 5, "total_ms": 2205},
    "repaired": False,
}


@pytest.mark.anyio
async def test_refine_success():
    with patch("app.routers.refine.run_refiner", new=AsyncMock(return_value=MOCK_REFINED_SPEC)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/refine", json={"rough_input": "order status agent"})
    assert resp.status_code == 200
    assert "Build an agent" in resp.json()["refined_spec"]


@pytest.mark.anyio
async def test_refine_input_too_short():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/refine", json={"rough_input": "hi"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_generate_success():
    with patch("app.routers.generate.run_pipeline", new=AsyncMock(return_value=MOCK_PIPELINE_RESULT)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.post("/generate", json={"refined_spec": "A" * 30})
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"]["pattern"] == "single-agent-router"
    assert "stages" in data["meta"]


@pytest.mark.anyio
async def test_generate_input_too_short():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.post("/generate", json={"refined_spec": "short"})
    assert resp.status_code == 422
```

---

## 15. Deployment Architecture

```
                    ┌─────────────────┐
   Browser ─────── │  Vercel (CDN)   │  frontend/
                    │  Next.js 14     │  NEXT_PUBLIC_API_URL →
                    └────────┬────────┘
                             │ HTTPS
          ┌──────────────────┼───────────────────────┐
          │                  │                       │
   POST /refine      POST /generate        POST /export/drawio
          │                  │                       │
          └──────────────────┼───────────────────────┘
                             │
                    ┌────────▼──────────────────────┐
                    │  Railway / Cloud Run           │  backend/
                    │  FastAPI + uvicorn             │
                    │                               │
                    │  /refine                      │
                    │   └─ ADK Runner               │
                    │       └─ refiner_agent (haiku)│
                    │                               │
                    │  /generate                    │
                    │   └─ ADK Runner               │
                    │       └─ SequentialAgent      │
                    │           ├─ router_agent     │
                    │           ├─ architect_agent  │
                    │           └─ validator_agent  │
                    └──────────────┬────────────────┘
                                   │
                         ┌─────────▼──────────┐
                         │  Anthropic API      │
                         │  via LiteLLM bridge │
                         │  claude-haiku-4-5   │
                         │  claude-sonnet-4    │
                         └────────────────────┘
```

---

## 16. Implementation Phases

### Phase 1 — ADK Backend Core (Week 1)
- [ ] Python project with `google-adk`, `litellm`, `anthropic` in `pyproject.toml`
- [ ] `config.py` with model strings using `litellm/anthropic/` prefix
- [ ] `refiner.py` — standalone LlmAgent + `run_refiner()` function
- [ ] `router_agent.py` — LlmAgent with `output_key="classification"`
- [ ] `architect_agent.py` — LlmAgent reading `{classification}` from state
- [ ] `validator_agent.py` — BaseAgent subclass with graph repair logic
- [ ] `pipeline.py` — SequentialAgent assembly + `run_pipeline()` runner
- [ ] All validator unit tests passing
- [ ] Manual curl test: `POST /refine` and `POST /generate`

### Phase 2 — Frontend Phase 1 Screens (Week 1–2)
- [ ] Zustand store extended with `roughInput`, `refinedSpec`, new screens
- [ ] `lib/api.ts` updated with `refineSpec()` function
- [ ] `RoughInputPanel.tsx` — rough input screen
- [ ] `refining` loading screen with Phase 1 messages
- [ ] `RefinedSpecEditor.tsx` — editable refined spec + approve button
- [ ] End-to-end test: type → refine → edit → generate → diagram

### Phase 3 — Diagram + Exports (Week 2)
- [ ] All existing diagram components from v2 wired to new store
- [ ] Export menu with all 4 formats
- [ ] draw.io exporter (`exporters/drawio.py`)
- [ ] `POST /export/drawio` route

### Phase 4 — Production Hardening (Week 3)
- [ ] Rate limiting on both `/refine` and `/generate`
- [ ] Route integration tests passing
- [ ] Dockerfile tested
- [ ] Railway + Vercel deployed with correct CORS config
- [ ] Error boundaries on all screens

---

## 17. Key ADK Design Decisions

**Why `SequentialAgent` over manual chaining:**  
ADK's `SequentialAgent` handles the invocation context lifecycle, session passing, and event loop between sub-agents automatically. Manual chaining would require rebuilding that plumbing. The tradeoff is that the pipeline is less inspectable mid-run, but the ADK web UI (for dev) and event stream compensate.

**Why `output_key` for state passing:**  
Using `output_key="classification"` on the router agent is the idiomatic ADK way to pass data between sequential steps. The architect agent then reads `{classification}` from its instruction template — ADK resolves this automatically. This is cleaner than manually writing to `ctx.session.state` in an LlmAgent.

**Why the Validator is a `BaseAgent` not an `LlmAgent`:**  
The validator does zero LLM work. Graph connectivity checks and tier validation are deterministic Python. Making it an LlmAgent would waste tokens, add latency, and introduce non-determinism. `BaseAgent` with `_run_async_impl` is the correct ADK primitive for custom non-LLM logic inside a pipeline.

**Why the Refiner is standalone (not in the SequentialAgent):**  
Phase 1 and Phase 2 are separate HTTP requests with a human pause between them. The refiner result is shown to the user, who may edit it. Putting the refiner inside the pipeline would mean running everything in one shot — losing the human-in-the-loop step. Two separate `Runner` invocations is the right architecture.

**Why `InMemorySessionService` per request:**  
Each `/refine` and `/generate` call creates a fresh session and discards it after the run. There's no multi-turn state to preserve between calls. Using `InMemorySessionService` keeps the backend stateless and horizontally scalable. For prod, swap to a Redis-backed session service from the ADK ecosystem if you want cross-request session continuity (e.g., for future iteration mode).

---

## 18. Out of Scope (v1)

- **Iteration mode** — "now add a caching layer" follow-up prompts (requires multi-turn session persistence)
- **Streaming** — architecture generates in full before rendering
- **PNG export** — SVG is sufficient and higher quality
- **User accounts + saved blueprints** — shareable URLs require persistence layer
- **ADK Web UI** — useful for dev debugging but not shipped to users
- **Multiple architecture variants** — side-by-side pattern comparison

---

*End of PRD — Version 3.0*
