/** @odoo-module **/
import { Component, useState, markup, onWillStart, onWillUnmount, useRef, useEffect } from "@odoo/owl";
import { chatService } from "./chatService";

const CONV_URL = "/erp_agent/conversation";
const PENDING_URL = "/erp_agent/pending_actions";
const PENDING_POLL_MS = 5000;

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
            conversations: [],
            activeId: null,
            showDropdown: false,
            input: "",
            loading: false,
            liveSteps: [],
            searchQuery: "",
            searchResults: [],
        });
        this._searchTimer = null;
        this._serviceUnsub = null;
        this._handledStatus = new Map();
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

        this._pendingPoll = setInterval(() => this._refreshPendingStatuses(), PENDING_POLL_MS);
        onWillUnmount(() => {
            clearInterval(this._pendingPoll);
            if (this._serviceUnsub) {
                this._serviceUnsub();
                this._serviceUnsub = null;
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

    async _pendingRpc(action, params = {}) {
        const r = await fetch(PENDING_URL, {
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
        this._subscribeToActive();
    }

    _subscribeToActive() {
        if (this._serviceUnsub) {
            this._serviceUnsub();
            this._serviceUnsub = null;
        }
        const convId = this.state.activeId;
        if (!convId) return;
        this._serviceUnsub = chatService.subscribe(convId, (s) => this._onServiceUpdate(convId, s));
        const snap = chatService.getState(convId);
        this._onServiceUpdate(convId, snap);
    }

    _onServiceUpdate(convId, s) {
        if (convId !== this.state.activeId) return;
        if (!s) {
            this.state.loading = false;
            this.state.liveSteps = [];
            return;
        }
        this.state.loading = s.status === "loading";
        this.state.liveSteps = [...s.liveSteps];

        // mirror in-flight pending bubbles into conv.messages so they render
        const conv = this.activeConv;
        if (conv) {
            const seen = new Set(conv.messages.filter(m => m.type === "pending").map(m => m.actionId));
            for (const pa of s.pendingActions) {
                if (!seen.has(pa.actionId)) {
                    conv.messages.push({
                        role: "assistant", type: "pending",
                        actionId: pa.actionId,
                        toolName: pa.toolName,
                        payload: pa.payload,
                        payloadText: JSON.stringify(pa.payload, null, 2),
                        status: "pending",
                        result: "",
                        error: "",
                    });
                }
            }
        }

        const finished = s.status === "done" || s.status === "error" || s.status === "aborted";
        if (finished && this._handledStatus.get(convId) !== s.status) {
            this._handledStatus.set(convId, s.status);
            this._refreshAfterFinish(convId);
        } else if (s.status === "loading") {
            this._handledStatus.set(convId, "loading");
        }
    }

    async _refreshAfterFinish(convId) {
        const conv = this.state.conversations.find(c => c.id === convId);
        if (!conv) return;
        try {
            const res = await this._rpc("messages", { id: convId });
            const pendingBubbles = conv.messages.filter(m => m.type === "pending");
            conv.messages = this._rowsToUI(res?.messages || []).concat(pendingBubbles);
            conv.loaded = true;
        } catch (e) {
            // best effort
        }
        this.state.loading = false;
        this.state.liveSteps = [];
    }

    async newConv() {
        const res = await this._rpc("create");
        if (res?.ok && res.conversation) {
            const c = { id: res.conversation.id, name: res.conversation.name, messages: [], loaded: true };
            this.state.conversations.unshift(c);
            this.state.activeId = c.id;
            this._subscribeToActive();
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

    async editSystemPrompt(id) {
        const cur = await this._rpc("get_system_prompt", { id });
        const next = window.prompt(
            "System prompt override for this conversation (leave blank to use the agent's default):",
            cur?.prompt || ""
        );
        if (next === null) return;
        await this._rpc("set_system_prompt", { id, prompt: next });
    }

    toggleDropdown() {
        this.state.showDropdown = !this.state.showDropdown;
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => this._runSearch(this.state.searchQuery), 250);
    }

    async _runSearch(q) {
        if (!q || q.length < 2) {
            this.state.searchResults = [];
            return;
        }
        try {
            const res = await this._rpc("search", { query: q });
            this.state.searchResults = res?.results || [];
        } catch (e) {
            this.state.searchResults = [];
        }
    }

    clearSearch() {
        this.state.searchQuery = "";
        this.state.searchResults = [];
    }

    async openSearchResult(convId) {
        this.clearSearch();
        await this.switchConv(convId);
    }

    async _refreshPendingStatuses() {
        const conv = this.activeConv;
        if (!conv) return;
        const pendingMsgs = (conv.messages || []).filter(m => m.type === "pending" && m.status === "pending");
        if (!pendingMsgs.length) return;
        try {
            const res = await this._pendingRpc("list", { conversation_id: conv.id });
            const byId = {};
            for (const row of res?.actions || []) byId[row.id] = row;
            for (const msg of pendingMsgs) {
                const row = byId[msg.actionId];
                if (row && row.status !== "pending") {
                    msg.status = row.status;
                    msg.result = row.result || "";
                    msg.error = row.error || "";
                }
            }
        } catch {
            // best effort; will retry on next tick
        }
    }

    async exportConv(id) {
        try {
            const res = await this._rpc("export", { id });
            if (!res?.ok) return;
            const blob = new Blob([res.markdown], { type: "text/markdown" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = res.filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            // best effort
        }
    }

    onSend() {
        if (!this.state.input.trim() || !this.activeConv) return;
        const conv = this.activeConv;
        if (chatService.isBusy(conv.id)) return;
        const text = this.state.input.trim();
        conv.messages.push({ text, role: "user" });
        this.state.input = "";
        this.state.liveSteps = [];
        this._handledStatus.delete(conv.id);
        // fire and forget; subscriber callback drives UI updates
        chatService.start(conv.id, text, this.props.profileId);
    }

    cancelSend() {
        if (this.state.activeId) chatService.abort(this.state.activeId);
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
