# DEPRECATED — profile state no longer lives in this daemon-side cache.
#
# Before Phase 2: this module held an in-memory mirror of the global
# `erp_agent.profiles` ir.config_parameter. The chat path read it via
# `profiles.get(ctx.profile_id)`. That made profiles a single shared list
# across all users with a per-request mutation race in `_sync_provider`.
#
# After Phase 2: each user has their own `erp_agent.profile` records (scoped
# by record rule). The `/erp_agent/chat` controller resolves the active
# profile for `request.env.user` and includes it in the chat bundle. The
# daemon reads it from `AgentContext.profile`, never from this cache.
#
# Kept as a stub so any legacy import doesn't crash; all functions are
# no-ops. Delete after confirming no stale imports remain.

import json
import uuid

from loguru import logger

_PARAM = "erp_agent.profiles"

# _cache: list | None = None
#
#
# def _parse(raw: str) -> list:
#     try:
#         data = json.loads(raw or "[]")
#     except Exception:
#         data = []
#     return data if isinstance(data, list) else []
#
#
# def refresh(icp) -> list:
#     global _cache
#     _cache = _parse(icp.get_param(_PARAM, default="[]"))
#     return _cache
#
#
# def _save(icp, profiles: list) -> None:
#     icp.set_param(_PARAM, json.dumps(profiles))
#     global _cache
#     _cache = profiles
#
#
# def invalidate() -> None:
#     global _cache
#     _cache = None
#
#
# def list_profiles() -> list:
#     return _cache or []
#
#
# def get(profile_id: str) -> dict | None:
#     if not profile_id:
#         return None
#     for p in (_cache or []):
#         if p.get("id") == profile_id:
#             return p
#     return None
#
#
# def create(icp, name: str, model: str, api_key: str) -> dict:
#     profiles = list(_parse(icp.get_param(_PARAM, default="[]")))
#     profile = {
#         "id": str(uuid.uuid4()),
#         "name": name,
#         "model": model,
#         "api_key": api_key,
#     }
#     profiles.append(profile)
#     _save(icp, profiles)
#     logger.info(f"[profiles] created {profile['id']} ({name})")
#     return profile
#
#
# def update(icp, profile_id: str, name=None, model=None, api_key=None) -> dict | None:
#     profiles = list(_parse(icp.get_param(_PARAM, default="[]")))
#     updated = None
#     for p in profiles:
#         if p.get("id") == profile_id:
#             if name:
#                 p["name"] = name
#             if model:
#                 p["model"] = model
#             if api_key:
#                 p["api_key"] = api_key
#             updated = p
#             break
#     if updated:
#         _save(icp, profiles)
#         logger.info(f"[profiles] updated {profile_id}")
#     return updated
#
#
# def delete(icp, profile_id: str) -> bool:
#     profiles = list(_parse(icp.get_param(_PARAM, default="[]")))
#     remaining = [p for p in profiles if p.get("id") != profile_id]
#     if len(remaining) == len(profiles):
#         return False
#     _save(icp, remaining)
#     logger.info(f"[profiles] deleted {profile_id}")
#     return True
