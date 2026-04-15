"""
draw.io XML exporter.
Converts an ArchResult into a draw.io-compatible XML string (.drawio / .xml).
"""
import xml.etree.ElementTree as ET
from app.models.schemas import ArchResult

# Tier → fill color mapping (matches frontend tierConfig)
TIER_COLORS: dict[str, str] = {
    "entry":  "#1a1a2e",
    "lite":   "#16213e",
    "medium": "#0f3460",
    "heavy":  "#533483",
}

NODE_WIDTH  = 160
NODE_HEIGHT = 60
H_GAP       = 40
V_GAP       = 80
START_X     = 60
START_Y     = 60


def _layer_x(layer: int) -> int:
    return START_X


def _node_y(layer: int, index_in_layer: int) -> int:
    return START_Y + layer * (NODE_HEIGHT + V_GAP) + index_in_layer * (NODE_HEIGHT + H_GAP)


def _node_x(index_in_layer: int) -> int:
    return START_X + index_in_layer * (NODE_WIDTH + H_GAP)


def arch_result_to_drawio_xml(result: ArchResult) -> str:
    root = ET.Element("mxGraphModel")
    graph_root = ET.SubElement(root, "root")
    ET.SubElement(graph_root, "mxCell", id="0")
    ET.SubElement(graph_root, "mxCell", id="1", parent="0")

    # Group nodes by layer
    layers: dict[int, list] = {}
    for node in result.nodes:
        layers.setdefault(node.layer, []).append(node)

    node_positions: dict[str, tuple[int, int]] = {}

    for layer_idx, nodes in sorted(layers.items()):
        for col_idx, node in enumerate(nodes):
            x = _node_x(col_idx)
            y = START_Y + layer_idx * (NODE_HEIGHT + V_GAP)
            node_positions[node.id] = (x, y)

            fill = TIER_COLORS.get(node.tier, "#333333")
            style = (
                f"rounded=1;whiteSpace=wrap;html=1;"
                f"fillColor={fill};fontColor=#ffffff;strokeColor=#ffffff;"
                f"fontSize=11;fontStyle=1;"
            )
            cell = ET.SubElement(
                graph_root, "mxCell",
                id=node.id,
                value=node.label,
                style=style,
                vertex="1",
                parent="1",
                tooltip=node.role,
            )
            ET.SubElement(
                cell, "mxGeometry",
                x=str(x), y=str(y),
                width=str(NODE_WIDTH), height=str(NODE_HEIGHT),
                **{"as": "geometry"},
            )

    # Edges
    for idx, edge in enumerate(result.edges):
        edge_id = f"edge_{idx}"
        cell = ET.SubElement(
            graph_root, "mxCell",
            id=edge_id,
            value=edge.label,
            style="edgeStyle=orthogonalEdgeStyle;html=1;exitX=0.5;exitY=1;entryX=0.5;entryY=0;",
            edge="1",
            source=edge.from_node,
            target=edge.to_node,
            parent="1",
        )
        ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

    return '<?xml version="1.0" encoding="UTF-8"?>' + ET.tostring(root, encoding="unicode")
