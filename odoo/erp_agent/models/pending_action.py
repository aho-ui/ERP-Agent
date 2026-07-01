from odoo import fields, models


class ErpAgentPendingAction(models.Model):
    _name = "erp_agent.pending_action"
    _description = "ERP Agent Pending Action"
    _order = "id desc"

    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.user.id,
    )
    conversation_id = fields.Many2one(
        "erp_agent.conversation",
        required=True,
        index=True,
        ondelete="cascade",
    )
    tool_name = fields.Char(required=True)
    payload_json = fields.Text()
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("executed", "Executed"),
            ("failed", "Failed"),
        ],
        required=True,
        default="pending",
        index=True,
    )
    created_at = fields.Datetime(default=fields.Datetime.now)
    acted_at = fields.Datetime()
    result = fields.Text()
    error = fields.Text()
