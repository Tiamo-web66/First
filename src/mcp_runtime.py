"""Runtime bridge used by the GUI-managed MCP service."""


class McpRuntime:
    """Expose GUI state and permission checks to the MCP server layer."""

    def __init__(self, context_getter, permission_checker, log_callback=None):
        """Store callbacks supplied by the GUI without importing PySide objects."""
        self._context_getter = context_getter
        self._permission_checker = permission_checker
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

    def log(self, message):
        """Forward an MCP service log message to the GUI if a callback exists."""
        if self._log_callback:
            try:
                self._log_callback(str(message))
            except Exception:
                pass
