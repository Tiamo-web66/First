"""Generate GUI style concept images for the desktop debugger."""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)


OUT_DIR = Path(__file__).resolve().parent
W, H = 1365, 920


def color(hex_color: str, alpha: int | None = None) -> QColor:
    """Create a QColor from a hex value and optionally override alpha."""
    c = QColor(hex_color)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def font(size: int, weight: int = QFont.Normal) -> QFont:
    """Return the preferred UI font used by the mockup text."""
    f = QFont("Microsoft YaHei UI")
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


def round_rect_path(rect: QRectF, radius: float) -> QPainterPath:
    """Build a rounded-rectangle painter path."""
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def draw_shadow(
    p: QPainter,
    rect: QRectF,
    radius: float,
    color_value: QColor,
    spread: int,
    dy: int = 10,
) -> None:
    """Draw a soft layered shadow behind a rounded rectangle."""
    for i in range(spread, 0, -1):
        alpha = max(3, int(color_value.alpha() * (i / spread) ** 2 / 5))
        c = QColor(color_value)
        c.setAlpha(alpha)
        offset = i * 1.4
        shadow_rect = rect.adjusted(-offset, -offset + dy, offset, offset + dy)
        p.fillPath(round_rect_path(shadow_rect, radius + offset), c)


def fill_round(
    p: QPainter,
    rect: QRectF,
    radius: float,
    fill: QColor | QLinearGradient,
    border: QColor | None = None,
    width: float = 1.0,
) -> None:
    """Fill a rounded rectangle and optionally draw its border."""
    path = round_rect_path(rect, radius)
    p.fillPath(path, fill)
    if border is not None:
        p.setPen(QPen(border, width))
        p.drawPath(path)
        p.setPen(Qt.NoPen)


def draw_text(
    p: QPainter,
    x: float,
    y: float,
    text: str,
    size: int,
    c: QColor,
    weight: int = QFont.Normal,
    w: float = 360,
    h: float = 30,
    align: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter,
) -> None:
    """Draw UI text using the configured Chinese UI font."""
    p.setFont(font(size, weight))
    p.setPen(c)
    p.drawText(QRectF(x, y, w, h), align, text)
    p.setPen(Qt.NoPen)


def draw_icon_dot(p: QPainter, cx: float, cy: float, c: QColor, label: str = "") -> None:
    """Draw a compact rounded icon marker with an optional glyph-like label."""
    fill_round(p, QRectF(cx - 14, cy - 14, 28, 28), 10, c, color("#ffffff", 130))
    if label:
        draw_text(p, cx - 11, cy - 12, label, 14, color("#ffffff"), QFont.DemiBold, 22, 24, Qt.AlignCenter)


def draw_mac_traffic(p: QPainter, x: float, y: float) -> None:
    """Draw macOS-style window traffic lights."""
    for i, c in enumerate(["#ff5f57", "#ffbd2e", "#28c840"]):
        p.setBrush(color(c))
        p.drawEllipse(QPointF(x + i * 22, y), 7, 7)
    p.setBrush(Qt.NoBrush)


