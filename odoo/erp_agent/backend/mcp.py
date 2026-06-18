from pathlib import Path
from nanobot.config.schema import MCPServerConfig

_HERE = Path(__file__).parent


SERVERS = {
    "odoo": MCPServerConfig(
        type="stdio",
        command="python",
        args=[str(_HERE / "mcp_servers" / "odoo.py")],
        env={},
    ),
    "sqlite": MCPServerConfig(
        type="stdio",
        command="python",
        args=[str(_HERE / "mcp_servers" / "sqlite.py")],
    ),
}
