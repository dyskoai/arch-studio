"""ADK-discoverable local entrypoint for the phase-1 refiner agent.

Run from the ``backend`` directory:
    adk web --port 8000 --no-reload
    adk run intentiv_refiner_agent
"""

from app.agents.refiner import build_refiner_agent


root_agent = build_refiner_agent()