def draw_window_controls(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw right-aligned minimize, maximize, and close window controls."""
    fill_round(
        p,
        rect,
        rect.height() / 2,
        color("#ffffff") if not dark else color("#111827"),
        color("#dfe5ef") if not dark else color("#34415f"),
    )
    centers = [
        QPointF(rect.left() + 17, rect.center().y()),
        QPointF(rect.left() + 43, rect.center().y()),
        QPointF(rect.left() + 69, rect.center().y()),
    ]
    btn_bg = color("#f3f6fb") if not dark else color("#1d2536")
    btn_border = color("#dfe5ef") if not dark else color("#34415f")
    icon = color("#6b778c") if not dark else color("#aeb8ce")
    close_bg = color("#fff1f0") if not dark else color("#3b1f24")
    close_icon = color("#dc2626") if not dark else color("#ff7a7a")

    for i, center in enumerate(centers):
        p.setBrush(close_bg if i == 2 else btn_bg)
        p.setPen(QPen(btn_border, 1))
        p.drawEllipse(center, 8.5, 8.5)
        p.setPen(QPen(close_icon if i == 2 else icon, 1.45, Qt.SolidLine, Qt.RoundCap))
        if i == 0:
            p.drawLine(QPointF(center.x() - 3.2, center.y()), QPointF(center.x() + 3.2, center.y()))
        elif i == 1:
            p.drawRect(QRectF(center.x() - 3.2, center.y() - 3.2, 6.4, 6.4))
        else:
            p.drawLine(QPointF(center.x() - 3.0, center.y() - 3.0), QPointF(center.x() + 3.0, center.y() + 3.0))
            p.drawLine(QPointF(center.x() + 3.0, center.y() - 3.0), QPointF(center.x() - 3.0, center.y() + 3.0))
    p.setPen(Qt.NoPen)
    p.setBrush(Qt.NoBrush)


def draw_sidebar_items(p: QPainter, x: float, y: float, dark: bool, active: int = 0) -> None:
    """Draw the common left navigation list for the debugger pages."""
    labels = ["调试会话", "脚本注入", "包提取", "云函数审计", "日志面板", "配置中心"]
    icon_labels = ["D", "J", "P", "C", "L", "S"]
    text_c = color("#9aa4b2") if not dark else color("#aeb8ce")
    active_c = color("#2f6fed") if not dark else color("#7aa2ff")
    for i, label in enumerate(labels):
        top = y + i * 56
        if i == active:
            fill_round(p, QRectF(x, top - 5, 210, 42), 12, color("#eef4ff") if not dark else color("#243250"))
            draw_icon_dot(p, x + 24, top + 16, active_c, icon_labels[i])
            draw_text(p, x + 48, top + 1, label, 15, color("#1d2b44") if not dark else color("#f4f7ff"), QFont.DemiBold)
        else:
            draw_icon_dot(p, x + 24, top + 16, color("#e3e8f2") if not dark else color("#30394f"), icon_labels[i])
            draw_text(p, x + 48, top + 1, label, 15, text_c)


def draw_line_chart(p: QPainter, rect: QRectF, accent: QColor, muted: QColor) -> None:
    """Draw a simplified monitoring line chart inside a card."""
    p.setPen(QPen(muted, 1))
    for i in range(4):
        y = rect.top() + 20 + i * (rect.height() - 36) / 3
        p.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
    points = []
    for i in range(7):
        x = rect.left() + i * rect.width() / 6
        v = 0.45 + math.sin(i * 1.2) * 0.23 + (i % 3) * 0.04
        y = rect.bottom() - 12 - v * (rect.height() - 36)
        points.append(QPointF(x, y))
    p.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    for a, b in zip(points, points[1:]):
        p.drawLine(a, b)
    p.setPen(QPen(accent, 7, Qt.SolidLine, Qt.RoundCap))
    p.drawPoint(points[-1])
    p.setPen(Qt.NoPen)


def draw_bar_chart(p: QPainter, rect: QRectF, colors: list[str]) -> None:
    """Draw a compact daily activity bar chart."""
    labels = ["一", "二", "三", "四", "五", "六", "日"]
    max_h = rect.height() - 34
    values = [0.34, 0.62, 0.48, 0.82, 0.52, 0.38, 0.72]
    for i, v in enumerate(values):
        x = rect.left() + i * rect.width() / 7 + 8
        h = max_h * v
        grad = QLinearGradient(x, rect.bottom() - h, x, rect.bottom())
        grad.setColorAt(0, color(colors[i % len(colors)]))
        grad.setColorAt(1, color(colors[i % len(colors)], 80))
        fill_round(p, QRectF(x, rect.bottom() - h, 16, h), 8, grad)
        draw_text(p, x - 2, rect.bottom() + 2, labels[i], 10, color("#9aa4b2"), w=24, h=18, align=Qt.AlignCenter)


def draw_ring(p: QPainter, cx: float, cy: float, radius: float, bg: QColor, parts: list[tuple[str, float]]) -> None:
    """Draw a segmented donut indicator for runtime status."""
    p.setPen(QPen(bg, 12, Qt.SolidLine, Qt.RoundCap))
    p.drawEllipse(QPointF(cx, cy), radius, radius)
    start = 90 * 16
    for hex_value, part in parts:
        p.setPen(QPen(color(hex_value), 12, Qt.SolidLine, Qt.RoundCap))
        span = int(-360 * part * 16)
        p.drawArc(QRectF(cx - radius, cy - radius, radius * 2, radius * 2), start, span)
        start += span
    p.setPen(Qt.NoPen)


def draw_console_rows(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw clipped log rows with a visible scrollbar inside a fixed viewport."""
    rows = [
        ("09:41:12", "CDP Runtime.evaluate ready", "#2f6fed"),
        ("09:41:18", "Frida hook attached to WMPF", "#24a148"),
        ("09:41:26", "userscript injected: cloud_audit", "#c27803"),
        ("09:41:33", "websocket proxy listening :62000", "#7357ff"),
        ("09:41:44", "hook app: 蜜雪冰城点单 wx8f2a4c9b", "#2f6fed"),
        ("09:41:56", "cloud.callFunction captured: orderSign", "#c27803"),
        ("09:42:08", "DevTools target refreshed", "#7357ff"),
        ("09:42:20", "navigator routes fetched: 47 pages", "#2f6fed"),
        ("09:42:31", "MCP HTTP service started: 127.0.0.1:8765/mcp", "#7357ff"),
        ("09:42:44", "sensitive extractor ready: 128 findings cached", "#ff7a59"),
    ]
    viewport = QRectF(rect.left(), rect.top(), rect.width() - 16, rect.height())
    fill_round(
        p,
        rect,
        12,
        color("#f6f8fc") if not dark else color("#0f1725", 170),
        color("#e2e8f0") if not dark else color("#2b3650"),
    )
    p.save()
    p.setClipPath(round_rect_path(viewport.adjusted(2, 2, -2, -2), 10))
    for i, (tm, msg, c) in enumerate(rows):
        y = rect.top() + 8 + i * 31
        fill_round(
            p,
            QRectF(rect.left() + 8, y, rect.width() - 36, 25),
            8,
            color("#ffffff") if not dark else color("#1d2536", 225),
            color("#edf1f7") if not dark else color("#303b55", 120),
        )
        draw_text(p, rect.left() + 20, y, tm, 11, color("#8792a6"), w=64)
        draw_text(p, rect.left() + 88, y, msg, 11, color(c), QFont.DemiBold, w=rect.width() - 145)
    p.restore()

    track = QRectF(rect.right() - 10, rect.top() + 10, 4, rect.height() - 20)
    fill_round(p, track, 2, color("#d6deea") if not dark else color("#34405b"))
    thumb_h = max(26, track.height() * min(1.0, rect.height() / (len(rows) * 31 + 16)))
    fill_round(
        p,
        QRectF(track.left(), track.top() + 8, track.width(), thumb_h),
        2,
        color("#8fa3c1") if not dark else color("#7aa2ff"),
    )


def draw_hook_target_badge(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the current hooked mini program summary in the title bar."""
    bg = color("#ffffff") if not dark else color("#111827")
    border = color("#dfe5ef") if not dark else color("#34415f")
    primary = color("#1f2a44") if not dark else color("#f7f9ff")
    secondary = color("#6b778c") if not dark else color("#9aa6bd")
    accent = color("#22a06b") if not dark else color("#5de4a7")
    chip_bg = color("#eaf7ef") if not dark else color("#183527")
    port_bg = color("#f3f6fb") if not dark else color("#1d2536")
    mid_y = rect.top() + rect.height() / 2
    fill_round(p, rect, rect.height() / 2, bg, border)
    p.setBrush(accent)
    p.drawEllipse(QPointF(rect.left() + 20, mid_y), 5, 5)
    p.setBrush(Qt.NoBrush)
    draw_text(p, rect.left() + 34, rect.top(), "Hook", 11, secondary, QFont.DemiBold, w=42, h=rect.height(), align=Qt.AlignVCenter)
    draw_text(p, rect.left() + 78, rect.top(), "蜜雪冰城点单", 13, primary, QFont.Bold, w=118, h=rect.height(), align=Qt.AlignVCenter)
    port_rect = QRectF(rect.right() - 168, rect.top() + 7, 88, 20)
    draw_text(p, rect.left() + 206, rect.top(), "wx8f2a4c9b7e0130", 11, secondary, QFont.DemiBold, w=port_rect.left() - rect.left() - 218, h=rect.height(), align=Qt.AlignVCenter)
    fill_round(p, port_rect, 10, port_bg, border)
    draw_text(p, port_rect.left() + 10, port_rect.top(), "CDP :62000", 11, secondary, QFont.DemiBold, w=68, h=18, align=Qt.AlignCenter)
    fill_round(p, QRectF(rect.right() - 72, rect.top() + 6, 56, 22), 11, chip_bg, color("#c7eed4") if not dark else color("#2f684a"))
    draw_text(p, rect.right() - 66, rect.top() + 6, "已连接", 11, accent, QFont.Bold, w=44, h=20, align=Qt.AlignCenter)


def draw_mac_light() -> None:
    """Render a clean macOS-inspired light theme concept."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#f5f6f9"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, color("#f7f9fc"))
    bg.setColorAt(1, color("#eef2f8"))
    p.fillRect(0, 0, W, H, bg)

    draw_shadow(p, QRectF(120, 64, 1125, 640), 28, color("#24304a", 120), 24, 18)
    fill_round(p, QRectF(120, 64, 1125, 640), 28, color("#ffffff", 235), color("#dfe5ef"))
    fill_round(p, QRectF(120, 64, 1125, 52), 28, color("#f7f9fc", 235), color("#ffffff", 180))
    draw_mac_traffic(p, 153, 91)
    draw_text(p, 214, 76, "微信小程序调试台", 18, color("#1f2a44"), QFont.DemiBold, w=240)
    draw_hook_target_badge(p, QRectF(790, 70, 422, 44), False)

    fill_round(p, QRectF(144, 132, 230, 548), 22, color("#f8fafd"), color("#e6ebf4"))
    draw_text(p, 170, 158, "MiniDebug", 24, color("#14213d"), QFont.Bold)
    draw_text(p, 171, 194, "授权目标 · 本地代理 · 注入脚本", 12, color("#8a96a9"), w=200)
    draw_sidebar_items(p, 163, 242, False, 0)

    fill_round(p, QRectF(402, 132, 812, 66), 18, color("#f6f8fc"), color("#e3e8f0"))
    for i, (label, c) in enumerate([("主控", "#2f6fed"), ("代理", "#7357ff"), ("Frida", "#ff7a59"), ("审计", "#22a06b")]):
        draw_icon_dot(p, 440 + i * 84, 165, color(c), label[:1])
        draw_text(p, 460 + i * 84, 151, label, 13, color("#33425f"), QFont.DemiBold, w=58)
    fill_round(p, QRectF(780, 149, 230, 32), 16, color("#ffffff"), color("#dde4ee"))
    draw_text(p, 800, 150, "搜索 AppID / 页面 / 日志", 12, color("#9aa4b2"), w=170)
    fill_round(p, QRectF(1032, 148, 68, 34), 12, color("#1f6feb"), color("#1f6feb"))
    draw_text(p, 1047, 151, "启动", 13, color("#ffffff"), QFont.DemiBold, w=40, align=Qt.AlignCenter)

    cards = [(402, 224, 250, 180), (676, 224, 250, 180), (950, 224, 264, 180)]
    titles = ["调试状态", "请求趋势", "运行占比"]
    for i, (x, y, w, h) in enumerate(cards):
        fill_round(p, QRectF(x, y, w, h), 20, color("#ffffff"), color("#e5eaf2"))
        draw_text(p, x + 22, y + 18, titles[i], 16, color("#23314d"), QFont.DemiBold)
    draw_ring(p, 527, 318, 48, color("#e6ebf4"), [("#2f6fed", .46), ("#22a06b", .22), ("#ffbd2e", .16)])
    draw_text(p, 493, 300, "92%", 24, color("#23314d"), QFont.Bold, w=70, align=Qt.AlignCenter)
    draw_line_chart(p, QRectF(706, 270, 190, 92), color("#2f6fed"), color("#edf1f7"))
    draw_bar_chart(p, QRectF(984, 270, 190, 92), ["#2f6fed", "#22a06b", "#ff7a59"])

    metric_specs = [("连接会话", "3", "#2f6fed"), ("已注入脚本", "12", "#7357ff"), ("捕获请求", "428", "#22a06b"), ("异常事件", "5", "#ff7a59")]
    for i, (name, val, c) in enumerate(metric_specs):
        x = 402 + i * 203
        fill_round(p, QRectF(x, 428, 182, 92), 18, color(c, 235), color("#ffffff", 80))
        draw_text(p, x + 18, 448, name, 13, color("#ffffff", 210), QFont.DemiBold, w=120)
        draw_text(p, x + 18, 474, val, 28, color("#ffffff"), QFont.Bold, w=90)

    fill_round(p, QRectF(402, 548, 500, 132), 20, color("#ffffff"), color("#e5eaf2"))
    draw_text(p, 426, 566, "实时日志", 16, color("#23314d"), QFont.DemiBold)
    draw_console_rows(p, QRectF(426, 596, 450, 68), False)
    fill_round(p, QRectF(930, 548, 284, 132), 20, color("#ffffff"), color("#e5eaf2"))
    draw_text(p, 954, 566, "快速动作", 16, color("#23314d"), QFont.DemiBold)
    for i, label in enumerate(["打开 DevTools", "导出日志", "停止代理"]):
        fill_round(p, QRectF(954, 600 + i * 30, 220, 24), 10, color("#f5f7fb"), color("#e2e8f0"))
        draw_text(p, 970, 598 + i * 30, label, 12, color("#526074"), w=160)
    p.end()
    img.save(str(OUT_DIR / "01_mac_light.png"))


def draw_mac_dark() -> None:
    """Render a restrained macOS-inspired dark theme concept."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#0e1118"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, color("#0e1118"))
    bg.setColorAt(1, color("#171d2b"))
    p.fillRect(0, 0, W, H, bg)
    for x in range(110, W, 190):
        p.setPen(QPen(color("#ffffff", 16), 1))
        p.drawLine(x, 0, x, H)
    p.setPen(Qt.NoPen)

    fill_round(p, QRectF(105, 72, 1155, 624), 30, color("#171d2b", 244), color("#2c3750"))
    draw_shadow(p, QRectF(105, 72, 1155, 624), 30, color("#000000", 200), 24, 20)
    fill_round(p, QRectF(105, 72, 1155, 624), 30, color("#171d2b", 245), color("#34415f"))
    fill_round(p, QRectF(105, 72, 1155, 54), 30, color("#1d2536"), color("#394560"))
    draw_mac_traffic(p, 140, 99)
    draw_text(p, 205, 84, "MiniDebug Console", 18, color("#f7f9ff"), QFont.DemiBold)
    draw_hook_target_badge(p, QRectF(800, 78, 412, 44), True)

    fill_round(p, QRectF(130, 146, 228, 526), 22, color("#111827"), color("#27334d"))
    draw_text(p, 158, 172, "调试工作区", 22, color("#f4f7ff"), QFont.Bold)
    draw_text(p, 158, 206, "CDP · Frida · Hook", 12, color("#7f8ba3"))
    draw_sidebar_items(p, 150, 254, True, 1)

    fill_round(p, QRectF(386, 146, 836, 66), 18, color("#111827"), color("#29354d"))
    for i, (label, c) in enumerate([("代理", "#7aa2ff"), ("注入", "#b18cff"), ("审计", "#5de4a7"), ("提取", "#ffad7a")]):
        fill_round(p, QRectF(412 + i * 92, 162, 72, 34), 12, color(c, 38), color(c, 120))
        draw_text(p, 412 + i * 92, 164, label, 13, color(c), QFont.DemiBold, w=72, align=Qt.AlignCenter)
    fill_round(p, QRectF(794, 164, 278, 30), 15, color("#1d2536"), color("#303b55"))
    draw_text(p, 816, 164, "筛选日志、AppID、页面路径", 12, color("#6f7a91"), w=190)
    fill_round(p, QRectF(1100, 162, 82, 34), 12, color("#7aa2ff"), color("#7aa2ff"))
    draw_text(p, 1119, 164, "运行中", 13, color("#0e1118"), QFont.Bold, w=44, align=Qt.AlignCenter)

    for x, title, accent in [(386, "Runtime", "#7aa2ff"), (662, "Network", "#5de4a7"), (938, "Inject", "#b18cff")]:
        fill_round(p, QRectF(x, 240, 250, 178), 20, color("#111827"), color("#28334c"))
        draw_text(p, x + 22, 258, title, 16, color("#f6f8ff"), QFont.DemiBold)
        draw_line_chart(p, QRectF(x + 28, 304, 188, 72), color(accent), color("#27324a"))
        draw_text(p, x + 22, 380, "稳定", 13, color(accent), QFont.DemiBold)

    for i, (name, val, c) in enumerate([("WebSocket", "62000", "#7aa2ff"), ("Hook 脚本", "8", "#b18cff"), ("捕获请求", "1,284", "#5de4a7"), ("错误", "2", "#ff7a59")]):
        x = 386 + i * 208
        fill_round(p, QRectF(x, 444, 184, 80), 18, color(c, 42), color(c, 110))
        draw_text(p, x + 18, 456, name, 12, color("#b7c0d4"), QFont.DemiBold)
        draw_text(p, x + 18, 480, val, 24, color("#f7f9ff"), QFont.Bold)

    fill_round(p, QRectF(386, 552, 532, 120), 18, color("#111827"), color("#28334c"))
    draw_text(p, 410, 568, "事件流", 16, color("#f7f9ff"), QFont.DemiBold)
    draw_console_rows(p, QRectF(410, 596, 474, 60), True)
    fill_round(p, QRectF(946, 552, 276, 120), 18, color("#111827"), color("#28334c"))
    draw_text(p, 970, 568, "运行占比", 16, color("#f7f9ff"), QFont.DemiBold)
    draw_ring(p, 1084, 624, 38, color("#28334c"), [("#7aa2ff", .44), ("#5de4a7", .28), ("#ffbd2e", .16)])
    p.end()
    img.save(str(OUT_DIR / "02_mac_dark.png"))


def draw_neumorphism() -> None:
    """Render a soft neumorphism concept with low-contrast controls."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#e9edf3"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.fillRect(0, 0, W, H, color("#e9edf3"))

    def neu_rect(rect: QRectF, radius: int, pressed: bool = False) -> None:
        """Draw one raised or inset neumorphic surface."""
        if not pressed:
            draw_shadow(p, rect, radius, color("#9aa7bd", 95), 16, 10)
            draw_shadow(p, rect.adjusted(0, 0, 0, 0), radius, color("#ffffff", 180), 10, -8)
            fill_round(p, rect, radius, color("#e9edf3"), color("#f7f9fc", 160))
        else:
            fill_round(p, rect, radius, color("#dfe5ee"), color("#f8fafc", 160))
            p.setPen(QPen(color("#b8c3d4", 110), 2))
            p.drawPath(round_rect_path(rect.adjusted(1, 1, -1, -1), radius))
            p.setPen(Qt.NoPen)

    neu_rect(QRectF(118, 58, 1128, 650), 34)
    draw_mac_traffic(p, 154, 92)
    draw_text(p, 214, 78, "柔和拟态调试台", 20, color("#273247"), QFont.Bold)
    neu_rect(QRectF(150, 132, 230, 534), 26)
    draw_text(p, 180, 166, "MiniDebug", 25, color("#273247"), QFont.Bold)
    draw_text(p, 181, 202, "更轻的层级，更少的边线", 12, color("#7b8799"), w=190)
    draw_sidebar_items(p, 170, 252, False, 3)

    neu_rect(QRectF(410, 132, 800, 64), 22, True)
    for i, label in enumerate(["主流程", "脚本", "捕获", "审计"]):
        neu_rect(QRectF(434 + i * 102, 147, 78, 34), 16, i == 0)
        draw_text(p, 434 + i * 102, 148, label, 13, color("#4d5c73"), QFont.DemiBold, w=78, align=Qt.AlignCenter)
    neu_rect(QRectF(804, 148, 244, 32), 16, True)
    draw_text(p, 826, 149, "搜索运行上下文", 12, color("#8a96a9"), w=170)
    neu_rect(QRectF(1072, 146, 84, 36), 17)
    draw_text(p, 1092, 149, "启动", 13, color("#2f6fed"), QFont.Bold, w=44, align=Qt.AlignCenter)

    for i, (x, title, accent) in enumerate([(410, "会话健康度", "#2f6fed"), (678, "请求分布", "#22a06b"), (946, "注入统计", "#7357ff")]):
        neu_rect(QRectF(x, 226, 238, 172), 24)
        draw_text(p, x + 24, 246, title, 16, color("#273247"), QFont.DemiBold)
        if i == 1:
            draw_bar_chart(p, QRectF(x + 30, 286, 170, 68), [accent, "#ff7a59", "#ffbd2e"])
        else:
            draw_ring(p, x + 118, 320, 42, color("#d6dee9"), [(accent, .56), ("#ffbd2e", .18), ("#22a06b", .12)])

    for i, (label, value, accent) in enumerate([("代理端口", "62000", "#2f6fed"), ("活动脚本", "12", "#7357ff"), ("捕获云函数", "36", "#22a06b"), ("风险项", "7", "#ff7a59")]):
        rect = QRectF(410 + i * 200, 430, 176, 82)
        neu_rect(rect, 22)
        draw_text(p, rect.left() + 18, rect.top() + 12, label, 12, color("#7b8799"), QFont.DemiBold)
        draw_text(p, rect.left() + 18, rect.top() + 38, value, 23, color(accent), QFont.Bold)

    neu_rect(QRectF(410, 548, 500, 118), 24, True)
    draw_text(p, 436, 564, "低噪音事件流", 16, color("#273247"), QFont.DemiBold)
    draw_console_rows(p, QRectF(436, 596, 438, 96), False)
    neu_rect(QRectF(942, 548, 268, 118), 24)
    draw_text(p, 968, 564, "一键操作", 16, color("#273247"), QFont.DemiBold)
    for i, label in enumerate(["打开面板", "导出报告", "清理缓存"]):
        neu_rect(QRectF(968, 596 + i * 29, 196, 24), 12, i == 1)
        draw_text(p, 980, 594 + i * 29, label, 12, color("#5b687c"), w=170)
    p.end()
    img.save(str(OUT_DIR / "03_neumorphism_soft.png"))


def draw_glassmorphism() -> None:
    """Render a translucent glass-style concept for a more visual dashboard."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#f2f6fb"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, color("#f3f7fb"))
    bg.setColorAt(.45, color("#eaf0f7"))
    bg.setColorAt(1, color("#f8f3ee"))
    p.fillRect(0, 0, W, H, bg)
    radial = QRadialGradient(QPointF(230, 120), 480)
    radial.setColorAt(0, color("#a7c7ff", 90))
    radial.setColorAt(1, color("#ffffff", 0))
    p.fillRect(0, 0, W, H, radial)
    radial2 = QRadialGradient(QPointF(1120, 650), 520)
    radial2.setColorAt(0, color("#ffb489", 80))
    radial2.setColorAt(1, color("#ffffff", 0))
    p.fillRect(0, 0, W, H, radial2)

    draw_shadow(p, QRectF(104, 66, 1158, 642), 34, color("#3d4a66", 110), 28, 16)
    fill_round(p, QRectF(104, 66, 1158, 642), 34, color("#ffffff", 150), color("#ffffff", 210), 1.4)
    fill_round(p, QRectF(132, 94, 1102, 586), 26, color("#ffffff", 105), color("#ffffff", 170))
    draw_mac_traffic(p, 160, 118)
    draw_text(p, 218, 101, "玻璃拟态调试台", 21, color("#1f2a44"), QFont.Bold)
    draw_text(p, 974, 104, "安全审计 · 实时代理", 13, color("#536177"), QFont.DemiBold, w=180, align=Qt.AlignRight | Qt.AlignVCenter)

    fill_round(p, QRectF(160, 156, 230, 492), 24, color("#ffffff", 128), color("#ffffff", 210))
    draw_text(p, 190, 186, "工作空间", 23, color("#1f2a44"), QFont.Bold)
    draw_text(p, 191, 220, "mac glass / translucent", 12, color("#6d7a90"), w=190)
    draw_sidebar_items(p, 180, 264, False, 2)

    fill_round(p, QRectF(420, 156, 782, 64), 22, color("#ffffff", 110), color("#ffffff", 200))
    for i, (label, c) in enumerate([("CDP", "#2f6fed"), ("Frida", "#7357ff"), ("Hook", "#ff7a59"), ("Cloud", "#22a06b")]):
        fill_round(p, QRectF(446 + i * 96, 170, 74, 36), 15, color(c, 38), color("#ffffff", 170))
        draw_text(p, 446 + i * 96, 172, label, 13, color(c), QFont.Bold, w=74, align=Qt.AlignCenter)
    fill_round(p, QRectF(800, 172, 230, 32), 16, color("#ffffff", 128), color("#ffffff", 190))
    draw_text(p, 820, 172, "搜索目标和日志", 12, color("#7b8799"), w=150)
    fill_round(p, QRectF(1056, 170, 90, 36), 15, color("#1f6feb", 210), color("#ffffff", 160))
    draw_text(p, 1074, 172, "连接", 13, color("#ffffff"), QFont.Bold, w=54, align=Qt.AlignCenter)

    for x, title, accent in [(420, "网络代理", "#2f6fed"), (690, "脚本注入", "#7357ff"), (960, "云审计", "#22a06b")]:
        fill_round(p, QRectF(x, 250, 242, 174), 24, color("#ffffff", 120), color("#ffffff", 205))
        draw_text(p, x + 22, 270, title, 16, color("#1f2a44"), QFont.Bold)
        draw_line_chart(p, QRectF(x + 28, 318, 184, 68), color(accent), color("#ffffff", 150))
        draw_text(p, x + 22, 386, "状态稳定", 12, color(accent), QFont.DemiBold)

    for i, (label, value, c) in enumerate([("会话", "3", "#2f6fed"), ("脚本", "12", "#7357ff"), ("请求", "428", "#22a06b"), ("风险", "7", "#ff7a59")]):
        rect = QRectF(420 + i * 196, 452, 168, 78)
        grad = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        grad.setColorAt(0, color(c, 165))
        grad.setColorAt(1, color("#ffffff", 90))
        fill_round(p, rect, 22, grad, color("#ffffff", 180))
        draw_text(p, rect.left() + 18, rect.top() + 11, label, 12, color("#ffffff", 220), QFont.Bold)
        draw_text(p, rect.left() + 18, rect.top() + 35, value, 25, color("#ffffff"), QFont.Bold)

    fill_round(p, QRectF(420, 560, 502, 88), 22, color("#ffffff", 120), color("#ffffff", 205))
    draw_text(p, 446, 578, "实时事件", 16, color("#1f2a44"), QFont.Bold)
    draw_console_rows(p, QRectF(446, 610, 438, 70), False)
    fill_round(p, QRectF(954, 560, 248, 88), 22, color("#ffffff", 120), color("#ffffff", 205))
    draw_text(p, 980, 578, "运行占比", 16, color("#1f2a44"), QFont.Bold)
    draw_ring(p, 1080, 616, 28, color("#ffffff", 145), [("#2f6fed", .4), ("#22a06b", .24), ("#ffbd2e", .18)])
    p.end()
    img.save(str(OUT_DIR / "04_glassmorphism.png"))


def draw_pill(p: QPainter, rect: QRectF, text: str, fg: str, bg: str, border: str | None = None) -> None:
    """Draw a compact status pill used by the function-aware mockups."""
    fill_round(p, rect, rect.height() / 2, color(bg), color(border) if border else None)
    draw_text(p, rect.left(), rect.top(), text, 11, color(fg), QFont.DemiBold, rect.width(), rect.height(), Qt.AlignCenter)


def draw_switch_mock(p: QPainter, x: float, y: float, on: bool, dark: bool) -> None:
    """Draw a small switch mock for settings and permission controls."""
    bg = "#2f6fed" if on and not dark else "#7aa2ff" if on else "#d8dee9" if not dark else "#33405a"
    knob = "#ffffff" if not dark else "#f7f9ff"
    fill_round(p, QRectF(x, y, 34, 18), 9, color(bg))
    kx = x + 24 if on else x + 10
    p.setBrush(color(knob))
    p.drawEllipse(QPointF(kx, y + 9), 7, 7)
    p.setBrush(Qt.NoBrush)


def draw_feature_card(
    p: QPainter,
    rect: QRectF,
    title: str,
    subtitle: str,
    accent: str,
    dark: bool,
    rows: list[tuple[str, str]] | None = None,
) -> None:
    """Draw a module card that reflects a real GUI page capability."""
    fill_round(p, rect, 18, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    draw_icon_dot(p, rect.left() + 26, rect.top() + 27, color(accent), title[:1])
    draw_text(p, rect.left() + 48, rect.top() + 12, title, 15, color("#172033") if not dark else color("#f7f9ff"), QFont.Bold, w=130)
    draw_text(p, rect.left() + 48, rect.top() + 35, subtitle, 11, color("#6b778c") if not dark else color("#9aa6bd"), w=rect.width() - 66, h=20)
    if rows:
        for i, (left, right) in enumerate(rows[:3]):
            y = rect.top() + 66 + i * 25
            fill_round(p, QRectF(rect.left() + 16, y, rect.width() - 32, 20), 8, color("#f6f8fc") if not dark else color("#1d2536"))
            draw_text(p, rect.left() + 26, y - 1, left, 11, color("#4d5c73") if not dark else color("#c3ccdd"), w=rect.width() - 115)
            draw_text(p, rect.right() - 88, y - 1, right, 11, color(accent), QFont.DemiBold, w=64, align=Qt.AlignRight | Qt.AlignVCenter)


def draw_real_sidebar(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the actual project navigation instead of a generic dashboard menu."""
    fill_round(p, rect, 22, color("#f8fafd") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    draw_text(p, rect.left() + 26, rect.top() + 24, "First", 26, color("#0f172a") if not dark else color("#f7f9ff"), QFont.Bold)
    draw_text(p, rect.left() + 26, rect.top() + 58, "小程序安全调试工具", 12, color("#7b8799") if not dark else color("#8d99ad"), w=160)
    items = [
        ("◉", "控制台"),
        ("⬡", "路由导航"),
        ("◈", "Hook"),
        ("☁", "云扫描"),
        ("M", "MCP"),
        ("◆", "敏感信息提取"),
        ("◇", "调试开关"),
        ("≡", "运行日志"),
        ("?", "常见问题"),
    ]
    for i, (ic, label) in enumerate(items):
        y = rect.top() + 108 + i * 43
        active = i == 0
        if active:
            fill_round(p, QRectF(rect.left() + 16, y - 4, rect.width() - 32, 34), 12, color("#eaf1ff") if not dark else color("#253554"))
        draw_icon_dot(p, rect.left() + 34, y + 13, color("#2f6fed") if active else color("#e2e8f0") if not dark else color("#30394f"), ic)
        draw_text(
            p,
            rect.left() + 58,
            y - 1,
            label,
            13,
            color("#172033") if active and not dark else color("#f7f9ff") if active else color("#7b8799") if not dark else color("#aeb8ce"),
            QFont.DemiBold if active else QFont.Normal,
            w=132,
        )
    theme_rect = QRectF(rect.left() + 18, rect.bottom() - 94, rect.width() - 36, 38)
    fill_round(
        p,
        theme_rect,
        14,
        color("#ffffff") if not dark else color("#1d2536"),
        color("#e2e8f0") if not dark else color("#34415f"),
    )
    theme_icon = "☀" if not dark else "☾"
    theme_label = "浅色模式" if not dark else "深色模式"
    icon_bg = "#fff7df" if not dark else "#27324a"
    icon_fg = "#ca8a04" if not dark else "#b18cff"
    fill_round(p, QRectF(theme_rect.left() + 12, theme_rect.top() + 7, 24, 24), 12, color(icon_bg), color("#f4d37c") if not dark else color("#4a5b7f"))
    draw_text(p, theme_rect.left() + 12, theme_rect.top() + 5, theme_icon, 15, color(icon_fg), QFont.Bold, w=24, h=26, align=Qt.AlignCenter)
    draw_text(p, theme_rect.left() + 46, theme_rect.top() + 4, theme_label, 12, color("#4d5c73") if not dark else color("#c3ccdd"), QFont.DemiBold, w=92, h=30)
    draw_text(p, theme_rect.right() - 36, theme_rect.top() + 4, "切换", 10, color("#8a96a9") if not dark else color("#8d99ad"), w=30, h=30, align=Qt.AlignRight | Qt.AlignVCenter)

    draw_text(p, rect.left() + 26, rect.bottom() - 34, "作者: TiAmo", 10, color("#8a96a9") if not dark else color("#8d99ad"), QFont.DemiBold, w=150, h=16)
    draw_text(p, rect.left() + 26, rect.bottom() - 16, "当前版本: v1.0.0", 10, color("#8a96a9") if not dark else color("#8d99ad"), QFont.DemiBold, w=150, h=16)


def draw_workflow_card(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the launch-debug to hook-injection flow that the real app requires."""
    fill_round(p, rect, 18, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    draw_text(p, rect.left() + 20, rect.top() + 14, "启动调试流程", 16, color("#172033") if not dark else color("#f7f9ff"), QFont.Bold, w=150)
    draw_text(p, rect.left() + 20, rect.top() + 38, "先启动调试，再打开小程序，连接稳定后自动/手动注入 Hook。", 11, color("#6b778c") if not dark else color("#9aa6bd"), w=315)
    fill_round(p, QRectF(rect.left() + 20, rect.top() + 70, 96, 30), 12, color("#f6f8fc") if not dark else color("#1d2536"), color("#dfe5ef") if not dark else color("#34415f"))
    draw_text(p, rect.left() + 32, rect.top() + 70, "CDP 62000", 12, color("#34425a") if not dark else color("#c8d2e4"), QFont.DemiBold, w=74, align=Qt.AlignCenter)
    draw_switch_mock(p, rect.left() + 136, rect.top() + 76, True, dark)
    draw_text(p, rect.left() + 178, rect.top() + 71, "允许 DevTools 断点", 12, color("#4d5c73") if not dark else color("#c3ccdd"), w=130)
    fill_round(p, QRectF(rect.right() - 124, rect.top() + 69, 104, 32), 13, color("#1f6feb") if not dark else color("#7aa2ff"))
    draw_text(p, rect.right() - 111, rect.top() + 70, "启动调试", 13, color("#ffffff") if not dark else color("#0e1118"), QFont.Bold, w=78, align=Qt.AlignCenter)
    steps = [("启动调试", "#2f6fed"), ("小程序连接", "#16a34a"), ("全局 Hook 注入", "#7357ff"), ("DevTools 可用", "#ff7a59")]
    base_x = rect.left() + 38
    y = rect.top() + 132
    p.setPen(QPen(color("#dbe3ef") if not dark else color("#34415f"), 2))
    p.drawLine(QPointF(base_x + 12, y), QPointF(base_x + 320, y))
    p.setPen(Qt.NoPen)
    for i, (label, c) in enumerate(steps):
        x = base_x + i * 108
        p.setBrush(color(c))
        p.drawEllipse(QPointF(x + 12, y), 9, 9)
        p.setBrush(Qt.NoBrush)
        draw_text(p, x - 16, y + 18, label, 11, color("#4d5c73") if not dark else color("#c3ccdd"), QFont.DemiBold, w=70, align=Qt.AlignCenter)


def draw_status_strip(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw connection status cards for Frida, MiniApp, CDP, and MCP."""
    names = [("Frida", "已连接", "#16a34a"), ("小程序", "已连接", "#16a34a"), ("CDP", ":62000", "#2f6fed"), ("MCP", "8765/mcp", "#7357ff")]
    for i, (name, value, accent) in enumerate(names):
        x = rect.left() + i * (rect.width() / 4)
        r = QRectF(x, rect.top(), rect.width() / 4 - 14, rect.height())
        fill_round(p, r, 16, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
        p.setBrush(color(accent))
        p.drawEllipse(QPointF(r.left() + 22, r.top() + 21), 5, 5)
        p.setBrush(Qt.NoBrush)
        draw_text(p, r.left() + 38, r.top() + 8, name, 12, color("#6b778c") if not dark else color("#9aa6bd"), QFont.DemiBold, w=80)
        draw_text(p, r.left() + 38, r.top() + 30, value, 15, color("#172033") if not dark else color("#f7f9ff"), QFont.Bold, w=110)


def draw_logs_panel(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the shared runtime log panel with debug option switches and scrollbar."""
    fill_round(p, rect, 18, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    draw_text(p, rect.left() + 18, rect.top() + 10, "运行日志", 15, color("#172033") if not dark else color("#f7f9ff"), QFont.Bold)
    draw_switch_mock(p, rect.right() - 188, rect.top() + 15, True, dark)
    draw_text(p, rect.right() - 146, rect.top() + 10, "调试主包", 11, color("#6b778c") if not dark else color("#9aa6bd"), w=60)
    draw_switch_mock(p, rect.right() - 82, rect.top() + 15, False, dark)
    draw_text(p, rect.right() - 40, rect.top() + 10, "Frida", 11, color("#6b778c") if not dark else color("#9aa6bd"), w=34)
    if rect.height() < 150:
        rows = [
            ("09:41:12", "[Main] 启动调试，CDP 代理监听 127.0.0.1:62000", "#2f6fed" if not dark else "#7aa2ff"),
            ("09:41:26", "[Hook] 自动注入全局脚本 order_sign.js", "#16a34a" if not dark else "#5de4a7"),
            ("09:41:40", "[MCP] HTTP 服务已启动: http://127.0.0.1:8765/mcp", "#7357ff" if not dark else "#b18cff"),
        ]
        viewport = QRectF(rect.left() + 16, rect.top() + 38, rect.width() - 32, rect.height() - 48)
        fill_round(p, viewport, 10, color("#f6f8fc") if not dark else color("#0f1725", 170), color("#e2e8f0") if not dark else color("#2b3650"))
        for i, (tm, msg, c) in enumerate(rows):
            y = viewport.top() + 5 + i * 20
            fill_round(p, QRectF(viewport.left() + 8, y, viewport.width() - 28, 16), 6, color("#ffffff") if not dark else color("#1d2536", 225))
            draw_text(p, viewport.left() + 18, y - 3, tm, 10, color("#8792a6"), w=58, h=20)
            draw_text(p, viewport.left() + 78, y - 3, msg, 10, color(c), QFont.DemiBold, w=viewport.width() - 118, h=20)
        fill_round(p, QRectF(viewport.right() - 8, viewport.top() + 6, 3, viewport.height() - 12), 2, color("#d6deea") if not dark else color("#34405b"))
        fill_round(p, QRectF(viewport.right() - 8, viewport.top() + 7, 3, 22), 2, color("#8fa3c1") if not dark else color("#7aa2ff"))
    else:
        draw_console_rows(p, QRectF(rect.left() + 16, rect.top() + 46, rect.width() - 32, rect.height() - 62), dark)


def draw_debug_switch_card(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the vConsole/debug-switch operation card with balanced spacing."""
    fill_round(p, rect, 18, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    primary = color("#172033") if not dark else color("#f7f9ff")
    secondary = color("#6b778c") if not dark else color("#9aa6bd")
    warn = color("#ca8a04") if not dark else color("#ffbd2e")
    draw_text(p, rect.left() + 24, rect.top() + 14, "调试开关", 15, primary, QFont.Bold, w=90)
    draw_pill(
        p,
        QRectF(rect.right() - 78, rect.top() + 14, 56, 22),
        "关闭",
        "#ca8a04" if not dark else "#ffbd2e",
        "#fff7df" if not dark else "#3b3119",
        "#f4d37c" if not dark else "#665229",
    )
    draw_text(p, rect.left() + 24, rect.top() + 44, "wx.setEnableDebug / vConsole", 11, secondary, w=180)
    draw_text(p, rect.left() + 24, rect.top() + 66, "用于 JSRPC 与 wx.cloud 调用调试", 10, warn, QFont.DemiBold, w=190, h=18)
    draw_pill(p, QRectF(rect.left() + 24, rect.bottom() - 28, 78, 24), "开启调试", "#ffffff" if not dark else "#0e1118", "#2f6fed" if not dark else "#7aa2ff")
    draw_pill(p, QRectF(rect.left() + 114, rect.bottom() - 28, 78, 24), "关闭调试", "#6b778c" if not dark else "#c3ccdd", "#f4f6fa" if not dark else "#1d2536", "#dfe5ef" if not dark else "#34415f")


def draw_faq_panel(p: QPainter, rect: QRectF, dark: bool) -> None:
    """Draw the restored FAQ page preview with the original troubleshooting topics."""
    fill_round(p, rect, 18, color("#ffffff") if not dark else color("#111827"), color("#e2e8f0") if not dark else color("#2b3650"))
    primary = color("#172033") if not dark else color("#f7f9ff")
    secondary = color("#6b778c") if not dark else color("#9aa6bd")
    warn = color("#ca8a04") if not dark else color("#ffbd2e")
    draw_text(p, rect.left() + 18, rect.top() + 10, "常见问题", 15, primary, QFont.Bold, w=100)
    draw_text(p, rect.left() + 102, rect.top() + 11, "原控制台问题解决方案", 10, secondary, w=150)
    rows = [
        ("Frida 连接失败", "检查 WMPF 版本区间"),
        ("DevTools 内容为空", "先启动调试，再打开小程序"),
        ("小程序端未连接", "重装微信并清理 RadiumWMPF"),
    ]
    for i, (title, detail) in enumerate(rows):
        y = rect.top() + 42 + i * 22
        fill_round(p, QRectF(rect.left() + 16, y, rect.width() - 32, 18), 7, color("#fff7df") if not dark else color("#2f2616"))
        draw_text(p, rect.left() + 26, y - 2, title, 10, warn, QFont.DemiBold, w=98, h=22)
        draw_text(p, rect.left() + 126, y - 2, detail, 10, secondary, w=rect.width() - 150, h=22)


def draw_mac_light_v2() -> None:
    """Render a function-aware macOS light concept for the existing First GUI."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#f4f7fb"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, color("#f8fbff"))
    bg.setColorAt(1, color("#eef3f9"))
    p.fillRect(0, 0, W, H, bg)
    draw_shadow(p, QRectF(92, 46, 1182, 820), 30, color("#24304a", 115), 22, 18)
    fill_round(p, QRectF(92, 46, 1182, 820), 30, color("#ffffff", 238), color("#dfe5ef"))
    fill_round(p, QRectF(92, 46, 1182, 56), 30, color("#f8fafc"), color("#ffffff", 180))
    draw_text(p, 124, 58, "First 小程序安全调试台", 18, color("#102033"), QFont.Bold, w=230)
    draw_hook_target_badge(p, QRectF(650, 58, 486, 34), False)
    draw_window_controls(p, QRectF(1138, 58, 88, 34), False)
    draw_real_sidebar(p, QRectF(120, 126, 224, 704), False)
    draw_workflow_card(p, QRectF(370, 126, 466, 220), False)
    fill_round(p, QRectF(860, 126, 364, 220), 18, color("#ffffff"), color("#e2e8f0"))
    draw_text(p, 882, 142, "当前小程序上下文", 16, color("#172033"), QFont.Bold, w=160)
    draw_pill(p, QRectF(1088, 141, 92, 24), "Hook 已注入", "#16a34a", "#eaf7ef", "#bce8cb")
    draw_text(p, 882, 174, "应用", 11, color("#8a96a9"), QFont.DemiBold, w=44)
    draw_text(p, 930, 174, "蜜雪冰城点单", 14, color("#172033"), QFont.Bold, w=140)
    draw_text(p, 882, 203, "AppID", 11, color("#8a96a9"), QFont.DemiBold, w=44)
    draw_text(p, 930, 203, "wx8f2a4c9b7e0130", 12, color("#4d5c73"), QFont.DemiBold, w=180)
    draw_text(p, 882, 232, "当前路由", 11, color("#8a96a9"), QFont.DemiBold, w=64)
    draw_text(p, 952, 232, "/pages/menu/index", 12, color("#2f6fed"), QFont.DemiBold, w=160)
    draw_text(p, 882, 266, "DevTools", 11, color("#8a96a9"), QFont.DemiBold, w=64)
    draw_pill(p, QRectF(952, 264, 96, 24), "可连接", "#2f6fed", "#edf4ff", "#bed3ff")
    draw_pill(p, QRectF(1062, 264, 96, 24), "vConsole 关", "#ca8a04", "#fff7df", "#f4d37c")
    draw_status_strip(p, QRectF(370, 370, 854, 68), False)
    draw_logs_panel(p, QRectF(370, 462, 854, 390), False)
    p.end()
    img.save(str(OUT_DIR / "01_mac_light.png"))


def draw_mac_dark_v2() -> None:
    """Render a function-aware macOS dark concept for the existing First GUI."""
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(color("#0e1118"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    bg = QLinearGradient(0, 0, W, H)
    bg.setColorAt(0, color("#0e1118"))
    bg.setColorAt(1, color("#171d2b"))
    p.fillRect(0, 0, W, H, bg)
    for x in range(110, W, 190):
        p.setPen(QPen(color("#ffffff", 15), 1))
        p.drawLine(x, 0, x, H)
    p.setPen(Qt.NoPen)
    draw_shadow(p, QRectF(92, 50, 1182, 812), 30, color("#000000", 210), 24, 22)
    fill_round(p, QRectF(92, 50, 1182, 812), 30, color("#171d2b", 246), color("#34415f"))
    fill_round(p, QRectF(92, 50, 1182, 56), 30, color("#1d2536"), color("#34415f"))
    draw_text(p, 124, 62, "First Debug Console", 18, color("#f7f9ff"), QFont.Bold, w=230)
    draw_hook_target_badge(p, QRectF(650, 62, 486, 34), True)
    draw_window_controls(p, QRectF(1138, 62, 88, 34), True)
    draw_real_sidebar(p, QRectF(120, 130, 224, 700), True)
    draw_workflow_card(p, QRectF(370, 130, 466, 218), True)
    fill_round(p, QRectF(860, 130, 364, 218), 18, color("#111827"), color("#2b3650"))
    draw_text(p, 882, 146, "当前小程序上下文", 16, color("#f7f9ff"), QFont.Bold, w=160)
    draw_pill(p, QRectF(1088, 145, 92, 24), "Hook 已注入", "#5de4a7", "#183527", "#2f684a")
    draw_text(p, 882, 177, "应用", 11, color("#8d99ad"), QFont.DemiBold, w=44)
    draw_text(p, 930, 177, "蜜雪冰城点单", 14, color("#f7f9ff"), QFont.Bold, w=140)
    draw_text(p, 882, 205, "AppID", 11, color("#8d99ad"), QFont.DemiBold, w=44)
    draw_text(p, 930, 205, "wx8f2a4c9b7e0130", 12, color("#c3ccdd"), QFont.DemiBold, w=180)
    draw_text(p, 882, 233, "当前路由", 11, color("#8d99ad"), QFont.DemiBold, w=64)
    draw_text(p, 952, 233, "/pages/menu/index", 12, color("#7aa2ff"), QFont.DemiBold, w=160)
    draw_text(p, 882, 264, "DevTools", 11, color("#8d99ad"), QFont.DemiBold, w=64)
    draw_pill(p, QRectF(952, 262, 96, 24), "可连接", "#7aa2ff", "#1d2e50", "#355c9d")
    draw_pill(p, QRectF(1062, 262, 96, 24), "vConsole 关", "#ffbd2e", "#3b3119", "#665229")
    draw_status_strip(p, QRectF(370, 372, 854, 68), True)
    draw_logs_panel(p, QRectF(370, 464, 854, 388), True)
    p.end()
    img.save(str(OUT_DIR / "02_mac_dark.png"))


def main() -> None:
    """Regenerate the two selected macOS-style concept images."""
    app = QGuiApplication.instance() or QGuiApplication([])
    draw_mac_light_v2()
    draw_mac_dark_v2()
    app.quit()


if __name__ == "__main__":
    main()
