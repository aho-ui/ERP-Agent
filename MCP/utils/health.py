from MCP.servers.odoo import health as _odoo_health
from MCP.servers.sqlite import health as _sqlite_health
from MCP.servers.info_extraction import health as _extraction_health

HEALTH_CHECKS: dict[str, callable] = {
    "odoo": _odoo_health,
    "sqlite": _sqlite_health,
    "extraction": _extraction_health,
}


def check_all() -> dict[str, bool]:
    return {name: fn() for name, fn in HEALTH_CHECKS.items()}
