"""
Pipeline Stage 3 — Validator Agent
Deterministic graph repair — no LLM involved.
Reads session.state["raw_architecture"], repairs structural issues,
writes session.state["final_architecture"] and session.state["repaired"].
"""
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
    Repairs: duplicate IDs, missing output node, bad edge targets,
             isolated nodes, entry tier at wrong layer.
    """

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        raw_json = ctx.session.state.get("raw_architecture", "")

        try:
            raw = json.loads(raw_json)
        except json.JSONDecodeError:
            yield Event(
                author=self.name,
                content=genai_types.Content(
                    parts=[genai_types.Part(text="VALIDATOR_ERROR: could not parse raw_architecture")]
                ),
                actions=EventActions(escalate=True, state_delta={"final_architecture": ""}),
            )
            return

        repaired, issues = self._repair(raw)

        summary = f"Validation complete. Issues found and repaired: {len(issues)}"

        # State must be written via EventActions(state_delta=...) so ADK
        # persists it back to the session service. Direct ctx.session.state
        # assignment is not persisted by InMemorySessionService.
        yield Event(
            author=self.name,
            content=genai_types.Content(
                parts=[genai_types.Part(text=summary)]
            ),
            actions=EventActions(
                state_delta={
                    "final_architecture": json.dumps(repaired),
                    "repaired": len(issues) > 0,
                    "validator_issues": [i["type"] for i in issues],
                }
            ),
        )

    # ── Repair orchestration ───────────────────────────────────────────────────

    def _repair(self, raw: dict) -> tuple[dict, list[dict]]:
        result = copy.deepcopy(raw)
        issues: list[dict] = []

        result, issues = self._fix_duplicate_ids(result, issues)
        result, issues = self._fix_missing_output(result, issues)
        result, issues = self._fix_bad_edge_targets(result, issues)
        result, issues = self._fix_isolated_nodes(result, issues)
        result, issues = self._fix_wrong_tier(result, issues)

        return result, issues

    # ── Individual repair passes ───────────────────────────────────────────────

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
            {**e,
             "from": id_remap.get(e["from"], e["from"]),
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
        connected = (
            {e["from"] for e in result["edges"]} | {e["to"] for e in result["edges"]}
        )
        for node in result["nodes"]:
            if node["id"] not in connected:
                pred = self._nearest_predecessor(
                    result["nodes"], target_layer=node["layer"], exclude=node["id"]
                )
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
