import ast
import json
import logging
from pathlib import Path

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ._helpers import _ensure_path

_logger = logging.getLogger(__name__)

_BASE_OPS = {("ir.model", "search")}
_MCP_SOURCE = Path(__file__).resolve().parent.parent / "backend" / "mcp_servers" / "odoo.py"


def _load_allowlist() -> dict:
    out: dict = {}
    try:
        tree = ast.parse(_MCP_SOURCE.read_text(encoding="utf-8"))
    except Exception:
        _logger.exception("[internal] failed to parse %s for allowlist", _MCP_SOURCE)
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        is_tool = any(
            isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == "tool"
            for d in node.decorator_list
        )
        if not is_tool:
            continue
        ops: set = set(_BASE_OPS)
        declared = False
        for d in node.decorator_list:
            if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "needs"):
                continue
            if not d.args or not isinstance(d.args[0], (ast.List, ast.Tuple)):
                continue
            for elt in d.args[0].elts:
                if not (isinstance(elt, ast.Tuple) and len(elt.elts) == 2):
                    continue
                m, mth = elt.elts
                if isinstance(m, ast.Constant) and isinstance(mth, ast.Constant):
                    ops.add((m.value, mth.value))
                    declared = True
        if declared:
            out[node.name] = ops
    return out


_TOOL_ALLOWED_OPS = _load_allowlist()


def _err(msg, status=400):
    return Response(json.dumps({"error": msg}), status=status, mimetype="application/json")


class InternalController(http.Controller):

    @http.route("/erp_agent/internal/execute", type="http", auth="public",
                methods=["POST"], csrf=False)
    def execute(self, **kw):
        _ensure_path()
        from backend.gateway import verify

        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return _err("invalid JSON", 400)

        token = body.get("token")
        if not token:
            return _err("missing token", 401)
        payload = verify(token)
        if payload is None:
            return _err("invalid or expired token", 401)

        uid = payload.get("uid")
        if not uid:
            return _err("token missing uid", 401)

        model = body.get("model")
        method = body.get("method")
        args = body.get("args") or []
        kwargs = body.get("kwargs") or {}
        if not model or not method:
            return _err("model and method required", 400)

        op = payload.get("op")
        allowed = _TOOL_ALLOWED_OPS.get(op, set())
        if (model, method) not in allowed:
            return _err("operation not allowed for this token", 403)

        try:
            env = request.env(user=int(uid))
            recordset = env[model]
            fn = getattr(recordset, method, None)
            if fn is None or not callable(fn):
                return _err(f"unknown method: {model}.{method}", 400)
            result = fn(*args, **kwargs)
        except Exception:
            _logger.exception("[internal] %s.%s failed", model, method)
            return _err("execution failed", 500)

        return Response(
            json.dumps({"result": result}, default=str),
            mimetype="application/json",
        )
