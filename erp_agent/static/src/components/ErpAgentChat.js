/** @odoo-module **/
// OWL equivalent of frontend/app/page.tsx
// Will connect to: /erp_agent/chat (SSE), /erp_agent/health, /erp_agent/actions/<id>/confirm|cancel

// import { Component, useState, onMounted } from "@odoo/owl";
// import { registry } from "@web/core/registry";
//
// class ErpAgentChat extends Component {
//     static template = "erp_agent.ErpAgentChat";
//
//     setup() {
//         this.state = useState({ messages: [], input: "", pending: [] });
//         // onMounted → fetch health, load session
//     }
//
//     async sendMessage() {
//         // POST /erp_agent/chat → consume SSE stream
//         // push progress + response events into this.state.messages
//     }
//
//     async confirmAction(actionId) {
//         // POST /erp_agent/actions/<actionId>/confirm
//     }
//
//     async cancelAction(actionId) {
//         // POST /erp_agent/actions/<actionId>/cancel
//     }
// }
//
// registry.category("actions").add("erp_agent_chat", ErpAgentChat);
