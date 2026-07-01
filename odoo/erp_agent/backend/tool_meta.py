import ast
import logging
from pathlib import Path

_logger = logging.getLogger(__name__)

_BASE_OPS: set[tuple[str, str]] = {("ir.model", "search")}
_MCP_SOURCE = Path(__file__).resolve().parent / "mcp_servers" / "odoo.py"


def _parse() -> tuple[dict[str, set[tuple[str, str]]], set[str]]:
    ops_by_tool: dict[str, set[tuple[str, str]]] = {}
    write_tools: set[str] = set()
    try:
        tree = ast.parse(_MCP_SOURCE.read_text(encoding="utf-8"))
    except Exception:
        _logger.exception("[tool_meta] failed to parse %s", _MCP_SOURCE)
        return ops_by_tool, write_tools

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        is_tool = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "tool"
            for d in node.decorator_list
        )
        if not is_tool:
            continue

        ops: set[tuple[str, str]] = set(_BASE_OPS)
        declared = False
        is_write = False
        for d in node.decorator_list:
            if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "needs"):
                continue
            if d.args and isinstance(d.args[0], (ast.List, ast.Tuple)):
                for elt in d.args[0].elts:
                    if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2):
                        continue
                    m, mth = elt.elts
                    if isinstance(m, ast.Constant) and isinstance(mth, ast.Constant):
                        ops.add((m.value, mth.value))
                        declared = True
            for kw in d.keywords:
                if kw.arg == "write" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    is_write = True

        if declared:
            ops_by_tool[node.name] = ops
            if is_write:
                write_tools.add(node.name)
    return ops_by_tool, write_tools


TOOL_ALLOWED_OPS, WRITE_TOOLS = _parse()
WRITE_TOOLS_PREFIXED: set[str] = {f"mcp_odoo_{name}" for name in WRITE_TOOLS}
