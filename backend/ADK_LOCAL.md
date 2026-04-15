# Local ADK Testing

This backend exposes the existing agents in ADK's standard local package shape:

- `intentiv_refiner_agent` runs the phase-1 rough-input refiner.
- `intentiv_pipeline_agent` runs the phase-2 router -> architect -> validator pipeline.

## Setup

Create `backend/.env` with at least:

```env
GOOGLE_API_KEY=your-gemini-api-key
REFINER_MODEL=gemini-2.5-flash
ROUTER_MODEL=gemini-2.5-flash
ARCHITECT_MODEL=gemini-2.5-pro
```

The model names can stay on the preview values from `.env.example` if your ADK
install and account have access to them.

## Run ADK Web

From `backend`:

```powershell
uv run adk web --port 8000 --no-reload
```

Open `http://localhost:8000` and select either `intentiv_refiner_agent` or
`intentiv_pipeline_agent`.

## Run ADK CLI

From `backend`:

```powershell
"Build an order status agent for support teams" | uv run adk run intentiv_refiner_agent
"Build an agent that connects to order, warehouse, and shipping systems and returns a table with CSV export." | uv run adk run intentiv_pipeline_agent
```

The pipeline agent prints the final architecture JSON as the last response and
also writes the same value to `session.state["final_architecture"]`.
