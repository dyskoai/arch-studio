"""ADK-discoverable local entrypoint for the architecture pipeline.

Run from the ``backend`` directory:
    adk web --port 8000 --no-reload
    adk run intentiv_pipeline_agent
"""

from app.agents.pipeline import _load_best_practices, build_pipeline


root_agent = build_pipeline(best_practices=_load_best_practices())

