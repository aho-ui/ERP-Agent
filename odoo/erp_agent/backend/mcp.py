from pathlib import Path
from nanobot.config.schema import MCPServerConfig

from backend import odoo_backend

_HERE = Path(__file__).parent


def _odoo_env() -> dict:
    # creds set via Settings UI; falls back to the script's hardcoded defaults
    # if the file isn't there yet (you'll see DOWN in Health until configured)
    cfg = odoo_backend.load()
    env = {}
    if cfg.get("url"):       env["ODOO_URL"] = cfg["url"]
    if cfg.get("db"):        env["ODOO_DB"] = cfg["db"]
    if cfg.get("user"):      env["ODOO_USER"] = cfg["user"]
    if cfg.get("password"):  env["ODOO_PASSWORD"] = cfg["password"]
    return env


SERVERS = {
    "odoo": MCPServerConfig(
        type="stdio",
        command="python",
        args=[str(_HERE / "mcp_servers" / "odoo.py")],
        env=_odoo_env(),
    ),
    "sqlite": MCPServerConfig(
        type="stdio",
        command="python",
        args=[str(_HERE / "mcp_servers" / "sqlite.py")],
    ),
}


def reload_odoo_env() -> None:
    # called by the controller after saving creds so a subsequent rebuild()
    # spawns the odoo subprocess with the new env
    SERVERS["odoo"].env = _odoo_env()
