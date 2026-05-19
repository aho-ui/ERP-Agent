/** @odoo-module **/
import { Component, useState, markup } from "@odoo/owl";

const BACKEND_URL = "http://localhost:8001/";

export class ErpAgentChat extends Component {
    static template = "erp_agent.ErpAgentChat";
    static props = { onSettings: Function, profileId: { type: String, optional: true } };

    setup() {
        this.state = useState({
            conversations: [{ id: 1, name: "Conversation 1", messages: [] }],
            activeId: 1,
            showDropdown: false,
            input: "",
            nextId: 2,
            loading: false,
        });
    }

    get activeConv() {
        return this.state.conversations.find(c => c.id === this.state.activeId);
    }

    get messages() {
        return this.activeConv ? this.activeConv.messages : [];
    }

    switchConv(id) {
        this.state.activeId = id;
        this.state.showDropdown = false;
    }

    newConv() {
        const id = this.state.nextId++;
        this.state.conversations.push({ id, name: `Conversation ${id}`, messages: [] });
        this.state.activeId = id;
        this.state.showDropdown = false;
    }

    deleteConv(id) {
        const idx = this.state.conversations.findIndex(c => c.id === id);
        this.state.conversations.splice(idx, 1);
        if (this.state.conversations.length === 0) {
            const newId = this.state.nextId++;
            this.state.conversations.push({ id: newId, name: `Conversation ${newId}`, messages: [] });
            this.state.activeId = newId;
        } else if (this.state.activeId === id) {
            this.state.activeId = this.state.conversations[Math.max(0, idx - 1)].id;
        }
    }

    toggleDropdown() {
        this.state.showDropdown = !this.state.showDropdown;
    }

    async onSend() {
        if (!this.state.input.trim() || this.state.loading) return;
        const text = this.state.input.trim();
        this.activeConv.messages.push({ text, role: "user" });
        this.state.input = "";
        this.state.loading = true;
        try {
            const resp = await fetch(`${BACKEND_URL}chat/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    session_key: `odoo:${this.state.activeId}`,
                    profile_id: this.props.profileId || "",
                }),
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
                    if (event.type === "response") {
                        this.activeConv.messages.push({ text: event.content, role: "assistant" });
                    } else if (event.type === "artifact" && event.artifact_type === "table") {
                        this.activeConv.messages.push({
                            role: "assistant",
                            type: "table",
                            title: event.title,
                            columns: event.columns,
                            rows: event.rows,
                        });
                    }
                }
            }
        } catch (e) {
            this.activeConv.messages.push({ text: `Error: ${e.message}`, role: "error" });
        } finally {
            this.state.loading = false;
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

    onKeydown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            this.onSend();
        }
    }
}
