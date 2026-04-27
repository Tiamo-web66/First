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
    {
        "name": "start_capture",
        "description": "Start capturing miniapp wx.request/uploadFile/downloadFile traffic.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "stop_capture",
        "description": "Stop request capture while keeping captured records available.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_requests",
        "description": "Read recent captured miniapp requests. Requires the read requests permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "number", "description": "Maximum number of recent records to return, capped at 200."},
            },
        },
    },
    {
        "name": "clear_requests",
        "description": "Clear captured request records from the miniapp runtime.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_runtime_scripts",
        "description": "Collect and list JavaScript scripts currently known to the miniapp runtime. Requires the read scripts permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "wait_seconds": {"type": "number", "description": "How long to wait for scriptParsed events, capped at 3 seconds."},
                "limit": {"type": "number", "description": "Maximum scripts to return, capped at 500."},
            },
        },
    },
    {
        "name": "get_runtime_script_source",
        "description": "Read source text for one runtime script by script_id. Requires the read scripts permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "script_id": {"type": "string", "description": "CDP Debugger scriptId returned by list_runtime_scripts."},
                "offset": {"type": "number", "description": "Character offset to start reading from."},
                "max_chars": {"type": "number", "description": "Maximum characters to return, capped at 100000."},
            },
            "required": ["script_id"],
        },
    },
    {
        "name": "search_runtime_scripts",
        "description": "Search runtime JavaScript source for a literal keyword. Requires the read scripts permission.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Literal text to search for."},
                "case_sensitive": {"type": "boolean", "description": "Whether the search is case-sensitive."},
                "max_results": {"type": "number", "description": "Maximum matches to return, capped at 100."},
                "max_scripts": {"type": "number", "description": "Maximum scripts to inspect, capped at 300."},
                "context_chars": {"type": "number", "description": "Characters of context around each match, capped at 300."},
            },
            "required": ["query"],
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
        """Return MCP tool metadata exposed by the GUI runtime."""
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
