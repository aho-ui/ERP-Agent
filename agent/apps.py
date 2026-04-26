from django.apps import AppConfig
from django.db.models.signals import post_migrate
from loguru import logger

from agent.framework.nanobot.agents.factory import seed_from_yaml


def _seed(sender, **kwargs):
    if sender.name != "agent":
        return
    count = seed_from_yaml(["odoo.yaml", "demo.yaml"])
    if count:
        logger.info(f"Seeded {count} default agent template(s) from YAML")


class AgentConfig(AppConfig):
    name = "agent"

    def ready(self):
        post_migrate.connect(_seed, sender=self)
