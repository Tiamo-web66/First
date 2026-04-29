"""
MiniProgramNavigator - inject JS navigator and control mini program pages.
"""
import asyncio
import json
from pathlib import Path

_NAV_JS = (Path(__file__).parent / "nav_inject.js").read_text(encoding="utf-8")
_RUNTIME_ROOT_EXPR = (
    "(typeof globalThis!=='undefined'?globalThis:"
    "(typeof window!=='undefined'?window:"
    "(typeof self!=='undefined'?self:this)))"
)


class MiniProgramNavigator:
    """Inject navigator JS and operate on the selected miniapp runtime target."""

    def __init__(self, engine):
        self.engine = engine
        self.pages = []
        self.tab_bar_pages = []
        self.app_info = {}
        self._injected = False
        self._capture_requested = False

    def _build_runtime_expr(self, body):
        """Wrap one JS body with a runtime-global resolver."""
        return f"(function(){{var g={_RUNTIME_ROOT_EXPR};{body}}})()"

    def _build_nav_expr(self, expression):
        """Build one JS expression that requires a ready navigator bridge."""
        return self._build_runtime_expr(
            "var nav=g&&g.nav;"
            "if(!nav)throw new Error('nav unavailable');"
            f"return ({expression});"
        )

    def _build_nav_json_expr(self, expression):
        """Build one JS expression that returns JSON text through the navigator bridge."""
        return self._build_runtime_expr(
            "try{"
            "var nav=g&&g.nav;"
            "if(!nav)return JSON.stringify({ok:false,error:'nav unavailable'});"
            f"return JSON.stringify({expression});"
            "}catch(e){"
            "return JSON.stringify({ok:false,error:e&&e.message?e.message:String(e)});"
            "}"
        )

    async def _eval_json(self, expression, timeout=5.0):
        """Evaluate one JS expression that returns JSON text and decode it."""
        result = await self.engine.evaluate_js(expression, timeout=timeout)
        value = self._extract_value(result)
        if value is None:
            raise RuntimeError("miniapp runtime returned no value")
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError(f"miniapp runtime returned invalid JSON: {exc}") from exc

    async def _ensure(self, force=False):
        """Ensure the navigator bridge exists in the current runtime target."""
        should_inject = force or not self._injected
        if not should_inject:
            should_inject = not await self._nav_ready()
        if should_inject:
            await self.engine.evaluate_js(_NAV_JS, timeout=10.0)
            self._injected = True
            await self._restore_capture_state()

    async def _nav_ready(self):
        """Check whether the current runtime target has a usable navigator bridge."""
        try:
            state = await self._eval_json(
                self._build_runtime_expr(
                    "try{"
                    "var nav=g&&g.nav;"
                    "return JSON.stringify({"
                    "hasNav:!!nav,"
                    "hasWxFrame:!!(nav&&nav.wxFrame),"
                    "hasWx:typeof wx!=='undefined',"
                    "hasGetCurrentPages:typeof getCurrentPages!=='undefined'"
                    "});"
                    "}catch(e){"
                    "return JSON.stringify({hasNav:false,error:e&&e.message?e.message:String(e)});"
                    "}"
                ),
                timeout=3.0,
            )
        except Exception:
            return False
        return bool(state.get("hasNav") and state.get("hasWxFrame"))

    async def _restore_capture_state(self):
        """Re-enable request capture after navigator reinjection when needed."""
        if not self._capture_requested:
            return
        result = await self._call_nav_json("nav.startCapture()", timeout=5.0)
        if not isinstance(result, dict) or not result.get("ok"):
            raise RuntimeError(result.get("error") or "failed to restore request capture state")

    async def _call_nav_json(self, expression, timeout=5.0):
        """Evaluate one navigator expression that returns JSON text."""
        return await self._eval_json(self._build_nav_json_expr(expression), timeout=timeout)

    async def fetch_config(self):
        """Inject navigator and read pages, tab bar, and app info from the runtime."""
        await self._ensure(force=True)
        config = await self._call_nav_json(
            "({"
            "pages:nav.allPages||[],"
            "tabBar:nav.tabBarPages||[],"
            "appid:nav.config?(nav.config.appid||nav.config.appId||''):'',"
            "entry:nav.config?(nav.config.entryPagePath||''):'',"
            "name:(function(){try{"
            "var f=nav.wxFrame;"
            "var a=(f&&f.__wxConfig)||g.__wxConfig||{};"
            "var b=a.accountInfo&&a.accountInfo.appAccount;"
            "return b&&b.nickname||a.appname||'';"
            "}catch(e){return ''}})()"
            "})",
            timeout=5.0,
        )
        if not isinstance(config, dict):
            return
        self.pages = config.get("pages", [])
        self.tab_bar_pages = config.get("tabBar", [])
        self.app_info = {
            "appid": config.get("appid", ""),
            "entry": config.get("entry", ""),
            "name": config.get("name", ""),
        }

    async def navigate_to(self, route):
        """Smart navigate via navigator.goTo."""
        await self._ensure()
        safe = route.replace("\\", "\\\\").replace("'", "\\'")
        await self.engine.evaluate_js(self._build_nav_expr(f"nav.goTo('{safe}')"), timeout=5.0)

    async def redirect_to(self, route):
        """Run wx.redirectTo through the current navigator bridge."""
        await self._ensure()
        safe = route.replace("\\", "\\\\").replace("'", "\\'")
        await self.engine.evaluate_js(
            self._build_nav_expr(f"nav.wxFrame.wx.redirectTo({{url:'/{safe}'}})"),
            timeout=5.0,
        )

    async def relaunch_to(self, route):
        """Safe navigate with reLaunch, switchTab, and redirectTo fallback."""
        await self._ensure()
        safe = route.replace("\\", "\\\\").replace("'", "\\'")
        await self.engine.evaluate_js(
            self._build_nav_expr(f"nav._safeNavigate('{safe}')"),
            timeout=5.0,
        )

    async def navigate_back(self, delta=1):
        """Run wx.navigateBack through the navigator bridge."""
        await self._ensure()
        await self.engine.evaluate_js(self._build_nav_expr(f"nav.back({delta})"), timeout=5.0)

    async def refresh_page(self):
        """Refresh the current page by relaunching to the active route."""
        await self._ensure()
        return await self._call_nav_json(
            "(function(){"
            "var cur=nav.current();"
            "if(!cur)return {ok:false,error:'no route'};"
            "var pages=(nav.wxFrame&&nav.wxFrame.getCurrentPages)?nav.wxFrame.getCurrentPages():[];"
            "var page=pages&&pages.length?pages[pages.length-1]:null;"
            "var opts=(page&&page.options)||{};"
            "var qs=Object.keys(opts).map(function(k){return k+'='+opts[k]}).join('&');"
            "var url='/' + cur;"
            "if(qs)url+='?'+qs;"
            "nav.wxFrame.wx.reLaunch({"
            "url:url,"
            "success:function(){},"
            "fail:function(){nav.wxFrame.wx.redirectTo({url:url,success:function(){},fail:function(){}});}"
            "});"
            "return {ok:true,route:cur};"
            "})()",
            timeout=5.0,
        )

    async def get_current_route(self):
        """Read the current page route through the navigator bridge."""
        await self._ensure()
        result = await self.engine.evaluate_js(self._build_nav_expr("nav.current()"), timeout=3.0)
        return self._extract_value(result) or ""

    async def start_capture(self):
        """Enable request capture in the current runtime target."""
        self._capture_requested = True
        await self._ensure()
        result = await self._call_nav_json("nav.startCapture()", timeout=5.0)
        return result if isinstance(result, dict) else {"ok": False}

    async def stop_capture(self):
        """Disable request capture while keeping buffered records available."""
        self._capture_requested = False
        await self._ensure()
        result = await self._call_nav_json("nav.stopCapture()", timeout=5.0)
        return result if isinstance(result, dict) else {"ok": False}

    async def get_recent_requests(self, limit=50):
        """Return recent captured miniapp requests."""
        await self._ensure()
        limit = max(1, min(int(limit or 50), 200))
        rows = await self._call_nav_json(f"nav.getCapturedRequests({limit})", timeout=5.0)
        if not isinstance(rows, list):
            raise RuntimeError("captured requests payload is not a list")
        return rows

    async def clear_captured_requests(self):
        """Clear request capture records kept in the current runtime target."""
        await self._ensure()
        result = await self._call_nav_json("nav.clearCapturedRequests()", timeout=5.0)
        return result if isinstance(result, dict) else {"ok": False}

    async def get_capture_state(self):
        """Inspect navigator, wx, and hook state in the current runtime target."""
        await self._ensure()
        state = await self._call_nav_json("nav.getRuntimeState()", timeout=5.0)
        if not isinstance(state, dict):
            raise RuntimeError("capture state payload is not an object")
        return state

    async def auto_visit(self, pages, delay=2.0, on_progress=None, cancel_event=None):
        """Visit pages sequentially using safe navigation."""
        total = len(pages)
        for i, route in enumerate(pages):
            if cancel_event and cancel_event.is_set():
                break
            if on_progress:
                on_progress(i, total, route)
            try:
                await self.relaunch_to(route)
            except Exception:
                pass
            await asyncio.sleep(delay)
        if on_progress:
            on_progress(total, total, "done")

    async def enable_redirect_guard(self):
        """Enable forced-navigation blocking in the current runtime target."""
        await self._ensure()
        result = await self._call_nav_json("nav.enableRedirectGuard()", timeout=5.0)
        return result if isinstance(result, dict) else {"ok": False}

    async def disable_redirect_guard(self):
        """Disable forced-navigation blocking in the current runtime target."""
        await self._ensure()
        await self.engine.evaluate_js(self._build_nav_expr("nav.disableRedirectGuard()"), timeout=5.0)

    async def get_blocked_redirects(self):
        """Return blocked redirect history kept by the current runtime target."""
        await self._ensure()
        result = await self._call_nav_json("nav.getBlockedRedirects()", timeout=5.0)
        return result if isinstance(result, list) else []

    @staticmethod
    def _extract_value(result):
        """Extract the primitive value returned by CDP Runtime.evaluate."""
        if not result:
            return None
        r = result.get("result", {})
        inner = r.get("result", {})
        return inner.get("value")
