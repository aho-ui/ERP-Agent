/** @odoo-module **/
import { Component, useState, useRef, onWillStart, onWillUnmount, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

const TABS = [
    { id: "activity", label: "Activity" },
    { id: "health", label: "Health" },
    { id: "agents", label: "Agents" },
    { id: "tools", label: "Tools" },
];


const STATE_LABEL = { 0: "Dead", 1: "DB down", 2: "Healthy" };
const STATE_COLOR = { 0: "#dc3545", 1: "#f0ad4e", 2: "#28a745" };
const SERVER_COLOR = { odoo: "#714B67", sqlite: "#2a8cae" };
const POLL_MS = 10000;
const CHART_JS = "/web/static/lib/Chart/Chart.js";

function _draftFromAgent(a) {
    const tools = {};
    for (const t of a.allowed_tools || []) tools[t] = true;
    return {
        name: a.name || "",
        description: a.description || "",
        system_prompt: a.system_prompt || "",
        tools,
    };
}

function _emptyDraft() {
    return { name: "", description: "", system_prompt: "", tools: {} };
}

export class Dashboard extends Component {
    static template = "erp_agent.Dashboard";
    static props = ["*"];

    setup() {
        this.tabs = TABS;
        this.state = useState({
            active: TABS[0].id,
            health: { running: false, backend_uptime: 0, servers: {}, known_mcps: [], disabled_mcps: [], is_admin: false },
            activity: {
                is_admin: false,
                totals: { sqlite: 0, odoo: 0 },
                history: [],
                errors: [],
                calls: [],
                per_agent: [],
                top_tools: [],
                avg_steps: 0,
            },
            activityDays: 50,
            expandedCalls: {},
            agents: [],
            agentTools: [],
            expandedAgents: {},   // id -> true
            agentEdits: {},       // id -> draft (for custom agents being edited)
            newDraft: null,       // _emptyDraft() while creating a new agent
            expandedTools: {},    // tool name -> true (Tools tab)
            toolsGroups: {},      // server -> [tool, ...] (from /erp_agent/tools)
            rebuilding: false,
        });
        this.canvasRef = useRef("uptimeChart");
        this.activityCanvasRef = useRef("activityChart");
        this.perAgentCanvasRef = useRef("perAgentChart");
        this.chart = null;
        this.activityChart = null;
        this.perAgentChart = null;

        onWillStart(async () => {
            await loadJS(CHART_JS);
            await this._fetchHealth();
            await this._fetchActivity();
            await this._fetchAgents();
            await this._fetchTools();
        });

        useEffect(
            () => {
                if (this.state.active === "health" && this.canvasRef.el && window.Chart) {
                    this._buildChart();
                    return () => this._destroyChart();
                }
            },
            () => [this.state.active]
        );

        useEffect(
            () => {
                if (this.state.active === "activity" && this.activityCanvasRef.el && window.Chart) {
                    this._buildActivityChart();
                    return () => this._destroyActivityChart();
                }
            },
            () => [this.state.active]
        );

        useEffect(
            () => {
                if (this.state.active === "activity" && this.perAgentCanvasRef.el && window.Chart) {
                    this._buildPerAgentChart();
                    return () => this._destroyPerAgentChart();
                }
            },
            () => [this.state.active]
        );

        this._poll = setInterval(() => {
            this._fetchHealth();
            this._fetchActivity();
            this._fetchTools();
        }, POLL_MS);
        onWillUnmount(() => {
            clearInterval(this._poll);
            this._destroyChart();
            this._destroyActivityChart();
            this._destroyPerAgentChart();
        });
    }

    switchTab(id) {
        this.state.active = id;
    }

    toggleCall(id) {
        if (!id) return;
        const next = { ...this.state.expandedCalls };
        if (next[id]) {
            delete next[id];
        } else {
            next[id] = true;
        }
        this.state.expandedCalls = next;
    }

    formatTs(ts) {
        if (!ts) return "—";
        return ts.length > 16 ? ts.slice(0, 16) : ts;
    }

    onDaysChange(value) {
        let v = parseInt(value, 10);
        if (isNaN(v)) return;
        v = Math.max(1, Math.min(90, v));
        if (v === this.state.activityDays) return;
        this.state.activityDays = v;
        this._fetchActivity();
    }

    async manualRebuild() {
        if (this.state.rebuilding) return;
        this.state.rebuilding = true;
        try {
            await rpc("/erp_agent/rebuild", {});
            // give the drain + respawn a moment, then refresh
            await new Promise((r) => setTimeout(r, 2000));
            await this._fetchHealth();
        } catch {
            // ignore
        } finally {
            this.state.rebuilding = false;
        }
    }

    async _fetchHealth() {
        try {
            this.state.health = await rpc("/erp_agent/health", {});
        } catch {
            this.state.health = { running: false, backend_uptime: 0, servers: {}, known_mcps: [], disabled_mcps: [], is_admin: false };
        }
        this._syncChart();
    }

    isMcpEnabled(name) {
        return !(this.state.health.disabled_mcps || []).includes(name);
    }

    async toggleMcp(name) {
        if (!this.state.health.is_admin) return;
        const enabled = !this.isMcpEnabled(name);
        try {
            const res = await rpc("/erp_agent/mcp_toggle", { name, enabled });
            if (res?.ok) {
                this.state.health = { ...this.state.health, disabled_mcps: res.disabled_mcps };
            }
        } catch {}
    }

    async _fetchActivity() {
        try {
            this.state.activity = await rpc("/erp_agent/activity", { days: this.state.activityDays });
        } catch {
            this.state.activity = {
                is_admin: false,
                totals: { sqlite: 0, odoo: 0 },
                history: [],
                errors: [],
                calls: [],
                per_agent: [],
                top_tools: [],
                avg_steps: 0,
            };
        }
        this._syncActivityChart();
        this._syncPerAgentChart();
    }

    async _fetchTools() {
        try {
            const res = await rpc("/erp_agent/tools", {});
            this.state.toolsGroups = res.groups || {};
        } catch {
            this.state.toolsGroups = {};
        }
    }

    async _fetchAgents() {
        try {
            const res = await rpc("/erp_agent/agent", { action: "list" });
            this.state.agents = res.agents || [];
            this.state.agentTools = res.tools || [];
        } catch {
            this.state.agents = [];
            this.state.agentTools = [];
        }
    }

    get serverList() {
        const servers = this.state.health.servers || {};
        return Object.keys(servers).map((name) => ({ name, ...servers[name] }));
    }

    stateLabel(s) {
        return STATE_LABEL[s] ?? "Unknown";
    }

    dotColor(s) {
        return STATE_COLOR[s] ?? "#999";
    }

    formatUptime(seconds) {
        if (!seconds || seconds <= 0) return "—";
        const s = Math.floor(seconds);
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        if (h) return `${h}h ${m}m`;
        if (m) return `${m}m`;
        return `${s}s`;
    }

    // ---- Health chart ----

    _chartData() {
        const servers = this.state.health.servers || {};
        const names = Object.keys(servers);
        const ref = names.length ? servers[names[0]].history || [] : [];
        const labels = ref.map((h, i) =>
            i === ref.length - 1 ? "now" : h.ago >= 60 ? `-${Math.round(h.ago / 60)}m` : `-${h.ago}s`
        );
        const datasets = names.map((n) => ({
            label: n,
            data: (servers[n].history || []).map((h) => h.state),
            borderColor: SERVER_COLOR[n] || "#555",
            backgroundColor: "transparent",
            stepped: true,
            tension: 0,
            pointRadius: 0,
            borderWidth: 2,
        }));
        return { labels, datasets };
    }

    _buildChart() {
        const Chart = window.Chart;
        if (!Chart || !this.canvasRef.el) return;
        this.chart = new Chart(this.canvasRef.el, {
            type: "line",
            data: this._chartData(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { intersect: false, mode: "index" },
                scales: {
                    y: { min: 0, max: 2, ticks: { stepSize: 1, callback: (v) => STATE_LABEL[v] ?? v } },
                    x: { ticks: { maxTicksLimit: 8 } },
                },
                plugins: { legend: { position: "bottom" } },
            },
        });
    }

    _syncChart() {
        if (!this.chart) return;
        this.chart.data = this._chartData();
        this.chart.update();
    }

    _destroyChart() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
    }

    // ---- Activity chart ----

    _activityChartData() {
        const hist = this.state.activity.history || [];
        const labels = hist.map((h) => (h.day ? h.day.slice(5) : ""));
        const data = hist.map((h) => h.count);
        const errors = this.state.activity.errors || [];
        return {
            labels,
            datasets: [
                {
                    label: "Calls",
                    data,
                    borderColor: "#714B67",
                    backgroundColor: "rgba(113,75,103,0.12)",
                    tension: 0.25,
                    pointRadius: 2,
                    borderWidth: 2,
                    fill: true,
                },
                {
                    label: "Errors",
                    data: errors,
                    borderColor: "#dc3545",
                    backgroundColor: "transparent",
                    tension: 0.25,
                    pointRadius: 2,
                    borderWidth: 2,
                    fill: false,
                },
            ],
        };
    }

    _buildActivityChart() {
        const Chart = window.Chart;
        if (!Chart || !this.activityCanvasRef.el) return;
        this.activityChart = new Chart(this.activityCanvasRef.el, {
            type: "line",
            data: this._activityChartData(),
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                interaction: { intersect: false, mode: "index" },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                    x: { ticks: { maxTicksLimit: 10 } },
                },
                plugins: { legend: { position: "bottom" } },
            },
        });
    }

    _syncActivityChart() {
        if (!this.activityChart) return;
        this.activityChart.data = this._activityChartData();
        this.activityChart.update();
    }

    _destroyActivityChart() {
        if (this.activityChart) {
            this.activityChart.destroy();
            this.activityChart = null;
        }
    }

    // ---- Per-agent bar ----

    _perAgentChartData() {
        const src = this.state.activity.per_agent || [];
        return {
            labels: src.map((a) => a.name),
            datasets: [{
                label: "Calls",
                data: src.map((a) => a.count),
                backgroundColor: "#714B67",
                borderRadius: 4,
            }],
        };
    }

    _syncPerAgentChart() {
        if (!this.perAgentChart) return;
        this.perAgentChart.data = this._perAgentChartData();
        this.perAgentChart.update();
    }

    _buildPerAgentChart() {
        const Chart = window.Chart;
        if (!Chart || !this.perAgentCanvasRef.el) return;
        this.perAgentChart = new Chart(this.perAgentCanvasRef.el, {
            type: "bar",
            data: this._perAgentChartData(),
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0 } },
                    y: { ticks: { font: { size: 11 } } },
                },
                plugins: { legend: { display: false } },
            },
        });
    }

    _destroyPerAgentChart() {
        if (this.perAgentChart) {
            this.perAgentChart.destroy();
            this.perAgentChart = null;
        }
    }


    toggleToolExpand(name) {
        const next = { ...this.state.expandedTools };
        if (next[name]) {
            delete next[name];
        } else {
            next[name] = true;
        }
        this.state.expandedTools = next;
    }

    get toolsByServer() {
        return this.state.toolsGroups || {};
    }

    // ---- Agents ----

    toolServer(name) {
        const parts = String(name).split("_");
        return parts[0] === "mcp" && parts.length >= 2 ? parts[1] : "";
    }

    openNewAgent() {
        this.state.newDraft = _emptyDraft();
    }

    cancelNewAgent() {
        this.state.newDraft = null;
    }

    toggleAgentExpand(a) {
        const next = { ...this.state.expandedAgents };
        if (next[a.id]) {
            delete next[a.id];
            const edits = { ...this.state.agentEdits };
            delete edits[a.id];
            this.state.agentEdits = edits;
        } else {
            next[a.id] = true;
            if (!a.is_default) {
                this.state.agentEdits = { ...this.state.agentEdits, [a.id]: _draftFromAgent(a) };
            }
        }
        this.state.expandedAgents = next;
    }

    toggleEditTool(id, name) {
        const edits = { ...this.state.agentEdits };
        const draft = { ...(edits[id] || _emptyDraft()) };
        const tools = { ...draft.tools };
        if (tools[name]) {
            delete tools[name];
        } else {
            tools[name] = true;
        }
        draft.tools = tools;
        edits[id] = draft;
        this.state.agentEdits = edits;
    }

    toggleNewTool(name) {
        if (!this.state.newDraft) return;
        const tools = { ...this.state.newDraft.tools };
        if (tools[name]) {
            delete tools[name];
        } else {
            tools[name] = true;
        }
        this.state.newDraft = { ...this.state.newDraft, tools };
    }

    async saveAgentEdit(a) {
        const draft = this.state.agentEdits[a.id];
        if (!draft || !draft.name.trim() || !draft.system_prompt.trim()) return;
        const allowed_tools = Object.keys(draft.tools).filter((k) => draft.tools[k]);
        try {
            await rpc("/erp_agent/agent", {
                action: "update",
                id: a.id,
                name: draft.name.trim(),
                description: draft.description || "",
                system_prompt: draft.system_prompt,
                allowed_tools,
            });
            const next = { ...this.state.expandedAgents };
            delete next[a.id];
            const edits = { ...this.state.agentEdits };
            delete edits[a.id];
            this.state.expandedAgents = next;
            this.state.agentEdits = edits;
            await this._fetchAgents();
        } catch {
            // keep edit panel open on failure
        }
    }

    async saveNewAgent() {
        const draft = this.state.newDraft;
        if (!draft || !draft.name.trim() || !draft.system_prompt.trim()) return;
        const allowed_tools = Object.keys(draft.tools).filter((k) => draft.tools[k]);
        try {
            await rpc("/erp_agent/agent", {
                action: "create",
                name: draft.name.trim(),
                description: draft.description || "",
                system_prompt: draft.system_prompt,
                allowed_tools,
            });
            this.state.newDraft = null;
            await this._fetchAgents();
        } catch {
            // keep draft on failure
        }
    }

    async deleteAgent(id) {
        try {
            await rpc("/erp_agent/agent", { action: "delete", id });
            const next = { ...this.state.expandedAgents };
            delete next[id];
            this.state.expandedAgents = next;
            await this._fetchAgents();
        } catch {
            // ignore
        }
    }

    async toggleAgentActive(a) {
        try {
            await rpc("/erp_agent/agent", {
                action: "toggle",
                id: a.id,
                active: !a.active,
            });
            await this._fetchAgents();
        } catch {
            // ignore
        }
    }
}

registry.category("actions").add("erp_agent.dashboard", Dashboard);
