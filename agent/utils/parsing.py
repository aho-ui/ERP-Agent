from typing import NamedTuple

import json_repair
from loguru import logger


class ParseResult(NamedTuple):
    summary: str
    confirmation_required: bool
    artifacts: list


def parse_agent_response(raw: str, agent_name: str, task: str, q, fallback: str, action_id=None) -> ParseResult:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    try:
        parsed = json_repair.loads(text)
        if not isinstance(parsed, dict):
            logger.warning(f"[{agent_name}] response not a dict after parse, skipping artifact")
            return ParseResult(summary=fallback, confirmation_required=False, artifacts=[])

        summary = parsed.get("summary", fallback)

        if parsed.get("confirmation_required"):
            logger.info(f"[{agent_name}] confirmation required, queue={'found' if q else 'NOT FOUND'}")
            if q:
                q.put_nowait({
                    "type": "confirmation",
                    "agent_name": agent_name,
                    "task": task,
                    "summary": summary,
                    "action_id": str(action_id) if action_id else None,
                })
            return ParseResult(summary=summary, confirmation_required=True, artifacts=[])

        collected: list = []

        chart_spec = parsed.get("chart")
        if chart_spec and isinstance(chart_spec, dict):
            artifact = {
                "artifact_type": "chart",
                "chart_type": chart_spec.get("type", "bar"),
                "title": chart_spec.get("title", ""),
                "x_key": chart_spec.get("x_key", ""),
                "series": chart_spec.get("series", []),
                "data": chart_spec.get("data", []),
            }
            collected.append(artifact)
            logger.info(f"[{agent_name}] emitting chart artifact, queue={'found' if q else 'NOT FOUND'}")
            if q:
                q.put_nowait({"type": "artifact", **artifact})

        records = parsed.get("records")
        if records and isinstance(records, list) and len(records) > 0:
            columns = list(records[0].keys())
            rows = [list(r.values()) for r in records]
            title = parsed.get("title", parsed.get("summary", "export"))[:60]
            artifact = {"artifact_type": "table", "columns": columns, "rows": rows, "title": title}
            collected.append(artifact)
            logger.info(f"[{agent_name}] emitting table artifact: {len(rows)} rows, queue={'found' if q else 'NOT FOUND'}")
            if q:
                q.put_nowait({"type": "artifact", **artifact})
                try:
                    import base64
                    from agent.utils.table_image import render_table_image
                    img = render_table_image(columns, rows)
                    q.put_nowait({"type": "image", "content": base64.b64encode(img).decode()})
                except Exception as e:
                    logger.warning(f"[{agent_name}] table image render failed: {e}")
        else:
            logger.info(f"[{agent_name}] no records in response, summary only")

        return ParseResult(summary=summary, confirmation_required=False, artifacts=collected)
    except Exception as e:
        logger.warning(f"[{agent_name}] artifact parse failed: {e}")
        return ParseResult(summary=fallback, confirmation_required=False, artifacts=[])
