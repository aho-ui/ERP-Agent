{
    "name": "ERP Agent",
    "version": "1.0.0",
    "category": "Tools",
    "summary": "AI-powered ERP agent — standalone frontend inside Odoo",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "erp_agent/static/src/xml/erp_agent.xml",
            "erp_agent/static/src/components/ErpAgentChat.js",
        ],
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}
