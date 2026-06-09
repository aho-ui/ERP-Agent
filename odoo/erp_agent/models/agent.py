from odoo import models, fields


class ErpAgentAgent(models.Model):
    _name = "erp_agent.agent"
    _description = "ERP Agent (custom)"
    _order = "name"

    name = fields.Char(required=True)
    description = fields.Char()
    system_prompt = fields.Text(required=True)
    allowed_tools = fields.Text()  # JSON list of mcp_<server>_<tool>
    active = fields.Boolean(default=True)
    user_id = fields.Many2one(
        "res.users",
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.user.id,
    )  # reserved for per-user scoping; not enforced yet
