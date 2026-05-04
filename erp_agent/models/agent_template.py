# Equivalent of agent/models.py:AgentTemplate
# Will connect to: framework/agents/registry.py (reads templates to build dispatch)

# from odoo import models, fields
#
# class AgentTemplate(models.Model):
#     _name = "erp_agent.template"
#     _description = "Agent Template"
#     name = fields.Char(required=True)
#     description = fields.Char()
#     instructions = fields.Text()
#     allowed_tools = fields.Json(default=list)
#     tool_config = fields.Json(default=dict)
#     requires_write_access = fields.Boolean(default=False)
#     is_active = fields.Boolean(default=True)
#     is_default = fields.Boolean(default=False)
