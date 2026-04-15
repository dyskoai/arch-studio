"""
Mermaid diagram exporter.
Generates Mermaid flowchart syntax from an ArchResult.
The output can be pasted directly into GitHub markdown fenced code blocks:

  ```mermaid
  flowchart TD
      ...
  ```

Reference: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams
"""
from app.models.schemas import ArchResult

_TIER_STYLE = {
    "entry":  "fill:#1a1a2e,color:#e2e8f0,stroke:#475569",
    "light":  "fill:#16213e,color:#e2e8f0,stroke:#1d4ed8",
    "medium": "fill:#0f3460,color:#e2e8f0,stroke:#0d9488",
    "heavy":  "fill:#533483,color:#e2e8f0,stroke:#a855f7",
}


def arch_result_to_mermaid(result: ArchResult) -> str:
    lines = ["flowchart TD"]

    # Node definitions — use rounded rectangle for entry, default rect otherwise
    for node in result.nodes:
        safe_label = node.label.replace('"', "'")
        if node.tier == "entry":
            lines.append(f'    {node.id}(["{safe_label}"])')
        elif node.tier == "light":
            lines.append(f'    {node.id}{{"{safe_label}"}}')
        else:
            lines.append(f'    {node.id}["{safe_label}"]')

    lines.append("")

    # Edges
    for edge in result.edges:
        label_part = f'|"{edge.label}"|' if edge.label else ""
        lines.append(f"    {edge.from_node} -->{label_part} {edge.to_node}")

    lines.append("")

    # Style classes
    for tier, style in _TIER_STYLE.items():
        lines.append(f"    classDef {tier} {style}")

    lines.append("")

    # Assign classes to nodes
    for tier in _TIER_STYLE:
        node_ids = [n.id for n in result.nodes if n.tier == tier]
        if node_ids:
            lines.append(f"    class {','.join(node_ids)} {tier}")

    return "\n".join(lines)
