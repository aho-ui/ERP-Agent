from odoo import models, fields


class ErpAgentProfile(models.Model):
    _name = "erp_agent.profile"
    _description = "ERP Agent LLM Profile (per-user)"
    _order = "name"

    name = fields.Char(required=True)
    model = fields.Char(required=True)
    api_key = fields.Char()
    user_id = fields.Many2one(
        "res.users",
        index=True,
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.user.id,
    )
