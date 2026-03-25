from MCP.servers.odoo import health as _odoo_health
from MCP.servers.sqlite import health as _sqlite_health

HEALTH_CHECKS: dict[str, callable] = {
    "odoo": _odoo_health,
    "sqlite": _sqlite_health,
}


def check_all() -> dict[str, bool]:
    return {name: fn() for name, fn in HEALTH_CHECKS.items()}
