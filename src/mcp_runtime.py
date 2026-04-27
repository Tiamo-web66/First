"""Runtime bridge used by the GUI-managed MCP service."""


BASIC_TOOLS = [
    {
        "name": "get_status",
        "description": "Read current Frida, miniapp, CDP, AppID, route, and permission status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "evaluate_js",
        "description": "Evaluate JavaScript in the current miniapp runtime. Requires the execute JS permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "JavaScript expression or IIFE to evaluate."},
                "timeout": {"type": "number", "description": "Optional timeout in seconds."},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "list_routes",
        "description": "List routes discovered from the current miniapp.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_current_route",
        "description": "Read the current miniapp page route.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "navigate_route",
        "description": "Navigate the miniapp to a route. Requires the page navigation permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "route": {"type": "string", "description": "Route path, with or without a leading slash."},
            },
            "required": ["route"],
        },
    },
]


class McpRuntime:
    """Expose GUI state and permission checks to the MCP server layer."""

    def __init__(self, context_getter, permission_checker, tool_handler=None, log_callback=None):
        """Store callbacks supplied by the GUI without importing PySide objects."""
        self._context_getter = context_getter
        self._permission_checker = permission_checker
        self._tool_handler = tool_handler
        self._log_callback = log_callback

    def get_context(self):
        """Return the current debugger context snapshot from the GUI."""
        try:
            return dict(self._context_getter() or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def has_permission(self, key):
        """Check whether a named MCP capability is currently allowed."""
        try:
            return bool(self._permission_checker(key))
        except Exception:
            return False

    def list_tools(self):
        """Return basic MCP tool metadata exposed by phase 4."""
        return list(BASIC_TOOLS)

    def call_tool(self, name, arguments=None):
        """Dispatch a named MCP tool call to the GUI-supplied handler."""
        if not self._tool_handler:
            return {"ok": False, "error": "tool handler not configured"}
        try:
            return self._tool_handler(name, arguments or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def log(self, message):
        """Forward an MCP service log message to the GUI if a callback exists."""
        if self._log_callback:
            try:
                self._log_callback(str(message))
            except Exception:
                pass
