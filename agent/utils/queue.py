import asyncio

_ARTIFACT_TYPES = {"pdf", "image", "artifact"}


class CollectingQueue(asyncio.Queue):
    def __init__(self):
        super().__init__()
        self.artifacts: list = []
        self.steps: list = []

    def put_nowait(self, item):
        if isinstance(item, dict) and item.get("type") in _ARTIFACT_TYPES:
            self.artifacts.append(item)
        if isinstance(item, dict) and item.get("type") == "progress":
            self.steps.append(item["content"])
        super().put_nowait(item)
