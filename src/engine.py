"""
DebugEngine - wraps debug_server, proxy_server, frida_server into a reusable class.
"""
import asyncio
import json
import random
import platform
import re
import subprocess
import sys
from collections import Counter, deque
from pathlib import Path

import frida
import websockets
import websockets.server
import websockets.exceptions

from .codex import (
    wrap_debug_message_data,
    unwrap_debug_message_data,
)
from .constants import DebugMessageCategory
from .third_party import wmpf_debug_pb2 as proto
from .userscript import (
    build_cdp_enable_page_command,
    build_cdp_add_script_command,
    build_injection_wrapper,
)


class DebugMessageBus:
    """Central event bus bridging debug server and CDP proxy server."""

    def __init__(self):
        self._cdp_callbacks = []
        self._proxy_callbacks = []

    def on_cdp_message(self, callback):
        self._cdp_callbacks.append(callback)

    def on_proxy_message(self, callback):
        self._proxy_callbacks.append(callback)

    def emit_cdp_message(self, message: str):
        for cb in self._cdp_callbacks:
            cb(message)

    def emit_proxy_message(self, message: str):
        for cb in self._proxy_callbacks:
            cb(message)


def buffer_to_hex_string(data: bytes) -> str:
    return data.hex()


def _build_protobuf_cdp_message(cdp_json: str, seq: int, jscontext_id: str = "") -> bytes:
    """Wrap a CDP JSON command into protobuf binary for sending to the miniapp runtime."""
    raw_payload = {
        "jscontext_id": str(jscontext_id or ""),
        "op_id": round(100 * random.random()),
        "payload": cdp_json,
    }
    wrapped = wrap_debug_message_data(raw_payload, "chromeDevtools", 0)
    out_msg = proto.WARemoteDebug_DebugMessage()
    out_msg.seq = seq
    out_msg.category = "chromeDevtools"
    out_msg.data = wrapped["buffer"]
    out_msg.compressAlgo = 0
    out_msg.originalSize = wrapped["originalSize"]
    return out_msg.SerializeToString()


