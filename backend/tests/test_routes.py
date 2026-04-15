import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from main import app

MOCK_REFINED_SPEC = (
    "Build an agent that connects to three backend systems to retrieve order status "
    "for multiple orders simultaneously, returning results in a structured table "
    "with CSV export capability."
)

MOCK_PIPELINE_RESULT = {
    "result": {
        "pattern": "single-agent-router",
        "title": "Order Status Agent",
        "justification": "Bounded routing. Direct dispatch.",
        "nodes": [
            {"id": "user_input", "label": "User Input", "tier": "entry", "layer": 0,
             "role": "Entry", "rationale": "", "primary": "", "secondary": ""},
            {"id": "router", "label": "Intent Router", "tier": "light", "layer": 1,
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
    "timings": {
        "router_ms": 200, "architect_ms": 2000, "validator_ms": 5, "total_ms": 2205
    },
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


@pytest.mark.anyio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
