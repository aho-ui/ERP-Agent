/** @odoo-module **/
import { Component, useState, markup, onWillStart, useRef, useEffect } from "@odoo/owl";
import { session } from "@web/session";

const BACKEND_URL = "http://localhost:8001/";
const CONV_URL = "/erp_agent/conversation";

const TOOL_RE = /-> (mcp_\w+)\(/;
function _toolsFromSteps(steps) {
    const out = [];
    for (const s of steps || []) {
        const m = TOOL_RE.exec(String(s || ""));
        if (m) out.push(m[1]);
    }
    return out;
}

export class ErpAgentChat extends Component {
    static template = "erp_agent.ErpAgentChat";
    static props = { onSettings: Function, profileId: { type: String, optional: true } };

    setup() {
        this.state = useState({
            conversations: [],   // [{id, name, messages: [], loaded: bool}]
            activeId: null,
            showDropdown: false,
            input: "",
            loading: false,
            liveSteps: [],       // progress lines for the in-flight turn
        });
        this._abortCtrl = null;  // AbortController for the in-flight chat fetch
        this.messagesRef = useRef("messages");

        // auto-scroll to bottom whenever the active conversation's message
        // count changes (new messages) or a live step comes in
        useEffect(
            () => {
                const el = this.messagesRef.el;
                if (el) el.scrollTop = el.scrollHeight;
            },
            () => [this.messages.length, this.state.liveSteps.length, this.state.activeId]
        );

        onWillStart(async () => {
            await this.loadConversations();
            if (this.state.conversations.length === 0) {
                await this.newConv();
            } else {
                await this.switchConv(this.state.conversations[0].id);
            }
        });
    }

    // --- Odoo controller RPC (same origin, trusted user) ---
    async _rpc(action, params = {}) {
        const r = await fetch(CONV_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { action, ...params } }),
        });
        const data = await r.json();
        return data.result;
    }

    get activeConv() {
        return this.state.conversations.find(c => c.id === this.state.activeId) || null;
    }

    get messages() {
        return this.activeConv ? this.activeConv.messages : [];
    }

    // stored message rows -> UI bubbles (mirror of live SSE handling)
    _rowsToUI(rows) {
        const out = [];
        for (const m of rows) {
            if (m.artifacts) {
                let arts = [];
                try { arts = JSON.parse(m.artifacts); } catch (e) { arts = []; }
                for (const a of arts) {
                    if (a.artifact_type === "table") {
                        out.push({
                            role: "assistant", type: "table",
                            title: a.title, columns: a.columns, rows: a.rows,
                        });
                    }
                }
            }
            if (m.content) {
                let steps;
                try { steps = m.steps ? JSON.parse(m.steps) : undefined; } catch (e) { steps = undefined; }
                let tools = [];
                try { tools = m.tools_used ? JSON.parse(m.tools_used) : []; } catch (e) { tools = []; }
                out.push({ role: m.role, text: m.content, steps, tools });
            }
        }
        return out;
    }

    async loadConversations() {
        const res = await this._rpc("list");
        this.state.conversations = (res?.conversations || []).map(c => ({
            id: c.id, name: c.name, messages: [], loaded: false,
        }));
    }

    async switchConv(id) {
        this.state.activeId = id;
        this.state.showDropdown = false;
        const conv = this.activeConv;
        if (conv && !conv.loaded) {
            const res = await this._rpc("messages", { id });
            conv.messages = this._rowsToUI(res?.messages || []);
            conv.loaded = true;
        }
    }

    async newConv() {
        const res = await this._rpc("create");
        if (res?.ok && res.conversation) {
            const c = { id: res.conversation.id, name: res.conversation.name, messages: [], loaded: true };
            this.state.conversations.unshift(c);
            this.state.activeId = c.id;
        }
        this.state.showDropdown = false;
    }

    async deleteConv(id) {
        await this._rpc("delete", { id });
        const idx = this.state.conversations.findIndex(c => c.id === id);
        if (idx !== -1) this.state.conversations.splice(idx, 1);
        if (this.state.conversations.length === 0) {
            await this.newConv();
        } else if (this.state.activeId === id) {
            await this.switchConv(this.state.conversations[Math.max(0, idx - 1)].id);
        }
    }

    async renameConv(id) {
        const conv = this.state.conversations.find(c => c.id === id);
        const name = window.prompt("Rename conversation", conv?.name || "");
        if (!name || !name.trim() || name.trim() === conv.name) return;
        const res = await this._rpc("rename", { id, name: name.trim() });
        if (res?.ok) conv.name = name.trim();
    }

    toggleDropdown() {
        this.state.showDropdown = !this.state.showDropdown;
    }

    async _persist(role, content, artifacts, steps) {
        try {
            await this._rpc("append", {
                id: this.state.activeId,
                role,
                content: content || "",
                artifacts: artifacts || "",
                steps: steps || "",
            });
        } catch (e) {
            // non-fatal: message still shows in UI this session
        }
    }

    async onSend() {
        if (!this.state.input.trim() || this.state.loading || !this.activeConv) return;
        const text = this.state.input.trim();
        const conv = this.activeConv;
        conv.messages.push({ text, role: "user" });
        this.state.input = "";
        this.state.loading = true;
        this.state.liveSteps = [];
        this._abortCtrl = new AbortController();
        await this._persist("user", text);

        const tables = [];
        let answer = "";
        try {
            const resp = await fetch(`${BACKEND_URL}chat/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    session_key: `odoo:conv:${conv.id}`,
                    profile_id: this.props.profileId || "",
                    uid: session.user_id || null,
                }),
                signal: this._abortCtrl.signal,
            });
            if (!resp.ok) throw new Error(`${resp.status}`);
            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const data = line.slice(6);
                    if (data === "[DONE]") continue;
                    const event = JSON.parse(data);
                    if (event.type === "progress") {
                        if (!String(event.content).startsWith("Tokens:")) {
                            this.state.liveSteps.push(event.content);
                        }
                    } else if (event.type === "response") {
                        answer = event.content;
                        conv.messages.push({
                            text: event.content, role: "assistant",
                            steps: [...this.state.liveSteps],
                            tools: _toolsFromSteps(this.state.liveSteps),
                        });
                    } else if (event.type === "artifact" && event.artifact_type === "table") {
                        const t = {
                            artifact_type: "table",
                            title: event.title, columns: event.columns, rows: event.rows,
                        };
                        tables.push(t);
                        conv.messages.push({
                            role: "assistant", type: "table",
                            title: event.title, columns: event.columns, rows: event.rows,
                        });
                    }
                }
            }
            if (answer) await this._persist("assistant", answer, "", JSON.stringify(this.state.liveSteps));
            for (const t of tables) await this._persist("assistant", "", JSON.stringify([t]));
        } catch (e) {
            if (e.name === "AbortError") {
                const note = "Cancelled by user.";
                conv.messages.push({ text: note, role: "error" });
                await this._persist("error", note);
            } else {
                conv.messages.push({ text: `Error: ${e.message}`, role: "error" });
                await this._persist("error", `Error: ${e.message}`);
            }
        } finally {
            this.state.loading = false;
            this.state.liveSteps = [];
            this._abortCtrl = null;
        }
    }

    cancelSend() {
        if (this._abortCtrl) this._abortCtrl.abort();
    }

    serversFromTools(tools) {
        const servers = new Set();
        for (const t of tools || []) {
            const parts = String(t).split("_");
            if (parts[0] === "mcp" && parts.length >= 2) servers.add(parts[1]);
        }
        return [...servers];
    }

    formatText(text) {
        const raw = String(text ?? "");
        // full markdown via vendored marked + DOMPurify (static/src/lib).
        // try/catch → if a lib failed to load, degrade to escaped plain text.
        try {
            const dirty = window.marked.parse(raw, { breaks: true });
            return markup(window.DOMPurify.sanitize(dirty));
        } catch (e) {
            const esc = raw
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\n/g, "<br/>");
            return markup(esc);
        }
    }

    downloadTable(msg) {
        const csv = [
            msg.columns.join(","),
            ...msg.rows.map(r => r.map(c => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")),
        ].join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${msg.title || "export"}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    onKeydown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            this.onSend();
        }
    }
}
