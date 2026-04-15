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
    orphan = {
        "id": "orphan", "label": "Orphan", "tier": "medium", "layer": 2,
        "role": "Does stuff", "rationale": "m", "primary": "C", "secondary": "O",
    }
    raw = _raw(BASE_NODES + [orphan], BASE_EDGES)
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "isolated_node" for i in issues)
    assert any(e["to"] == "orphan" for e in repaired["edges"])


def test_entry_at_wrong_layer_demoted():
    bad = {
        "id": "bad_entry", "label": "Bad", "tier": "entry", "layer": 2,
        "role": "Wrong", "rationale": "", "primary": "", "secondary": "",
    }
    extra_edge = {"from": "router", "to": "bad_entry", "label": "data"}
    raw = _raw(BASE_NODES + [bad], BASE_EDGES + [extra_edge])
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "wrong_tier" for i in issues)
    node = next(n for n in repaired["nodes"] if n["id"] == "bad_entry")
    assert node["tier"] == "medium"


def test_duplicate_ids_renamed():
    dup_router = {**BASE_NODES[1]}   # duplicate router id
    raw = _raw(BASE_NODES + [dup_router], BASE_EDGES)
    repaired, issues = agent._repair(raw)
    assert any(i["type"] == "duplicate_id" for i in issues)
    ids = [n["id"] for n in repaired["nodes"]]
    assert len(ids) == len(set(ids))
