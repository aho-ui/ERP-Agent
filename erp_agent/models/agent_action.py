# Equivalent of agent/models.py:AgentAction
# Will connect to: framework/agents/dispatch.py (writes action records + status updates)

# from odoo import models, fields
#
# class AgentAction(models.Model):
#     _name = "erp_agent.action"
#     _description = "Agent Action"
#     _order = "create_date desc"
#     run_id = fields.Char()
#     source = fields.Char(default="odoo")
#     user_id = fields.Char()
#     intent = fields.Char()
#     agent_name = fields.Char()
#     tool_called = fields.Char(default="")
#     status = fields.Selection([("pending","Pending"),("approved","Approved"),
#                                ("success","Success"),("failed","Failed")], default="pending")
#     input_params = fields.Json(default=dict)
#     output = fields.Json(default=dict)
#     artifacts = fields.Json(default=list)
