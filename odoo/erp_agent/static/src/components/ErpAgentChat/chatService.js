/** @odoo-module **/

const CHAT_URL = "/erp_agent/chat";
const CONV_URL = "/erp_agent/conversation";
const PENDING_URL = "/erp_agent/pending_actions";
const GC_DELAY_MS = 60000;

const _chats = new Map();
const _subs = new Map();

function _notify(convId) {
    const state = _chats.get(convId);
    const subs = _subs.get(convId);
    if (subs) for (const cb of subs) cb(state);
}

async function _rpc(url, action, params = {}) {
    const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", params: { action, ...params } }),
    });
    const d = await r.json();
    return d.result;
}

function _scheduleGc(convId, state) {
    setTimeout(() => {
        const cur = _chats.get(convId);
        if (cur === state) _chats.delete(convId);
    }, GC_DELAY_MS);
}

export const chatService = {
    getState(convId) {
        return _chats.get(convId);
    },

    subscribe(convId, cb) {
        if (!_subs.has(convId)) _subs.set(convId, new Set());
        _subs.get(convId).add(cb);
        return () => this.unsubscribe(convId, cb);
    },

    unsubscribe(convId, cb) {
        _subs.get(convId)?.delete(cb);
    },

    abort(convId) {
        const s = _chats.get(convId);
        if (s?.abortCtrl) s.abortCtrl.abort();
    },

    isBusy(convId) {
        return _chats.get(convId)?.status === "loading";
    },

    async start(convId, text, profileId) {
        this.abort(convId);

        const ctrl = new AbortController();
        const state = {
            status: "loading",
            liveSteps: [],
            response: "",
            tables: [],
            pendingActions: [],
            abortCtrl: ctrl,
            error: "",
        };
        _chats.set(convId, state);
        _notify(convId);

        try {
            await _rpc(CONV_URL, "append", { id: convId, role: "user", content: text });
        } catch (e) {
            // non-fatal; carry on
        }

        try {
            const resp = await fetch(CHAT_URL, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    session_key: `odoo:conv:${convId}`,
                    profile_id: profileId || "",
                }),
                signal: ctrl.signal,
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
                    let event;
                    try { event = JSON.parse(data); } catch { continue; }

                    if (event.type === "progress") {
                        if (!String(event.content).startsWith("Tokens:")) {
                            state.liveSteps.push(event.content);
                            _notify(convId);
                        }
                    } else if (event.type === "response") {
                        state.response = event.content;
                        _notify(convId);
                    } else if (event.type === "artifact" && event.artifact_type === "table") {
                        state.tables.push({
                            artifact_type: "table",
                            title: event.title,
                            columns: event.columns,
                            rows: event.rows,
                        });
                        _notify(convId);
                    } else if (event.type === "pending_action") {
                        try {
                            const created = await _rpc(PENDING_URL, "create", {
                                conversation_id: convId,
                                tool_name: event.tool_name,
                                payload: event.payload,
                            });
                            if (created?.ok) {
                                state.pendingActions.push({
                                    actionId: created.action.id,
                                    toolName: event.tool_name,
                                    payload: event.payload,
                                });
                                _notify(convId);
                            }
                        } catch (e) { /* skip */ }
                    }
                }
            }

            if (state.response) {
                try {
                    await _rpc(CONV_URL, "append", {
                        id: convId,
                        role: "assistant",
                        content: state.response,
                        steps: JSON.stringify(state.liveSteps),
                    });
                } catch (e) { /* non-fatal */ }
            }
            for (const t of state.tables) {
                try {
                    await _rpc(CONV_URL, "append", {
                        id: convId,
                        role: "assistant",
                        content: "",
                        artifacts: JSON.stringify([t]),
                    });
                } catch (e) { /* non-fatal */ }
            }
            state.status = "done";
            _notify(convId);
        } catch (e) {
            const aborted = e.name === "AbortError";
            state.status = aborted ? "aborted" : "error";
            const msg = aborted ? "Cancelled by user." : `Error: ${e.message}`;
            state.error = msg;
            try {
                await _rpc(CONV_URL, "append", { id: convId, role: "error", content: msg });
            } catch { /* non-fatal */ }
            _notify(convId);
        } finally {
            _scheduleGc(convId, state);
        }
    },
};
