from odoo import models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    erp_agent_disabled_defaults = fields.Text(default="[]")
