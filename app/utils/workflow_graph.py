"""Validation for workflow graph definitions.

A definition is the JSON the visual builder produces:

    {"nodes": [{"id": "t1", "type": "trigger", "label": "New invoice",
                "config": {}}, ...],
     "edges": [{"source": "t1", "target": "a1"}, ...]}

`validate_definition` is a pure function returning a list of human-readable
problems (empty means valid). It has no FastAPI or SQLAlchemy dependency so
the builder's preview endpoint can reuse it and the rules stay unit-testable.
"""

from __future__ import annotations

from typing import Any

NODE_TYPES = ("trigger", "agent", "condition", "action")
MAX_NODES = 200
MAX_EDGES = 500


def _is_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_definition(definition: Any) -> list[str]:
    """Return every problem with `definition`; an empty list means valid."""
    problems: list[str] = []

    if not isinstance(definition, dict):
        return ["definition must be an object with 'nodes' and 'edges'"]

    nodes = definition.get("nodes")
    edges = definition.get("edges")

    if not isinstance(nodes, list):
        problems.append("'nodes' must be a list")
        nodes = []
    if not isinstance(edges, list):
        problems.append("'edges' must be a list")
        edges = []

    if len(nodes) > MAX_NODES:
        problems.append(f"too many nodes ({len(nodes)} > {MAX_NODES})")
    if len(edges) > MAX_EDGES:
        problems.append(f"too many edges ({len(edges)} > {MAX_EDGES})")

    seen: set[str] = set()
    triggers = 0
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            problems.append(f"node {index} must be an object")
            continue
        node_id = node.get("id")
        if not _is_str(node_id):
            problems.append(f"node {index} has no id")
            continue
        if node_id in seen:
            problems.append(f"duplicate node id '{node_id}'")
            continue
        seen.add(node_id)

        node_type = node.get("type")
        if node_type not in NODE_TYPES:
            problems.append(
                f"node '{node_id}' has unknown type '{node_type}' "
                f"(expected one of {', '.join(NODE_TYPES)})"
            )
        elif node_type == "trigger":
            triggers += 1

        config = node.get("config")
        if config is not None and not isinstance(config, dict):
            problems.append(f"node '{node_id}' config must be an object")

    if triggers == 0:
        problems.append("definition needs exactly one 'trigger' node, found none")
    elif triggers > 1:
        problems.append(f"definition needs exactly one 'trigger' node, found {triggers}")

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            problems.append(f"edge {index} must be an object")
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not _is_str(source) or not _is_str(target):
            problems.append(f"edge {index} needs both 'source' and 'target'")
            continue
        for endpoint, role in ((source, "source"), (target, "target")):
            if endpoint not in seen:
                problems.append(
                    f"edge {index} {role} '{endpoint}' does not match any declared node"
                )

    return problems


def empty_definition() -> dict:
    """The definition a freshly created workflow starts with."""
    return {"nodes": [], "edges": []}
