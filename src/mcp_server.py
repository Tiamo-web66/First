"""Lightweight local HTTP skeleton for the GUI-managed MCP endpoint."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    """ThreadingHTTPServer variant that can restart quickly on the same port."""

    allow_reuse_address = True


class McpHttpService:
    """Run a local HTTP endpoint that exposes a minimal MCP-compatible shell."""

    def __init__(self, runtime, host="127.0.0.1", port=8765, path="/mcp"):
        """Prepare the service; call start() to bind the HTTP listener."""
        self.runtime = runtime
        self.host = host
        self.port = int(port)
        self.path = path or "/mcp"
        self.max_body_size = 1024 * 1024
        self._server = None
        self._thread = None

    @property
    def is_running(self):
        """Return True when the HTTP server thread is alive."""
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        """Start the local HTTP listener in a daemon thread."""
        if self.is_running:
            return
        handler = self._make_handler()
        self._server = _ReusableThreadingHTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="first-mcp-http",
            daemon=True,
        )
        self._thread.start()
        self.runtime.log(f"MCP HTTP 服务已启动: http://{self.host}:{self.port}{self.path}")

    def stop(self):
        """Stop the local HTTP listener and wait briefly for shutdown."""
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._server = None
        self._thread = None
        self.runtime.log("MCP HTTP 服务已停止")

    def _make_handler(self):
        service = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "FirstMCP/0.1"

            def log_message(self, fmt, *args):
                service.runtime.log("[http] " + (fmt % args))

            def do_OPTIONS(self):
                self._send_json({"ok": True})

            def do_GET(self):
                if self.path == "/health":
                    self._send_json({"ok": True})
                    return
                if self.path != service.path:
                    self._send_json({"ok": False, "error": "not found"}, status=404)
                    return
                payload = {
                    "ok": True,
                    "name": "first-debugger",
                    "transport": "http",
                    "phase": 7,
                    "path": service.path,
                    "status": service.runtime.get_context(),
                    "tools": [tool["name"] for tool in service.runtime.list_tools()],
                }
                self._send_json(payload)

            def do_POST(self):
                if self.path != service.path:
                    self._send_json({"ok": False, "error": "not found"}, status=404)
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0") or "0")
                    if length > service.max_body_size:
                        self._send_json(self._rpc_error(None, -32600, "request body too large"))
                        return
                    raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                    request = json.loads(raw)
                except Exception as exc:
                    self._send_json(self._rpc_error(None, -32700, f"parse error: {exc}"))
                    return
                try:
                    response = self._handle_rpc(request)
                except Exception as exc:
                    response = self._rpc_error(None, -32603, f"internal error: {exc}")
                self._send_json(response)

            def _handle_rpc(self, request):
                if isinstance(request, list):
                    if not request:
                        return self._rpc_error(None, -32600, "invalid request: empty batch")
                    return [self._handle_rpc(item) for item in request]
                if not isinstance(request, dict):
                    return self._rpc_error(None, -32600, "invalid request: expected object")
                req_id = request.get("id")
                jsonrpc = request.get("jsonrpc")
                if jsonrpc not in (None, "2.0"):
                    return self._rpc_error(req_id, -32600, "invalid request: jsonrpc must be '2.0'")
                method = request.get("method", "")
                if not isinstance(method, str) or not method:
                    return self._rpc_error(req_id, -32600, "invalid request: method must be a non-empty string")
                service.runtime.log(f"tool:{method or 'unknown'} called")
                if method == "initialize":
                    return self._rpc_result(req_id, {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "first-debugger", "version": "0.1.0"},
                        "capabilities": {"tools": {}},
                    })
                if method == "ping":
                    return self._rpc_result(req_id, {})
                if method == "tools/list":
                    return self._rpc_result(req_id, {"tools": service.runtime.list_tools()})
                if method == "tools/call":
                    params = request.get("params", {}) or {}
                    if not isinstance(params, dict):
                        return self._rpc_error(req_id, -32600, "invalid request: params must be an object")
                    name = params.get("name", "")
                    if not isinstance(name, str) or not name:
                        return self._rpc_error(req_id, -32600, "invalid request: tool name must be a non-empty string")
                    arguments = params.get("arguments", {}) or {}
                    if not isinstance(arguments, dict):
                        return self._rpc_error(req_id, -32600, "invalid request: arguments must be an object")
                    result = service.runtime.call_tool(name, arguments)
                    is_error = not bool(result.get("ok", True)) if isinstance(result, dict) else False
                    return self._rpc_result(req_id, {
                        "content": [{
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2),
                        }],
                        "isError": is_error,
                    })
                return self._rpc_error(req_id, -32601, f"method not found: {method}")

            def _rpc_result(self, req_id, result):
                return {"jsonrpc": "2.0", "id": req_id, "result": result}

            def _rpc_error(self, req_id, code, message):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": code, "message": message},
                }

            def _send_json(self, payload, status=200):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                origin = self.headers.get("Origin", "")
                parsed_origin = urlparse(origin) if origin else None
                if parsed_origin and parsed_origin.scheme == "http" and parsed_origin.hostname in ("127.0.0.1", "localhost"):
                    self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Headers", "content-type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        return Handler
