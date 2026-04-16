import os
from pyngrok import ngrok

_tunnels: dict[str, str] = {}


def start_tunnel(bot_id: str, path: str, port: int = 8000) -> str:
    if bot_id in _tunnels:
        return _tunnels[bot_id]
    token = os.environ.get("NGROK_AUTHTOKEN")
    if token:
        ngrok.set_auth_token(token)
    tunnel = ngrok.connect(port, "http")
    url = f"{tunnel.public_url}{path}"
    _tunnels[bot_id] = url
    return url


def stop_tunnel(bot_id: str):
    url = _tunnels.pop(bot_id, None)
    if url:
        public_url = url.split("/api/")[0]
        ngrok.disconnect(public_url)


def get_tunnel(bot_id: str) -> str | None:
    return _tunnels.get(bot_id)


def get_tunnel_base(bot_id: str) -> str | None:
    url = _tunnels.get(bot_id)
    if not url:
        return None
    return url.split("/api/")[0]
