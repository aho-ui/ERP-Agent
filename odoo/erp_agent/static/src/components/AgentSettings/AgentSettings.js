/** @odoo-module **/
import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";

export class AgentSettings extends Component {
    static template = "erp_agent.AgentSettings";
    static props = { onBack: Function, profileId: String, onSelectProfile: Function };

    setup() {
        this.state = useState({
            profiles: [],
            models: [],
            mode: "list",
            formMode: "create",
            form: { id: "", name: "", model: "", apiKey: "" },
            showLogs: false,
            logs: [],
            running: false,
            error: "",
            busy: false,
        });
        this._logTimer = null;

        onWillStart(() => this.loadProfiles());
        onWillUnmount(() => this._stopLogPoll());
    }

    async _rpc(url, params = {}) {
        const r = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params }),
        });
        const data = await r.json();
        return data.result;
    }

    get currentProfile() {
        return this.state.profiles.find(p => p.id === this.props.profileId) || null;
    }

    async loadProfiles() {
        try {
            const res = await this._rpc("/erp_agent/profile", { action: "list" });
            this.state.profiles = res?.profiles || [];
            this.state.models = res?.models || [];
            this.state.error = "";
        } catch (e) {
            this.state.error = e.message;
        }
    }

    onSelect(ev) {
        this.props.onSelectProfile(ev.target.value);
    }

    async onRefresh() {
        await this.loadProfiles();
    }

    openCreate() {
        this.state.formMode = "create";
        this.state.form = { id: "", name: "", model: this.state.models[0] || "", apiKey: "" };
        this.state.mode = "form";
    }

    openEdit() {
        const p = this.currentProfile;
        if (!p) return;
        this.state.formMode = "edit";
        this.state.form = { id: p.id, name: p.name, model: p.model, apiKey: "" };
        this.state.mode = "form";
    }

    cancelForm() {
        this.state.mode = "list";
        this.state.error = "";
    }

    async onSave() {
        const f = this.state.form;
        if (!f.name.trim() || !f.model) {
            this.state.error = "Name and model are required.";
            return;
        }
        if (this.state.formMode === "create" && !f.apiKey.trim()) {
            this.state.error = "API key is required.";
            return;
        }
        this.state.busy = true;
        this.state.error = "";
        try {
            const action = this.state.formMode === "create" ? "create" : "update";
            const res = await this._rpc("/erp_agent/profile", {
                action,
                id: f.id,
                name: f.name,
                model: f.model,
                api_key: f.apiKey,
            });
            if (res?.ok && res.profile) {
                await this.loadProfiles();
                this.props.onSelectProfile(res.profile.id);
                this.state.mode = "list";
            } else {
                this.state.error = "Save failed.";
            }
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.busy = false;
        }
    }

    async onDelete() {
        const p = this.currentProfile;
        if (!p) return;
        this.state.busy = true;
        try {
            await this._rpc("/erp_agent/profile", { action: "delete", id: p.id });
            await this.loadProfiles();
            this.props.onSelectProfile(this.state.profiles[0]?.id || "");
        } catch (e) {
            this.state.error = e.message;
        } finally {
            this.state.busy = false;
        }
    }

    toggleLogs() {
        this.state.showLogs = !this.state.showLogs;
        if (this.state.showLogs) {
            this.refreshLogs();
            this._logTimer = setInterval(() => this.refreshLogs(), 2000);
        } else {
            this._stopLogPoll();
        }
    }

    _stopLogPoll() {
        if (this._logTimer) {
            clearInterval(this._logTimer);
            this._logTimer = null;
        }
    }

    async refreshLogs() {
        try {
            const data = await this._rpc("/erp_agent/logs");
            this.state.running = data?.running ?? false;
            this.state.logs = data?.logs ?? [];
        } catch (e) {
            this.state.error = e.message;
        }
    }
}
