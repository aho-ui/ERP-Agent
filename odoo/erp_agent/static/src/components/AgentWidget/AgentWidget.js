/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ErpAgentChat } from "../ErpAgentChat/ErpAgentChat";
import { AgentSettings } from "../AgentSettings/AgentSettings";

class AgentWidget extends Component {
    static template = "erp_agent.AgentWidget";
    static components = { ErpAgentChat, AgentSettings };

    setup() {
        this.state = useState({
            x: window.innerWidth - 72,
            y: window.innerHeight - 72,
            dragging: false,
            open: false,
            view: "chat",
            panelW: 320,
            panelH: 480,
            activeProfileId: localStorage.getItem("erp_agent_profile") || "",
        });
        this._drag = { startX: 0, startY: 0, origX: 0, origY: 0 };
        this._resize = { active: false, startX: 0, startY: 0, origW: 0, origH: 0 };

        this._onMouseMove = (e) => {
            if (this.state.dragging) {
                const size = 48;
                const newX = this._drag.origX + (e.clientX - this._drag.startX);
                const newY = this._drag.origY + (e.clientY - this._drag.startY);
                this.state.x = Math.min(Math.max(0, newX), window.innerWidth - size);
                this.state.y = Math.min(Math.max(0, newY), window.innerHeight - size);
            } else if (this._resize.active) {
                const dw = this.bubbleOnRight
                    ? this._resize.startX - e.clientX
                    : e.clientX - this._resize.startX;
                // const dh = e.clientY - this._resize.startY;
                const dh = this.bubbleOnBottom
                    ? this._resize.startY - e.clientY
                    : e.clientY - this._resize.startY;
                this.state.panelW = Math.max(280, this._resize.origW + dw);
                this.state.panelH = Math.max(300, this._resize.origH + dh);
            }
        };

        this._onMouseUp = (e) => {
            if (this._resize.active) {
                this._resize.active = false;
                return;
            }
            const dx = e.clientX - this._drag.startX;
            const dy = e.clientY - this._drag.startY;
            const moved = Math.sqrt(dx * dx + dy * dy) > 5;
            this.state.dragging = false;
            if (!moved) this.state.open = !this.state.open;
        };

        onMounted(() => {
            document.addEventListener("mousemove", this._onMouseMove);
            document.addEventListener("mouseup", this._onMouseUp);
        });
        onWillUnmount(() => {
            document.removeEventListener("mousemove", this._onMouseMove);
            document.removeEventListener("mouseup", this._onMouseUp);
        });
    }

    selectProfile(id) {
        this.state.activeProfileId = id || "";
        if (id) {
            localStorage.setItem("erp_agent_profile", id);
        } else {
            localStorage.removeItem("erp_agent_profile");
        }
    }

    get bubbleOnRight() {
        return this.state.x >= window.innerWidth / 2;
    }

    get bubbleOnBottom() {
        return this.state.y >= window.innerHeight / 2;
    }

    get showPanel() {
        return this.state.open && !this.state.dragging;
    }

    get panelStyle() {
        const { x, y, panelW, panelH } = this.state;
        const gap = 12, size = 48;
        const left = this.bubbleOnRight ? x - panelW - gap : x + size + gap;
        // const top = Math.min(y, window.innerHeight - panelH);
        const top = Math.max(0, this.bubbleOnBottom ? (y + size) - panelH : y);
        return `position:fixed;z-index:9998;left:${left}px;top:${top}px;` +
               `width:${panelW}px;height:${panelH}px;background:white;border-radius:12px;` +
               `box-shadow:0 8px 32px rgba(0,0,0,0.15);` +
               `display:flex;flex-direction:column;overflow:hidden;`;
    }

    get posStyle() {
        const { x, y } = this.state;
        return `position:fixed;z-index:9999;left:${x}px;top:${y}px;` +
               `width:48px;height:48px;border-radius:50%;` +
               `background:#714B67;user-select:none;` +
               `display:flex;align-items:center;justify-content:center;`;
    }

    onMouseDown(e) {
        this._drag = { startX: e.clientX, startY: e.clientY, origX: this.state.x, origY: this.state.y };
        this.state.dragging = true;
        e.preventDefault();
    }

    onResizeDown(e) {
        this._resize = { active: true, startX: e.clientX, startY: e.clientY, origW: this.state.panelW, origH: this.state.panelH };
        e.stopPropagation();
        e.preventDefault();
    }
}

registry.category("main_components").add("AgentWidget", { Component: AgentWidget });
