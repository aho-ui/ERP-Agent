from odoo import models, fields


class ErpAgentConversation(models.Model):
    _name = "erp_agent.conversation"
    _description = "ERP Agent Conversation"
    _order = "write_date desc"

    name = fields.Char(required=True, default="Conversation")
    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
        default=lambda self: self.env.user.id,
    )
    message_ids = fields.One2many(
        "erp_agent.message", "conversation_id", string="Messages"
    )
    system_prompt_override = fields.Text()


class ErpAgentMessage(models.Model):
    _name = "erp_agent.message"
    _description = "ERP Agent Message"
    _order = "id"

    conversation_id = fields.Many2one(
        "erp_agent.conversation",
        required=True,
        index=True,
        ondelete="cascade",
    )
    role = fields.Selection(
        [("user", "User"), ("assistant", "Assistant"), ("error", "Error")],
        required=True,
    )
    content = fields.Text()
    artifacts = fields.Text()
    steps = fields.Text()
    tools_used = fields.Text()
    agent_name = fields.Char()
    prompt_tokens = fields.Integer(default=0)
    completion_tokens = fields.Integer(default=0)
    model = fields.Char()
    cost_usd = fields.Float(digits=(10, 6), default=0.0)