class DebugEngine:
    """Wraps all three subsystems: debug server, proxy server, frida injection."""

    def __init__(self, options, logger, userscripts=None):
        self.options = options
        self.logger = logger
        self.bus = DebugMessageBus()
        self.userscripts = userscripts or []
        self.debug_srv = None
        self.proxy_srv = None
        self.frida_session = None
        self.frida_script = None
        self.miniapp_clients = set()
        self.devtools_clients = set()
        self.message_counter = 0
        self._pending_responses = {}
        self._cmd_counter = 80000
        self._status_callbacks = []
        self._event_listeners = {}   # method -> [callback, ...]
        self._context_callbacks = []
        self._js_contexts = {}
        self._selected_jscontext_id = ""
        self._connected_jscontext_id = ""
        self._recent_debug_categories = deque(maxlen=20)
        self._last_observed_jscontext_id = ""
        self._last_context_diagnostic_state = ""
        self.status = {"frida": False, "miniapp": False, "devtools": False}

    def on_status_change(self, callback):
        self._status_callbacks.append(callback)

    def on_contexts_change(self, callback):
        """Subscribe to js context registry changes."""
        self._context_callbacks.append(callback)

    def _notify_contexts(self):
        self._last_context_diagnostic_state = self._context_diagnostic_state()
        snapshot = self.list_js_contexts()
        for cb in self._context_callbacks:
            try:
                cb(snapshot)
            except Exception:
                pass

    def _notify_contexts_if_diagnostics_changed(self):
        """Notify context subscribers when only the diagnostic state changed."""
        state = self._context_diagnostic_state()
        if state != self._last_context_diagnostic_state:
            self._notify_contexts()

    def _remember_debug_category(self, category):
        """Record one recently seen miniapp debug message category."""
        name = str(category or "").strip()
        if name:
            self._recent_debug_categories.append(name)

    def _observe_js_context(self, jscontext_id, jscontext_name="", connected=False, source="observed"):
        """Upsert one js context discovered from protocol events or CDP traffic."""
        ctx_id = str(jscontext_id or "").strip()
        if not ctx_id:
            return False
        row = self._js_contexts.get(ctx_id, {}).copy()
        row["jscontext_id"] = ctx_id
        if jscontext_name:
            row["jscontext_name"] = str(jscontext_name or "")
        else:
            row.setdefault("jscontext_name", "")
        if source:
            row["source"] = str(source)
        changed = self._js_contexts.get(ctx_id) != row
        self._js_contexts[ctx_id] = row
        self._last_observed_jscontext_id = ctx_id
        if connected and self._connected_jscontext_id != ctx_id:
            self._connected_jscontext_id = ctx_id
            changed = True
        prev_selected = self._selected_jscontext_id
        self._maybe_autoselect_context()
        if self._selected_jscontext_id != prev_selected:
            changed = True
        return changed

    def get_debug_context_summary(self):
        """Return recent protocol hints useful for js context diagnostics."""
        return {
            "recent_debug_categories": list(self._recent_debug_categories),
            "last_observed_jscontext_id": self._last_observed_jscontext_id,
            "connected_jscontext_id": self._connected_jscontext_id,
        }

    def _context_diagnostic_state(self):
        """Return the compact state name for JS context availability diagnostics."""
        if self._js_contexts:
            return "enumerated"
        if not self.status.get("miniapp", False):
            return "miniapp_disconnected"
        if any(category == "chromeDevtoolsResult" for category in self._recent_debug_categories):
            return "default_runtime_without_ids"
        return "waiting_for_contexts"

    def get_js_context_diagnostics(self):
        """Describe whether the miniapp runtime has advertised selectable JS contexts."""
        contexts = self.list_js_contexts()
        recent_categories = list(self._recent_debug_categories)
        state = self._context_diagnostic_state()
        if state == "enumerated":
            state = "enumerated"
            hint = "JS contexts have been advertised by the miniapp runtime."
        elif state == "miniapp_disconnected":
            hint = "Miniapp has not connected to the fixed debug server port."
        elif state == "default_runtime_without_ids":
            hint = (
                "The runtime is responding to CDP commands, but protocol messages do not "
                "include jscontext_id values; commands are using the default runtime."
            )
        else:
            hint = "Miniapp is connected, but no addJsContext/connectJsContext message has been observed yet."
        return {
            "state": state,
            "hint": hint,
            "target_count": len(contexts),
            "last_observed_jscontext_id": self._last_observed_jscontext_id,
            "connected_jscontext_id": self._connected_jscontext_id,
            "recent_debug_categories": recent_categories,
        }

    def _notify_status(self, key, value):
        self.status[key] = value
        for cb in self._status_callbacks:
            try:
                cb(dict(self.status))
            except Exception:
                pass
        self._notify_contexts_if_diagnostics_changed()

    def _next_cmd_id(self):
        self._cmd_counter += 1
        return self._cmd_counter

    async def start(self):
        """Start all three subsystems."""
        self.debug_srv = await self._start_debug_server()
        self.proxy_srv = await self._start_proxy_server()
        try:
            self.frida_session, self.frida_script = await self._start_frida()
            self._notify_status("frida", True)
        except Exception as e:
            self.logger.error(str(e))
            raise

    async def stop(self):
        """Graceful shutdown."""
        if self.debug_srv:
            self.debug_srv.close()
            await self.debug_srv.wait_closed()
            self.debug_srv = None
        if self.proxy_srv:
            self.proxy_srv.close()
            await self.proxy_srv.wait_closed()
            self.proxy_srv = None
        if self.frida_script:
            try:
                self.frida_script.unload()
            except Exception:
                pass
            self.frida_script = None
        if self.frida_session:
            try:
                self.frida_session.detach()
            except Exception:
                pass
            self.frida_session = None
        self._notify_status("frida", False)
        self._notify_status("miniapp", False)
        self._notify_status("devtools", False)
        self.miniapp_clients.clear()
        self.devtools_clients.clear()
        self.message_counter = 0
        self._pending_responses.clear()
        self._js_contexts.clear()
        self._selected_jscontext_id = ""
        self._connected_jscontext_id = ""
        self._last_observed_jscontext_id = ""
        self._recent_debug_categories.clear()
        self._last_context_diagnostic_state = ""
        self._notify_contexts()
        self.logger.info("[server] engine stopped")

    def _preferred_jscontext_id(self):
        """Return the selected js context id or a best-effort fallback."""
        if self._selected_jscontext_id and self._selected_jscontext_id in self._js_contexts:
            return self._selected_jscontext_id
        if self._connected_jscontext_id and self._connected_jscontext_id in self._js_contexts:
            return self._connected_jscontext_id
        recommended = next(
            (ctx["jscontext_id"] for ctx in self.list_js_contexts() if ctx.get("recommended")),
            "",
        )
        return recommended

    def _emit_wrapped_cdp_command(self, cdp_cmd: str, jscontext_id: str = ""):
        """Send one wrapped CDP command to all connected miniapp clients."""
        self.message_counter += 1
        payload = {
            "jscontext_id": str(jscontext_id or ""),
            "op_id": round(100 * random.random()),
            "payload": str(cdp_cmd),
        }
        self.logger.main_debug(payload)
        encoded = _build_protobuf_cdp_message(cdp_cmd, self.message_counter, jscontext_id)
        clients_snapshot = list(self.miniapp_clients)
        for ws in clients_snapshot:
            try:
                task = asyncio.ensure_future(ws.send(encoded))
                task.add_done_callback(
                    lambda t: t.exception() if t.done() and not t.cancelled() and t.exception() else None)
            except Exception:
                pass

    def _emit_debug_message(self, category: str, data: dict):
        """Send one non-CDP debug message to all connected miniapp clients."""
        self.message_counter += 1
        wrapped = wrap_debug_message_data(data, category, 0)
        out_msg = proto.WARemoteDebug_DebugMessage()
        out_msg.seq = self.message_counter
        out_msg.category = category
        out_msg.data = wrapped["buffer"]
        out_msg.compressAlgo = 0
        out_msg.originalSize = wrapped["originalSize"]
        encoded = out_msg.SerializeToString()
        clients_snapshot = list(self.miniapp_clients)
        for ws in clients_snapshot:
            try:
                task = asyncio.ensure_future(ws.send(encoded))
                task.add_done_callback(
                    lambda t: t.exception() if t.done() and not t.cancelled() and t.exception() else None)
            except Exception:
                pass

    async def evaluate_js(self, expression, timeout=5.0, jscontext_id=None):
        """Send Runtime.evaluate via CDP to the selected miniapp js context when available."""
        if not self.miniapp_clients:
            raise RuntimeError("No miniapp client connected")
        cmd_id = self._next_cmd_id()
        target_id = str(jscontext_id or self._preferred_jscontext_id() or "")
        cdp_cmd = json.dumps({
            "id": cmd_id,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True}
        })
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_responses[cmd_id] = future
        self._emit_wrapped_cdp_command(cdp_cmd, target_id)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_responses.pop(cmd_id, None)
            raise

    async def send_cdp_command(self, method, params=None, timeout=5.0, jscontext_id=None):
        """Send an arbitrary CDP command to the selected miniapp js context and return the response."""
        if not self.miniapp_clients:
            raise RuntimeError("No miniapp client connected")
        cmd_id = self._next_cmd_id()
        target_id = str(jscontext_id or self._preferred_jscontext_id() or "")
        cdp_cmd = json.dumps({"id": cmd_id, "method": method, "params": params or {}})
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_responses[cmd_id] = future
        self._emit_wrapped_cdp_command(cdp_cmd, target_id)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_responses.pop(cmd_id, None)
            raise

    def _context_kind(self, name):
        """Classify a js context name into appservice, webview, or unknown."""
        lowered = str(name or "").strip().lower()
        if any(token in lowered for token in ("appservice", "waservice", "service")):
            return "appservice"
        if any(token in lowered for token in ("webview", "renderer", "render")):
            return "webview"
        return "unknown"

    def _maybe_autoselect_context(self):
        """Select a preferred js context when the current selection is missing."""
        if self._selected_jscontext_id and self._selected_jscontext_id in self._js_contexts:
            return
        contexts = self.list_js_contexts()
        if not contexts:
            self._selected_jscontext_id = ""
            return
        preferred = next((ctx["jscontext_id"] for ctx in contexts if ctx.get("recommended")), "")
        self._selected_jscontext_id = preferred or contexts[0]["jscontext_id"]

    def list_js_contexts(self):
        """Return cached js contexts with selection and recommendation metadata."""
        rows = []
        for ctx_id, item in self._js_contexts.items():
            name = item.get("jscontext_name", "")
            kind = self._context_kind(name)
            rows.append({
                "jscontext_id": ctx_id,
                "jscontext_name": name,
                "source": item.get("source", ""),
                "kind": kind,
                "recommended": kind == "appservice",
                "selected": ctx_id == self._selected_jscontext_id,
                "connected": ctx_id == self._connected_jscontext_id,
            })
        rows.sort(key=lambda item: (
            0 if item.get("selected") else 1,
            0 if item.get("recommended") else 1,
            0 if item.get("connected") else 1,
            item.get("jscontext_name", ""),
            item.get("jscontext_id", ""),
        ))
        return rows

    def get_selected_js_context(self):
        """Return the currently selected js context metadata when available."""
        selected_id = self._preferred_jscontext_id()
        if not selected_id:
            return {}
        return next((ctx for ctx in self.list_js_contexts() if ctx["jscontext_id"] == selected_id), {})

    def select_js_context(self, jscontext_id):
        """Select one cached js context by id for subsequent JS execution."""
        target_id = str(jscontext_id or "").strip()
        if not target_id:
            self._selected_jscontext_id = ""
            self._maybe_autoselect_context()
            self._notify_contexts()
            return self.get_selected_js_context()
        if target_id not in self._js_contexts:
            raise KeyError(target_id)
        self._selected_jscontext_id = target_id
        self._notify_contexts()
        return self.get_selected_js_context()

    async def activate_js_context(self, jscontext_id):
        """Select one js context and ask the remote runtime to switch to it."""
        selected = self.select_js_context(jscontext_id)
        target_id = str(selected.get("jscontext_id", "") or "")
        if target_id:
            self._emit_debug_message(
                DebugMessageCategory.ConnectJsContext,
                {"jscontext_id": target_id},
            )
        return selected

    async def set_extra_headers(self, headers: dict):
        """Enable Network domain and set extra HTTP headers via CDP."""
        await self.send_cdp_command("Network.enable")
        await self.send_cdp_command("Network.setExtraHTTPHeaders",
                                    {"headers": headers})

    def _allow_devtools_breakpoints(self):
        """Return whether DevTools breakpoints should be allowed to pause execution."""
        return bool(getattr(self.options, "allow_devtools_breakpoints", False))

    def _build_skip_all_pauses_command(self, cmd_id):
        """Build the CDP command that applies the current DevTools pause policy."""
        skip = not self._allow_devtools_breakpoints()
        return json.dumps({
            "id": cmd_id,
            "method": "Debugger.setSkipAllPauses",
            "params": {"skip": skip},
        })

    def _log_skip_all_pauses_mode(self):
        """Record the active DevTools pause policy in the main log."""
        if self._allow_devtools_breakpoints():
            self.logger.info("[devtools] breakpoints enabled, pauses are allowed")
        else:
            self.logger.info("[anti-debug] Debugger.setSkipAllPauses(true) sent")

    def on_cdp_event(self, method, callback):
        """Subscribe to a CDP event by method name (e.g. 'Debugger.scriptParsed')."""
        self._event_listeners.setdefault(method, []).append(callback)

    def off_cdp_event(self, method, callback):
        """Unsubscribe from a CDP event."""
        cbs = self._event_listeners.get(method, [])
        if callback in cbs:
            cbs.remove(callback)

    def _handle_cdp_response(self, message_str):
        """Check if a CDP response matches a pending evaluate_js call, or dispatch events."""
        try:
            data = json.loads(message_str)
        except (json.JSONDecodeError, TypeError):
            return
        msg_id = data.get("id")
        if msg_id is not None and msg_id in self._pending_responses:
            future = self._pending_responses.pop(msg_id)
            if not future.done():
                future.set_result(data)
        # Dispatch CDP events (messages with "method" but no "id")
        method = data.get("method")
        if method and method in self._event_listeners:
            for cb in self._event_listeners[method]:
                try:
                    cb(data)
                except Exception:
                    pass

    # ── Debug Server ──

    async def _start_debug_server(self):
        """Start the miniapp debug server and bridge miniapp messages to CDP clients."""
        engine = self
        logger = self.logger
        bus = self.bus
        userscripts = self.userscripts

        scripts_injected = False

        def on_proxy_message(message: str):
            engine.message_counter += 1
            raw_payload = {
                "jscontext_id": "",
                "op_id": round(100 * random.random()),
                "payload": str(message),
            }
            logger.main_debug(raw_payload)
            wrapped = wrap_debug_message_data(raw_payload, "chromeDevtools", 0)
            out_msg = proto.WARemoteDebug_DebugMessage()
            out_msg.seq = engine.message_counter
            out_msg.category = "chromeDevtools"
            out_msg.data = wrapped["buffer"]
            out_msg.compressAlgo = 0
            out_msg.originalSize = wrapped["originalSize"]
            encoded = out_msg.SerializeToString()
            clients_snapshot = list(engine.miniapp_clients)
            for ws in clients_snapshot:
                try:
                    task = asyncio.ensure_future(ws.send(encoded))
                    task.add_done_callback(lambda t: t.exception() if t.done() and not t.cancelled() and t.exception() else None)
                except Exception:
                    pass

        bus.on_proxy_message(on_proxy_message)

        async def handler(websocket):
            nonlocal scripts_injected
            engine.miniapp_clients.add(websocket)
            engine._notify_status("miniapp", True)
            logger.info("[miniapp] miniapp client connected")

            if userscripts and not scripts_injected:
                scripts_injected = True
                logger.info("[userscript] registering scripts immediately on connection...")
                try:
                    seq = engine.message_counter
                    cmd_id = 90000
                    seq += 1
                    await websocket.send(_build_protobuf_cdp_message(
                        build_cdp_enable_page_command(cmd_id), seq
                    ))
                    cmd_id += 1
                    seq += 1
                    await websocket.send(_build_protobuf_cdp_message(
                        json.dumps({"id": cmd_id, "method": "Debugger.enable", "params": {}}), seq
                    ))
                    cmd_id += 1
                    logger.info("[anti-debug] Debugger.enable sent")
                    seq += 1
                    await websocket.send(_build_protobuf_cdp_message(
                        engine._build_skip_all_pauses_command(cmd_id), seq
                    ))
                    cmd_id += 1
                    engine._log_skip_all_pauses_mode()
                    for script in userscripts:
                        seq += 1
                        await websocket.send(_build_protobuf_cdp_message(
                            build_cdp_add_script_command(script, cmd_id), seq
                        ))
                        cmd_id += 1
                        logger.info(f"[userscript] registered (persistent): {script.name}")
                    engine.message_counter = seq
                    logger.info("[userscript] registration done, scripts will run on page load")
                except Exception as e:
                    logger.error(f"[userscript] registration error: {e}")

            immediate_done = False
            try:
                async for message in websocket:
                    if isinstance(message, str):
                        message = message.encode("utf-8")
                    msg_category = ""
                    try:
                        decoded_msg = proto.WARemoteDebug_DebugMessage()
                        decoded_msg.ParseFromString(message)
                        msg_category = decoded_msg.category
                    except Exception:
                        pass
                    self._process_miniapp_message(message)
                    if msg_category == "setupContext" and userscripts and not immediate_done:
                        immediate_done = True
                        await asyncio.sleep(0.5)
                        try:
                            seq = engine.message_counter
                            cmd_id = 91000
                            seq += 1
                            await websocket.send(_build_protobuf_cdp_message(
                                json.dumps({"id": cmd_id, "method": "Debugger.enable", "params": {}}), seq
                            ))
                            cmd_id += 1
                            seq += 1
                            await websocket.send(_build_protobuf_cdp_message(
                                engine._build_skip_all_pauses_command(cmd_id), seq
                            ))
                            cmd_id += 1
                            engine._log_skip_all_pauses_mode()
                            for script in userscripts:
                                wrapped = build_injection_wrapper(script)
                                seq += 1
                                cdp_cmd = json.dumps({
                                    "id": cmd_id,
                                    "method": "Runtime.evaluate",
                                    "params": {
                                        "expression": wrapped,
                                        "includeCommandLineAPI": True,
                                        "silent": False,
                                    },
                                })
                                await websocket.send(_build_protobuf_cdp_message(cdp_cmd, seq))
                                cmd_id += 1
                                logger.info(f"[userscript] immediate inject (Runtime.evaluate): {script.name}")
                            engine.message_counter = seq
                        except Exception as e:
                            logger.warn(f"[userscript] immediate inject warning: {e}")
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                logger.error(f"[miniapp] miniapp client err: {e}")
            finally:
                engine.miniapp_clients.discard(websocket)
                if not engine.miniapp_clients:
                    engine._notify_status("miniapp", False)
                    engine._js_contexts.clear()
                    engine._selected_jscontext_id = ""
                    engine._connected_jscontext_id = ""
                    engine._last_observed_jscontext_id = ""
                    engine._recent_debug_categories.clear()
                    engine._last_context_diagnostic_state = ""
                    engine._notify_contexts()
                    # 清理所有挂起的 CDP 响应，防止 future 泄漏
                    for fid, fut in list(engine._pending_responses.items()):
                        if not fut.done():
                            fut.set_exception(RuntimeError("miniapp disconnected"))
                    engine._pending_responses.clear()
                logger.info("[miniapp] miniapp client disconnected")

        server = await websockets.server.serve(
            handler, "0.0.0.0", self.options.debug_port,
            max_size=None,
        )
        logger.info(f"[server] debug server running on ws://localhost:{self.options.debug_port}")
        logger.info("[server] debug server waiting for miniapp to connect...")
        return server

    def _process_miniapp_message(self, message: bytes):
        self.logger.main_debug(
            f"[miniapp] client received raw message (hex): {buffer_to_hex_string(message)}"
        )
        unwrapped_data = None
        try:
            decoded = proto.WARemoteDebug_DebugMessage()
            decoded.ParseFromString(message)
            unwrapped_data = unwrap_debug_message_data(decoded)
            self.logger.main_debug("[miniapp] [DEBUG] decoded data:")
            self.logger.main_debug(unwrapped_data)
        except Exception as e:
            self.logger.error(f"[miniapp] miniapp client err: {e}")

        if unwrapped_data is None:
            return

        category = unwrapped_data.get("category")
        self._remember_debug_category(category)
        data = unwrapped_data.get("data", {}) if isinstance(unwrapped_data.get("data"), dict) else {}
        if category == "addJsContext":
            if self._observe_js_context(
                data.get("jscontext_id", ""),
                data.get("jscontext_name", ""),
                source="addJsContext",
            ):
                self._notify_contexts()
        elif category == "removeJsContext":
            ctx_id = str(data.get("jscontext_id", "") or "").strip()
            if ctx_id and ctx_id in self._js_contexts:
                self._js_contexts.pop(ctx_id, None)
                if self._connected_jscontext_id == ctx_id:
                    self._connected_jscontext_id = ""
                if self._selected_jscontext_id == ctx_id:
                    self._selected_jscontext_id = ""
                self._maybe_autoselect_context()
                self._notify_contexts()
        elif category == "connectJsContext":
            if self._observe_js_context(
                data.get("jscontext_id", ""),
                connected=True,
                source="connectJsContext",
            ):
                self._notify_contexts()
        elif category in ("chromeDevtools", "chromeDevtoolsResult"):
            if self._observe_js_context(
                data.get("jscontext_id", ""),
                connected=(category == "chromeDevtoolsResult"),
                source=category,
            ):
                self._notify_contexts()
        self._notify_contexts_if_diagnostics_changed()

        if category == "chromeDevtoolsResult":
            payload = data.get("payload", "")
            self.bus.emit_cdp_message(payload)
            # Also check for pending evaluate_js responses
            self._handle_cdp_response(payload)

    # ── Proxy Server ──

    async def _start_proxy_server(self):
        engine = self
        logger = self.logger
        bus = self.bus

        def on_cdp_message(message: str):
            clients_snapshot = list(engine.devtools_clients)
            for ws in clients_snapshot:
                try:
                    task = asyncio.ensure_future(ws.send(message))
                    task.add_done_callback(lambda t: t.exception() if t.done() and not t.cancelled() and t.exception() else None)
                except Exception:
                    pass

        bus.on_cdp_message(on_cdp_message)

        async def handler(websocket):
            engine.devtools_clients.add(websocket)
            engine._notify_status("devtools", True)
            logger.info("[cdp] CDP client connected")
            try:
                async for message in websocket:
                    if isinstance(message, bytes):
                        message = message.decode("utf-8")
                    bus.emit_proxy_message(message)
            except websockets.exceptions.ConnectionClosed:
                pass
            except Exception as e:
                logger.error(f"[cdp] CDP client err: {e}")
            finally:
                engine.devtools_clients.discard(websocket)
                if not engine.devtools_clients:
                    engine._notify_status("devtools", False)
                logger.info("[cdp] CDP client disconnected")

        server = await websockets.server.serve(
            handler, "0.0.0.0", self.options.cdp_port,
            max_size=None,
        )
        logger.info(f"[server] proxy server running on ws://localhost:{self.options.cdp_port}")
        logger.info(f"[server] link: devtools://devtools/bundled/inspector.html?ws=127.0.0.1:{self.options.cdp_port}")
        return server

    # ── Frida ──

    # ── Frida: platform helpers ──

    def _get_project_root(self):
        if getattr(sys, 'frozen', False):
            return Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve()
        return Path(__file__).parent.parent.resolve()

    def _find_wmpf_pids_win(self):
        """Windows: find main WeChatAppEx.exe PID via ppid frequency."""
        device = frida.get_local_device()
        processes = device.enumerate_processes(scope="metadata")
        wmpf_procs = [p for p in processes if p.name == "WeChatAppEx.exe"]
        if not wmpf_procs:
            raise RuntimeError("[frida] WeChatAppEx.exe process not found")

        ppids = [p.parameters.get("ppid", 0) or 0 for p in wmpf_procs]
        main_pid = Counter(ppids).most_common(1)[0][0]
        if main_pid == 0:
            raise RuntimeError("[frida] WeChatAppEx.exe main process not found")

        main_proc = next((p for p in processes if p.pid == main_pid), None)
        if main_proc is None:
            raise RuntimeError("[frida] could not locate main WMPF process")

        proc_path = main_proc.parameters.get("path", "")
        nums = re.findall(r"\d+", proc_path)
        if not nums:
            raise RuntimeError("[frida] cannot detect WMPF version from path")
        version = int(nums[-1])
        if version == 0:
            raise RuntimeError("[frida] invalid WMPF version")

        return [main_pid], version

    def _find_wmpf_pids_darwin(self):
        """macOS: find WeChatAppEx PIDs via pgrep, version via Info.plist."""
        try:
            out = subprocess.check_output(
                ["pgrep", "-f", "/MacOS/WeChatAppEx.app/Contents/MacOS/WeChatAppEx"],
                text=True,
            ).strip()
            pids = [int(p) for p in out.splitlines() if p.strip()]
        except (subprocess.CalledProcessError, ValueError):
            pids = []
        if not pids:
            raise RuntimeError("[frida] WeChatAppEx process not found on macOS")

        try:
            ver_out = subprocess.check_output(
                ["defaults", "read",
                 "/Applications/WeChat.app/Contents/MacOS/WeChatAppEx.app/Contents/Info.plist",
                 "CFBundleVersion"],
                text=True,
            ).strip()
            version = int(ver_out.split(".")[1])
        except Exception:
            raise RuntimeError("[frida] cannot detect WeChatAppEx version from Info.plist")

        return pids, version

    async def _start_frida(self):
        logger = self.logger
        is_mac = sys.platform == "darwin"
        platform_dir = "mac" if is_mac else "win"

        # Find PIDs and version
        if is_mac:
            pids, wmpf_version = self._find_wmpf_pids_darwin()
        else:
            pids, wmpf_version = self._find_wmpf_pids_win()

        # Load hook script and config
        project_root = self._get_project_root()
        hook_path = project_root / "frida" / "hook.js"
        if not hook_path.exists():
            raise RuntimeError("[frida] hook script not found")

        config_path = project_root / "frida" / "config" / platform_dir / f"addresses.{wmpf_version}.json"
        if not config_path.exists():
            raise RuntimeError(f"[frida] version config not found: {platform_dir}/{wmpf_version}")

        script_content = hook_path.read_text(encoding="utf-8")
        config_content = json.dumps(json.loads(config_path.read_text(encoding="utf-8")))
        final_script = script_content.replace("@@CONFIG@@", config_content)

        # Inject into all target PIDs
        device = frida.get_local_device()
        session = None
        script = None

        def on_message(message, data):
            if message.get("type") == "error":
                logger.error("[frida client]", message)
                return
            logger.frida_debug("[frida client]", message.get("payload", ""))

        for pid in pids:
            try:
                s = device.attach(pid)
                sc = s.create_script(final_script)
                sc.on("message", on_message)
                sc.load()
                logger.info(f"[frida] injected pid={pid}, version={wmpf_version}")
                # Keep first successful session/script as primary
                if session is None:
                    session, script = s, sc
            except Exception as e:
                logger.error(f"[frida] failed to inject pid={pid}: {e}")

        if session is None:
            raise RuntimeError("[frida] failed to inject any WeChatAppEx process")

        logger.info(f"[frida] ready ({platform_dir}), version={wmpf_version}, {len(pids)} process(es)")
        logger.info("[frida] you can now open any miniapps")
        return session, script
