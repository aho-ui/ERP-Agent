# Odoo HTTP layer — equivalent of agent/api/
# Will connect to: framework/main.py (agent loop), utils/mcp/ (health)
#
# from odoo import http
# from odoo.http import request
#
# class NanobotController(http.Controller):
#
#     @http.route("/erp_agent/chat", auth="user", methods=["POST"], csrf=False)
#     def chat(self, **kwargs):
#         # → framework/main.py:get_agent_loop(), set_context()
#         pass
#
#     @http.route("/erp_agent/health", auth="user", methods=["GET", "POST"], csrf=False)
#     def health(self, **kwargs):
#         # GET  → utils/mcp:_health_cache
#         # POST → utils/mcp:health(), then DispatchTool.refresh()
#         pass
#
#     @http.route("/erp_agent/sessions", auth="user", methods=["GET", "POST"], csrf=False)
#     def sessions(self, **kwargs):
#         # → nanobot.session model (to be added)
#         pass
#
#     @http.route("/erp_agent/actions", auth="user", methods=["GET"], csrf=False)
#     def actions(self, **kwargs):
#         # → nanobot.action model
#         pass
#
#     @http.route("/erp_agent/actions/<int:action_id>/confirm", auth="user", methods=["POST"], csrf=False)
#     def confirm_action(self, action_id, **kwargs):
#         # → framework/agents/dispatch.py confirmation flow
#         pass
#
#     @http.route("/erp_agent/actions/<int:action_id>/cancel", auth="user", methods=["POST"], csrf=False)
#     def cancel_action(self, action_id, **kwargs):
#         pass
