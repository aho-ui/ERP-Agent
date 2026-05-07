/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { DEFAULT_URL, DEFAULT_API_KEY } from "../../test/agent";

export class AgentSettings extends Component {
    static template = "erp_agent.AgentSettings";
    static props = { onBack: Function };

    setup() {
        this.state = useState({
            url: localStorage.getItem("erp_agent_url") || DEFAULT_URL,
            apiKey: localStorage.getItem("erp_agent_api_key") || DEFAULT_API_KEY,
        });
    }

    onSave() {
        // stored locally for now — wired to backend in phase 2
        localStorage.setItem("erp_agent_url", this.state.url);
        localStorage.setItem("erp_agent_api_key", this.state.apiKey);
        this.props.onBack();
    }
}
