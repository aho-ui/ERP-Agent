import asyncio

from loguru import logger

from backend.agent_loop import get_agent_loop, rebuild, wrap_mcp_tools
from backend.health import probe_all

_INTERVAL = 30        # seconds between health ticks (e.g. 1800 = 30 min)
_READY_TIMEOUT = 60
_ready = asyncio.Event()


async def wait_ready() -> None:
    try:
        await asyncio.wait_for(_ready.wait(), timeout=_READY_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("[monitor] not ready within timeout; continuing")


async def run_monitor() -> None:
    agent = get_agent_loop()
    try:
        await agent._connect_mcp()          # this task owns the MCP stack (anyio requirement)
        wrap_mcp_tools(agent)
        prev = await probe_all(agent.tools)
        logger.info(f"[monitor] boot states: {prev}")
    finally:
        _ready.set()

    while True:
        await asyncio.sleep(_INTERVAL)
        try:
            states = await probe_all(agent.tools)
            if states != prev:
                logger.info(f"[monitor] {prev} -> {states}; state changed")
            if any(st == 0 for st in states.values()):
                await rebuild()
                states = await probe_all(agent.tools)
            prev = states
        except Exception as e:
            logger.error(f"[monitor] tick failed: {e}")
