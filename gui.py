"""
First GUI — PySide6 版
Author: Spade-sec | https://github.com/Spade-sec/First
"""
import asyncio
import json
import multiprocessing
import os
import queue
import re
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qsl, urlparse

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QRect,
    Signal, QPoint, QUrl,
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QIcon, QPixmap, QDesktopServices, QFontDatabase,
    QPen, QPainterPath,
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QFrame, QPushButton, QScrollArea, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QProgressBar, QStackedWidget,
    QMenu, QHeaderView, QAbstractItemView, QFileDialog, QInputDialog,
    QTabWidget, QTableWidget, QTableWidgetItem, QDialog, QSizePolicy,
    QCheckBox, QGridLayout, QComboBox,
)

from src.cli import CliOptions, CDP_PORT
from src.logger import Logger
from src.engine import DebugEngine
from src.navigator import MiniProgramNavigator
from src.cloud_audit import CloudAuditor
from src.mcp_runtime import McpRuntime
from src.mcp_server import McpHttpService

# ══════════════════════════════════════════
#  配色
# ══════════════════════════════════════════
_D = dict(
    bg="#0e1118",       card="#111827",     input="#1d2536",
    sidebar="#111827",  sb_hover="#1d2536", sb_active="#253554",
    border="#2b3650",   border2="#34415f",
    text1="#f7f9ff",    text2="#c3ccdd",    text3="#8d99ad",   text4="#4b5872",
    accent="#7aa2ff",   accent2="#5d87ec",
    success="#5de4a7",  error="#ff7a7a",    warning="#ffbd2e",
)
_L = dict(
    bg="#f4f7fb",       card="#ffffff",     input="#f6f8fc",
    sidebar="#f8fafd",  sb_hover="#eef4ff", sb_active="#eaf1ff",
    border="#e2e8f0",   border2="#d7dfeb",
    text1="#172033",    text2="#4d5c73",    text3="#8a96a9",   text4="#c7d1df",
    accent="#2f6fed",   accent2="#1f5fd3",
    success="#16a34a",  error="#dc2626",    warning="#ca8a04",
)
_TH = {"dark": _D, "light": _L}
_FN = "Microsoft YaHei UI"
_FM = "Consolas"


def _install_app_font():
    """加载 Windows 中文字体，避免 Qt 字体回退失败导致中文显示为方块。"""
    global _FN
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf"):
        if not os.path.exists(path):
            continue
        fid = QFontDatabase.addApplicationFont(path)
        if fid < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(fid)
        if families:
            _FN = families[0]
            return
_MENU = [
    ("control",   "控", "控制台"),
    ("navigator", "路", "路由导航"),
    ("hook",      "H", "Hook"),
    ("cloud",     "云", "云扫描"),
    ("mcp",       "M", "MCP"),
    ("extract",   "敏", "敏感信息提取"),
    ("vconsole",  "调", "调试开关"),
    ("logs",      "志", "运行日志"),
    ("faq",       "?", "常见问题"),
]
_MCP_PERMISSIONS = [
    ("read_status", "读取状态", True),
    ("read_requests", "读取请求", True),
    ("read_scripts", "读取源码", True),
    ("navigate_page", "页面跳转", True),
    ("execute_js", "执行 JS", False),
    ("auto_breakpoint", "自动断点", False),
    ("auto_visit", "自动访问", False),
    ("inject_probe", "注入探针", False),
    ("call_cloud", "调用云函数", False),
    ("export_report", "导出报告", True),
]
_MCP_TOOL_SUMMARIES = {
    "get_status": "读取当前调试状态",
    "evaluate_js": "执行小程序运行时 JS",
    "list_routes": "列出已发现页面路由",
    "get_current_route": "读取当前页面路由",
    "navigate_route": "跳转到指定页面路由",
    "start_capture": "开始捕获网络请求",
    "stop_capture": "停止捕获网络请求",
    "get_recent_requests": "读取最近捕获请求",
    "clear_requests": "清空已捕获请求",
    "list_runtime_scripts": "列出运行时脚本",
    "get_runtime_script_source": "读取运行时脚本源码",
    "set_auto_breakpoint": "设置自动断点",
    "wait_for_pause": "等待断点命中暂停",
    "resume_execution": "继续执行或单步",
    "remove_breakpoint": "移除自动断点",
    "search_runtime_scripts": "搜索运行时脚本源码",
    "inspect_request_parameters": "分析请求参数特征",
    "trace_parameter_logic": "追踪参数生成逻辑",
    "find_crypto_candidates": "查找加密签名代码线索",
}

# ══════════════════════════════════════════
#  配置持久化
# ══════════════════════════════════════════
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
_CFG_FILE = os.path.join(_BASE_DIR, "gui_config.json")

os.makedirs(os.path.join(_BASE_DIR, "hook_scripts"), exist_ok=True)


def _load_cfg():
    try:
        with open(_CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(data):
    try:
        with open(_CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ══════════════════════════════════════════
#  QSS 主题
# ══════════════════════════════════════════

def build_qss(tn):
    c = _TH[tn]
    sel_bg = "#1e3a2a" if tn == "dark" else "#d4edda"
    sel_fg = "#a0f0c0" if tn == "dark" else "#155724"
    hdr_bg = "#222230" if tn == "dark" else "#e8e8ec"
    row_bg = c["input"]
    return f"""
    /* ── 全局 ── */
    QMainWindow, QWidget#central {{
        background: {c['bg']};
    }}

    /* ── 侧栏 ── */
    QFrame#sidebar {{
        background: {c['sidebar']};
        border: 1px solid {c['border']};
        border-radius: 16px;
    }}
    QFrame#sidebar QLabel {{
        background: transparent;
    }}
    QFrame#sb_head {{
        background: transparent;
    }}
    QLabel#sb_logo {{
        color: {c['text1']};
        font-size: 24px; font-weight: bold;
        background: transparent;
    }}
    QFrame#sb_hline {{
        background: {c['border']};
        max-height: 1px; min-height: 1px;
    }}
    QLabel#sb_theme {{
        color: {c['text2']};
        background: transparent;
    }}
    QLabel#sb_theme:hover {{
        color: {c['text1']};
    }}
    QWidget#theme_switch {{
        background: {c['input']};
        border: 1px solid {c['border2']};
        border-radius: 16px;
    }}
    QWidget#theme_switch:hover {{
        border: 1px solid {c['accent']};
    }}

    /* ── 菜单项 ── */
    QFrame.sb_item {{
        background: transparent;
        border-radius: 8px;
        padding: 8px 10px;
    }}
    QFrame.sb_item:hover {{
        background: {c['sb_hover']};
    }}
    QFrame.sb_item_active {{
        background: {c['sb_active']};
        border-radius: 8px;
        padding: 8px 10px;
    }}
    QFrame.sb_item QLabel.sb_icon {{
        color: {c['text3']};
        background: {c['input']};
        border-radius: 7px;
        min-width: 22px; max-width: 22px;
        min-height: 22px; max-height: 22px;
    }}
    QFrame.sb_item QLabel.sb_name {{
        color: {c['text2']};
        background: transparent;
    }}
    QFrame.sb_item_active QLabel.sb_icon {{
        color: #ffffff;
        background: {c['accent']};
        border-radius: 7px;
    }}
    QFrame.sb_item_active QLabel.sb_name {{
        color: {c['text1']};
        background: transparent;
    }}
    QFrame#sidebar QFrame.sb_item QLabel.sb_icon {{
        color: {c['text3']};
        background: {c['input']};
        border-radius: 7px;
    }}
    QFrame#sidebar QFrame.sb_item_active QLabel.sb_icon {{
        color: #ffffff;
        background: {c['accent']};
        border-radius: 7px;
    }}

    /* ── 分割线 ── */
    QFrame#vline {{
        background: {c['border']};
        max-width: 1px; min-width: 1px;
    }}
    QFrame#hdr_line {{
        background: {c['border']};
        max-height: 1px; min-height: 1px;
    }}

    /* ── 标题 ── */
    QLabel#page_title {{
        color: {c['text1']};
        font-size: 13px; font-weight: bold;
        padding-left: 6px;
        background: transparent;
    }}

    QFrame#top_bar {{
        background: {c['card']};
        border-radius: 14px;
        border: 1px solid {c['border']};
    }}
    QFrame#target_badge {{
        background: {c['input']};
        border-radius: 16px;
        border: 1px solid {c['border']};
    }}
    QFrame#target_badge:hover {{
        border: 1px solid {c['accent']};
        background: {c['sb_hover']};
    }}
    QLabel#target_badge_label {{
        color: {c['text3']};
        font-size: 10px;
        font-weight: bold;
    }}
    QLabel#target_badge_value {{
        color: {c['text1']};
        font-size: 11px;
        font-weight: bold;
    }}
    QLabel#target_badge_meta {{
        color: {c['text3']};
        font-size: 10px;
        font-weight: bold;
    }}
    QLabel#target_badge_status {{
        color: {c['success']};
        background: {"#183527" if tn == "dark" else "#eaf7ef"};
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 10px;
        font-weight: bold;
    }}

    /* ── 圆角卡片 ── */
    QFrame.card {{
        background: {c['card']};
        border-radius: 16px;
        border: 1px solid {c['border']};
    }}
    QFrame.card QLabel {{
        background: transparent;
    }}
    QFrame.card QLabel.title {{
        color: {c['text1']};
        font-weight: bold;
        font-size: 11px;
    }}
    QFrame.card QLabel.subtitle {{
        color: {c['text2']};
        font-size: 9px;
    }}

    /* ── 通用 Label ── */
    QLabel {{
        color: {c['text2']};
        background: transparent;
    }}
    QLabel.bold {{
        color: {c['text1']};
        font-weight: bold;
    }}
    QLabel.muted {{
        color: {c['text3']};
    }}
    QLabel.accent {{
        color: {c['accent']};
    }}

    /* ── 按钮 ── */
    QPushButton {{
        background: {c['accent']};
        color: {"#ffffff" if tn == "light" else "#111118"};
        border: none;
        border-radius: 8px;
        padding: 5px 16px;
        font-size: 10px;
    }}
    QPushButton:hover {{
        background: {c['accent2']};
    }}
    QPushButton:pressed {{
        background: {c['accent2']};
        padding-top: 6px;
        padding-bottom: 4px;
    }}
    QPushButton:disabled {{
        background: {"#1d2536" if tn == "dark" else "#edf2f8"};
        color: {"#68758f" if tn == "dark" else "#9aa6b8"};
    }}
    QPushButton#devtools_copy_btn {{
        background: {c['input']};
        color: {c['accent']};
        border: 1px solid {c['border2']};
        border-radius: 10px;
        padding: 3px 12px;
        font-size: 9px;
        min-height: 18px;
    }}
    QPushButton#devtools_copy_btn:hover {{
        background: {c['sb_hover']};
        border: 1px solid {c['accent']};
    }}
    QPushButton#devtools_copy_btn:pressed {{
        background: {c['accent']};
        color: {"#ffffff" if tn == "light" else "#111118"};
        padding-top: 4px;
        padding-bottom: 2px;
    }}
    QPushButton#devtools_copy_btn:disabled {{
        background: transparent;
        color: {c['text4']};
        border: 1px solid {c['border']};
    }}
    /* 表格内按钮 — 清除全局样式，由 inline setStyleSheet 控制 */
    QTableWidget QPushButton {{
        background: transparent;
        color: {c['text2']};
        border: none;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 12px;
    }}
    QTableWidget QPushButton:hover {{
        background: transparent;
    }}

    /* ── 输入框 ── */
    QLineEdit {{
        background: {c['input']};
        color: {c['text1']};
        border: none;
        border-radius: 10px;
        padding: 6px 12px;
        font-size: 10px;
        selection-background-color: {c['accent']};
        selection-color: #111118;
    }}
    QLineEdit:focus {{
        border: 1px solid {c['accent']};
    }}

    QComboBox {{
        background: {c['input']};
        color: {c['text1']};
        border: none;
        border-radius: 10px;
        padding: 6px 28px 6px 12px;
        font-size: 10px;
        min-width: 92px;
    }}
    QComboBox:focus {{
        border: 1px solid {c['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: {c['input']};
        color: {c['text1']};
        border: 1px solid {c['border']};
        selection-background-color: {c['accent']};
        selection-color: #111118;
        outline: 0;
    }}

    /* ── 文本框 ── */
    QTextEdit {{
        background: {c['input']};
        color: {c['accent']};
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        font-family: {_FM};
        font-size: 10px;
        selection-background-color: {c['accent']};
        selection-color: #111118;
    }}

    /* ── 树形控件 ── */
    QTreeWidget {{
        background: {c['card']};
        color: {c['text2']};
        border: none;
        font-size: 10px;
        outline: 0;
    }}
    QTreeWidget::item {{
        padding: 4px 8px;
        border: none;
        text-align: left;
    }}
    QTreeWidget::item:selected {{
        background: {sel_bg};
        color: {sel_fg};
    }}
    QTreeWidget::item:hover {{
        background: {c['sb_hover']};
    }}
    QHeaderView::section {{
        background: {hdr_bg};
        color: {c['text1']};
        border: none;
        padding: 4px 8px;
        font-weight: bold;
        font-size: 10px;
        text-align: left;
    }}

    /* ── 进度条 ── */
    QProgressBar {{
        background: {c['border']};
        border: none;
        border-radius: 4px;
        height: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: {c['accent']};
        border-radius: 4px;
    }}

    /* ── 滚动条 ── */
    QScrollBar:vertical {{
        background: transparent;
        width: 6px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {"#3d4a62" if tn == "dark" else "#cbd5e1"};
        border-radius: 3px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['accent']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background: {"#3d4a62" if tn == "dark" else "#cbd5e1"};
        border-radius: 3px;
        min-width: 20px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c['accent']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* ── 表格控件 ── */
    QTableWidget {{
        background: {c['card']};
        color: {c['text2']};
        border: none;
        font-size: 12px;
        outline: 0;
        gridline-color: {c['border']};
    }}
    QTableWidget::item {{
        padding: 6px 10px;
        border: none;
        background: {c['card']};
        color: {c['text2']};
    }}
    QTableWidget::item:selected {{
        background: {sel_bg};
        color: {sel_fg};
    }}
    QTableWidget QHeaderView::section {{
        background: {hdr_bg};
        color: {c['text1']};
        border: none;
        padding: 6px 10px;
        font-weight: bold;
        font-size: 12px;
    }}

    /* ── 滚动区域 ── */
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}

    /* ── 右键菜单 ── */
    QMenu {{
        background: {c['card']};
        color: {c['text1']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 20px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {c['accent']};
        color: #ffffff;
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}

    QToolTip {{
        background: {c['card']};
        color: {c['text1']};
        border: 1px solid {c['border2']};
        border-radius: 6px;
        padding: 6px 8px;
    }}

    /* ── QCheckBox ── */
    QCheckBox {{
        color: {c['text1']};
        background: transparent;
        spacing: 5px;
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 3px;
        border: 1px solid {c['border2']};
        background: {c['input']};
    }}
    QCheckBox::indicator:checked {{
        background: {c['accent']};
        border-color: {c['accent']};
        image: none;
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['accent']};
    }}

    /* ── Hook 行 ── */
    QFrame.hook_row {{
        background: {row_bg};
        border-radius: 8px;
    }}
    QFrame.hook_row QLabel {{
        background: transparent;
    }}
    QLabel.js_badge {{
        background: {c['accent']};
        color: {"#ffffff" if tn == "dark" else "#111118"};
        font-weight: bold;
        font-size: 9px;
        padding: 2px 6px;
        border-radius: 4px;
    }}

    /* ── Completer popup ── */
    QListView {{
        background: {c['input']};
        color: {c['text1']};
        border: 1px solid {c['border']};
        border-radius: 6px;
        outline: 0;
    }}
    QListView::item:selected {{
        background: {c['accent']};
        color: #111118;
    }}
    """


# ══════════════════════════════════════════
#  自定义控件
# ══════════════════════════════════════════

class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self._on_color = QColor("#4ade80")
        self._off_color = QColor("#3c3c4c")
        self._thumb_color = QColor("#ffffff")
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumbPos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

    def isChecked(self):
        return self._checked

    def setChecked(self, v):
        if self._checked == v:
            return
        self._checked = v
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if v else 0.0)
        self._anim.start()
        self.toggled.emit(v)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, v):
        self._thumb_pos = v
        self.update()

    thumbPos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def mousePressEvent(self, e):
        self.setChecked(not self._checked)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2

        # track
        track_color = QColor(self._on_color) if self._checked else QColor(self._off_color)
        p.setPen(Qt.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(0, 0, w, h, r, r)

        # thumb
        tr = r - 3
        cx = r + self._thumb_pos * (w - 2 * r)
        p.setBrush(self._thumb_color)
        p.drawEllipse(QPoint(int(cx), int(r)), int(tr), int(tr))

    def set_colors(self, on, off):
        self._on_color = QColor(on)
        self._off_color = QColor(off)
        self.update()


class AnimatedStackedWidget(QStackedWidget):
    """Page switch with a lightweight vertical slide animation.

    Uses QPropertyAnimation on widget geometry instead of
    QGraphicsOpacityEffect, which forces expensive off-screen
    compositing of the entire subtree (causing visible lag on
    heavy pages like the cloud-scan QTreeWidget).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anim = None

    def setCurrentIndexAnimated(self, idx):
        if idx == self.currentIndex():
            return
        old_idx = self.currentIndex()
        old_widget = self.currentWidget()
        new_widget = self.widget(idx)
        if new_widget is None:
            self.setCurrentIndex(idx)
            return

        # Determine slide direction: down when going forward, up when back
        h = self.height()
        offset = h // 4  # slide only a quarter of the height for subtlety
        start_y = offset if idx > old_idx else -offset

        # Immediately switch the page (no off-screen compositing)
        self.setCurrentIndex(idx)

        # Animate just the position of the new page
        final_rect = new_widget.geometry()
        start_rect = QRect(final_rect)
        start_rect.moveTop(final_rect.top() + start_y)

        anim = QPropertyAnimation(new_widget, b"geometry")
        anim.setDuration(150)
        anim.setStartValue(start_rect)
        anim.setEndValue(final_rect)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim = anim          # prevent GC
        anim.start()


class StatusDot(QWidget):
    """绘制小型圆点状态指示器。"""

    def __init__(self, parent=None):
        """初始化固定尺寸状态点和默认未连接颜色。"""
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = QColor("#3c3c4c")

    def set_color(self, color):
        """更新状态点颜色并触发重绘。"""
        self._color = QColor(color)
        self.update()

    def paintEvent(self, e):
        """绘制圆形状态点。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(1, 1, 8, 8)


class CheckMarkBox(QCheckBox):
    """绘制带对号的复选框，用于避免 checked 状态显示为实心填充块。"""

    def __init__(self, text="", theme="dark", parent=None):
        """初始化复选框文本和主题。"""
        super().__init__(text, parent)
        self._theme = theme
        self.setCursor(Qt.PointingHandCursor)

    def set_theme(self, theme):
        """切换复选框主题色并重绘。"""
        self._theme = theme
        self.update()

    def paintEvent(self, e):
        """绘制圆角方框、选中对号和右侧文本。"""
        c = _TH.get(self._theme, _D)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        box = 14
        x = 1
        y = (self.height() - box) // 2
        checked = self.isChecked()
        p.setPen(QPen(QColor(c["accent"] if checked else c["border2"]), 1.4))
        p.setBrush(QColor(c["accent"] if checked else c["input"]))
        p.drawRoundedRect(x, y, box, box, 3, 3)
        if checked:
            pen = QPen(QColor("#ffffff"), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawLine(x + 4, y + 7, x + 6, y + 10)
            p.drawLine(x + 6, y + 10, x + 11, y + 4)
        p.setPen(QColor(c["text1"]))
        p.setFont(self.font())
        p.drawText(x + box + 7, 0, self.width() - box - 7, self.height(), Qt.AlignVCenter, self.text())


class ThemeIcon(QWidget):
    """绘制侧栏主题切换图标，避免依赖字体中的太阳或月亮字符。"""

    def __init__(self, theme="dark", parent=None):
        """初始化固定尺寸的主题图标控件。"""
        super().__init__(parent)
        self._theme = theme
        self.setFixedSize(18, 18)

    def set_theme(self, theme):
        """切换图标展示的主题状态并触发重绘。"""
        self._theme = theme
        self.update()

    def paintEvent(self, e):
        """根据当前主题绘制太阳或月亮图标。"""
        c = _TH.get(self._theme, _D)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if self._theme == "light":
            sun = QColor(c["warning"])
            p.setBrush(sun)
            p.drawEllipse(6, 6, 6, 6)
            p.setPen(sun)
            for x1, y1, x2, y2 in (
                (9, 1, 9, 4), (9, 14, 9, 17), (1, 9, 4, 9), (14, 9, 17, 9),
                (3, 3, 5, 5), (13, 13, 15, 15), (13, 5, 15, 3), (3, 15, 5, 13),
            ):
                p.drawLine(x1, y1, x2, y2)
        else:
            moon = QColor(c["accent"])
            p.setBrush(moon)
            p.drawEllipse(4, 3, 11, 12)
            p.setBrush(QColor(c["sidebar"]))
            p.drawEllipse(8, 1, 10, 13)


class ThemeTransitionOverlay(QWidget):
    """用旧界面截图遮罩出从点击点扩散的新主题区域。"""

    finished = Signal()

    def __init__(self, old_pixmap, origin, parent=None):
        """保存旧界面截图和扩散起点，并准备半径动画。"""
        super().__init__(parent)
        self._old_pixmap = old_pixmap
        self._origin = QPoint(origin)
        self._radius = 0.0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        if parent:
            self.setGeometry(parent.rect())
        self._max_radius = self._calc_max_radius() + 2
        self._anim = QPropertyAnimation(self, b"radius", self)
        self._anim.setDuration(480)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(self._max_radius))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self.finished.emit)

    def _calc_max_radius(self):
        """计算覆盖整个 overlay 所需的最大圆半径。"""
        corners = (
            QPoint(0, 0),
            QPoint(self.width(), 0),
            QPoint(0, self.height()),
            QPoint(self.width(), self.height()),
        )
        ox, oy = self._origin.x(), self._origin.y()
        return max(((ox - p.x()) ** 2 + (oy - p.y()) ** 2) ** 0.5 for p in corners)

    def start(self):
        """显示遮罩并启动圆形扩散动画。"""
        self.show()
        self.raise_()
        self._anim.start()

    def get_radius(self):
        """返回当前扩散半径。"""
        return self._radius

    def set_radius(self, value):
        """更新当前扩散半径并触发重绘。"""
        self._radius = float(value)
        self.update()

    radius = Property(float, get_radius, set_radius)

    def paintEvent(self, e):
        """绘制除扩散圆以外的旧界面截图，让新主题从圆内露出。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRect(self.rect())
        hole = QPainterPath()
        hole.addEllipse(self._origin, self._radius, self._radius)
        painter.setClipPath(path.subtracted(hole))
        painter.drawPixmap(self.rect(), self._old_pixmap)


class MenuIcon(QWidget):
    """绘制侧栏菜单图标，避免使用字体缩写造成风格不统一。"""

    def __init__(self, kind, theme="dark", parent=None):
        """初始化指定菜单类型的图标块。"""
        super().__init__(parent)
        self._kind = kind
        self._theme = theme
        self._active = False
        self.setFixedSize(22, 22)

    def set_state(self, active, theme):
        """更新菜单图标的激活状态和主题颜色。"""
        self._active = bool(active)
        self._theme = theme
        self.update()

    def paintEvent(self, e):
        """绘制菜单图标底色和简化线性符号。"""
        c = _TH.get(self._theme, _D)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        bg = QColor(c["accent"] if self._active else c["input"])
        fg = QColor("#ffffff" if self._active else c["text3"])
        p.setPen(Qt.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(0, 0, 22, 22, 7, 7)
        pen = QPen(fg, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        k = self._kind
        if k == "control":
            p.drawRoundedRect(6, 6, 10, 10, 2, 2)
            p.drawLine(11, 3, 11, 6)
            p.drawLine(11, 16, 11, 19)
            p.drawLine(3, 11, 6, 11)
            p.drawLine(16, 11, 19, 11)
        elif k == "navigator":
            p.drawLine(6, 16, 10, 6)
            p.drawLine(10, 6, 16, 16)
            p.drawLine(8, 12, 14, 12)
        elif k == "hook":
            p.drawLine(7, 5, 7, 17)
            p.drawLine(15, 5, 15, 17)
            p.drawLine(7, 11, 15, 11)
        elif k == "cloud":
            p.drawArc(5, 8, 7, 7, 30 * 16, 210 * 16)
            p.drawArc(9, 6, 7, 8, 20 * 16, 210 * 16)
            p.drawLine(6, 15, 16, 15)
        elif k == "mcp":
            p.drawRoundedRect(5, 5, 5, 5, 1, 1)
            p.drawRoundedRect(12, 5, 5, 5, 1, 1)
            p.drawRoundedRect(8, 13, 6, 5, 1, 1)
            p.drawLine(10, 10, 11, 13)
            p.drawLine(14, 10, 12, 13)
        elif k == "extract":
            p.drawEllipse(6, 5, 10, 10)
            p.drawLine(13, 13, 17, 17)
            p.drawLine(8, 10, 14, 10)
        elif k == "vconsole":
            p.drawRoundedRect(5, 5, 12, 12, 2, 2)
            p.drawLine(8, 9, 11, 12)
            p.drawLine(11, 12, 15, 8)
        elif k == "logs":
            for y in (7, 11, 15):
                p.drawLine(6, y, 16, y)
        else:
            p.drawEllipse(7, 5, 8, 8)
            p.drawPoint(11, 17)


class WindowButton(QWidget):
    """绘制右上角窗口控制按钮。"""

    clicked = Signal()

    def __init__(self, role, theme="dark", parent=None):
        """初始化最小化、最大化或关闭按钮。"""
        super().__init__(parent)
        self._role = role
        self._theme = theme
        self._hover = False
        self.setFixedSize(18, 18)
        self.setCursor(Qt.PointingHandCursor)

    def set_theme(self, theme):
        """切换窗口按钮主题色。"""
        self._theme = theme
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, e):
        """绘制圆形按钮和内部符号。"""
        c = _TH.get(self._theme, _D)
        if self._role == "close":
            fill = QColor("#ff5f57" if self._hover else c["input"])
            mark = QColor("#ffffff" if self._hover else c["text3"])
        else:
            fill = QColor(c["sb_hover"] if self._hover else c["input"])
            mark = QColor(c["text2"])
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(c["border"]), 1))
        p.setBrush(fill)
        p.drawEllipse(1, 1, 16, 16)
        p.setPen(QPen(mark, 1.4))
        if self._role == "min":
            p.drawLine(6, 10, 12, 10)
        elif self._role == "max":
            p.drawRect(6, 6, 6, 6)
        else:
            p.drawLine(6, 6, 12, 12)
            p.drawLine(12, 6, 6, 12)


class FlowStepper(QWidget):
    """绘制控制台启动调试流程节点，统一展示连接和注入状态。"""

    _STEPS = (
        ("start", "启动调试", "accent"),
        ("miniapp", "小程序连接", "success"),
        ("hook", "Hook 注入", "accent2"),
        ("devtools", "DevTools", "warning"),
    )

    def __init__(self, theme="dark", parent=None):
        """初始化流程节点控件，并设置默认状态。"""
        super().__init__(parent)
        self._theme = theme
        self._states = {key: False for key, _, _ in self._STEPS}
        self.setMinimumHeight(54)

    def set_states(self, states, theme):
        """根据当前调试状态刷新流程节点颜色。"""
        self._theme = theme
        self._states.update({key: bool(states.get(key, False)) for key, _, _ in self._STEPS})
        ready = [label for key, label, _ in self._STEPS if self._states.get(key)]
        pending = [label for key, label, _ in self._STEPS if not self._states.get(key)]
        if pending:
            self.setToolTip(f"已完成: {'、'.join(ready) if ready else '无'}\n待完成: {'、'.join(pending)}")
        else:
            self.setToolTip("启动调试流程已完成")
        self.update()

    def paintEvent(self, e):
        """绘制平滑流程线、节点圆点和节点标签。"""
        c = _TH.get(self._theme, _D)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        width = max(1, self.width())
        left, right = 24, 24
        y = 18
        label_y = 36
        step_count = len(self._STEPS)
        gap = (width - left - right) / max(1, step_count - 1)
        xs = [int(left + i * gap) for i in range(step_count)]

        for idx in range(step_count - 1):
            a, b = xs[idx], xs[idx + 1]
            active = self._states.get(self._STEPS[idx][0], False) and self._states.get(self._STEPS[idx + 1][0], False)
            p.setPen(QPen(QColor(c["accent"] if active else c["border"]), 2))
            p.drawLine(a + 8, y, b - 8, y)

        for idx, (key, label, color_key) in enumerate(self._STEPS):
            x = xs[idx]
            active = self._states.get(key, False)
            fill = QColor(c[color_key] if active else c["input"])
            border = QColor(c[color_key] if active else c["border2"])
            text = QColor(c["text1"] if active else c["text3"])
            p.setPen(QPen(border, 2))
            p.setBrush(fill)
            p.drawEllipse(x - 7, y - 7, 14, 14)
            p.setPen(text)
            p.setFont(QFont(_FN, 8))
            rect_w = 96
            p.drawText(x - rect_w // 2, label_y, rect_w, 16, Qt.AlignCenter, label)


# ══════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════

def _make_card():
    f = QFrame()
    f.setProperty("class", "card")
    return f


def _make_label(text, bold=False, muted=False, mono=False):
    l = QLabel(text)
    if bold:
        l.setProperty("class", "bold")
    elif muted:
        l.setProperty("class", "muted")
    if mono:
        l.setFont(QFont(_FM, 10))
    return l


def _make_btn(text, callback=None):
    b = QPushButton(text)
    if callback:
        b.clicked.connect(callback)
    return b


def _make_entry(placeholder="", width=None):
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    if width:
        e.setFixedWidth(width)
    return e



# ══════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        _install_app_font()
        self._os_tag = "macOS" if sys.platform == "darwin" else "Windows"
        self.setWindowTitle(f"微钩-WeHook-{self._os_tag}")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        _ico = os.path.join(_BASE_DIR, "icon.png")
        if os.path.exists(_ico):
            self.setWindowIcon(QIcon(_ico))
        self.resize(1160, 760)
        self.setMinimumSize(920, 640)

        self._cfg = _load_cfg()
        self._tn = self._cfg.get("theme", "dark")
        self._pg = "control"
        self._running = False
        self._loop = self._loop_th = self._engine = self._navigator = self._auditor = None
        self._cloud_call_history = {}
        self._cloud_all_items = []
        self._cloud_row_results = {}
        self._cloud_result_by_vals = {}
        self._last_sts = {}
        self._drag_pos = None
        self._cancel_ev = None
        self._route_poll_id = None
        self._all_routes = []
        self._flat_routes = []  # tree visual order for prev/next
        self._cloud_scan_active = False
        self._cloud_scan_poll_timer = None
        self._redirect_guard_on = False
        self._hook_injected = set()
        self._global_hook_scripts = set(self._cfg.get("global_hook_scripts", []))
        self._global_inject_gen = 0
        self._blocked_seen = 0
        self._miniapp_connected = False
        self._sb_fetch_gen = 0
        self._vc_stable_gen = 0
        self._mcp_running = False
        self._mcp_endpoint = self._cfg.get("mcp_endpoint", "http://127.0.0.1:8765/mcp")
        self._mcp_appid = ""
        self._mcp_route = ""
        self._current_app_name = ""
        self._current_app_id = ""
        self._mcp_service = None
        self._mcp_permissions = {k: default for k, _, default in _MCP_PERMISSIONS}
        self._mcp_permissions.update(self._cfg.get("mcp_permissions", {}))
        self._mcp_permission_toggles = {}
        self._mcp_q = queue.Queue()
        self._mcp_targets = []
        self._mcp_target_syncing = False
        self._mcp_runtime_scripts = {}
        self._mcp_breakpoints = {}
        self._mcp_pause_state = None
        self._mcp_pause_seq = 0
        self._mcp_wait_pause_since_seq = None
        self._mcp_pause_cv = threading.Condition()
        self._mcp_breakpoint_engine = None
        self._mcp_breakpoint_listener_attached = False
        self._log_q = queue.Queue()
        self._log_entries = []
        self._sts_q = queue.Queue()
        self._rte_q = queue.Queue()
        self._cld_q = queue.Queue()
        self._nav_route_idx = -1

        self._sb_items = {}
        self._page_map = {}

        # 敏感信息提取 状态
        self._ext_proc = None
        self._ext_thread = None
        self._ext_q = queue.Queue()
        self._ext_custom_patterns = dict(self._cfg.get("extract_custom_patterns", {}))
        self._ext_app_states = {}   # {appid: {"decompiled": bool, "scanned": bool, ...}}
        self._ext_app_widgets = {}  # {appid: row widget ref}
        self._ext_current_op = None  # ("decompile"/"scan", appid) or None

        self._build()
        self.setStyleSheet(build_qss(self._tn))
        self._show("control")

        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(80)

    # ──────────────────────────────────
    #  布局
    # ──────────────────────────────────

    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        hdr_wrap = QWidget()
        hdr_wrap_lay = QVBoxLayout(hdr_wrap)
        hdr_wrap_lay.setContentsMargins(12, 10, 12, 8)
        hdr_wrap_lay.setSpacing(0)
        self._hdr_frame = QFrame()
        self._hdr_frame.setObjectName("top_bar")
        self._hdr_frame.setFixedHeight(48)
        self._hdr_frame.mousePressEvent = self._header_mouse_press
        self._hdr_frame.mouseMoveEvent = self._header_mouse_move
        self._hdr_frame.mouseDoubleClickEvent = self._header_mouse_double_click
        hdr_lay = QHBoxLayout(self._hdr_frame)
        hdr_lay.setContentsMargins(14, 0, 10, 0)
        hdr_lay.setSpacing(10)
        self._hdr_title = QLabel("微钩 WeHook 小程序安全调试台")
        self._hdr_title.setObjectName("page_title")
        hdr_lay.addWidget(self._hdr_title)
        hdr_lay.addStretch()
        self._target_badge = QFrame()
        self._target_badge.setObjectName("target_badge")
        self._target_badge.setFixedHeight(32)
        self._target_badge.setCursor(Qt.PointingHandCursor)
        self._target_badge.setToolTip("当前 Hook 目标、小程序 AppID、CDP 端口和连接状态，点击复制")
        self._target_badge.mousePressEvent = lambda e: self._copy_target_summary()
        target_lay = QHBoxLayout(self._target_badge)
        target_lay.setContentsMargins(14, 0, 10, 0)
        target_lay.setSpacing(12)
        self._target_dot = StatusDot()
        target_lay.addWidget(self._target_dot)
        self._target_hook_lbl = QLabel("Hook")
        self._target_hook_lbl.setObjectName("target_badge_label")
        target_lay.addWidget(self._target_hook_lbl)
        self._target_name_lbl = QLabel("未连接小程序")
        self._target_name_lbl.setObjectName("target_badge_value")
        self._target_name_lbl.setMinimumWidth(86)
        self._target_name_lbl.setMaximumWidth(128)
        target_lay.addWidget(self._target_name_lbl)
        self._target_appid_lbl = QLabel("AppID --")
        self._target_appid_lbl.setObjectName("target_badge_meta")
        self._target_appid_lbl.setMinimumWidth(86)
        self._target_appid_lbl.setMaximumWidth(128)
        target_lay.addWidget(self._target_appid_lbl)
        self._target_cdp_lbl = QLabel("CDP --")
        self._target_cdp_lbl.setObjectName("target_badge_meta")
        self._target_cdp_lbl.setMaximumWidth(86)
        target_lay.addWidget(self._target_cdp_lbl)
        self._target_status_lbl = QLabel("未连接")
        self._target_status_lbl.setObjectName("target_badge_status")
        target_lay.addWidget(self._target_status_lbl)
        hdr_lay.addWidget(self._target_badge)
        self._win_btn_min = WindowButton("min", self._tn)
        self._win_btn_min.setToolTip("最小化")
        self._win_btn_min.clicked.connect(self.showMinimized)
        hdr_lay.addWidget(self._win_btn_min)
        self._win_btn_max = WindowButton("max", self._tn)
        self._win_btn_max.setToolTip("最大化 / 还原")
        self._win_btn_max.clicked.connect(self._toggle_window_maximized)
        hdr_lay.addWidget(self._win_btn_max)
        self._win_btn_close = WindowButton("close", self._tn)
        self._win_btn_close.setToolTip("关闭")
        self._win_btn_close.clicked.connect(self.close)
        hdr_lay.addWidget(self._win_btn_close)
        hdr_wrap_lay.addWidget(self._hdr_frame)
        root_v.addWidget(hdr_wrap)

        body = QWidget()
        body_h = QHBoxLayout(body)
        body_h.setContentsMargins(12, 0, 12, 12)
        body_h.setSpacing(12)

        # ── 侧栏 ──
        self._sb = QFrame()
        self._sb.setObjectName("sidebar")
        self._sb.setFixedWidth(224)
        sb_lay = QVBoxLayout(self._sb)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        sb_head = QFrame()
        sb_head.setObjectName("sb_head")
        sb_head.setFixedHeight(112)
        sb_head_lay = QVBoxLayout(sb_head)
        sb_head_lay.setContentsMargins(26, 22, 20, 14)
        sb_head_lay.setSpacing(4)

        self._sb_logo = QLabel("微钩")
        self._sb_logo.setObjectName("sb_logo")
        sb_head_lay.addWidget(self._sb_logo)
        sb_desc = QLabel("WeHook 小程序调试工具")
        sb_desc.setProperty("class", "muted")
        sb_desc.setFont(QFont(_FN, 9))
        sb_head_lay.addWidget(sb_desc)
        sb_lay.addWidget(sb_head)

        hline = QFrame()
        hline.setObjectName("sb_hline")
        hline.setFixedHeight(1)
        sb_lay.addWidget(hline, 0, Qt.AlignTop)

        sb_nav = QWidget()
        sb_nav_lay = QVBoxLayout(sb_nav)
        sb_nav_lay.setContentsMargins(16, 10, 16, 10)
        sb_nav_lay.setSpacing(5)
        for pid, icon, name in _MENU:
            row = QFrame()
            row.setCursor(Qt.PointingHandCursor)
            row.setToolTip(f"打开{name}页面")
            row.setFixedHeight(38)
            row.setProperty("class", "sb_item")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(10, 0, 8, 0)
            row_lay.setSpacing(6)
            ic = MenuIcon(pid, self._tn)
            nm = QLabel(name)
            nm.setProperty("class", "sb_name")
            nm.setFont(QFont(_FN, 10))
            row_lay.addWidget(ic)
            row_lay.addWidget(nm, 1)
            sb_nav_lay.addWidget(row)
            row.mousePressEvent = lambda e, p=pid: self._show(p)
            self._sb_items[pid] = (row, ic, nm)
        sb_nav_lay.addStretch()
        sb_lay.addWidget(sb_nav, 1)

        self._sb_theme = QLabel()
        self._sb_theme.setObjectName("sb_theme")
        self._sb_theme.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._sb_theme.setCursor(Qt.PointingHandCursor)
        self._sb_theme.setFont(QFont(_FN, 9))
        self._sb_theme.mousePressEvent = lambda e, w=self._sb_theme: self._toggle_theme(w, e)
        sb_lay.addSpacing(8)
        self._sb_theme_icon = ThemeIcon(self._tn)
        self._sb_theme_icon.setCursor(Qt.PointingHandCursor)
        self._sb_theme_icon.mousePressEvent = lambda e, w=self._sb_theme_icon: self._toggle_theme(w, e)
        self._sb_theme_action = QLabel("切换")
        self._sb_theme_action.setObjectName("sb_theme")
        self._sb_theme_action.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._sb_theme_action.setCursor(Qt.PointingHandCursor)
        self._sb_theme_action.setFont(QFont(_FN, 8))
        self._sb_theme_action.mousePressEvent = lambda e, w=self._sb_theme_action: self._toggle_theme(w, e)
        self._theme_wrap = QWidget()
        self._theme_wrap.setObjectName("theme_switch")
        self._theme_wrap.setFixedHeight(34)
        self._theme_wrap.setCursor(Qt.PointingHandCursor)
        self._theme_wrap.setToolTip("切换浅色 / 深色主题")
        self._theme_wrap.mousePressEvent = lambda e, w=self._theme_wrap: self._toggle_theme(w, e)
        theme_lay = QHBoxLayout(self._theme_wrap)
        theme_lay.setContentsMargins(12, 0, 12, 0)
        theme_lay.setSpacing(8)
        theme_lay.addWidget(self._sb_theme_icon)
        theme_lay.addWidget(self._sb_theme)
        theme_lay.addStretch()
        theme_lay.addWidget(self._sb_theme_action)
        theme_outer = QWidget()
        theme_outer_lay = QHBoxLayout(theme_outer)
        theme_outer_lay.setContentsMargins(26, 0, 26, 0)
        theme_outer_lay.addWidget(self._theme_wrap)
        sb_lay.addWidget(theme_outer)
        sb_lay.addSpacing(10)

        self._sb_author = QLabel("作者: TiAmo")
        self._sb_author.setObjectName("sb_theme")
        self._sb_author.setAlignment(Qt.AlignLeft)
        self._sb_author.setFont(QFont(_FN, 8))
        self._sb_author.setContentsMargins(26, 0, 0, 0)
        sb_lay.addWidget(self._sb_author)
        self._sb_version = QLabel("当前版本: v1.0.0")
        self._sb_version.setObjectName("sb_theme")
        self._sb_version.setAlignment(Qt.AlignLeft)
        self._sb_version.setFont(QFont(_FN, 8))
        self._sb_version.setContentsMargins(26, 0, 0, 0)
        sb_lay.addWidget(self._sb_version)
        sb_lay.addSpacing(16)
        self._update_theme_label()

        body_h.addWidget(self._sb)

        # ── 右侧 ──
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        self._stack = AnimatedStackedWidget()
        right_lay.addWidget(self._stack, 1)
        body_h.addWidget(right, 1)
        root_v.addWidget(body, 1)

        self._build_control()
        self._build_navigator()
        self._build_hook()
        self._build_cloud()
        self._build_mcp()
        self._build_extract()
        self._build_vconsole()
        self._build_logs()
        self._build_faq()
        self._update_target_badge(False)

    # ── 控制台 ──

    def _build_control(self):
        """构建主控制台页面，提供连接参数、断点策略和运行状态。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(14)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # Card 1: 启动调试流程
        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(18, 14, 18, 14)
        c1_lay.setSpacing(10)
        c1_lay.addWidget(_make_label("启动调试流程", bold=True))
        flow_tip = QLabel("先启动调试，再打开小程序；连接稳定后可自动或手动注入 Hook。")
        flow_tip.setProperty("class", "muted")
        flow_tip.setWordWrap(True)
        c1_lay.addWidget(flow_tip)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(QLabel("CDP 端口"))
        self._cp_ent = _make_entry(width=100)
        self._cp_ent.setText(str(self._cfg.get("cdp_port", CDP_PORT)))
        self._cp_ent.textChanged.connect(lambda: (self._auto_save(), self._update_target_badge()))
        row1.addWidget(self._cp_ent)
        row1.addSpacing(16)
        self._tog_devtools_bp = ToggleSwitch(self._cfg.get("allow_devtools_breakpoints", False))
        self._tog_devtools_bp.toggled.connect(self._on_devtools_breakpoints_toggled)
        row1.addWidget(self._tog_devtools_bp)
        row1.addWidget(QLabel("断点"))
        row1.addSpacing(12)
        self._devtools_bp_status_lbl = QLabel("")
        self._devtools_bp_status_lbl.setProperty("class", "muted")
        row1.addWidget(self._devtools_bp_status_lbl)
        c1_lay.addLayout(row1)
        self._refresh_devtools_breakpoint_status()

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._btn_start = _make_btn("启动调试", self._do_start)
        self._btn_start.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_start.setMinimumWidth(84)
        action_row.addWidget(self._btn_start)
        self._btn_stop = _make_btn("停止", self._do_stop)
        self._btn_stop.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_stop.setMinimumWidth(64)
        self._btn_stop.setEnabled(False)
        action_row.addWidget(self._btn_stop)
        self._btn_control_hook = _make_btn("Hook 注入", self._open_hook_page_from_control)
        self._btn_control_hook.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_control_hook.setMinimumWidth(86)
        self._btn_control_hook.setToolTip("进入 Hook 页面选择脚本并执行注入")
        self._btn_control_hook.setVisible(False)
        action_row.addWidget(self._btn_control_hook)
        action_row.addStretch()
        c1_lay.addLayout(action_row)

        self._flow_stepper = FlowStepper(self._tn)
        c1_lay.addWidget(self._flow_stepper)

        dt_row = QHBoxLayout()
        dt_row.addWidget(QLabel("DevTools"))
        self._devtools_lbl = QLabel("未生成")
        self._devtools_lbl.setProperty("class", "accent")
        self._devtools_lbl.setFont(QFont(_FM, 8))
        self._devtools_lbl.setCursor(Qt.PointingHandCursor)
        self._devtools_lbl.setToolTip("启动调试后生成 DevTools 调试链接")
        self._devtools_lbl.setStyleSheet(f"color: {_TH[self._tn]['text3']};")
        self._devtools_lbl.mousePressEvent = lambda e: self._copy_devtools_url()
        dt_row.addWidget(self._devtools_lbl)
        self._devtools_copy_hint = QPushButton("点击复制")
        self._devtools_copy_hint.setObjectName("devtools_copy_btn")
        self._devtools_copy_hint.setFont(QFont(_FN, 8))
        self._devtools_copy_hint.setCursor(Qt.PointingHandCursor)
        self._devtools_copy_hint.setToolTip("复制 DevTools 调试链接")
        self._devtools_copy_hint.clicked.connect(self._copy_devtools_url)
        self._devtools_copy_hint.setEnabled(False)
        self._devtools_copy_hint.setVisible(False)
        dt_row.addWidget(self._devtools_copy_hint)
        dt_row.addStretch()
        c1_lay.addLayout(dt_row)
        top_row.addWidget(c1, 5)

        ctx_card = _make_card()
        ctx_card.setMinimumWidth(190)
        ctx_lay = QVBoxLayout(ctx_card)
        ctx_lay.setContentsMargins(18, 14, 18, 14)
        ctx_lay.setSpacing(8)
        ctx_lay.addWidget(_make_label("当前小程序上下文", bold=True))
        self._appname_lbl = QLabel("应用: --")
        self._appname_lbl.setProperty("class", "bold")
        ctx_lay.addWidget(self._appname_lbl)
        self._app_lbl = QLabel("AppID: --")
        self._app_lbl.setProperty("class", "muted")
        ctx_lay.addWidget(self._app_lbl)
        self._control_route_lbl = QLabel("当前路由: --")
        self._control_route_lbl.setProperty("class", "muted")
        ctx_lay.addWidget(self._control_route_lbl)
        ctx_lay.addStretch()
        top_row.addWidget(ctx_card, 2)
        lay.addLayout(top_row)

        # Card 2: 运行状态条
        c3 = _make_card()
        c3_lay = QHBoxLayout(c3)
        c3_lay.setContentsMargins(18, 12, 18, 12)
        c3_lay.setSpacing(18)
        self._dots = {}
        for key, name in [("frida", "Frida"), ("miniapp", "小程序"), ("devtools", "DevTools")]:
            dr = QHBoxLayout()
            dot = StatusDot()
            dot.set_color(_TH[self._tn]["text4"])
            dot.setToolTip(f"{name}: 未连接")
            dr.addWidget(dot)
            lb = QLabel(f"{name}: 未连接")
            lb.setToolTip(f"{name}: 未连接")
            dr.addWidget(lb)
            dr.addStretch()
            c3_lay.addLayout(dr)
            self._dots[key] = (dot, lb, name)
        self._control_mcp_status_lbl = QLabel("MCP: 未启动")
        self._control_mcp_status_lbl.setProperty("class", "muted")
        c3_lay.addWidget(self._control_mcp_status_lbl)
        c3_lay.addStretch()
        lay.addWidget(c3)

        log_card = _make_card()
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(16, 12, 16, 12)
        log_lay.setSpacing(8)
        log_hdr = QHBoxLayout()
        log_hdr.addWidget(_make_label("运行日志", bold=True))
        log_hdr.addStretch()
        self._btn_control_clear = _make_btn("清空", self._do_clear)
        log_hdr.addWidget(self._btn_control_clear)
        log_lay.addLayout(log_hdr)
        self._control_logbox = QTextEdit()
        self._control_logbox.setReadOnly(True)
        self._control_logbox.setPlaceholderText("运行日志会显示在这里。")
        self._control_logbox.setFont(QFont(_FM, 9))
        log_lay.addWidget(self._control_logbox, 1)
        lay.addWidget(log_card, 1)

        self._update_flow_steps()
        self._stack.addWidget(page)
        self._page_map["control"] = self._stack.count() - 1

    # ── 路由导航 ──

    def _build_navigator(self):
        """构建路由导航页面，提供路由获取、搜索、跳转、遍历和空状态提示。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(14)

        top_card = _make_card()
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(18, 14, 18, 14)
        top_lay.setSpacing(10)

        sf = QHBoxLayout()
        sf.addWidget(_make_label("路由搜索", bold=True))
        self._srch_ent = _make_entry("输入路由关键字搜索...")
        self._srch_ent.textChanged.connect(self._do_filter)
        sf.addWidget(self._srch_ent, 1)
        self._btn_clear_route_search = _make_btn("清除搜索", self._clear_route_search)
        self._btn_clear_route_search.setEnabled(False)
        sf.addWidget(self._btn_clear_route_search)
        self._btn_fetch = _make_btn("获取路由", self._do_fetch)
        self._btn_fetch.setEnabled(False)
        sf.addWidget(self._btn_fetch)
        top_lay.addLayout(sf)

        mi = QHBoxLayout()
        mi.addWidget(QLabel("手动跳转"))
        self._nav_input = _make_entry("输入路由路径，回车跳转...")
        self._nav_input.returnPressed.connect(self._do_manual_go)
        mi.addWidget(self._nav_input, 1)
        self._btn_manual_go = _make_btn("跳转", self._do_manual_go)
        mi.addWidget(self._btn_manual_go)
        self._btn_copy_route = _make_btn("复制路由", self._do_copy_route)
        self._btn_copy_route.setEnabled(False)
        mi.addWidget(self._btn_copy_route)
        top_lay.addLayout(mi)
        lay.addWidget(top_card)

        tc = _make_card()
        tc_lay = QVBoxLayout(tc)
        tc_lay.setContentsMargins(16, 12, 16, 12)
        tc_lay.setSpacing(8)
        tree_hdr = QHBoxLayout()
        tree_hdr.addWidget(_make_label("路由列表", bold=True))
        self._route_count_lbl = QLabel("0 条")
        self._route_count_lbl.setProperty("class", "muted")
        tree_hdr.addWidget(self._route_count_lbl)
        tree_hdr.addStretch()
        self._btn_copy_route_list = _make_btn("复制列表", self._do_copy_route_list)
        self._btn_copy_route_list.setEnabled(False)
        tree_hdr.addWidget(self._btn_copy_route_list)
        self._route_lbl = QLabel("当前路由: --")
        self._route_lbl.setProperty("class", "muted")
        tree_hdr.addWidget(self._route_lbl)
        tc_lay.addLayout(tree_hdr)
        self._route_empty_hint = QLabel("连接小程序后点击「获取路由」，路由树会显示在这里。")
        self._route_empty_hint.setProperty("class", "muted")
        self._route_empty_hint.setAlignment(Qt.AlignCenter)
        tc_lay.addWidget(self._route_empty_hint)
        self._tree = QTreeWidget()
        self._tree.setMinimumHeight(300)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._nav_context_menu)
        tc_lay.addWidget(self._tree)
        lay.addWidget(tc, 1)

        op_card = _make_card()
        op_lay = QVBoxLayout(op_card)
        op_lay.setContentsMargins(18, 12, 18, 12)
        op_lay.setSpacing(10)
        b1 = QHBoxLayout()
        b1.addWidget(_make_label("页面操作", bold=True))
        self._btn_go = _make_btn("跳转", self._do_go)
        self._btn_go.setEnabled(False)
        b1.addWidget(self._btn_go)
        self._btn_relaunch = _make_btn("重启到页面", self._do_relaunch)
        self._btn_relaunch.setEnabled(False)
        b1.addWidget(self._btn_relaunch)
        self._btn_back = _make_btn("返回上页", self._do_back)
        self._btn_back.setEnabled(False)
        b1.addWidget(self._btn_back)
        self._btn_refresh = _make_btn("刷新页面", self._do_refresh)
        self._btn_refresh.setEnabled(False)
        b1.addWidget(self._btn_refresh)
        b1.addStretch()
        op_lay.addLayout(b1)

        b2 = QHBoxLayout()
        b2.addWidget(_make_label("遍历与保护", bold=True))
        self._btn_prev = _make_btn("上一个", self._do_prev)
        self._btn_prev.setEnabled(False)
        b2.addWidget(self._btn_prev)
        self._btn_next = _make_btn("下一个", self._do_next)
        self._btn_next.setEnabled(False)
        b2.addWidget(self._btn_next)
        self._btn_auto = _make_btn("自动遍历", self._do_autovis)
        self._btn_auto.setEnabled(False)
        b2.addWidget(self._btn_auto)
        self._btn_autostop = _make_btn("停止遍历", self._do_autostop)
        self._btn_autostop.setEnabled(False)
        b2.addWidget(self._btn_autostop)
        b2.addSpacing(12)
        self._guard_switch = ToggleSwitch(False)
        self._guard_switch.setFixedSize(36, 18)
        self._guard_switch.setEnabled(False)
        self._guard_switch.toggled.connect(self._do_toggle_guard_switch)
        b2.addWidget(self._guard_switch)
        self._guard_label = QLabel("防跳转: 关闭")
        b2.addWidget(self._guard_label)
        b2.addStretch()
        op_lay.addLayout(b2)
        self._nav_hint_lbl = QLabel("连接小程序并获取路由后，可选择路由执行跳转、重启、遍历和防跳转。")
        self._nav_hint_lbl.setProperty("class", "muted")
        self._nav_hint_lbl.setWordWrap(True)
        op_lay.addWidget(self._nav_hint_lbl)

        self._prog = QProgressBar()
        self._prog.setMaximum(100)
        self._prog.setValue(0)
        self._prog.setTextVisible(False)
        self._prog.setFixedHeight(6)
        op_lay.addWidget(self._prog)
        lay.addWidget(op_card)

        self._stack.addWidget(page)
        self._page_map["navigator"] = self._stack.count() - 1

    # ── Hook 页面 ──

    def _build_hook(self):
        """构建 Hook 脚本页面，提供脚本搜索、全局注入和即时注入操作。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(14)

        top_card = _make_card()
        top_lay = QVBoxLayout(top_card)
        top_lay.setContentsMargins(18, 14, 18, 14)
        top_lay.setSpacing(8)
        top_lay.addWidget(_make_label("Hook 脚本", bold=True))
        tip_row = QHBoxLayout()
        self._hook_tip = QLabel("将 .js 文件放入 hook_scripts/ 目录，点击「注入」即时执行")
        self._hook_tip.setProperty("class", "muted")
        self._hook_tip.setWordWrap(True)
        tip_row.addWidget(self._hook_tip)
        tip_row.addStretch()
        self._btn_hook_refresh = _make_btn("刷新列表", self._hook_refresh)
        tip_row.addWidget(self._btn_hook_refresh)
        self._btn_hook_copy_dir = _make_btn("复制目录", self._copy_hook_dir)
        tip_row.addWidget(self._btn_hook_copy_dir)
        top_lay.addLayout(tip_row)
        lay.addWidget(top_card)

        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(16, 12, 16, 12)
        c1_lay.setSpacing(8)
        hdr = QHBoxLayout()
        hdr.addWidget(_make_label("脚本列表", bold=True))
        self._hook_search_ent = _make_entry("搜索脚本文件名...", width=220)
        self._hook_search_ent.textChanged.connect(self._hook_refresh)
        hdr.addWidget(self._hook_search_ent)
        self._btn_hook_clear_search = _make_btn("清除搜索", self._clear_hook_search)
        self._btn_hook_clear_search.setEnabled(False)
        hdr.addWidget(self._btn_hook_clear_search)
        hdr.addStretch()
        self._hook_count_lbl = QLabel("")
        self._hook_count_lbl.setProperty("class", "muted")
        hdr.addWidget(self._hook_count_lbl)
        c1_lay.addLayout(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(320)
        self._hook_inner = QWidget()
        self._hook_inner_lay = QVBoxLayout(self._hook_inner)
        self._hook_inner_lay.setContentsMargins(0, 0, 0, 0)
        self._hook_inner_lay.setSpacing(6)
        self._hook_inner_lay.addStretch()
        scroll.setWidget(self._hook_inner)
        c1_lay.addWidget(scroll)
        lay.addWidget(c1, 1)

        self._hook_status_lbls = {}
        self._hook_refresh()

        self._stack.addWidget(page)
        self._page_map["hook"] = self._stack.count() - 1

    def _hook_refresh(self):
        """刷新 Hook 脚本列表，并按搜索关键字过滤展示结果。"""
        while self._hook_inner_lay.count() > 1:
            item = self._hook_inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._hook_status_lbls = {}

        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        all_files = sorted(f for f in os.listdir(hook_dir) if f.endswith(".js")) if os.path.isdir(hook_dir) else []
        kw = self._hook_search_ent.text().strip().lower() if hasattr(self, "_hook_search_ent") else ""
        js_files = [f for f in all_files if not kw or kw in f.lower()]
        if hasattr(self, "_hook_count_lbl"):
            global_count = len([f for f in all_files if f in self._global_hook_scripts])
            injected_count = len([f for f in all_files if f in self._hook_injected])
            count_text = (
                f"{len(js_files)} / {len(all_files)} 个脚本"
                if kw else f"{len(all_files)} 个脚本 · 全局 {global_count} · 已注入 {injected_count}"
            )
            self._hook_count_lbl.setText(count_text)
        if hasattr(self, "_btn_hook_clear_search"):
            self._btn_hook_clear_search.setEnabled(bool(kw))

        if not all_files:
            lbl = QLabel("hook_scripts/ 目录下暂无 .js 文件。")
            lbl.setProperty("class", "muted")
            lbl.setAlignment(Qt.AlignCenter)
            self._hook_inner_lay.insertWidget(0, lbl)
            return

        if not js_files:
            lbl = QLabel("没有匹配的 Hook 脚本。")
            lbl.setProperty("class", "muted")
            lbl.setAlignment(Qt.AlignCenter)
            self._hook_inner_lay.insertWidget(0, lbl)
            return

        for fn in js_files:
            row = QFrame()
            row.setProperty("class", "hook_row")
            row.setFixedHeight(66)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(14, 0, 14, 0)
            row_lay.setSpacing(12)

            icon_lbl = QLabel("JS")
            icon_lbl.setProperty("class", "js_badge")
            icon_lbl.setFont(QFont(_FM, 8, QFont.Bold))
            icon_lbl.setFixedSize(34, 24)
            icon_lbl.setAlignment(Qt.AlignCenter)
            row_lay.addWidget(icon_lbl)

            name_box = QVBoxLayout()
            name_box.setSpacing(2)
            name_lbl = QLabel(fn)
            name_lbl.setFont(QFont(_FN, 10, QFont.Bold))
            name_box.addWidget(name_lbl)
            path_lbl = QLabel(os.path.join("hook_scripts", fn))
            path_lbl.setProperty("class", "muted")
            path_lbl.setFont(QFont(_FN, 8))
            name_box.addWidget(path_lbl)
            row_lay.addLayout(name_box, 1)

            is_global = fn in self._global_hook_scripts
            injected = fn in self._hook_injected
            if is_global and injected:
                status_text = "全局 ● 已注入"
            elif is_global:
                status_text = "全局 ○ 待注入"
            elif injected:
                status_text = "● 已注入"
            else:
                status_text = "○ 未注入"
            status_lbl = QLabel(status_text)
            c = _TH[self._tn]
            status_lbl.setStyleSheet(f"color: {c['success'] if injected else c['text3']};")
            status_lbl.setMinimumWidth(90)
            row_lay.addWidget(status_lbl)
            self._hook_status_lbls[fn] = status_lbl

            global_cb = QCheckBox("全局")
            global_cb.setChecked(is_global)
            global_cb.toggled.connect(lambda checked, f=fn: self._hook_global_toggle(f, checked))
            row_lay.addWidget(global_cb)

            inject_btn = _make_btn("注入", lambda checked=False, f=fn: self._hook_inject(f))
            inject_btn.setEnabled(bool(self._engine and self._loop and self._loop.is_running()))
            inject_btn.setToolTip("需要先启动调试并连接小程序")
            row_lay.addWidget(inject_btn)
            clear_btn = _make_btn("清除", lambda checked=False, f=fn: self._hook_clear(f))
            row_lay.addWidget(clear_btn)

            self._hook_inner_lay.insertWidget(self._hook_inner_lay.count() - 1, row)

    def _clear_hook_search(self):
        """清空 Hook 脚本搜索关键字并恢复完整列表。"""
        if hasattr(self, "_hook_search_ent"):
            self._hook_search_ent.clear()
        self._hook_refresh()

    def _copy_hook_dir(self):
        """复制 Hook 脚本目录路径，便于用户定位脚本存放位置。"""
        path = os.path.join(_BASE_DIR, "hook_scripts")
        QApplication.clipboard().setText(path)
        self._log_add("info", f"[Hook] 已复制脚本目录: {path}")

    def _hook_inject(self, filename):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[Hook] 请先启动调试")
            return
        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        filepath = os.path.join(hook_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception as e:
            self._log_add("error", f"[Hook] 读取文件失败: {e}")
            return
        asyncio.run_coroutine_threadsafe(
            self._ahook_inject(filename, source), self._loop)

    async def _ahook_inject(self, filename, source):
        try:
            await self._engine.evaluate_js(source, timeout=5.0)
            self._hook_injected.add(filename)
            self._log_q.put(("info", f"[Hook] 已注入: {filename}"))
            self._log_q.put(("__hook_status__", filename, True))
        except Exception as e:
            self._log_q.put(("error", f"[Hook] 注入失败 {filename}: {e}"))

    def _hook_clear(self, filename):
        self._hook_injected.discard(filename)
        self._hook_update_status(filename, False)
        self._log_add("info", f"[Hook] 已清除标记: {filename}（注意: JS 注入后无法真正撤销，需刷新页面）")

    def _hook_update_status(self, filename, injected):
        c = _TH[self._tn]
        lbl = self._hook_status_lbls.get(filename)
        if lbl:
            is_global = filename in self._global_hook_scripts
            if is_global and injected:
                lbl.setText("全局 ● 已注入")
                lbl.setStyleSheet(f"color: {c['success']};")
            elif is_global:
                lbl.setText("全局 ○ 待注入")
                lbl.setStyleSheet(f"color: {c['text3']};")
            elif injected:
                lbl.setText("● 已注入")
                lbl.setStyleSheet(f"color: {c['success']};")
            else:
                lbl.setText("○ 未注入")
                lbl.setStyleSheet(f"color: {c['text3']};")
        self._update_flow_steps()

    def _hook_global_toggle(self, filename, checked):
        if checked:
            self._global_hook_scripts.add(filename)
        else:
            self._global_hook_scripts.discard(filename)
        injected = filename in self._hook_injected
        self._hook_update_status(filename, injected)
        self._auto_save()

    def _hook_auto_inject_globals(self):
        """Auto-inject all global hook scripts (called when miniapp stabilizes)."""
        if not self._engine or not self._loop or not self._loop.is_running():
            return
        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        for fn in list(self._global_hook_scripts):
            if fn in self._hook_injected:
                continue
            filepath = os.path.join(hook_dir, fn)
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    source = f.read()
            except Exception:
                continue
            asyncio.run_coroutine_threadsafe(
                self._ahook_inject(fn, source), self._loop)

    def _do_global_inject(self, gen):
        """独立的全局注入定时回调，只在小程序连接变化时触发，不受 CDP 等影响。"""
        if gen != self._global_inject_gen:
            return
        if not self._miniapp_connected:
            return
        if self._global_hook_scripts:
            self._hook_auto_inject_globals()
            self._log_add("info", "[Hook] 自动注入全局脚本")

    # ── 云扫描 ──

    def _build_cloud(self):
        """构建云扫描页面，集中展示捕获操作、云函数记录和手动调用结果。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(12)

        toolbar_card = _make_card()
        toolbar_lay = QVBoxLayout(toolbar_card)
        toolbar_lay.setContentsMargins(16, 12, 16, 12)
        toolbar_lay.setSpacing(10)

        toolbar_top = QHBoxLayout()
        toolbar_top.setSpacing(10)
        toolbar_top.addWidget(_make_label("云扫描控制", bold=True))
        self._cloud_env_lbl = QLabel("全局捕获（默认开启）")
        self._cloud_env_lbl.setProperty("class", "muted")
        toolbar_top.addWidget(self._cloud_env_lbl)
        toolbar_top.addStretch()
        self._btn_cloud_toggle = _make_btn("停止捕获", self._cloud_do_toggle)
        toolbar_top.addWidget(self._btn_cloud_toggle)
        self._btn_cloud_static = _make_btn("静态扫描", self._cloud_do_static_scan)
        toolbar_top.addWidget(self._btn_cloud_static)
        self._btn_cloud_clear = _make_btn("清空记录", self._cloud_do_clear)
        toolbar_top.addWidget(self._btn_cloud_clear)
        self._btn_cloud_export = _make_btn("导出报告", self._cloud_do_export)
        toolbar_top.addWidget(self._btn_cloud_export)
        toolbar_lay.addLayout(toolbar_top)

        toolbar_bottom = QHBoxLayout()
        toolbar_bottom.setSpacing(10)
        self._cloud_status_lbl = QLabel("捕获: 0 条")
        self._cloud_status_lbl.setProperty("class", "muted")
        toolbar_bottom.addWidget(self._cloud_status_lbl)
        self._cloud_filter_count_lbl = QLabel("")
        self._cloud_filter_count_lbl.setProperty("class", "muted")
        toolbar_bottom.addWidget(self._cloud_filter_count_lbl)
        self._cloud_scan_lbl = QLabel("")
        self._cloud_scan_lbl.setProperty("class", "muted")
        toolbar_bottom.addWidget(self._cloud_scan_lbl)
        toolbar_bottom.addStretch()
        toolbar_bottom.addWidget(QLabel("搜索"))
        self._cloud_search_ent = _make_entry("AppID / 类型 / 名称 / 参数", width=240)
        self._cloud_search_ent.textChanged.connect(self._cloud_filter)
        toolbar_bottom.addWidget(self._cloud_search_ent)
        self._btn_cloud_clear_search = _make_btn("清除搜索", self._cloud_clear_search)
        self._btn_cloud_clear_search.setEnabled(False)
        toolbar_bottom.addWidget(self._btn_cloud_clear_search)
        toolbar_lay.addLayout(toolbar_bottom)
        lay.addWidget(toolbar_card)

        tc = _make_card()
        tc_lay = QVBoxLayout(tc)
        tc_lay.setContentsMargins(16, 12, 16, 12)
        tc_lay.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.addWidget(_make_label("云函数捕获记录", bold=True))
        title_row.addStretch()
        self._btn_cloud_copy_visible = _make_btn("复制当前", self._cloud_copy_visible_records)
        self._btn_cloud_copy_visible.setEnabled(False)
        title_row.addWidget(self._btn_cloud_copy_visible)
        tc_lay.addLayout(title_row)
        self._cloud_empty_hint = QLabel("等待捕获云函数、数据库、存储或容器调用记录。")
        self._cloud_empty_hint.setProperty("class", "muted")
        self._cloud_empty_hint.setAlignment(Qt.AlignCenter)
        tc_lay.addWidget(self._cloud_empty_hint)

        self._cloud_tree = QTreeWidget()
        self._cloud_tree.setMinimumHeight(280)
        self._cloud_tree.setRootIsDecorated(False)
        self._cloud_tree.setIndentation(0)
        self._cloud_tree.setHeaderLabels(["AppID", "类型", "名称", "参数", "状态", "时间"])
        header = self._cloud_tree.header()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self._cloud_tree.setColumnWidth(0, 100)
        self._cloud_tree.setColumnWidth(1, 70)
        self._cloud_tree.setColumnWidth(2, 140)
        self._cloud_tree.setColumnWidth(4, 50)
        self._cloud_tree.setColumnWidth(5, 70)
        self._cloud_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self._cloud_tree.itemClicked.connect(self._cloud_on_select)
        self._cloud_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._cloud_tree.customContextMenuRequested.connect(self._cloud_tree_context_menu)
        tc_lay.addWidget(self._cloud_tree)
        lay.addWidget(tc, 1)

        call_card = _make_card()
        call_lay = QVBoxLayout(call_card)
        call_lay.setContentsMargins(16, 12, 16, 12)
        call_lay.setSpacing(8)
        call_hdr = QHBoxLayout()
        call_hdr.addWidget(_make_label("手动调用", bold=True))
        call_hdr.addStretch()
        self._btn_cloud_copy_result = _make_btn("复制结果", self._cloud_copy_result)
        self._btn_cloud_copy_result.setEnabled(False)
        call_hdr.addWidget(self._btn_cloud_copy_result)
        call_lay.addLayout(call_hdr)

        call_row = QHBoxLayout()
        call_row.setSpacing(10)
        call_row.addWidget(QLabel("函数名"))
        self._cloud_name_ent = _make_entry(width=140)
        call_row.addWidget(self._cloud_name_ent)
        call_row.addWidget(QLabel("参数"))
        self._cloud_data_ent = _make_entry()
        self._cloud_data_ent.setText("{}")
        call_row.addWidget(self._cloud_data_ent, 1)
        self._btn_cloud_call = _make_btn("调用", self._cloud_do_call)
        call_row.addWidget(self._btn_cloud_call)
        call_lay.addLayout(call_row)

        self._cloud_result = QTextEdit()
        self._cloud_result.setReadOnly(True)
        self._cloud_result.setPlaceholderText("手动调用或右键查看返回结果后，会显示详细响应。")
        self._cloud_result.setMinimumHeight(128)
        self._cloud_result.setMaximumHeight(170)
        self._cloud_result.setFont(QFont(_FM, 9))
        call_lay.addWidget(self._cloud_result)
        lay.addWidget(call_card)

        self._stack.addWidget(page)
        self._page_map["cloud"] = self._stack.count() - 1

    # ── MCP ──

    def _build_mcp(self):
        """构建 MCP 控制台页面，展示服务状态、连接信息、权限和日志。"""
        page = QWidget()
        page_lay = QVBoxLayout(page)
        page_lay.setContentsMargins(24, 12, 24, 16)
        page_lay.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.setAlignment(Qt.AlignTop)

        status_card = _make_card()
        status_lay = QVBoxLayout(status_card)
        status_lay.setContentsMargins(16, 12, 16, 12)
        status_lay.setSpacing(10)

        mcp_row = QHBoxLayout()
        mcp_row.setSpacing(8)
        mcp_row.addWidget(_make_label("本地 MCP 服务", bold=True))
        mcp_row.addStretch()
        self._mcp_status_dot = StatusDot()
        mcp_row.addWidget(self._mcp_status_dot)
        self._mcp_status_lbl = QLabel("MCP: 未启动")
        self._mcp_status_lbl.setProperty("class", "muted")
        mcp_row.addWidget(self._mcp_status_lbl)
        status_lay.addLayout(mcp_row)

        self._mcp_frida_lbl = QLabel("Frida: 未连接")
        self._mcp_miniapp_lbl = QLabel("MiniApp: 未连接")
        self._mcp_devtools_lbl = QLabel("CDP: 未连接")
        self._mcp_app_lbl = QLabel("AppID: --")
        self._mcp_route_lbl = QLabel("当前路由: --")
        for lbl in (self._mcp_frida_lbl, self._mcp_miniapp_lbl,
                    self._mcp_devtools_lbl, self._mcp_app_lbl,
                    self._mcp_route_lbl):
            lbl.setProperty("class", "muted")

        status_grid = QGridLayout()
        status_grid.setHorizontalSpacing(16)
        status_grid.setVerticalSpacing(8)
        status_grid.addWidget(self._mcp_frida_lbl, 0, 0)
        status_grid.addWidget(self._mcp_miniapp_lbl, 0, 1)
        status_grid.addWidget(self._mcp_devtools_lbl, 1, 0)
        status_grid.addWidget(self._mcp_app_lbl, 1, 1)
        status_grid.addWidget(self._mcp_route_lbl, 2, 0, 1, 2)
        status_lay.addLayout(status_grid)

        target_row = QHBoxLayout()
        target_row.setSpacing(10)
        target_row.addWidget(QLabel("Target"))
        self._mcp_target_combo = QComboBox()
        self._mcp_target_combo.setMinimumWidth(320)
        self._mcp_target_combo.currentIndexChanged.connect(self._on_mcp_target_changed)
        target_row.addWidget(self._mcp_target_combo, 1)
        self._mcp_target_hint_lbl = QLabel("未发现 JS Context")
        self._mcp_target_hint_lbl.setProperty("class", "muted")
        target_row.addWidget(self._mcp_target_hint_lbl)
        status_lay.addLayout(target_row)
        self._refresh_mcp_target_combo([])

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(8)
        self._btn_mcp_start = _make_btn("启动 MCP", self._do_mcp_start)
        self._btn_mcp_stop = _make_btn("停止 MCP", self._do_mcp_stop)
        self._btn_mcp_restart = _make_btn("重启 MCP", self._do_mcp_restart)
        self._btn_mcp_stop.setEnabled(False)
        self._btn_mcp_restart.setEnabled(False)
        ctrl_row.addWidget(self._btn_mcp_start)
        ctrl_row.addWidget(self._btn_mcp_stop)
        ctrl_row.addWidget(self._btn_mcp_restart)
        ctrl_row.addStretch()
        status_lay.addLayout(ctrl_row)

        tip = QLabel("当前提供本地 MCP HTTP 服务，外部 AI 可按权限调用调试工具。")
        tip.setWordWrap(True)
        tip.setProperty("class", "muted")
        status_lay.addWidget(tip)

        conn_card = _make_card()
        conn_lay = QVBoxLayout(conn_card)
        conn_lay.setContentsMargins(16, 12, 16, 12)
        conn_lay.setSpacing(10)

        conn_hdr = QHBoxLayout()
        conn_hdr.addWidget(_make_label("连接信息", bold=True))
        conn_hdr.addStretch()
        self._btn_mcp_copy_cfg = _make_btn("复制客户端配置", self._copy_mcp_config)
        conn_hdr.addWidget(self._btn_mcp_copy_cfg)
        conn_lay.addLayout(conn_hdr)

        addr_row = QHBoxLayout()
        addr_row.setSpacing(10)
        addr_row.addWidget(QLabel("MCP 地址"))
        self._mcp_addr_ent = _make_entry(width=None)
        self._mcp_addr_ent.setText(self._mcp_endpoint)
        self._mcp_addr_ent.setReadOnly(True)
        self._mcp_addr_ent.setFont(QFont(_FM, 9))
        addr_row.addWidget(self._mcp_addr_ent, 1)
        self._btn_mcp_copy_addr = _make_btn("复制地址", self._copy_mcp_address)
        addr_row.addWidget(self._btn_mcp_copy_addr)
        conn_lay.addLayout(addr_row)

        self._mcp_config_box = QTextEdit()
        self._mcp_config_box.setReadOnly(True)
        self._mcp_config_box.setMinimumHeight(120)
        self._mcp_config_box.setMaximumHeight(150)
        self._mcp_config_box.setLineWrapMode(QTextEdit.NoWrap)
        self._mcp_config_box.setFont(QFont(_FM, 8))
        self._mcp_config_box.setPlainText(self._mcp_client_config())
        conn_lay.addWidget(self._mcp_config_box)

        lay.addWidget(status_card)
        lay.addWidget(conn_card)

        perm_card = _make_card()
        perm_lay = QVBoxLayout(perm_card)
        perm_lay.setContentsMargins(16, 12, 16, 12)
        perm_lay.setSpacing(10)

        perm_hdr = QHBoxLayout()
        perm_hdr.addWidget(_make_label("权限开关", bold=True))
        perm_hdr.addStretch()
        self._btn_mcp_copy_perms = _make_btn("复制权限", self._copy_mcp_permissions)
        perm_hdr.addWidget(self._btn_mcp_copy_perms)
        self._btn_mcp_reset_perms = _make_btn("恢复默认", self._reset_mcp_permissions)
        perm_hdr.addWidget(self._btn_mcp_reset_perms)
        perm_lay.addLayout(perm_hdr)

        perm_tip = QLabel("读取类能力默认允许；自动访问、探针注入、云函数调用等高影响能力需单独开启。")
        perm_tip.setWordWrap(True)
        perm_tip.setProperty("class", "muted")
        perm_lay.addWidget(perm_tip)

        perm_grid = QGridLayout()
        perm_grid.setHorizontalSpacing(24)
        perm_grid.setVerticalSpacing(10)
        for idx, (key, label, _) in enumerate(_MCP_PERMISSIONS):
            cell = QHBoxLayout()
            cell.setSpacing(8)
            tog = ToggleSwitch(bool(self._mcp_permissions.get(key, False)))
            tog.toggled.connect(lambda checked, k=key: self._set_mcp_permission(k, checked))
            self._mcp_permission_toggles[key] = tog
            text = QLabel(label)
            text.setMinimumWidth(86)
            cell.addWidget(tog)
            cell.addWidget(text)
            cell.addStretch()
            perm_grid.addLayout(cell, idx // 3, idx % 3)
        perm_lay.addLayout(perm_grid)
        lay.addWidget(perm_card)

        log_card = _make_card()
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(16, 12, 16, 12)
        log_lay.setSpacing(8)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(_make_label("MCP 日志", bold=True))
        log_hdr.addStretch()
        self._btn_mcp_copy_log = _make_btn("复制日志", self._copy_mcp_log)
        log_hdr.addWidget(self._btn_mcp_copy_log)
        self._btn_mcp_clear_log = _make_btn("清空", self._clear_mcp_log)
        log_hdr.addWidget(self._btn_mcp_clear_log)
        log_lay.addLayout(log_hdr)

        self._mcp_logbox = QTextEdit()
        self._mcp_logbox.setReadOnly(True)
        self._mcp_logbox.setPlaceholderText("MCP 服务日志会显示在这里。")
        self._mcp_logbox.setMinimumHeight(190)
        self._mcp_logbox.setFont(QFont(_FM, 9))
        log_lay.addWidget(self._mcp_logbox)
        lay.addWidget(log_card, 1)

        self._set_mcp_status("未启动", False)
        self._mcp_add_log("MCP 页面已就绪，等待外部客户端连接。")

        scroll.setWidget(content)
        page_lay.addWidget(scroll)
        self._stack.addWidget(page)
        self._page_map["mcp"] = self._stack.count() - 1

    # ── 敏感信息提取 ──

    def _build_extract(self):
        """构建敏感信息提取页面，提供目录选择、批处理操作、小程序列表和处理日志。"""
        # 外层使用 QStackedWidget 实现子页面切换
        self._ext_stack = QStackedWidget()

        # =================== 主页面 ===================
        main_page = QWidget()
        main_lay = QVBoxLayout(main_page)
        main_lay.setContentsMargins(24, 12, 24, 16)
        main_lay.setSpacing(12)

        # --- Row 1: Applet目录 ---
        c1 = _make_card()
        c1_lay = QVBoxLayout(c1)
        c1_lay.setContentsMargins(16, 12, 16, 12)
        c1_lay.setSpacing(10)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        path_row.addWidget(_make_label("Applet目录", bold=True))
        self._ext_path_ent = _make_entry("wxapkg 包目录路径...")
        # 自动检测默认路径
        from src.wxapkg import get_default_packages_dir
        default_pkg = get_default_packages_dir() or ""
        saved_path = self._cfg.get("extract_packages_dir", "")
        if saved_path:
            self._ext_path_ent.setText(saved_path)
        elif default_pkg:
            self._ext_path_ent.setText(default_pkg)
        # 先连接信号，然后手动刷新一次（setText 不会重复触发因为信号在之后连接）
        # 注意: setText 在信号连接前调用，所以不会触发重复刷新
        self._ext_path_ent.textChanged.connect(self._ext_on_path_changed)
        path_row.addWidget(self._ext_path_ent, 1)
        btn_auto = _make_btn("自动选择", self._ext_auto_detect)
        path_row.addWidget(btn_auto)
        btn_browse = _make_btn("选择", self._ext_browse)
        path_row.addWidget(btn_browse)
        c1_lay.addLayout(path_row)
        main_lay.addWidget(c1)

        # --- Row 2: 功能区 ---
        action_card = _make_card()
        action_lay = QVBoxLayout(action_card)
        action_lay.setContentsMargins(16, 12, 16, 12)
        action_lay.setSpacing(10)

        func_row = QHBoxLayout()
        func_row.setSpacing(10)
        func_row.addWidget(_make_label("处理操作", bold=True))
        self._btn_ext_regex = _make_btn("正则配置", self._ext_goto_regex)
        func_row.addWidget(self._btn_ext_regex)
        self._btn_ext_clear_decompiled = _make_btn("清空解包文件", self._ext_clear_decompiled)
        func_row.addWidget(self._btn_ext_clear_decompiled)
        self._btn_ext_clear_applet = _make_btn("清空Applet目录", self._ext_clear_applet)
        func_row.addWidget(self._btn_ext_clear_applet)
        func_row.addStretch()
        # 自动反编译 & 自动提取 开关
        func_row.addWidget(_make_label("自动反编译"))
        self._tog_auto_dec = ToggleSwitch(self._cfg.get("auto_decompile", False))
        self._tog_auto_dec.toggled.connect(lambda v: self._auto_save())
        func_row.addWidget(self._tog_auto_dec)
        func_row.addWidget(_make_label("自动提取"))
        self._tog_auto_scan = ToggleSwitch(self._cfg.get("auto_scan", False))
        self._tog_auto_scan.toggled.connect(lambda v: self._auto_save())
        func_row.addWidget(self._tog_auto_scan)
        action_lay.addLayout(func_row)

        # --- 进度 + 状态 ---
        self._ext_prog = QProgressBar()
        self._ext_prog.setMaximum(100)
        self._ext_prog.setValue(0)
        self._ext_prog.setTextVisible(False)
        self._ext_prog.setFixedHeight(6)
        action_lay.addWidget(self._ext_prog)
        self._ext_status_lbl = QLabel("就绪")
        self._ext_status_lbl.setProperty("class", "muted")
        action_lay.addWidget(self._ext_status_lbl)
        main_lay.addWidget(action_card)

        # --- Row 3: 小程序列表 ---
        list_card = _make_card()
        list_lay = QVBoxLayout(list_card)
        list_lay.setContentsMargins(16, 12, 16, 12)
        list_lay.setSpacing(8)

        list_header = QHBoxLayout()
        list_header.setSpacing(8)
        list_header.addWidget(_make_label("小程序列表", bold=True))
        self._ext_app_count_lbl = _make_label("0 个", muted=True)
        list_header.addWidget(self._ext_app_count_lbl)
        self._ext_app_search_ent = _make_entry("搜索 AppID / 名称...", width=220)
        self._ext_app_search_ent.textChanged.connect(self._ext_filter_app_rows)
        list_header.addWidget(self._ext_app_search_ent)
        list_header.addStretch()
        self._btn_ext_copy_apps = _make_btn("复制当前", self._ext_copy_visible_apps)
        self._btn_ext_copy_apps.setEnabled(False)
        list_header.addWidget(self._btn_ext_copy_apps)
        list_lay.addLayout(list_header)

        # 表头
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr_appid = _make_label("AppID", bold=True)
        hdr_appid.setFixedWidth(180)
        hdr.addWidget(hdr_appid)
        hdr_name = _make_label("名称", bold=True)
        hdr_name.setMinimumWidth(100)
        hdr.addWidget(hdr_name, 1)
        hdr_ops = _make_label("操作", bold=True)
        hdr.addWidget(hdr_ops)
        list_lay.addLayout(hdr)

        # 分割线
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(128,128,128,0.2);")
        list_lay.addWidget(sep)

        self._ext_app_empty_hint = QLabel("没有匹配的小程序。")
        self._ext_app_empty_hint.setProperty("class", "muted")
        self._ext_app_empty_hint.setAlignment(Qt.AlignCenter)
        self._ext_app_empty_hint.hide()
        list_lay.addWidget(self._ext_app_empty_hint)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._ext_list_inner = QWidget()
        self._ext_list_layout = QVBoxLayout(self._ext_list_inner)
        self._ext_list_layout.setContentsMargins(0, 4, 0, 0)
        self._ext_list_layout.setSpacing(4)
        self._ext_list_layout.addStretch()
        scroll.setWidget(self._ext_list_inner)
        list_lay.addWidget(scroll, 1)

        main_lay.addWidget(list_card, 1)

        # 日志区
        log_card = _make_card()
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(16, 12, 16, 12)
        log_lay.setSpacing(8)
        log_lay.addWidget(_make_label("处理日志", bold=True))
        self._ext_logbox = QTextEdit()
        self._ext_logbox.setReadOnly(True)
        self._ext_logbox.setPlaceholderText("反编译、扫描和自动处理日志会显示在这里。")
        self._ext_logbox.setFont(QFont(_FM, 9))
        self._ext_logbox.setMinimumHeight(120)
        self._ext_logbox.setMaximumHeight(170)
        log_lay.addWidget(self._ext_logbox)
        main_lay.addWidget(log_card)

        self._ext_stack.addWidget(main_page)  # index 0

        # =================== 正则配置子页面 ===================
        regex_page = QWidget()
        regex_lay = QVBoxLayout(regex_page)
        regex_lay.setContentsMargins(24, 12, 24, 16)
        regex_lay.setSpacing(12)

        # 返回按钮行
        regex_top_card = _make_card()
        regex_top_lay = QHBoxLayout(regex_top_card)
        regex_top_lay.setContentsMargins(16, 12, 16, 12)
        regex_top_lay.setSpacing(10)
        btn_back_regex = _make_btn("← 返回", lambda: self._ext_stack.setCurrentIndex(0))
        regex_top_lay.addWidget(btn_back_regex)
        regex_top_lay.addWidget(_make_label("正则配置", bold=True))
        regex_top_lay.addWidget(_make_label("提取时会与内置规则合并使用", muted=True))
        regex_top_lay.addStretch()
        regex_lay.addWidget(regex_top_card)

        # 自定义正则卡片
        custom_card = _make_card()
        cc_lay = QVBoxLayout(custom_card)
        cc_lay.setContentsMargins(16, 12, 16, 12)
        cc_lay.setSpacing(8)
        cc_hdr = QHBoxLayout()
        cc_hdr.addWidget(_make_label("自定义正则", bold=True))
        cc_hdr.addStretch()
        btn_add = _make_btn("新建", self._ext_add_pattern)
        cc_hdr.addWidget(btn_add)
        cc_lay.addLayout(cc_hdr)

        # 表头行
        cc_hdr_row = QHBoxLayout()
        cc_hdr_row.setContentsMargins(12, 4, 12, 4)
        h1 = _make_label("栏目", bold=True); h1.setFixedWidth(120)
        cc_hdr_row.addWidget(h1)
        h2 = _make_label("正则表达式", bold=True)
        cc_hdr_row.addWidget(h2, 1)
        h3 = _make_label("状态", bold=True); h3.setFixedWidth(50)
        cc_hdr_row.addWidget(h3)
        h4 = _make_label("操作", bold=True); h4.setFixedWidth(180)
        cc_hdr_row.addWidget(h4)
        cc_lay.addLayout(cc_hdr_row)
        cc_sep = QFrame(); cc_sep.setFixedHeight(1)
        cc_sep.setStyleSheet("background: rgba(128,128,128,0.2);")
        cc_lay.addWidget(cc_sep)
        # 滚动区域放行列表
        self._ext_pat_scroll = QScrollArea()
        self._ext_pat_scroll.setWidgetResizable(True)
        self._ext_pat_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._ext_pat_scroll.setMinimumHeight(190)
        self._ext_pat_inner = QWidget()
        self._ext_pat_layout = QVBoxLayout(self._ext_pat_inner)
        self._ext_pat_layout.setContentsMargins(0, 0, 0, 0)
        self._ext_pat_layout.setSpacing(4)
        self._ext_pat_layout.addStretch()
        self._ext_pat_scroll.setWidget(self._ext_pat_inner)
        cc_lay.addWidget(self._ext_pat_scroll)
        regex_lay.addWidget(custom_card, 1)  # stretch=1，自定义区域占大空间

        # 内置正则卡片（紧凑）
        builtin_card = _make_card()
        bc_lay = QVBoxLayout(builtin_card)
        bc_lay.setContentsMargins(16, 12, 16, 12)
        bc_lay.setSpacing(8)
        bc_lay.addWidget(_make_label("内置正则规则 (只读)", bold=True))

        self._ext_builtin_tree = QTreeWidget()
        self._ext_builtin_tree.setHeaderLabels(["分类", "正则/说明"])
        bh = self._ext_builtin_tree.header()
        bh.setStretchLastSection(True)
        bh.setSectionResizeMode(0, QHeaderView.Interactive)
        self._ext_builtin_tree.setColumnWidth(0, 200)
        self._ext_builtin_tree.setRootIsDecorated(False)
        self._ext_builtin_tree.setMinimumHeight(180)
        self._ext_builtin_tree.setMaximumHeight(220)
        bc_lay.addWidget(self._ext_builtin_tree)
        regex_lay.addWidget(builtin_card)  # 无stretch，内置区域紧凑

        self._ext_stack.addWidget(regex_page)  # index 1

        # =================== 查看敏感信息子页面 ===================
        view_page = QWidget()
        view_lay = QVBoxLayout(view_page)
        view_lay.setContentsMargins(24, 12, 24, 16)
        view_lay.setSpacing(12)

        view_top_card = _make_card()
        view_top = QHBoxLayout(view_top_card)
        view_top.setContentsMargins(16, 12, 16, 12)
        view_top.setSpacing(10)
        btn_back_view = _make_btn("← 返回", lambda: self._ext_stack.setCurrentIndex(0))
        view_top.addWidget(btn_back_view)
        self._ext_view_title = _make_label("查看敏感信息", bold=True)
        view_top.addWidget(self._ext_view_title)
        view_top.addStretch()
        self._btn_ext_open_html = _make_btn("网页访问", self._ext_open_html)
        view_top.addWidget(self._btn_ext_open_html)
        view_lay.addWidget(view_top_card)

        # 结果展示区 (滚动)
        view_result_card = _make_card()
        view_result_lay = QVBoxLayout(view_result_card)
        view_result_lay.setContentsMargins(16, 12, 16, 12)
        view_result_lay.setSpacing(8)
        result_hdr = QHBoxLayout()
        result_hdr.setSpacing(8)
        result_hdr.addWidget(_make_label("扫描结果", bold=True))
        self._ext_result_count_lbl = _make_label("0 条", muted=True)
        result_hdr.addWidget(self._ext_result_count_lbl)
        self._ext_result_search_ent = _make_entry("搜索分类或结果内容...", width=240)
        self._ext_result_search_ent.textChanged.connect(self._ext_filter_result_widgets)
        result_hdr.addWidget(self._ext_result_search_ent)
        result_hdr.addStretch()
        self._btn_ext_copy_visible_results = _make_btn("复制当前", self._ext_copy_visible_results)
        self._btn_ext_copy_visible_results.setEnabled(False)
        result_hdr.addWidget(self._btn_ext_copy_visible_results)
        self._btn_ext_clear_result_search = _make_btn("清除搜索", self._ext_clear_result_search)
        self._btn_ext_clear_result_search.setEnabled(False)
        result_hdr.addWidget(self._btn_ext_clear_result_search)
        view_result_lay.addLayout(result_hdr)
        self._ext_view_scroll = QScrollArea()
        self._ext_view_scroll.setWidgetResizable(True)
        self._ext_view_scroll.setStyleSheet("QScrollArea { border: none; }")
        self._ext_view_inner = QWidget()
        self._ext_view_top_layout = QVBoxLayout(self._ext_view_inner)
        self._ext_view_top_layout.setContentsMargins(0, 0, 0, 0)
        self._ext_view_top_layout.setSpacing(0)
        self._ext_view_scroll.setWidget(self._ext_view_inner)
        view_result_lay.addWidget(self._ext_view_scroll, 1)
        view_lay.addWidget(view_result_card, 1)

        self._ext_stack.addWidget(view_page)  # index 2

        # 注册到主 stack
        self._stack.addWidget(self._ext_stack)
        self._page_map["extract"] = self._stack.count() - 1

        # 填充内置正则
        self._ext_fill_builtin_patterns()
        self._ext_refresh_custom_patterns()

        # 延迟加载小程序列表
        QTimer.singleShot(500, self._ext_refresh_apps)

        # 定时监控目录变化 (每5秒)
        self._ext_watch_timer = QTimer()
        self._ext_watch_timer.timeout.connect(self._ext_check_dir_changes)
        self._ext_watch_timer.start(5000)
        self._ext_last_appids = set()  # 上一次扫描到的 appids

        # 存储当前查看的 html path
        self._ext_current_html = ""
        self._ext_current_json = ""

    # ============================================
    # 提取页 - 辅助方法
    # ============================================

    def _ext_browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择小程序包目录", self._ext_path_ent.text())
        if d:
            self._ext_path_ent.setText(d)

    def _ext_on_path_changed(self):
        """路径变化时自动保存和刷新列表"""
        self._auto_save()
        self._ext_refresh_apps()

    def _ext_check_dir_changes(self):
        """定时检查目录是否有新的小程序包"""
        pkg_dir = self._ext_path_ent.text().strip()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            return

        # 快速扫描子目录名称
        try:
            current_dirs = set()
            for entry in os.listdir(pkg_dir):
                if os.path.isdir(os.path.join(pkg_dir, entry)):
                    current_dirs.add(entry)
        except Exception:
            return

        if current_dirs != self._ext_last_appids:
            new_ids = current_dirs - self._ext_last_appids
            self._ext_last_appids = current_dirs
            if new_ids:
                self._ext_refresh_apps()
                for nid in new_ids:
                    self._ext_log(f"检测到新小程序: {nid}")
                # 自动处理新增的小程序
                self._ext_auto_process_new(new_ids)

    def _ext_auto_detect(self):
        """自动检测默认路径"""
        from src.wxapkg import get_default_packages_dir
        default_pkg = get_default_packages_dir()
        if default_pkg:
            if self._ext_path_ent.text().strip() == default_pkg:
                self._ext_refresh_apps()
            else:
                self._ext_path_ent.setText(default_pkg)
            self._ext_log(f"已自动检测到 Applet 目录: {default_pkg}")
        else:
            hint = ("~/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
                    "app_data/radium/users/<微信用户ID>/applet/packages"
                    if sys.platform == "darwin" else
                    "未找到默认 Applet 目录")
            self._ext_log(f"未自动检测到目录，请手动选择。macOS 参考路径: {hint}"
                          if sys.platform == "darwin" else
                          f"{hint}，请手动选择")

    def _ext_auto_process_new(self, new_ids):
        """对新增的小程序自动执行反编译/扫描（按开关状态）"""
        if not self._tog_auto_dec.isChecked() and not self._tog_auto_scan.isChecked():
            return
        # 如果当前已有任务在运行，排队延迟处理
        if self._ext_current_op is not None:
            QTimer.singleShot(3000, lambda ids=set(new_ids): self._ext_auto_process_new(ids))
            return
        for appid in sorted(new_ids):
            state = self._ext_app_states.get(appid, {})
            if self._tog_auto_dec.isChecked() and not state.get("decompiled", False):
                self._ext_log(f"[自动] 开始反编译: {appid}")
                self._ext_do_decompile(appid)
                return  # 一次处理一个，完成后 _handle_ext 会触发下一步
            if self._tog_auto_scan.isChecked() and state.get("decompiled", False) and not state.get("scanned", False):
                self._ext_log(f"[自动] 开始提取: {appid}")
                self._ext_do_scan(appid)
                return

    def _ext_auto_process_pending(self):
        """遍历所有已知app，对未处理的自动执行反编译/扫描"""
        if self._ext_current_op is not None:
            return
        for appid, state in self._ext_app_states.items():
            if self._tog_auto_dec.isChecked() and not state.get("decompiled", False):
                self._ext_log(f"[自动] 开始反编译: {appid}")
                self._ext_do_decompile(appid)
                return
            if self._tog_auto_scan.isChecked() and state.get("decompiled", False) and not state.get("scanned", False):
                self._ext_log(f"[自动] 开始提取: {appid}")
                self._ext_do_scan(appid)
                return

    def _ext_log(self, msg):
        c = _TH[self._tn]
        self._ext_logbox.append(f'<span style="color:{c["text2"]}">{msg}</span>')
        sb = self._ext_logbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _ext_get_app_name(self, appid, pkgs, output_base):
        """尝试从已解包文件中读取小程序名称"""
        app_output = os.path.join(output_base, appid)
        decompile_dir = os.path.join(app_output, "decompiled")

        # 尝试从 app-config.json 读取
        for fname in ("app-config.json", "app.json"):
            cfg_path = os.path.join(decompile_dir, fname)
            if os.path.isfile(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                    # 多种可能的字段
                    name = (cfg.get("window", {}).get("navigationBarTitleText", "")
                            or cfg.get("appname", "")
                            or cfg.get("entryPagePath", ""))
                    if name:
                        return f"{name}  ({len(pkgs)}pkg)"
                except Exception:
                    pass

        return f"{len(pkgs)} pkg"

    def _ext_clear_app_rows(self):
        """清空敏感信息提取页的小程序行，并重置行缓存。"""
        while self._ext_list_layout.count() > 1:  # 保留 stretch
            item = self._ext_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._ext_app_widgets.clear()

    def _ext_refresh_apps(self):
        """刷新小程序列表，并在目录无效或无结果时同步更新空状态。"""
        pkg_dir = self._ext_path_ent.text().strip()
        self._ext_clear_app_rows()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            self._ext_status_lbl.setText("请选择有效的 Applet 目录")
            if hasattr(self, "_ext_app_count_lbl"):
                self._ext_app_count_lbl.setText("0 个")
            if hasattr(self, "_btn_ext_copy_apps"):
                self._btn_ext_copy_apps.setEnabled(False)
            if hasattr(self, "_ext_app_empty_hint"):
                self._ext_app_empty_hint.setText("请选择有效的 Applet 目录。")
                self._ext_app_empty_hint.show()
            return

        # 扫描目录
        try:
            from src.wxapkg import find_wxapkg_files
            all_pkgs = find_wxapkg_files(pkg_dir)
        except Exception as e:
            self._ext_status_lbl.setText("扫描目录失败")
            if hasattr(self, "_ext_app_count_lbl"):
                self._ext_app_count_lbl.setText("0 个")
            if hasattr(self, "_btn_ext_copy_apps"):
                self._btn_ext_copy_apps.setEnabled(False)
            if hasattr(self, "_ext_app_empty_hint"):
                self._ext_app_empty_hint.setText("扫描目录失败，请查看处理日志。")
                self._ext_app_empty_hint.show()
            self._ext_log(f"扫描目录失败: {e}")
            return

        # 按 appid 分组
        appid_groups = {}
        for pkg in all_pkgs:
            appid_groups.setdefault(pkg["appid"], []).append(pkg)

        if not appid_groups:
            self._ext_status_lbl.setText("未找到小程序")
            if hasattr(self, "_ext_app_count_lbl"):
                self._ext_app_count_lbl.setText("0 个")
            if hasattr(self, "_btn_ext_copy_apps"):
                self._btn_ext_copy_apps.setEnabled(False)
            if hasattr(self, "_ext_app_empty_hint"):
                self._ext_app_empty_hint.setText("未找到小程序。")
                self._ext_app_empty_hint.show()
            return

        c = _TH[self._tn]
        output_base = os.path.join(_BASE_DIR, "output")

        # 按最新包文件的修改时间排序，最旧的先插入，最新的最后插入到位置0因此显示在最上面
        def _appid_mtime(item):
            _, pkgs = item
            return max((os.path.getmtime(p["path"]) for p in pkgs if os.path.exists(p["path"])), default=0)

        for appid, pkgs in sorted(appid_groups.items(), key=_appid_mtime):
            row = QFrame()
            row.setStyleSheet(
                f"QFrame {{ background: {c['input']}; border-radius: 8px; }}"
                f"QFrame QLabel {{ background: transparent; }}")
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(12, 6, 12, 6)
            row_lay.setSpacing(6)

            lbl_id = QLabel(appid)
            lbl_id.setFixedWidth(180)
            lbl_id.setFont(QFont(_FM, 9))
            lbl_id.setStyleSheet(f"color: {c['text1']};")
            row_lay.addWidget(lbl_id)

            # 检查是否已解包
            app_output = os.path.join(output_base, appid)
            decompile_dir = os.path.join(app_output, "decompiled")
            result_dir = os.path.join(app_output, "result")
            is_decompiled = os.path.isdir(decompile_dir) and any(
                f.endswith(('.js', '.html', '.htm'))
                for _, _, files in os.walk(decompile_dir) for f in files
            ) if os.path.isdir(decompile_dir) else False
            is_scanned = os.path.isfile(os.path.join(result_dir, "report.json"))

            # 尝试读取小程序名称
            app_name = self._ext_get_app_name(appid, pkgs, output_base) if is_decompiled else f"{len(pkgs)} pkg (未反编译)"
            lbl_name = QLabel(app_name)
            lbl_name.setMinimumWidth(100)
            lbl_name.setFont(QFont(_FN, 9))
            lbl_name.setStyleSheet(f"color: {c['text2']};")
            row_lay.addWidget(lbl_name, 1)

            self._ext_app_states[appid] = {
                "decompiled": is_decompiled,
                "scanned": is_scanned,
                "packages": pkgs,
                "decompile_dir": decompile_dir,
                "result_dir": result_dir,
            }

            # 按钮
            btn_dec = QPushButton("反编译")
            btn_dec.setFixedWidth(60)
            btn_dec.clicked.connect(lambda _, a=appid: self._ext_do_decompile(a))
            if is_decompiled:
                btn_dec.setStyleSheet(
                    f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
            row_lay.addWidget(btn_dec)

            btn_scan = QPushButton("提取")
            btn_scan.setFixedWidth(50)
            btn_scan.setEnabled(is_decompiled)
            btn_scan.clicked.connect(lambda _, a=appid: self._ext_do_scan(a))
            row_lay.addWidget(btn_scan)

            btn_view = QPushButton("查看")
            btn_view.setFixedWidth(50)
            btn_view.setEnabled(is_scanned)
            btn_view.clicked.connect(lambda _, a=appid: self._ext_view_results(a))
            row_lay.addWidget(btn_view)

            btn_more = QPushButton("更多")
            btn_more.setFixedWidth(50)
            btn_more.clicked.connect(lambda _, a=appid, b=btn_more: self._ext_show_app_menu(a, b))
            row_lay.addWidget(btn_more)

            btn_del = QPushButton("删除")
            btn_del.setFixedWidth(50)
            btn_del.clicked.connect(lambda _, a=appid: self._ext_delete_app(a))
            btn_del.setStyleSheet(
                f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                f"QPushButton:hover {{ background: #dc2626; }}")
            row_lay.addWidget(btn_del)

            self._ext_app_widgets[appid] = {
                "row": row, "btn_dec": btn_dec, "btn_scan": btn_scan,
                "btn_view": btn_view, "btn_more": btn_more, "btn_del": btn_del,
                "lbl_name": lbl_name, "name": app_name,
            }

            # 插入在最前面（最新的在上面）
            self._ext_list_layout.insertWidget(0, row)

        self._ext_status_lbl.setText(f"发现 {len(appid_groups)} 个小程序")
        # 记录当前已知 appid 集合 (供目录监控用)
        self._ext_last_appids = set(appid_groups.keys())
        self._ext_filter_app_rows()

    def _ext_update_app_buttons(self, appid):
        """更新指定 app 的按钮状态"""
        state = self._ext_app_states.get(appid, {})
        widgets = self._ext_app_widgets.get(appid, {})
        if not widgets:
            return
        c = _TH[self._tn]
        is_dec = state.get("decompiled", False)
        is_scanned = state.get("scanned", False)

        btn_dec = widgets["btn_dec"]
        if is_dec:
            btn_dec.setStyleSheet(
                f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
        else:
            btn_dec.setStyleSheet("")

        widgets["btn_scan"].setEnabled(is_dec)
        widgets["btn_view"].setEnabled(is_scanned)

    def _ext_visible_appids(self):
        """返回当前小程序列表中可见的小程序 AppID。"""
        visible = []
        for appid, widgets in self._ext_app_widgets.items():
            row = widgets.get("row")
            if row and row.isVisible():
                visible.append(appid)
        return visible

    def _ext_filter_app_rows(self):
        """按 AppID 或显示名称过滤敏感信息提取的小程序列表。"""
        kw = self._ext_app_search_ent.text().strip().lower() if hasattr(self, "_ext_app_search_ent") else ""
        visible = 0
        total = len(self._ext_app_widgets)
        for appid, widgets in self._ext_app_widgets.items():
            name = str(widgets.get("name", ""))
            matched = not kw or kw in appid.lower() or kw in name.lower()
            row = widgets.get("row")
            if row:
                row.setVisible(matched)
            if matched:
                visible += 1
        if total:
            self._ext_status_lbl.setText(f"显示 {visible} / {total} 个小程序" if kw else f"发现 {total} 个小程序")
        if hasattr(self, "_ext_app_count_lbl"):
            self._ext_app_count_lbl.setText(f"{visible} / {total}" if kw else f"{total} 个")
        if hasattr(self, "_btn_ext_copy_apps"):
            self._btn_ext_copy_apps.setEnabled(visible > 0)
        if hasattr(self, "_ext_app_empty_hint"):
            self._ext_app_empty_hint.setText("没有匹配的小程序。" if kw else "未找到小程序。")
            self._ext_app_empty_hint.setVisible(visible == 0)

    def _ext_copy_visible_apps(self):
        """复制当前可见小程序列表的 AppID 和名称。"""
        rows = []
        for appid in self._ext_visible_appids():
            widgets = self._ext_app_widgets.get(appid, {})
            rows.append(f"{appid}\t{widgets.get('name', '')}")
        if not rows:
            self._ext_log("当前没有可复制的小程序")
            return
        QApplication.clipboard().setText("\n".join(rows))
        self._ext_log(f"已复制 {len(rows)} 个小程序")

    def _ext_copy_appid(self, appid):
        """复制小程序 AppID 到剪贴板，并写入处理日志。"""
        QApplication.clipboard().setText(appid)
        self._ext_log(f"已复制 AppID: {appid}")

    def _ext_show_app_menu(self, appid, button):
        """显示单个小程序的更多操作菜单。"""
        menu = QMenu(self)
        menu.addAction("复制 AppID", lambda: self._ext_copy_appid(appid))
        menu.addAction("打开输出目录", lambda: self._ext_open_output_dir(appid))
        state = self._ext_app_states.get(appid, {})
        result_dir = state.get("result_dir", "")
        html_path = os.path.join(result_dir, "report.html")
        if os.path.isfile(html_path):
            menu.addAction("打开 HTML 报告", lambda p=html_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
        menu.exec(button.mapToGlobal(QPoint(0, button.height())))

    def _ext_open_output_dir(self, appid):
        """打开指定小程序的输出目录，不存在时创建目录。"""
        path = os.path.join(_BASE_DIR, "output", appid)
        try:
            os.makedirs(path, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
            self._ext_log(f"已打开输出目录: {path}")
        except Exception as e:
            self._ext_log(f"打开输出目录失败: {e}")

    # ============================================
    # 提取页 - 反编译
    # ============================================

    def _ext_do_decompile(self, appid):
        if self._ext_proc:
            self._ext_log("有任务正在运行，请等待完成")
            return

        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        os.makedirs(app_output, exist_ok=True)

        pkg_dir = self._ext_path_ent.text().strip()
        worker_path = os.path.join(_BASE_DIR, "src", "extract_worker.py")
        cmd = [
            sys.executable, worker_path, "decompile",
            "--packages-dir", pkg_dir,
            "--appid", appid,
            "--output-dir", app_output,
        ]

        self._ext_log(f"开始反编译: {appid}")
        self._ext_prog.setValue(0)
        self._ext_status_lbl.setText(f"正在反编译 {appid}...")
        self._ext_current_op = ("decompile", appid)

        try:
            self._ext_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self._ext_log(f"启动失败: {e}")
            return

        self._ext_thread = threading.Thread(target=self._ext_reader, daemon=True)
        self._ext_thread.start()

    # ============================================
    # 提取页 - 敏感信息扫描
    # ============================================

    def _ext_do_scan(self, appid):
        if self._ext_proc:
            self._ext_log("有任务正在运行，请等待完成")
            return

        state = self._ext_app_states.get(appid, {})
        if not state.get("decompiled"):
            self._ext_log(f"请先反编译 {appid}")
            return

        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        decompile_dir = state.get("decompile_dir", os.path.join(app_output, "decompiled"))
        result_dir = os.path.join(app_output, "result")
        os.makedirs(result_dir, exist_ok=True)

        # 保存自定义正则
        custom_file = ""
        if self._ext_custom_patterns:
            custom_file = os.path.join(_BASE_DIR, ".extract_custom_patterns.json")
            with open(custom_file, "w", encoding="utf-8") as f:
                json.dump(self._ext_custom_patterns, f, ensure_ascii=False)

        worker_path = os.path.join(_BASE_DIR, "src", "extract_worker.py")
        cmd = [
            sys.executable, worker_path, "scan",
            "--scan-dir", decompile_dir,
            "--output-dir", result_dir,
        ]
        if custom_file:
            cmd += ["--custom-patterns", custom_file]

        self._ext_log(f"开始提取敏感信息: {appid}")
        self._ext_prog.setValue(0)
        self._ext_status_lbl.setText(f"正在扫描 {appid}...")
        self._ext_current_op = ("scan", appid)

        try:
            self._ext_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:
            self._ext_log(f"启动失败: {e}")
            return

        self._ext_thread = threading.Thread(target=self._ext_reader, daemon=True)
        self._ext_thread.start()

    # ============================================
    # 提取页 - 子进程通信
    # ============================================

    def _ext_reader(self):
        """后台线程读取子进程 stdout"""
        proc = self._ext_proc
        if not proc or not proc.stdout:
            return
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    self._ext_q.put(obj)
                except json.JSONDecodeError:
                    self._ext_q.put({"type": "log", "msg": line})
        except Exception as e:
            self._ext_q.put({"type": "log", "msg": f"读取子进程输出失败: {e}"})
        finally:
            proc.wait()
            stderr_out = ""
            if proc.stderr:
                try:
                    stderr_out = proc.stderr.read()
                except Exception:
                    pass
            if stderr_out:
                self._ext_q.put({"type": "log", "msg": f"[stderr] {stderr_out[:500]}"})
            self._ext_q.put({"type": "__done__", "returncode": proc.returncode})

    # ============================================
    # 提取页 - 查看结果
    # ============================================

    def _ext_view_results(self, appid):
        """查看敏感信息子页面 — 双列布局，仿 HTML 报告样式"""
        state = self._ext_app_states.get(appid, {})
        result_dir = state.get("result_dir", "")
        json_path = os.path.join(result_dir, "report.json")
        html_path = os.path.join(result_dir, "report.html")

        if not os.path.isfile(json_path):
            self._ext_log(f"未找到 {appid} 的扫描结果")
            return

        self._ext_current_html = html_path
        self._ext_current_json = json_path
        self._ext_view_title.setText(f"查看敏感信息 - {appid}")
        if hasattr(self, "_ext_result_search_ent"):
            self._ext_result_search_ent.blockSignals(True)
            self._ext_result_search_ent.clear()
            self._ext_result_search_ent.blockSignals(False)
        self._ext_result_widgets = []

        # 清除旧内容
        layout = self._ext_view_top_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                # 递归删除子布局
                sub = item.layout()
                while sub.count():
                    si = sub.takeAt(0)
                    sw = si.widget()
                    if sw:
                        sw.deleteLater()

        # 加载 JSON 数据
        try:
            with open(json_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            self._ext_log(f"加载结果失败: {e}")
            return

        c = _TH[self._tn]
        accent = c["accent"]  # 绿色

        cat_labels = {
            'ip': 'IP', 'ip_port': 'IP:PORT', 'domain': '域名',
            'sfz': '身份证', 'mobile': '手机号', 'mail': '邮箱',
            'jwt': 'JWT', 'algorithm': '加密算法', 'secret': 'Secret/密钥',
            'path': 'Path', 'incomplete_path': 'IncompletePath',
            'url': 'URL', 'static': 'StaticUrl'
        }
        # 反向映射: 中文标签 → 内置key
        label_to_key = {v: k for k, v in cat_labels.items()}

        left_cats = ['ip', 'ip_port', 'domain', 'sfz', 'mobile', 'mail', 'jwt', 'algorithm', 'secret']
        right_cats = ['path', 'incomplete_path', 'url', 'static']
        all_builtin = set(left_cats + right_cats)

        # 合并自定义结果到同名内置分类，去重
        merged_data = {}
        custom_only_keys = []
        for k, v in data.items():
            if k == "_meta":
                continue
            items = v if isinstance(v, list) else []
            if k in all_builtin:
                merged_data.setdefault(k, []).extend(items)
            elif k in label_to_key:
                # 自定义名称和内置中文标签相同，合并到内置分类
                builtin_key = label_to_key[k]
                merged_data.setdefault(builtin_key, []).extend(items)
            else:
                merged_data.setdefault(k, []).extend(items)
                if k not in all_builtin:
                    custom_only_keys.append(k)

        # 去重
        for k in merged_data:
            seen = set()
            deduped = []
            for item in merged_data[k]:
                s = str(item)
                if s not in seen:
                    seen.add(s)
                    deduped.append(item)
            merged_data[k] = deduped

        def _build_cat_widget(key, label, items):
            """构建单个分类的 widget — 支持展开/折叠"""
            w = QWidget()
            w.setProperty("result_label", label)
            w.setProperty("result_text", "\n".join(str(i) for i in items))
            lay = QVBoxLayout(w)
            lay.setContentsMargins(0, 8, 0, 4)
            lay.setSpacing(2)

            # 标题行: ▶ 分类名 (数量)   [复制]
            title_row = QHBoxLayout()
            title_row.setContentsMargins(0, 0, 0, 0)

            # 展开/折叠按钮
            btn_fold = QPushButton("▼")
            btn_fold.setFixedSize(20, 20)
            btn_fold.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_fold.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {c['text3']}; border: none;"
                f"font-size: 10px; padding: 0; }}"
                f"QPushButton:hover {{ color: {c['text1']}; }}")
            title_row.addWidget(btn_fold)

            title_lbl = QLabel(f"{label} ({len(items)})")
            title_lbl.setFont(QFont(_FN, 11, QFont.Weight.Bold))
            title_lbl.setStyleSheet(
                f"color: {c['text1']}; border-left: 4px solid {accent}; padding-left: 8px;"
                f"background: transparent;")
            title_row.addWidget(title_lbl)
            title_row.addStretch()

            btn_copy = QPushButton("复制")
            btn_copy.setFixedSize(48, 26)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.setStyleSheet(
                f"QPushButton {{ background: {c['input']}; color: {accent}; border: 1px solid {accent};"
                f"border-radius: 4px; font-size: 11px; padding: 2px 8px; }}"
                f"QPushButton:hover {{ background: {accent}; color: #111; }}")
            copy_text = "\n".join(str(i) for i in items)
            btn_copy.clicked.connect(lambda _, t=copy_text, b=btn_copy: self._ext_copy_cat(t, b))
            btn_copy.setEnabled(bool(items))
            if not items:
                btn_copy.setToolTip("当前分类没有可复制的结果")
            title_row.addWidget(btn_copy)
            lay.addLayout(title_row)

            # 内容区域（可折叠）
            content_widget = QWidget()
            content_lay = QVBoxLayout(content_widget)
            content_lay.setContentsMargins(0, 0, 0, 0)
            content_lay.setSpacing(0)
            if items:
                content_lbl = QLabel()
                content_lbl.setFont(QFont(_FM, 9))
                content_lbl.setWordWrap(True)
                content_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                content_lbl.setStyleSheet(
                    f"color: {c['text2']}; padding-left: 14px; background: transparent;")
                display_items = items[:200]
                lines = [str(i) for i in display_items]
                if len(items) > 200:
                    lines.append(f"... 共 {len(items)} 条，仅显示前 200 条")
                content_lbl.setText("\n".join(lines))
                content_lay.addWidget(content_lbl)
            lay.addWidget(content_widget)

            # 展开/折叠逻辑 — 默认展开
            def toggle_fold():
                visible = content_widget.isVisible()
                content_widget.setVisible(not visible)
                btn_fold.setText("▶" if visible else "▼")

            btn_fold.clicked.connect(toggle_fold)
            self._ext_result_widgets.append((w, label, [str(i) for i in items]))

            return w

        # === 双列布局 ===
        cols_widget = QWidget()
        cols_layout = QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(16)

        # 左列
        left_col = QWidget()
        left_lay = QVBoxLayout(left_col)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)
        for cat in left_cats:
            label = cat_labels.get(cat, cat)
            items = merged_data.get(cat, [])
            left_lay.addWidget(_build_cat_widget(cat, label, items))
        # 自定义规则(非同名)放左列底部
        for key in custom_only_keys:
            items = merged_data.get(key, [])
            left_lay.addWidget(_build_cat_widget(key, key, items))
        left_lay.addStretch()
        cols_layout.addWidget(left_col, 1)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(128,128,128,0.2);")
        cols_layout.addWidget(sep)

        # 右列
        right_col = QWidget()
        right_lay = QVBoxLayout(right_col)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        for cat in right_cats:
            label = cat_labels.get(cat, cat)
            items = merged_data.get(cat, [])
            right_lay.addWidget(_build_cat_widget(cat, label, items))
        right_lay.addStretch()
        cols_layout.addWidget(right_col, 1)

        layout.addWidget(cols_widget)
        self._ext_result_empty_hint = QLabel("没有匹配的扫描结果。")
        self._ext_result_empty_hint.setProperty("class", "muted")
        self._ext_result_empty_hint.setAlignment(Qt.AlignCenter)
        self._ext_result_empty_hint.hide()
        layout.addWidget(self._ext_result_empty_hint)
        layout.addStretch()
        self._ext_filter_result_widgets()

        # 切换到查看页
        self._ext_stack.setCurrentIndex(2)

    def _ext_copy_cat(self, text, btn):
        """复制分类内容并显示反馈"""
        QApplication.clipboard().setText(text)
        old = btn.text()
        btn.setText("✓")
        QTimer.singleShot(1200, lambda: btn.setText(old))

    def _ext_filter_result_widgets(self):
        """按关键字过滤敏感信息结果分类。"""
        kw = self._ext_result_search_ent.text().strip().lower() if hasattr(self, "_ext_result_search_ent") else ""
        visible = 0
        visible_items = 0
        total_items = 0
        for widget, label, items in getattr(self, "_ext_result_widgets", []):
            text = "\n".join(items).lower()
            matched = not kw or kw in label.lower() or kw in text
            widget.setVisible(matched)
            total_items += len(items)
            if matched:
                visible += 1
                visible_items += len(items)
        total = len(getattr(self, "_ext_result_widgets", []))
        if hasattr(self, "_ext_result_count_lbl"):
            if kw:
                self._ext_result_count_lbl.setText(f"{visible} / {total} 类，{visible_items} 条")
            else:
                self._ext_result_count_lbl.setText(f"{total} 类，{total_items} 条")
        if hasattr(self, "_btn_ext_copy_visible_results"):
            self._btn_ext_copy_visible_results.setEnabled(visible_items > 0)
        if hasattr(self, "_btn_ext_clear_result_search"):
            self._btn_ext_clear_result_search.setEnabled(bool(kw))
        if hasattr(self, "_ext_result_empty_hint"):
            self._ext_result_empty_hint.setVisible(visible == 0)

    def _ext_clear_result_search(self):
        """清空敏感信息结果页搜索条件。"""
        if hasattr(self, "_ext_result_search_ent"):
            self._ext_result_search_ent.clear()
        self._ext_filter_result_widgets()

    def _ext_copy_visible_results(self):
        """复制当前可见的敏感信息结果分类内容。"""
        chunks = []
        for widget, label, items in getattr(self, "_ext_result_widgets", []):
            if not widget.isVisible() or not items:
                continue
            chunks.append(f"[{label}]\n" + "\n".join(items))
        if not chunks:
            self._ext_log("当前没有可复制的扫描结果")
            return
        QApplication.clipboard().setText("\n\n".join(chunks))
        self._ext_log(f"已复制 {len(chunks)} 个分类的扫描结果")

    def _ext_open_html(self):
        """浏览器打开 HTML 报告"""
        if self._ext_current_html and os.path.isfile(self._ext_current_html):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._ext_current_html))
        else:
            self._ext_log("HTML 报告不存在")

    # ============================================
    # 提取页 - 删除
    # ============================================

    def _ext_delete_app(self, appid):
        """删除指定小程序的解包和结果"""
        import shutil
        output_base = os.path.join(_BASE_DIR, "output")
        app_output = os.path.join(output_base, appid)
        if os.path.isdir(app_output):
            try:
                shutil.rmtree(app_output)
                self._ext_log(f"已删除 {appid} 的数据")
            except Exception as e:
                self._ext_log(f"删除失败: {e}")

        # 更新状态
        if appid in self._ext_app_states:
            self._ext_app_states[appid]["decompiled"] = False
            self._ext_app_states[appid]["scanned"] = False
        self._ext_update_app_buttons(appid)
        # 如果开启了自动反编译，重新处理
        QTimer.singleShot(500, self._ext_auto_process_pending)

    def _ext_clear_decompiled(self):
        """清空所有解包文件"""
        import shutil
        output_base = os.path.join(_BASE_DIR, "output")
        if not os.path.isdir(output_base):
            return
        count = 0
        for appid in os.listdir(output_base):
            dec_dir = os.path.join(output_base, appid, "decompiled")
            if os.path.isdir(dec_dir):
                try:
                    shutil.rmtree(dec_dir)
                    count += 1
                except Exception:
                    pass
        self._ext_log(f"已清空 {count} 个小程序的解包文件")
        # 刷新状态（不触发自动处理，用户主动清空不应自动重跑）
        for appid in self._ext_app_states:
            self._ext_app_states[appid]["decompiled"] = False
            self._ext_app_states[appid]["scanned"] = False
            self._ext_update_app_buttons(appid)

    def _ext_clear_applet(self):
        """清空 Applet 目录"""
        import shutil
        pkg_dir = self._ext_path_ent.text().strip()
        if not pkg_dir or not os.path.isdir(pkg_dir):
            self._ext_log("Applet 目录不存在")
            return
        try:
            for entry in os.listdir(pkg_dir):
                full = os.path.join(pkg_dir, entry)
                if os.path.isdir(full):
                    shutil.rmtree(full)
            self._ext_log("已清空 Applet 目录")
            # 清空后重置已知 appid 集合，防止旧 appid 触发自动反编译
            self._ext_app_states.clear()
            self._ext_last_appids = set()
            self._ext_refresh_apps()
        except Exception as e:
            self._ext_log(f"清空失败: {e}")

    # ============================================
    # 提取页 - 正则管理
    # ============================================

    def _ext_goto_regex(self):
        self._ext_stack.setCurrentIndex(1)

    def _ext_fill_builtin_patterns(self):
        """填充内置正则到树"""
        from src.extractor import Extractor
        builtin = Extractor.get_all_builtin_patterns()
        self._ext_builtin_tree.clear()
        for name, pat in builtin.items():
            display = pat if len(pat) < 200 else pat[:200] + "..."
            item = QTreeWidgetItem([name, display])
            self._ext_builtin_tree.addTopLevelItem(item)

    def _ext_refresh_custom_patterns(self):
        """刷新自定义正则行列表 — 用 QFrame 行代替 QTableWidget"""
        lay = self._ext_pat_layout
        # 清除旧行(保留最后一个 stretch)
        while lay.count() > 1:
            item = lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        c = _TH[self._tn]
        for name, info in self._ext_custom_patterns.items():
            if isinstance(info, str):
                pat = info; enabled = True
            else:
                pat = info.get("regex", ""); enabled = info.get("enabled", True)
            row = QFrame()
            row.setObjectName("_ext_pat_row")
            row.setStyleSheet(
                f"QFrame#_ext_pat_row {{ background: {c['input']}; border-radius: 8px; }}"
                f"QFrame#_ext_pat_row QLabel {{ background: transparent; border: none; }}")
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(lambda pos, n=name: self._ext_pattern_ctx(pos, n))
            rl = QHBoxLayout(row)
            rl.setContentsMargins(12, 6, 12, 6)
            rl.setSpacing(6)
            lbl_n = QLabel(name)
            lbl_n.setFixedWidth(120)
            lbl_n.setFont(QFont(_FM, 9))
            lbl_n.setStyleSheet(f"color: {c['text1']};")
            rl.addWidget(lbl_n)
            lbl_p = QLabel(pat if len(pat) < 60 else pat[:60] + "...")
            lbl_p.setFont(QFont(_FM, 9))
            lbl_p.setStyleSheet(f"color: {c['text2']};")
            lbl_p.setToolTip(pat)
            lbl_p.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            rl.addWidget(lbl_p, 1)
            lbl_s = QLabel("启用" if enabled else "禁用")
            lbl_s.setFixedWidth(50)
            lbl_s.setStyleSheet(f"color: {c['success'] if enabled else c['error']};")
            rl.addWidget(lbl_s)
            btn_edit = QPushButton("修改")
            btn_edit.setFixedWidth(50)
            btn_edit.clicked.connect(lambda _, n=name: self._ext_edit_pattern(n))
            rl.addWidget(btn_edit)
            btn_toggle = QPushButton("禁用" if enabled else "启用")
            btn_toggle.setFixedWidth(50)
            if enabled:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background: {c['warning']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                    f"QPushButton:hover {{ background: #ca8a04; }}")
            else:
                btn_toggle.setStyleSheet(
                    f"QPushButton {{ background: {c['success']}; color: #111; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}")
            btn_toggle.clicked.connect(lambda _, n=name: self._ext_toggle_pattern(n))
            rl.addWidget(btn_toggle)
            btn_del = QPushButton("删除")
            btn_del.setFixedWidth(50)
            btn_del.setStyleSheet(
                f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
                f"QPushButton:hover {{ background: #dc2626; }}")
            btn_del.clicked.connect(lambda _, n=name: self._ext_delete_pattern(n))
            rl.addWidget(btn_del)
            lay.insertWidget(lay.count() - 1, row)

    def _ext_add_pattern(self):
        """新建空白行 — 用 QLineEdit 输入"""
        c = _TH[self._tn]
        row = QFrame()
        row.setObjectName("_ext_new_row")
        row.setStyleSheet(
            f"QFrame#_ext_new_row {{ background: {c['input']}; border-radius: 8px; border: 1px solid {c['accent']}; }}"
            f"QFrame#_ext_new_row QLabel {{ background: transparent; border: none; }}"
            f"QFrame#_ext_new_row QLineEdit {{ border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 6px; background: {c['card']}; color: {c['text1']}; }}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 12, 6)
        rl.setSpacing(6)
        ent_name = QLineEdit()
        ent_name.setPlaceholderText("栏目名...")
        ent_name.setFixedWidth(120)
        rl.addWidget(ent_name)
        ent_regex = QLineEdit()
        ent_regex.setPlaceholderText("正则表达式...")
        rl.addWidget(ent_regex, 1)
        lbl_s = QLabel("启用")
        lbl_s.setFixedWidth(50)
        rl.addWidget(lbl_s)
        btn_ok = QPushButton("确认")
        btn_ok.setFixedWidth(50)
        btn_ok.clicked.connect(lambda: self._ext_confirm_new(ent_name, ent_regex, row))
        rl.addWidget(btn_ok)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(50)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
            f"QPushButton:hover {{ background: #dc2626; }}")
        btn_cancel.clicked.connect(lambda: (row.deleteLater(),))
        rl.addWidget(btn_cancel)
        self._ext_pat_layout.insertWidget(self._ext_pat_layout.count() - 1, row)
        ent_name.setFocus()

    def _ext_confirm_new(self, ent_name, ent_regex, row_widget):
        """确认新建正则"""
        name = ent_name.text().strip()
        regex = ent_regex.text().strip()
        if not name or not regex:
            self._ext_log("栏目名和正则不能为空")
            return
        import re as _re
        try:
            _re.compile(regex)
        except _re.error as e:
            self._ext_log(f"正则语法错误: {e}")
            return
        self._ext_custom_patterns[name] = {"regex": regex, "enabled": True}
        row_widget.deleteLater()
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已添加规则: {name}")

    def _ext_pattern_ctx(self, pos, name):
        """右键菜单"""
        info = self._ext_custom_patterns.get(name, "")
        regex = info.get("regex", info) if isinstance(info, dict) else info
        menu = QMenu(self)
        menu.addAction("测试正则", lambda: self._ext_test_pattern(name))
        menu.addAction("复制正则", lambda: QApplication.clipboard().setText(regex))
        # 找到发送信号的 widget
        sender = self.sender()
        if sender:
            menu.exec(sender.mapToGlobal(pos))
        else:
            menu.exec(self.cursor().pos())

    def _ext_test_pattern(self, name):
        """弹窗测试正则"""
        info = self._ext_custom_patterns.get(name, "")
        regex = info.get("regex", info) if isinstance(info, dict) else info
        import re as _re
        c = _TH[self._tn]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"测试正则 - {name}")
        dlg.resize(600, 400)
        dlg.setStyleSheet(f"""
            QDialog {{ background: {c['bg']}; color: {c['text1']}; }}
            QLabel {{ color: {c['text2']}; background: transparent; }}
            QTextEdit {{
                background: {c['input']}; color: {c['text1']};
                border: 1px solid {c['border']}; border-radius: 8px;
                padding: 6px; font-family: {_FM};
            }}
            QPushButton {{
                background: {c['accent']}; color: #111;
                border-radius: 8px; padding: 8px 16px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {c['accent2']}; }}
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)

        lay.addWidget(QLabel(f"正则: {regex}"))

        input_lbl = QLabel("输入测试文本:")
        lay.addWidget(input_lbl)
        input_box = QTextEdit()
        input_box.setFont(QFont(_FM, 9))
        input_box.setPlaceholderText("在此粘贴或输入要测试的文本...")
        lay.addWidget(input_box, 1)

        result_lbl = QLabel("匹配结果:")
        lay.addWidget(result_lbl)
        result_box = QTextEdit()
        result_box.setReadOnly(True)
        result_box.setFont(QFont(_FM, 9))
        lay.addWidget(result_box, 1)

        def do_test():
            text = input_box.toPlainText()
            try:
                pat = _re.compile(regex, _re.IGNORECASE)
                matches = pat.findall(text)
                if matches:
                    if isinstance(matches[0], tuple):
                        matches = [m.group(0) for m in pat.finditer(text)]
                    result_box.setPlainText(f"找到 {len(matches)} 个匹配:\n" + "\n".join(str(m) for m in matches))
                else:
                    result_box.setPlainText("无匹配")
            except _re.error as e:
                result_box.setPlainText(f"正则错误: {e}")

        btn_test = QPushButton("测试")
        btn_test.clicked.connect(do_test)
        lay.addWidget(btn_test)
        dlg.exec()

    def _ext_edit_pattern(self, name):
        """编辑正则 — 替换该行为可编辑的 QLineEdit 行"""
        info = self._ext_custom_patterns.get(name, "")
        if isinstance(info, str):
            pat = info; enabled = True
        else:
            pat = info.get("regex", ""); enabled = info.get("enabled", True)
        c = _TH[self._tn]
        # 找到并删除原行
        lay = self._ext_pat_layout
        idx = -1
        for i in range(lay.count()):
            w = lay.itemAt(i).widget()
            if w:
                rl = w.layout()
                if rl and rl.count() > 0:
                    first = rl.itemAt(0).widget()
                    if isinstance(first, QLabel) and first.text() == name:
                        idx = i
                        w.deleteLater()
                        break
        if idx < 0:
            idx = lay.count() - 1  # before stretch
        # 创建编辑行
        row = QFrame()
        row.setObjectName("_ext_edit_row")
        row.setStyleSheet(
            f"QFrame#_ext_edit_row {{ background: {c['input']}; border-radius: 8px; border: 1px solid {c['accent']}; }}"
            f"QFrame#_ext_edit_row QLabel {{ background: transparent; border: none; }}"
            f"QFrame#_ext_edit_row QLineEdit {{ border: 1px solid {c['border']}; border-radius: 4px; padding: 4px 6px; background: {c['card']}; color: {c['text1']}; }}")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 12, 6)
        rl.setSpacing(6)
        ent_name = QLineEdit(name)
        ent_name.setFixedWidth(120)
        rl.addWidget(ent_name)
        ent_regex = QLineEdit(pat)
        rl.addWidget(ent_regex, 1)
        lbl_s = QLabel("启用" if enabled else "禁用")
        lbl_s.setFixedWidth(50)
        rl.addWidget(lbl_s)
        btn_save = QPushButton("保存")
        btn_save.setFixedWidth(50)
        btn_save.clicked.connect(lambda: self._ext_save_edit(name, ent_name, ent_regex, enabled, row))
        rl.addWidget(btn_save)
        btn_cancel = QPushButton("取消")
        btn_cancel.setFixedWidth(50)
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background: {c['error']}; color: #fff; border-radius: 6px; padding: 4px 8px; font-size: 9px; }}"
            f"QPushButton:hover {{ background: #dc2626; }}")
        btn_cancel.clicked.connect(lambda: (row.deleteLater(), self._ext_refresh_custom_patterns()))
        rl.addWidget(btn_cancel)
        lay.insertWidget(idx, row)
        ent_name.setFocus()

    def _ext_save_edit(self, old_name, ent_name, ent_regex, enabled, row_widget):
        """保存编辑后的正则"""
        new_name = ent_name.text().strip()
        new_regex = ent_regex.text().strip()
        if not new_name or not new_regex:
            self._ext_log("栏目名和正则不能为空")
            return
        import re as _re
        try:
            _re.compile(new_regex)
        except _re.error as e:
            self._ext_log(f"正则语法错误: {e}")
            return
        self._ext_custom_patterns.pop(old_name, None)
        self._ext_custom_patterns[new_name] = {"regex": new_regex, "enabled": enabled}
        row_widget.deleteLater()
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已保存规则: {new_name}")

    def _ext_toggle_pattern(self, name):
        """切换正则启用/禁用"""
        info = self._ext_custom_patterns.get(name, "")
        if isinstance(info, str):
            self._ext_custom_patterns[name] = {"regex": info, "enabled": False}
        else:
            info["enabled"] = not info.get("enabled", True)
        self._ext_refresh_custom_patterns()
        self._auto_save()

    def _ext_delete_pattern(self, name):
        self._ext_custom_patterns.pop(name, None)
        self._ext_refresh_custom_patterns()
        self._auto_save()
        self._ext_log(f"已删除规则: {name}")

    # ── 调试开关 (vConsole) ──

    def _build_vconsole(self):
        """构建调试开关页面，用于检测并切换小程序 vConsole 调试状态。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(12)
        lay.setAlignment(Qt.AlignTop)

        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # 风险警告卡片
        warn_card = _make_card()
        warn_lay = QVBoxLayout(warn_card)
        warn_lay.setContentsMargins(16, 12, 16, 12)
        warn_lay.setSpacing(8)
        warn_title = QLabel("风险提示")
        warn_title.setFont(QFont(_FN, 11, QFont.Bold))
        warn_title.setStyleSheet("color: #e6a23c;")
        warn_lay.addWidget(warn_title)
        warn_text = QLabel(
            "非正规开启小程序调试有封号风险。测试需谨慎！\n"
            "请勿在主力账号上使用，建议使用测试号操作。")
        warn_text.setWordWrap(True)
        warn_text.setStyleSheet("color: #e6a23c; font-size: 12px;")
        warn_lay.addWidget(warn_text)
        top_row.addWidget(warn_card, 1)

        # 操作卡片
        op_card = _make_card()
        op_lay = QVBoxLayout(op_card)
        op_lay.setContentsMargins(16, 12, 16, 12)
        op_lay.setSpacing(10)

        op_hdr = QHBoxLayout()
        op_hdr.addWidget(_make_label("调试状态", bold=True))
        op_hdr.addStretch()
        self._vc_status_lbl = QLabel("状态: 未连接小程序")
        self._vc_status_lbl.setProperty("class", "muted")
        op_hdr.addWidget(self._vc_status_lbl)
        op_lay.addLayout(op_hdr)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_vc_enable = _make_btn("开启调试", self._do_vc_enable)
        self._btn_vc_enable.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_vc_enable.setEnabled(False)
        btn_row.addWidget(self._btn_vc_enable)
        self._btn_vc_disable = _make_btn("关闭调试", self._do_vc_disable)
        self._btn_vc_disable.setFont(QFont(_FN, 10, QFont.Bold))
        self._btn_vc_disable.setEnabled(False)
        btn_row.addWidget(self._btn_vc_disable)
        self._btn_vc_detect = _make_btn("检测状态", self._do_vc_detect)
        self._btn_vc_detect.setEnabled(False)
        btn_row.addWidget(self._btn_vc_detect)
        self._btn_vc_copy = _make_btn("复制状态", self._copy_vc_status)
        btn_row.addWidget(self._btn_vc_copy)
        btn_row.addStretch()
        op_lay.addLayout(btn_row)
        op_tip = QLabel("连接小程序后会自动检测当前调试状态，切换结果通常需要重启小程序后完全生效。")
        op_tip.setWordWrap(True)
        op_tip.setProperty("class", "muted")
        op_lay.addWidget(op_tip)
        top_row.addWidget(op_card, 1)
        lay.addLayout(top_row)

        # 功能说明卡片
        info_card = _make_card()
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(16, 12, 16, 12)
        info_lay.setSpacing(8)
        info_lay.addWidget(_make_label("功能说明", bold=True))
        desc = QLabel(
            "通过官方 API wx.setEnableDebug 开启小程序内置的 vConsole 调试面板。"
            "开启后可在小程序内执行 JS，也可直接调试 wx.cloud.callFunction。"
            "关闭后重启小程序即可恢复正常。")
        desc.setWordWrap(True)
        desc.setProperty("class", "muted")
        info_lay.addWidget(desc)
        ref_lbl = QLabel(
            '学习文档: <a href="https://mp.weixin.qq.com/s/hTlekrCPiMJCvsHYx7CAxw">'
            '微信公众号文档</a>')
        ref_lbl.setOpenExternalLinks(True)
        ref_lbl.setStyleSheet("font-size: 11px;")
        info_lay.addWidget(ref_lbl)
        lay.addWidget(info_card)

        lay.addStretch()

        self._stack.addWidget(page)
        self._page_map["vconsole"] = self._stack.count() - 1

    def _do_vc_enable(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[调试] 请先启动调试并连接小程序")
            return
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.warning(
            self, "风险确认",
            "非正规开启小程序调试有封号风险。\n测试需谨慎！\n\n确定要开启吗？",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if r != QMessageBox.Ok:
            return
        self._btn_vc_enable.setEnabled(False)
        asyncio.run_coroutine_threadsafe(self._avc_set_debug(True), self._loop)

    def _do_vc_disable(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[调试] 请先启动调试并连接小程序")
            return
        self._btn_vc_disable.setEnabled(False)
        asyncio.run_coroutine_threadsafe(self._avc_set_debug(False), self._loop)

    def _do_vc_detect(self):
        """手动检测当前小程序 vConsole 调试状态。"""
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[调试] 请先启动调试并连接小程序")
            return
        self._vc_status_lbl.setText("状态: 正在检测...")
        self._vc_status_lbl.setProperty("class", "muted")
        self._btn_vc_detect.setEnabled(False)
        asyncio.run_coroutine_threadsafe(self._avc_detect_debug(), self._loop)

    def _copy_vc_status(self):
        """复制当前调试开关页面的状态快照到剪贴板。"""
        status = self._vc_status_lbl.text() if hasattr(self, "_vc_status_lbl") else "状态: --"
        data = {
            "vconsole": status.replace("状态:", "").strip(),
            "miniapp_connected": bool(self._miniapp_connected),
            "app_name": self._current_app_name or "",
            "appid": self._current_app_id or "",
            "cdp_port": self._cp_ent.text() if hasattr(self, "_cp_ent") else "",
            "devtools_breakpoints": "allow" if self._devtools_breakpoints_enabled() else "skip",
        }
        QApplication.clipboard().setText(json.dumps(data, ensure_ascii=False, indent=2))
        self._log_add("info", "[调试] 状态快照已复制到剪贴板")

    async def _avc_set_debug(self, enable):
        try:
            val = "true" if enable else "false"
            # 先确保 navigator 已注入，通过 wxFrame.wx 调用避免超时
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var nav=window.nav;"
                "if(!nav||!nav.wxFrame||!nav.wxFrame.wx)return JSON.stringify({err:'no wxFrame'});"
                f"nav.wxFrame.wx.setEnableDebug({{enableDebug:{val},"
                "success:function(){console.log('[First] setEnableDebug success')},"
                "fail:function(e){console.error('[First] setEnableDebug fail',e)}"
                "});"
                "return JSON.stringify({ok:true})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                import json as _json
                info = _json.loads(value)
                if info.get("err"):
                    raise RuntimeError(info["err"])
            state = "已开启" if enable else "已关闭"
            self._rte_q.put(("__vc__", enable, True))
            self._log_q.put(("info", f"[调试] vConsole {state}"))
        except Exception as e:
            self._rte_q.put(("__vc__", enable, False))
            self._log_q.put(("error", f"[调试] 操作失败: {e}"))

    async def _avc_detect_debug(self):
        """自动检测小程序是否已开启 vConsole 调试。"""
        try:
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var f=window.nav&&window.nav.wxFrame?window.nav.wxFrame:window;"
                "var c=f.__wxConfig||{};"
                "var d=!!c.debug;"
                "var v=!!(f.document&&f.document.getElementById('__vconsole'));"
                "return JSON.stringify({debug:d,vconsole:v})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                info = json.loads(value)
                if info.get("err"):
                    return
                is_debug = info.get("debug", False) or info.get("vconsole", False)
                self._rte_q.put(("__vc_detect__", is_debug))
        except Exception:
            pass

    # ── 日志 ──

    def _build_logs(self):
        """构建运行日志页面，提供调试日志开关和滚动日志输出。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(12)

        # 调试选项卡片
        dc = _make_card()
        dc_lay = QVBoxLayout(dc)
        dc_lay.setContentsMargins(16, 12, 16, 12)
        dc_lay.setSpacing(10)

        dc_hdr = QHBoxLayout()
        dc_hdr.addWidget(_make_label("调试选项", bold=True))
        dc_hdr.addStretch()
        warn_lbl = QLabel("开启后可能导致小程序卡死，请谨慎使用")
        warn_lbl.setStyleSheet("color: #fbbf24; font-size: 9px;")
        dc_hdr.addWidget(warn_lbl)
        dc_lay.addLayout(dc_hdr)

        chkr = QHBoxLayout()
        chkr.setSpacing(8)
        self._tog_dm = ToggleSwitch(self._cfg.get("debug_main", False))
        self._tog_dm.toggled.connect(lambda v: self._auto_save())
        chkr.addWidget(self._tog_dm)
        chkr.addWidget(QLabel("调试主包"))
        chkr.addSpacing(24)
        self._tog_df = ToggleSwitch(self._cfg.get("debug_frida", False))
        self._tog_df.toggled.connect(lambda v: self._auto_save())
        chkr.addWidget(self._tog_df)
        chkr.addWidget(QLabel("调试 Frida"))
        chkr.addStretch()
        dc_lay.addLayout(chkr)
        lay.addWidget(dc)

        lc = _make_card()
        lc_lay = QVBoxLayout(lc)
        lc_lay.setContentsMargins(16, 12, 16, 12)
        lc_lay.setSpacing(8)

        hdr = QHBoxLayout()
        hdr.addWidget(_make_label("日志输出", bold=True))
        hdr.addStretch()
        self._btn_copy_logs = _make_btn("复制当前", self._copy_logs)
        hdr.addWidget(self._btn_copy_logs)
        self._btn_export_logs = _make_btn("导出当前", self._export_logs)
        hdr.addWidget(self._btn_export_logs)
        self._btn_clear = _make_btn("清空", self._do_clear)
        hdr.addWidget(self._btn_clear)
        lc_lay.addLayout(hdr)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filter_row.addWidget(QLabel("筛选"))
        self._log_filter_ent = _make_entry("输入关键字过滤日志...")
        self._log_filter_ent.textChanged.connect(self._render_logbox)
        filter_row.addWidget(self._log_filter_ent, 1)
        self._log_level_combo = QComboBox()
        self._log_level_combo.addItem("全部级别", "")
        for lv, label in (
            ("info", "Info"),
            ("warn", "Warn"),
            ("error", "Error"),
            ("debug", "Debug"),
            ("frida", "Frida"),
        ):
            self._log_level_combo.addItem(label, lv)
        self._log_level_combo.currentIndexChanged.connect(self._render_logbox)
        filter_row.addWidget(self._log_level_combo)
        self._btn_clear_log_filter = _make_btn("清除筛选", self._clear_log_filter)
        self._btn_clear_log_filter.setEnabled(False)
        filter_row.addWidget(self._btn_clear_log_filter)
        self._log_autoscroll_cb = CheckMarkBox("自动滚动", self._tn)
        self._log_autoscroll_cb.setChecked(True)
        self._log_autoscroll_cb.setToolTip("勾选后日志追加时自动滚动到底部")
        filter_row.addWidget(self._log_autoscroll_cb)
        self._log_count_lbl = QLabel("0 条")
        self._log_count_lbl.setProperty("class", "muted")
        filter_row.addWidget(self._log_count_lbl)
        lc_lay.addLayout(filter_row)

        self._logbox = QTextEdit()
        self._logbox.setReadOnly(True)
        self._logbox.setPlaceholderText("启动调试、Hook、路由、云扫描和 MCP 日志会显示在这里。")
        self._logbox.setMinimumHeight(420)
        self._logbox.setFont(QFont(_FM, 9))
        lc_lay.addWidget(self._logbox)
        lay.addWidget(lc, 1)

        self._stack.addWidget(page)
        self._page_map["logs"] = self._stack.count() - 1

    def _build_faq(self):
        """构建常见问题页面，承载原控制台中的问题解决方案。"""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(24, 12, 24, 16)
        lay.setSpacing(12)

        intro_card = _make_card()
        intro_lay = QVBoxLayout(intro_card)
        intro_lay.setContentsMargins(16, 12, 16, 12)
        intro_lay.setSpacing(8)
        intro_lay.addWidget(_make_label("常见问题", bold=True))
        intro = QLabel("以下内容用于排查启动调试、Frida 连接和 DevTools 空白等常见问题。")
        intro.setProperty("class", "muted")
        intro.setWordWrap(True)
        intro_lay.addWidget(intro)
        faq_tools = QHBoxLayout()
        faq_tools.setSpacing(8)
        faq_tools.addWidget(QLabel("搜索"))
        self._faq_count_lbl = _make_label("0 / 0", muted=True)
        faq_tools.addWidget(self._faq_count_lbl)
        self._faq_search_ent = _make_entry("输入问题或解决方案关键字...")
        self._faq_search_ent.textChanged.connect(self._filter_faq_items)
        faq_tools.addWidget(self._faq_search_ent, 1)
        self._btn_open_radium_wmpf = _make_btn("打开 RadiumWMPF", self._open_radium_wmpf_dir)
        faq_tools.addWidget(self._btn_open_radium_wmpf)
        self._btn_faq_copy_all = _make_btn("复制全部", self._copy_all_faq)
        faq_tools.addWidget(self._btn_faq_copy_all)
        self._btn_faq_clear_search = _make_btn("清除搜索", self._clear_faq_search)
        faq_tools.addWidget(self._btn_faq_clear_search)
        intro_lay.addLayout(faq_tools)
        lay.addWidget(intro_card)

        self._faq_items = [
            ("Frida 连接失败", "请确认当前版本是否在 WMPF 版本区间内，如无法解决建议安装推荐版本。"),
            ("DevTools 打开内容为空", "点击启动调试前请勿打开小程序；启动调试后再次打开小程序即可。"),
            (
                "Frida 已显示连接，但小程序端显示未连接或无法断点",
                r"若操作顺序无误，建议先彻底卸载微信并重启电脑。删除路径 C:\Users\用户名\AppData\Roaming\Tencent\xwechat\XPlugin\Plugins\RadiumWMPF 下所有以数字命名的文件夹，再次重启电脑后安装微信 4.1.0.30 版本。安装完成后检查上述路径，确认文件夹编号为 16389。",
            ),
        ]

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(10)

        self._faq_cards = []
        for idx, (title, solution) in enumerate(self._faq_items, start=1):
            card = _make_card()
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(16, 12, 16, 12)
            card_lay.setSpacing(8)
            head = QHBoxLayout()
            num = QLabel(f"{idx:02d}")
            num.setFont(QFont(_FM, 10, QFont.Bold))
            num.setProperty("class", "muted")
            head.addWidget(num)
            head.addWidget(_make_label(title, bold=True))
            head.addStretch()
            btn_copy = _make_btn("复制", lambda checked=False, t=title, s=solution: self._copy_faq_item(t, s))
            head.addWidget(btn_copy)
            card_lay.addLayout(head)
            content = QLabel(solution)
            content.setProperty("class", "muted")
            content.setWordWrap(True)
            content.setTextInteractionFlags(Qt.TextSelectableByMouse)
            card_lay.addWidget(content)
            inner_lay.addWidget(card)
            self._faq_cards.append((card, title, solution))

        self._faq_empty_hint = QLabel("没有匹配的常见问题。")
        self._faq_empty_hint.setProperty("class", "muted")
        self._faq_empty_hint.setAlignment(Qt.AlignCenter)
        self._faq_empty_hint.hide()
        inner_lay.addWidget(self._faq_empty_hint)
        inner_lay.addStretch()
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        self._filter_faq_items()
        self._stack.addWidget(page)
        self._page_map["faq"] = self._stack.count() - 1

    def _filter_faq_items(self):
        """按关键字过滤常见问题卡片，并在无结果时显示空状态。"""
        kw = self._faq_search_ent.text().strip().lower() if hasattr(self, "_faq_search_ent") else ""
        visible = 0
        cards = getattr(self, "_faq_cards", [])
        for card, title, solution in cards:
            matched = not kw or kw in title.lower() or kw in solution.lower()
            card.setVisible(matched)
            if matched:
                visible += 1
        total = len(cards)
        if hasattr(self, "_faq_count_lbl"):
            self._faq_count_lbl.setText(f"{visible} / {total}" if kw else f"{total} 条")
        if hasattr(self, "_btn_faq_copy_all"):
            self._btn_faq_copy_all.setEnabled(visible > 0)
        if hasattr(self, "_btn_faq_clear_search"):
            self._btn_faq_clear_search.setEnabled(bool(kw))
        if hasattr(self, "_faq_empty_hint"):
            self._faq_empty_hint.setVisible(visible == 0)

    def _clear_faq_search(self):
        """清空常见问题搜索关键字并恢复全部条目。"""
        if hasattr(self, "_faq_search_ent"):
            self._faq_search_ent.clear()
        self._filter_faq_items()

    def _copy_faq_item(self, title, solution):
        """复制单条常见问题及其解决方案。"""
        QApplication.clipboard().setText(f"{title}\n{solution}")
        self._log_add("info", f"[FAQ] 已复制: {title}")

    def _open_radium_wmpf_dir(self):
        """打开当前用户的 RadiumWMPF 插件目录，便于查看数字版本文件夹。"""
        path = os.path.join(
            os.path.expanduser("~"),
            "AppData",
            "Roaming",
            "Tencent",
            "xwechat",
            "XPlugin",
            "Plugins",
            "RadiumWMPF",
        )
        if not os.path.isdir(path):
            self._log_add("warn", f"[FAQ] RadiumWMPF 目录不存在: {path}")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self._log_add("warn", f"[FAQ] 打开 RadiumWMPF 目录失败: {path}")
            return
        self._log_add("info", f"[FAQ] 已打开 RadiumWMPF 目录: {path}")

    def _copy_all_faq(self):
        """复制当前匹配的常见问题列表。"""
        items = []
        for card, title, solution in getattr(self, "_faq_cards", []):
            if card.isVisible():
                items.append(f"{title}\n{solution}")
        if not items:
            self._log_add("warn", "[FAQ] 当前没有可复制的问题")
            return
        QApplication.clipboard().setText("\n\n".join(items))
        self._log_add("info", f"[FAQ] 已复制 {len(items)} 条常见问题")

    # ──────────────────────────────────
    #  页面切换
    # ──────────────────────────────────

    def _show(self, pid):
        """切换右侧页面，并同步侧栏高亮和顶部页面标题。"""
        self._pg = pid
        idx = self._page_map.get(pid, 0)
        self._stack.setCurrentIndexAnimated(idx)
        title = next((name for key, _, name in _MENU if key == pid), "控制台")
        if hasattr(self, "_hdr_title"):
            self._hdr_title.setText(f"微钩 WeHook · {title}")
        self._hl_sb()

    def _open_hook_page_from_control(self):
        """从控制台快捷进入 Hook 页面，并提示脚本准备状态。"""
        self._show("hook")
        hook_dir = os.path.join(_BASE_DIR, "hook_scripts")
        has_scripts = os.path.isdir(hook_dir) and any(f.endswith(".js") for f in os.listdir(hook_dir))
        if has_scripts:
            self._log_add("info", "[Hook] 已打开 Hook 注入页面，可选择脚本执行注入")
        else:
            self._log_add("warn", "[Hook] hook_scripts/ 目录下暂无 .js 脚本")

    def _update_control_hook_button(self):
        """根据调试引擎运行状态显示或隐藏控制台 Hook 注入入口。"""
        btn = getattr(self, "_btn_control_hook", None)
        if not btn:
            return
        active = bool(self._running and self._engine and self._loop and self._loop.is_running())
        btn.setVisible(active)
        btn.setEnabled(active)

    def _header_mouse_press(self, event):
        """记录顶部栏拖拽起点，用于无边框窗口移动。"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _header_mouse_move(self, event):
        """拖动顶部栏移动窗口，最大化状态下不移动。"""
        if event.buttons() & Qt.LeftButton and self._drag_pos and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _header_mouse_double_click(self, event):
        """双击顶部栏切换最大化和还原状态。"""
        if event.button() == Qt.LeftButton:
            self._toggle_window_maximized()

    def _toggle_window_maximized(self):
        """切换主窗口最大化和普通窗口状态。"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _hl_sb(self):
        for pid, (fr, ic, nm) in self._sb_items.items():
            if pid == self._pg:
                fr.setProperty("class", "sb_item_active")
            else:
                fr.setProperty("class", "sb_item")
            fr.style().unpolish(fr)
            fr.style().polish(fr)
            if hasattr(ic, "set_state"):
                ic.set_state(pid == self._pg, self._tn)
            else:
                ic.style().unpolish(ic)
                ic.style().polish(ic)
            nm.style().unpolish(nm)
            nm.style().polish(nm)

    # ──────────────────────────────────
    #  主题
    # ──────────────────────────────────

    def _theme_origin(self, source=None, event=None):
        """计算主题扩散动画在主窗口坐标中的起点。"""
        if source is not None and event is not None:
            try:
                pos = event.position().toPoint()
            except AttributeError:
                pos = event.pos()
            return source.mapTo(self, pos)
        if hasattr(self, "_theme_wrap"):
            return self._theme_wrap.mapTo(self, self._theme_wrap.rect().center())
        return QPoint(0, self.height())

    def _apply_theme_name(self, theme):
        """切换浅色和深色主题，并刷新所有主题敏感控件。"""
        self._tn = theme
        self.setStyleSheet(build_qss(self._tn))
        self._update_theme_label()
        self._update_toggle_colors()
        self._refresh_devtools_breakpoint_status()
        self._refresh_sb_app_card()
        self._set_mcp_status("运行中" if self._mcp_running else "未启动", self._mcp_running)
        self._update_mcp_debug_status()
        self._ext_refresh_custom_patterns()
        self._render_control_logbox()
        self._render_logbox()
        self._hl_sb()
        self._update_window_buttons()
        self._auto_save()

    def _toggle_theme(self, source=None, event=None):
        """从主题按钮点击位置向外扩散切换浅色和深色主题。"""
        if getattr(self, "_theme_transitioning", False):
            return
        next_theme = "light" if self._tn == "dark" else "dark"
        origin = self._theme_origin(source, event)
        old_pixmap = self.grab()
        overlay = ThemeTransitionOverlay(old_pixmap, origin, self)
        self._theme_transitioning = True
        if hasattr(self, "_theme_wrap"):
            self._theme_wrap.setEnabled(False)

        def finish():
            """清理主题切换遮罩并恢复主题按钮状态。"""
            self._theme_transitioning = False
            if hasattr(self, "_theme_wrap"):
                self._theme_wrap.setEnabled(True)
            overlay.deleteLater()

        overlay.finished.connect(finish)
        self._apply_theme_name(next_theme)
        overlay.start()

    def _update_theme_label(self):
        """刷新侧栏主题切换胶囊中的文字、图标和提示。"""
        txt = "浅色模式" if self._tn == "light" else "深色模式"
        self._sb_theme.setText(txt)
        target = "深色模式" if self._tn == "light" else "浅色模式"
        if hasattr(self, "_theme_wrap"):
            self._theme_wrap.setToolTip(f"当前为{txt}，点击切换到{target}")
        if hasattr(self, "_sb_theme_icon"):
            self._sb_theme_icon.set_theme(self._tn)
        if hasattr(self, "_devtools_lbl"):
            c = _TH[self._tn]
            url = self._devtools_lbl.text()
            self._devtools_lbl.setStyleSheet(
                f"color: {c['accent'] if url.startswith('devtools://') else c['text3']};"
            )
        self._update_window_buttons()

    def _update_window_buttons(self):
        """刷新自定义窗口按钮的主题颜色。"""
        for btn in (getattr(self, "_win_btn_min", None),
                    getattr(self, "_win_btn_max", None),
                    getattr(self, "_win_btn_close", None)):
            if btn:
                btn.set_theme(self._tn)

    def _update_toggle_colors(self):
        """根据当前主题刷新所有开关控件的开启和关闭颜色。"""
        c = _TH[self._tn]
        for tog in (self._tog_devtools_bp, self._tog_dm, self._tog_df,
                    self._tog_auto_dec, self._tog_auto_scan):
            tog.set_colors(c["accent"], c["text4"])
        for tog in getattr(self, "_mcp_permission_toggles", {}).values():
            tog.set_colors(c["accent"], c["text4"])
        if hasattr(self, "_log_autoscroll_cb"):
            self._log_autoscroll_cb.set_theme(self._tn)

    def _refresh_sb_app_card(self):
        """主题切换时刷新顶部 Hook 目标信息条。"""
        self._update_target_badge()
        self._update_flow_steps()

    def _update_target_badge(self, connected=None):
        """刷新顶部当前 Hook 小程序、AppID、CDP 端口和连接状态。"""
        if not hasattr(self, "_target_name_lbl"):
            return
        c = _TH[self._tn]
        is_connected = self._miniapp_connected if connected is None else bool(connected)
        app_name = self._current_app_name or "未连接小程序"
        app_id = self._current_app_id or "--"
        app_name_text = app_name if len(app_name) <= 12 else f"{app_name[:11]}..."
        app_id_text = app_id if len(app_id) <= 16 else f"{app_id[:8]}...{app_id[-5:]}"
        self._target_hook_lbl.setText("Hook")
        self._target_hook_lbl.setStyleSheet(f"color: {c['success'] if is_connected else c['text3']};")
        if hasattr(self, "_target_dot"):
            self._target_dot.set_color(c["success"] if is_connected else c["text4"])
        self._target_name_lbl.setText(app_name_text)
        self._target_name_lbl.setToolTip(app_name)
        self._target_appid_lbl.setText(f"AppID {app_id_text}")
        self._target_appid_lbl.setToolTip(app_id)
        self._target_cdp_lbl.setText(f"CDP :{self._cp_ent.text() if hasattr(self, '_cp_ent') else '--'}")
        self._target_status_lbl.setText("已连接" if is_connected else "未连接")
        self._target_status_lbl.setStyleSheet(
            f"color: {c['success'] if is_connected else c['text3']};"
            f"background: {'#183527' if self._tn == 'dark' and is_connected else '#263044' if self._tn == 'dark' else '#eaf7ef' if is_connected else '#f3f6fb'};"
            "border-radius: 10px; padding: 2px 10px; font-size: 10px; font-weight: bold;"
        )
        self._target_badge.setToolTip(
            f"当前目标: {app_name}\nAppID: {app_id}\nCDP 端口: {self._target_cdp_lbl.text()}\n"
            f"状态: {'已连接' if is_connected else '未连接'}\n点击复制目标信息"
        )

    def _copy_target_summary(self):
        """复制顶部当前 Hook 目标摘要，便于反馈调试状态。"""
        app_name = self._current_app_name or "未连接小程序"
        app_id = self._current_app_id or "--"
        cdp_port = self._cp_ent.text() if hasattr(self, "_cp_ent") else "--"
        status = self._target_status_lbl.text() if hasattr(self, "_target_status_lbl") else "未连接"
        text = "\n".join([
            f"软件: 微钩 WeHook",
            f"当前目标: {app_name}",
            f"AppID: {app_id}",
            f"CDP 端口: {cdp_port}",
            f"连接状态: {status}",
        ])
        QApplication.clipboard().setText(text)
        self._log_add("info", "[GUI] 已复制当前 Hook 目标信息")

    def _update_flow_steps(self, sts=None):
        """根据调试运行状态刷新控制台流程提示中的步骤圆点。"""
        if not hasattr(self, "_flow_stepper"):
            return
        current = sts or self._last_sts or {}
        states = {
            "start": bool(self._running),
            "miniapp": bool(self._miniapp_connected or current.get("miniapp")),
            "hook": bool(self._hook_injected),
            "devtools": bool(current.get("devtools")),
        }
        self._flow_stepper.set_states(states, self._tn)

    def _auto_save(self):
        """保存 GUI 的主题、调试开关、提取配置和 MCP 权限配置。"""
        data = {
            "theme": self._tn,
            "cdp_port": self._cp_ent.text(),
            "allow_devtools_breakpoints": self._devtools_breakpoints_enabled(),
            "debug_main": self._tog_dm.isChecked(),
            "debug_frida": self._tog_df.isChecked(),
            "extract_packages_dir": self._ext_path_ent.text(),
            "extract_custom_patterns": dict(self._ext_custom_patterns),
            "auto_decompile": self._tog_auto_dec.isChecked(),
            "auto_scan": self._tog_auto_scan.isChecked(),
            "global_hook_scripts": list(self._global_hook_scripts),
            "mcp_endpoint": self._mcp_endpoint,
            "mcp_permissions": dict(self._mcp_permissions),
        }
        _save_cfg(data)

    def _mcp_client_config(self):
        """Build the client-side MCP configuration shown in the GUI."""
        return json.dumps({
            "mcpServers": {
                "first-debugger": {
                    "url": self._mcp_endpoint
                }
            }
        }, indent=2, ensure_ascii=False)

    def _set_mcp_status(self, text, running):
        """Update MCP status labels and service control button states."""
        self._mcp_running = running
        if not hasattr(self, "_mcp_status_lbl"):
            return
        c = _TH[self._tn]
        self._mcp_status_lbl.setText(f"MCP: {text}")
        self._mcp_status_lbl.setStyleSheet(f"color: {c['success'] if running else c['text2']};")
        self._mcp_status_dot.set_color(c["success"] if running else c["text4"])
        self._btn_mcp_start.setEnabled(not running)
        self._btn_mcp_stop.setEnabled(running)
        self._btn_mcp_restart.setEnabled(running)
        if hasattr(self, "_control_mcp_status_lbl"):
            self._control_mcp_status_lbl.setText(f"MCP: {text}")
            self._control_mcp_status_lbl.setStyleSheet(f"color: {c['success'] if running else c['text2']};")

    def _mcp_add_log(self, text):
        """Append one MCP log line to the MCP page log box."""
        if not hasattr(self, "_mcp_logbox"):
            return
        self._mcp_logbox.append(text)
        sb = self._mcp_logbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _mcp_target_label(self, item):
        """Build one compact display label for a JS runtime target."""
        name = str(item.get("jscontext_name", "") or "").strip() or "(unnamed)"
        kind = str(item.get("kind", "unknown") or "unknown")
        ctx_id = str(item.get("jscontext_id", "") or "")
        parts = [name, kind]
        if ctx_id:
            parts.append(ctx_id[:12])
        if item.get("recommended"):
            parts.append("recommended")
        if item.get("connected"):
            parts.append("active")
        return " | ".join(parts)

    def _mcp_target_empty_hint(self):
        """Return a specific UI hint when no selectable JS runtime target is advertised."""
        if self._engine:
            diag = self._engine.get_js_context_diagnostics()
            state = diag.get("state", "")
            if state == "default_runtime_without_ids":
                return "已连接，当前运行时未暴露可选 JS Context"
            if state == "miniapp_disconnected":
                return "未连接小程序"
            if state == "waiting_for_contexts":
                return "等待小程序上报 JS Context"
        return "未发现 JS Context"

    def _refresh_mcp_target_combo(self, contexts):
        """Refresh the MCP target combo box from the latest JS context snapshot."""
        self._mcp_targets = list(contexts or [])
        if not hasattr(self, "_mcp_target_combo"):
            return
        selected_id = next(
            (ctx.get("jscontext_id", "") for ctx in self._mcp_targets if ctx.get("selected")),
            "",
        )
        self._mcp_target_syncing = True
        try:
            combo = self._mcp_target_combo
            combo.clear()
            combo.addItem("自动选择（推荐）", "")
            target_index = 0
            for idx, item in enumerate(self._mcp_targets, start=1):
                combo.addItem(self._mcp_target_label(item), item.get("jscontext_id", ""))
                if item.get("jscontext_id", "") == selected_id:
                    target_index = idx
            combo.setCurrentIndex(target_index)
        finally:
            self._mcp_target_syncing = False

        if not self._mcp_targets:
            self._mcp_target_hint_lbl.setText(self._mcp_target_empty_hint())
        else:
            selected = next((ctx for ctx in self._mcp_targets if ctx.get("selected")), None)
            recommended = next((ctx for ctx in self._mcp_targets if ctx.get("recommended")), None)
            current = selected or recommended or self._mcp_targets[0]
            hint = current.get("jscontext_name", "") or current.get("jscontext_id", "") or "unknown"
            self._mcp_target_hint_lbl.setText(f"当前: {hint}")

    def _on_mcp_target_changed(self, index):
        """Apply one manually selected MCP JS runtime target."""
        if self._mcp_target_syncing:
            return
        if not self._engine or not self._loop or not self._loop.is_running():
            return
        target_id = self._mcp_target_combo.itemData(index) if hasattr(self, "_mcp_target_combo") else ""
        asyncio.run_coroutine_threadsafe(self._engine.activate_js_context(target_id), self._loop)

    def _set_mcp_permission(self, key, enabled):
        """Persist a changed MCP permission and record the change in the log."""
        self._mcp_permissions[key] = bool(enabled)
        label = next((name for k, name, _ in _MCP_PERMISSIONS if k == key), key)
        self._mcp_add_log(f"权限变更: {label} -> {'允许' if enabled else '禁止'}")
        self._auto_save()

    def _copy_mcp_permissions(self):
        """复制当前 MCP 权限配置，包含权限键名、显示名称和启用状态。"""
        data = [
            {
                "key": key,
                "label": label,
                "enabled": bool(self._mcp_permissions.get(key, default)),
            }
            for key, label, default in _MCP_PERMISSIONS
        ]
        QApplication.clipboard().setText(json.dumps(data, ensure_ascii=False, indent=2))
        self._mcp_add_log("已复制 MCP 权限配置")
        self._log_add("info", "[MCP] 权限配置已复制到剪贴板")

    def _reset_mcp_permissions(self):
        """将 MCP 权限恢复为内置默认值，并同步刷新所有开关控件。"""
        self._mcp_permissions = {key: default for key, _, default in _MCP_PERMISSIONS}
        for key, toggle in self._mcp_permission_toggles.items():
            toggle.blockSignals(True)
            toggle.setChecked(bool(self._mcp_permissions.get(key, False)))
            toggle.blockSignals(False)
        self._mcp_add_log("MCP 权限已恢复默认配置")
        self._log_add("info", "[MCP] 权限已恢复默认配置")
        self._auto_save()

    def _mcp_has_permission(self, key):
        """Return whether a named MCP capability is enabled."""
        return bool(self._mcp_permissions.get(key, False))

    def _mcp_auto_breakpoint_enabled(self):
        """Return whether MCP automatic breakpoint workflows are allowed."""
        return self._mcp_has_permission("auto_breakpoint")

    def _mcp_has_active_breakpoints(self):
        """Return whether the current debugger state should preserve existing breakpoints."""
        return bool(
            self._mcp_breakpoints or
            self._mcp_pause_state or
            self._devtools_breakpoints_enabled()
        )

    def _mcp_permission_log_name(self, key):
        """格式化 MCP 权限名，并附带中文作用说明供日志展示。"""
        label = next((name for name_key, name, _ in _MCP_PERMISSIONS if name_key == key), "")
        return f"{key}（{label}）" if label else str(key)

    def _mcp_check_permission(self, key):
        """Check a named MCP capability and log denied attempts."""
        allowed = self._mcp_has_permission(key)
        if not allowed:
            self._mcp_add_log(f"权限拒绝: {self._mcp_permission_log_name(key)}")
        return allowed

    def _mcp_require_permission(self, key):
        """Thread-safe permission check used by MCP tool handlers."""
        allowed = self._mcp_has_permission(key)
        if not allowed:
            self._mcp_q.put(("log", f"权限拒绝: {self._mcp_permission_log_name(key)}"))
        return allowed

    def _clear_mcp_log(self):
        """Clear the MCP page log box."""
        if hasattr(self, "_mcp_logbox"):
            self._mcp_logbox.clear()

    def _copy_mcp_log(self):
        """复制 MCP 页面当前日志文本到剪贴板。"""
        box = getattr(self, "_mcp_logbox", None)
        text = box.toPlainText().strip() if box else ""
        if not text:
            self._mcp_add_log("当前没有可复制的 MCP 日志")
            return
        QApplication.clipboard().setText(text)
        self._mcp_add_log("已复制 MCP 日志")
        self._log_add("info", "[MCP] MCP 日志已复制到剪贴板")

    def _copy_mcp_address(self):
        """Copy the configured MCP endpoint URL to the clipboard."""
        QApplication.clipboard().setText(self._mcp_endpoint)
        self._mcp_add_log(f"已复制 MCP 地址: {self._mcp_endpoint}")
        self._log_add("info", "[MCP] MCP 地址已复制到剪贴板")

    def _copy_mcp_config(self):
        """Copy the external client configuration snippet to the clipboard."""
        cfg = self._mcp_client_config()
        QApplication.clipboard().setText(cfg)
        self._mcp_add_log("已复制 MCP 客户端配置")
        self._log_add("info", "[MCP] 客户端配置已复制到剪贴板")

    def _do_mcp_start(self):
        """Start the local MCP HTTP skeleton service from the GUI."""
        if self._mcp_service and self._mcp_service.is_running:
            return
        try:
            parsed = urlparse(self._mcp_endpoint)
            if parsed.scheme != "http" or not parsed.hostname:
                raise ValueError("MCP 地址必须是 http://host:port/path 格式")
            host = parsed.hostname or "127.0.0.1"
            if host not in ("127.0.0.1", "localhost"):
                raise ValueError("MCP 服务仅允许监听 127.0.0.1 或 localhost")
            port = parsed.port or 8765
            path = parsed.path or "/mcp"
            runtime = McpRuntime(
                context_getter=self._mcp_context_snapshot,
                permission_checker=self._mcp_has_permission,
                tool_handler=self._mcp_call_tool,
                log_callback=lambda msg: self._mcp_q.put(("log", msg)),
            )
            self._mcp_service = McpHttpService(runtime, host=host, port=port, path=path)
            self._mcp_service.start()
            self._set_mcp_status("运行中", True)
            self._mcp_add_log(f"启动 MCP: {self._mcp_endpoint}")
            self._log_add("info", f"[MCP] 服务已启动: {self._mcp_endpoint}")
        except Exception as e:
            self._mcp_service = None
            self._set_mcp_status("异常", False)
            self._mcp_add_log(f"启动失败: {e}")
            self._log_add("error", f"[MCP] 启动失败: {e}")

    def _do_mcp_stop(self):
        """Stop the local MCP HTTP skeleton service from the GUI."""
        if self._mcp_service:
            try:
                self._mcp_service.stop()
            except Exception as e:
                self._mcp_add_log(f"停止异常: {e}")
                self._log_add("error", f"[MCP] 停止异常: {e}")
            finally:
                self._mcp_service = None
        self._set_mcp_status("未启动", False)
        self._mcp_add_log("停止 MCP：服务已停止。")
        self._log_add("info", "[MCP] MCP 控制台已停止")

    def _do_mcp_restart(self):
        """Restart the local MCP HTTP skeleton service."""
        self._mcp_add_log("重启 MCP：正在重启本地服务。")
        self._do_mcp_stop()
        self._do_mcp_start()

    def _update_mcp_debug_status(self, sts=None):
        """Refresh debugger status fields on the MCP page."""
        if not hasattr(self, "_mcp_frida_lbl"):
            return
        c = _TH[self._tn]
        sts = sts or (self._engine.status if self._engine else {})
        items = [
            ("frida", self._mcp_frida_lbl, "Frida"),
            ("miniapp", self._mcp_miniapp_lbl, "MiniApp"),
            ("devtools", self._mcp_devtools_lbl, "CDP"),
        ]
        for key, lbl, name in items:
            on = sts.get(key, False)
            lbl.setText(f"{name}: {'已连接' if on else '未连接'}")
            lbl.setStyleSheet(f"color: {c['success'] if on else c['text2']};")
        self._mcp_app_lbl.setText(f"AppID: {self._mcp_appid or '--'}")
        self._mcp_route_lbl.setText(f"当前路由: /{self._mcp_route}" if self._mcp_route else "当前路由: --")

    def _mcp_context_snapshot(self):
        """Build a lightweight state snapshot returned by the MCP service."""
        sts = self._engine.status if self._engine else {}
        selected_target = self._engine.get_selected_js_context() if self._engine else {}
        debug_context = self._engine.get_debug_context_summary() if self._engine else {}
        target_diagnostics = self._engine.get_js_context_diagnostics() if self._engine else {}
        return {
            "ok": True,
            "debug_running": self._running,
            "frida": bool(sts.get("frida", False)),
            "miniapp": bool(sts.get("miniapp", False)),
            "devtools": bool(sts.get("devtools", False)),
            "appid": self._mcp_appid,
            "route": self._mcp_route,
            "selected_target": selected_target,
            "target_count": len(self._engine.list_js_contexts()) if self._engine else 0,
            "target_diagnostics": target_diagnostics,
            "recent_debug_categories": debug_context.get("recent_debug_categories", []),
            "last_observed_jscontext_id": debug_context.get("last_observed_jscontext_id", ""),
            "connected_jscontext_id": debug_context.get("connected_jscontext_id", ""),
            "permissions": dict(self._mcp_permissions),
        }

    def _mcp_tool_log_name(self, name):
        """格式化 MCP 工具名，并附带中文作用说明供日志展示。"""
        summary = _MCP_TOOL_SUMMARIES.get(name, "")
        return f"{name}（{summary}）" if summary else str(name)

    def _mcp_call_tool(self, name, arguments):
        """Handle basic MCP tools from the HTTP service thread."""
        self._mcp_q.put(("log", f"调用工具: {self._mcp_tool_log_name(name)}"))
        if name == "get_status":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            return self._mcp_context_snapshot()
        if name == "evaluate_js":
            if not self._mcp_require_permission("execute_js"):
                return {"ok": False, "error": "permission denied: execute_js"}
            expression = str(arguments.get("expression", "")).strip()
            if not expression:
                return {"ok": False, "error": "missing expression"}
            timeout = max(0.5, min(float(arguments.get("timeout", 5.0) or 5.0), 15.0))
            return self._mcp_tool_evaluate_js(expression, timeout)
        if name == "list_routes":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            return {
                "ok": True,
                "routes": list(self._all_routes),
                "tab_bar_routes": list(self._navigator.tab_bar_pages if self._navigator else []),
            }
        if name == "get_current_route":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            return self._mcp_tool_get_current_route()
        if name == "navigate_route":
            if not self._mcp_require_permission("navigate_page"):
                return {"ok": False, "error": "permission denied: navigate_page"}
            route = str(arguments.get("route", "")).strip().lstrip("/")
            if not route:
                return {"ok": False, "error": "missing route"}
            return self._mcp_tool_navigate_route(route)
        if name == "start_capture":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            return self._mcp_tool_start_capture()
        if name == "stop_capture":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            return self._mcp_tool_stop_capture()
        if name == "get_recent_requests":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            try:
                limit = int(arguments.get("limit", 50) or 50)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid limit"}
            return self._mcp_tool_get_recent_requests(limit)
        if name == "clear_requests":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            return self._mcp_tool_clear_requests()
        if name == "get_capture_state":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            return self._mcp_tool_get_capture_state()
        if name == "get_recent_cloud_calls":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            try:
                limit = int(arguments.get("limit", 50) or 50)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid limit"}
            return self._mcp_tool_get_recent_cloud_calls(limit)
        if name == "clear_cloud_calls":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            return self._mcp_tool_clear_cloud_calls()
        if name == "list_targets":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            return self._mcp_tool_list_targets()
        if name == "get_selected_target":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            return self._mcp_tool_get_selected_target()
        if name == "select_target":
            if not self._mcp_require_permission("read_status"):
                return {"ok": False, "error": "permission denied: read_status"}
            jscontext_id = str(arguments.get("jscontext_id", "") or "").strip()
            if not jscontext_id:
                return {"ok": False, "error": "missing jscontext_id"}
            return self._mcp_tool_select_target(jscontext_id)
        if name == "list_runtime_scripts":
            if not self._mcp_require_permission("read_scripts"):
                return {"ok": False, "error": "permission denied: read_scripts"}
            wait_seconds = self._mcp_number_arg(arguments, "wait_seconds", 1.5, 0.2, 3.0)
            limit = int(self._mcp_number_arg(arguments, "limit", 200, 1, 500))
            return self._mcp_tool_list_runtime_scripts(wait_seconds, limit)
        if name == "get_runtime_script_source":
            if not self._mcp_require_permission("read_scripts"):
                return {"ok": False, "error": "permission denied: read_scripts"}
            script_id = str(arguments.get("script_id", "")).strip()
            if not script_id:
                return {"ok": False, "error": "missing script_id"}
            offset = int(self._mcp_number_arg(arguments, "offset", 0, 0, 10000000))
            max_chars = int(self._mcp_number_arg(arguments, "max_chars", 20000, 1, 100000))
            return self._mcp_tool_get_runtime_script_source(script_id, offset, max_chars)
        if name == "set_auto_breakpoint":
            script_id = str(arguments.get("script_id", "") or "").strip()
            url = str(arguments.get("url", "") or "").strip()
            if not script_id and not url:
                return {"ok": False, "error": "missing script_id or url"}
            try:
                line_number = int(arguments.get("line_number", 0) or 0)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid line_number"}
            if line_number < 1:
                return {"ok": False, "error": "line_number must be >= 1"}
            column_number = int(self._mcp_number_arg(arguments, "column_number", 0, 0, 1000000))
            condition = str(arguments.get("condition", "") or "")
            return self._mcp_tool_set_auto_breakpoint(
                script_id, url, line_number, column_number, condition)
        if name == "wait_for_pause":
            timeout = self._mcp_number_arg(arguments, "timeout", 20.0, 0.1, 120.0)
            return self._mcp_tool_wait_for_pause(timeout, arguments.get("since_pause_seq"))
        if name == "resume_execution":
            mode = str(arguments.get("mode", "resume") or "resume")
            return self._mcp_tool_resume_execution(mode)
        if name == "remove_breakpoint":
            breakpoint_id = str(arguments.get("breakpoint_id", "") or "").strip()
            if not breakpoint_id:
                return {"ok": False, "error": "missing breakpoint_id"}
            return self._mcp_tool_remove_breakpoint(breakpoint_id)
        if name == "search_runtime_scripts":
            if not self._mcp_require_permission("read_scripts"):
                return {"ok": False, "error": "permission denied: read_scripts"}
            query = str(arguments.get("query", "")).strip()
            if not query:
                return {"ok": False, "error": "missing query"}
            case_sensitive = bool(arguments.get("case_sensitive", False))
            max_results = int(self._mcp_number_arg(arguments, "max_results", 30, 1, 100))
            max_scripts = int(self._mcp_number_arg(arguments, "max_scripts", 200, 1, 300))
            context_chars = int(self._mcp_number_arg(arguments, "context_chars", 100, 0, 300))
            return self._mcp_tool_search_runtime_scripts(
                query, case_sensitive, max_results, max_scripts, context_chars)
        if name == "inspect_request_parameters":
            if not self._mcp_require_permission("read_requests"):
                return {"ok": False, "error": "permission denied: read_requests"}
            request_id = arguments.get("request_id")
            try:
                request_id = int(request_id) if request_id not in (None, "") else None
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid request_id"}
            limit = int(self._mcp_number_arg(arguments, "limit", 50, 1, 200))
            return self._mcp_tool_inspect_request_parameters(request_id, limit)
        if name == "trace_parameter_logic":
            if not self._mcp_require_permission("read_scripts"):
                return {"ok": False, "error": "permission denied: read_scripts"}
            param_name = str(arguments.get("param_name", "") or "").strip()
            sample_value = str(arguments.get("sample_value", "") or "").strip()
            if not param_name and not sample_value:
                return {"ok": False, "error": "missing param_name or sample_value"}
            max_scripts = int(self._mcp_number_arg(arguments, "max_scripts", 200, 1, 300))
            max_results = int(self._mcp_number_arg(arguments, "max_results", 30, 1, 100))
            context_chars = int(self._mcp_number_arg(arguments, "context_chars", 160, 40, 500))
            return self._mcp_tool_trace_parameter_logic(
                param_name, sample_value, max_scripts, max_results, context_chars)
        if name == "find_crypto_candidates":
            if not self._mcp_require_permission("read_scripts"):
                return {"ok": False, "error": "permission denied: read_scripts"}
            max_scripts = int(self._mcp_number_arg(arguments, "max_scripts", 200, 1, 300))
            max_results = int(self._mcp_number_arg(arguments, "max_results", 40, 1, 100))
            context_chars = int(self._mcp_number_arg(arguments, "context_chars", 180, 40, 500))
            return self._mcp_tool_find_crypto_candidates(max_scripts, max_results, context_chars)
        return {"ok": False, "error": f"unknown tool: {name}"}

    def _mcp_require_runtime(self):
        """Return an error string when the debug runtime is not ready."""
        if not self._engine or not self._navigator or not self._loop or not self._loop.is_running():
            return "debug engine not started"
        return ""

    def _mcp_require_auto_breakpoint(self):
        """Return an error string when MCP automatic breakpoint capability is unavailable."""
        if not self._mcp_require_permission("auto_breakpoint"):
            return "permission denied: auto_breakpoint"
        reason = self._mcp_require_runtime()
        return reason

    def _mcp_require_auto_breakpoint_pause_mode(self):
        """Return an error string when automatic breakpoint pause mode is not ready."""
        reason = self._mcp_require_auto_breakpoint()
        if reason:
            return reason
        if not self._devtools_breakpoints_enabled():
            return "devtools breakpoints disabled"
        return ""

    def _mcp_clear_pause_state(self):
        """Clear the cached paused debugger snapshot used by MCP auto breakpoint tools."""
        with self._mcp_pause_cv:
            self._mcp_pause_state = None
            self._mcp_pause_cv.notify_all()

    def _mcp_reset_runtime_script_cache(self):
        """Clear cached runtime script metadata collected from previous MCP inspections."""
        self._mcp_runtime_scripts = {}

    def _mcp_detach_breakpoint_listeners(self):
        """Detach cached Debugger pause listeners from the current engine when present."""
        engine = self._mcp_breakpoint_engine
        if engine and self._mcp_breakpoint_listener_attached:
            try:
                engine.off_cdp_event("Debugger.paused", self._mcp_on_debugger_paused)
            except Exception:
                pass
            try:
                engine.off_cdp_event("Debugger.resumed", self._mcp_on_debugger_resumed)
            except Exception:
                pass
        self._mcp_breakpoint_engine = None
        self._mcp_breakpoint_listener_attached = False
        self._mcp_breakpoints = {}
        self._mcp_wait_pause_since_seq = None
        self._mcp_clear_pause_state()

    def _mcp_attach_breakpoint_listeners(self):
        """Ensure Debugger pause listeners are attached to the active debug engine once."""
        if not self._engine:
            raise RuntimeError("debug engine not started")
        if self._mcp_breakpoint_engine is self._engine and self._mcp_breakpoint_listener_attached:
            return
        self._mcp_detach_breakpoint_listeners()
        self._engine.on_cdp_event("Debugger.paused", self._mcp_on_debugger_paused)
        self._engine.on_cdp_event("Debugger.resumed", self._mcp_on_debugger_resumed)
        self._mcp_breakpoint_engine = self._engine
        self._mcp_breakpoint_listener_attached = True

    def _mcp_call_frame_snapshot(self, frame):
        """Build a compact call frame snapshot from a Debugger.paused event frame."""
        location = frame.get("location", {}) if isinstance(frame, dict) else {}
        script_id = str(frame.get("scriptId", "") or "") if isinstance(frame, dict) else ""
        meta = self._mcp_runtime_scripts.get(script_id, {})
        url = ""
        if isinstance(frame, dict):
            url = str(frame.get("url", "") or "")
        if not url:
            url = str(meta.get("url", "") or "")
        return {
            "function_name": str(frame.get("functionName", "") or "(anonymous)") if isinstance(frame, dict) else "(unknown)",
            "script_id": script_id,
            "url": url,
            "line_number": int(location.get("lineNumber", 0) or 0) + 1,
            "column_number": int(location.get("columnNumber", 0) or 0) + 1,
        }

    def _mcp_pause_snapshot(self):
        """Return a shallow copy of the current paused debugger snapshot for MCP callers."""
        with self._mcp_pause_cv:
            return dict(self._mcp_pause_state) if self._mcp_pause_state else None

    def _mcp_on_debugger_paused(self, data):
        """Cache the latest Debugger.paused event so MCP callers can wait on it."""
        params = data.get("params", {}) if isinstance(data, dict) else {}
        call_frames = params.get("callFrames", []) if isinstance(params, dict) else []
        frames = [self._mcp_call_frame_snapshot(frame) for frame in call_frames[:20]]
        top = frames[0] if frames else {}
        with self._mcp_pause_cv:
            self._mcp_pause_seq += 1
            self._mcp_pause_state = {
                "pause_seq": self._mcp_pause_seq,
                "reason": str(params.get("reason", "") or ""),
                "hit_breakpoints": list(params.get("hitBreakpoints", []) or []),
                "call_frames": frames,
                "top_frame": dict(top),
            }
            self._mcp_pause_cv.notify_all()
        if top:
            self._mcp_q.put((
                "log",
                f"自动断点命中: {top.get('url', '--')}:{top.get('line_number', 0)}"
            ))
        else:
            self._mcp_q.put(("log", "自动断点命中: 当前运行时已暂停"))

    def _mcp_on_debugger_resumed(self, _data):
        """Clear cached pause state after the runtime resumes from a debugger stop."""
        self._mcp_clear_pause_state()
        self._mcp_q.put(("log", "自动断点继续执行"))

    def _mcp_number_arg(self, arguments, key, default, min_value, max_value):
        """Read a numeric MCP argument and clamp it to a bounded range."""
        try:
            value = float(arguments.get(key, default))
        except (TypeError, ValueError):
            value = float(default)
        return max(float(min_value), min(value, float(max_value)))

    def _mcp_run_coro(self, coro, timeout):
        """Run a coroutine on the debugger event loop from the MCP HTTP thread."""
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def _mcp_tool_evaluate_js(self, expression, timeout):
        """Execute JavaScript through DebugEngine.evaluate_js for MCP callers."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._engine.evaluate_js(expression, timeout=timeout), timeout + 1.0)
            inner = result.get("result", {}).get("result", {}) if isinstance(result, dict) else {}
            return {"ok": True, "value": inner.get("value"), "raw": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_current_route(self):
        """Read the current miniapp route through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            route = self._mcp_run_coro(self._navigator.get_current_route(), 5.0)
            return {"ok": True, "route": route}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_navigate_route(self, route):
        """Navigate to a miniapp route through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            self._mcp_run_coro(self._navigator.navigate_to(route), 6.0)
            return {"ok": True, "route": route}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_start_capture(self):
        """Enable request capture through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._navigator.start_capture(), 6.0)
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_stop_capture(self):
        """Disable request capture through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._navigator.stop_capture(), 6.0)
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_recent_requests(self, limit):
        """Read recent captured request rows through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        limit = max(1, min(int(limit or 50), 200))
        try:
            rows = self._mcp_run_coro(self._navigator.get_recent_requests(limit), 6.0)
            return {"ok": True, "requests": rows, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_clear_requests(self):
        """Clear captured request rows through MiniProgramNavigator."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._navigator.clear_captured_requests(), 6.0)
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_capture_state(self):
        """Inspect current navigator and request-hook state on the selected runtime target."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            state = self._mcp_run_coro(self._navigator.get_capture_state(), 6.0)
            return state if isinstance(state, dict) else {"ok": False, "error": "capture state unavailable"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_recent_cloud_calls(self, limit):
        """Read recent captured cloud, database, storage, or container calls."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        if not self._auditor:
            return {"ok": False, "error": "cloud auditor not available"}
        limit = max(1, min(int(limit or 50), 200))
        try:
            rows = self._mcp_run_coro(self._auditor.get_recent_calls(limit), 8.0)
            return {"ok": True, "calls": rows, "count": len(rows)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_clear_cloud_calls(self):
        """Clear captured cloud, database, storage, and container call records."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        if not self._auditor:
            return {"ok": False, "error": "cloud auditor not available"}
        try:
            result = self._mcp_run_coro(self._auditor.clear_calls(), 6.0)
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _mcp_targets_snapshot_async(self):
        """Read current js runtime targets from the debug engine event loop."""
        return {
            "targets": self._engine.list_js_contexts() if self._engine else [],
            "selected_target": self._engine.get_selected_js_context() if self._engine else {},
            "diagnostics": self._engine.get_js_context_diagnostics() if self._engine else {},
        }

    async def _mcp_select_target_async(self, jscontext_id):
        """Select one js runtime target on the debug engine event loop."""
        if not self._engine:
            raise RuntimeError("debug engine not started")
        return await self._engine.activate_js_context(jscontext_id)

    def _mcp_tool_list_targets(self):
        """List current miniapp js runtime targets."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._mcp_targets_snapshot_async(), 5.0)
            return {"ok": True, **result, "count": len(result.get("targets", []))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_selected_target(self):
        """Read the current selected miniapp js runtime target."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            result = self._mcp_run_coro(self._mcp_targets_snapshot_async(), 5.0)
            return {"ok": True, "selected_target": result.get("selected_target", {})}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_select_target(self, jscontext_id):
        """Select one miniapp js runtime target by jscontext_id."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            selected = self._mcp_run_coro(self._mcp_select_target_async(jscontext_id), 5.0)
            return {"ok": True, "selected_target": selected}
        except KeyError:
            return {"ok": False, "error": f"unknown jscontext_id: {jscontext_id}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_preview_value(self, value, limit=180):
        """Return a compact string preview for MCP analysis output."""
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = str(value)
        return text if len(text) <= limit else text[:limit] + "..."

    def _mcp_flatten_params(self, value, location, prefix="", depth=0, out=None):
        """Flatten nested request data into parameter rows."""
        out = out if out is not None else []
        if len(out) >= 300 or depth > 5:
            return out
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                self._mcp_flatten_params(child, location, path, depth + 1, out)
            return out
        if isinstance(value, list):
            for index, child in enumerate(value[:50]):
                path = f"{prefix}[{index}]" if prefix else f"[{index}]"
                self._mcp_flatten_params(child, location, path, depth + 1, out)
            return out
        row = {
            "name": prefix,
            "path": prefix,
            "location": location,
            "value_type": type(value).__name__,
            "value": self._mcp_preview_value(value),
            "length": len(str(value)) if value is not None else 0,
        }
        score, reasons = self._mcp_parameter_score(prefix, value)
        row["score"] = score
        row["reasons"] = reasons
        out.append(row)
        return out

    def _mcp_parameter_score(self, name, value):
        """Score whether a parameter looks generated, signed, or encrypted."""
        score = 0
        reasons = []
        lname = (name or "").lower()
        value_text = "" if value is None else str(value)
        name_hints = (
            "sign", "signature", "token", "auth", "nonce", "timestamp", "ts",
            "encrypt", "encrypted", "cipher", "secret", "key", "hash", "hmac",
            "iv", "salt", "session", "ticket",
        )
        for hint in name_hints:
            if hint in lname:
                score += 3
                reasons.append(f"name:{hint}")
                break
        if len(value_text) >= 24:
            score += 1
            reasons.append("long_value")
        if re.fullmatch(r"[0-9a-fA-F]{24,}", value_text or ""):
            score += 3
            reasons.append("hex_like")
        if re.fullmatch(r"[A-Za-z0-9+/=_-]{24,}", value_text or ""):
            score += 2
            reasons.append("base64_like")
        if any(ch in value_text for ch in ("%", "+", "/", "=")) and len(value_text) >= 16:
            score += 1
            reasons.append("encoded_chars")
        return score, reasons

    def _mcp_crypto_terms(self):
        """Common source terms that often appear near signing/encryption logic."""
        return [
            "CryptoJS", "crypto-js", "md5", "sha1", "sha256", "sha512", "hmac",
            "HmacSHA", "AES", "DES", "RSA", "encrypt", "decrypt", "cipher",
            "signature", "sign", "nonce", "timestamp", "token", "secret", "salt",
            "iv", "btoa", "atob", "base64", "encodeURIComponent", "decodeURIComponent",
            "JSON.stringify", "sort", "join", "URLSearchParams",
        ]

    def _mcp_crypto_hints(self, snippet):
        """Return crypto/signature terms present in a snippet."""
        lower = snippet.lower()
        hints = []
        for term in self._mcp_crypto_terms():
            if term.lower() in lower and term not in hints:
                hints.append(term)
        return hints

    def _mcp_extract_request_parameters(self, request):
        """Extract query, header, body, and response fields from a captured request."""
        params = []
        url = request.get("url", "") or ""
        try:
            parsed = urlparse(url)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True):
                row = {
                    "name": key,
                    "path": key,
                    "location": "query",
                    "value_type": "str",
                    "value": self._mcp_preview_value(value),
                    "length": len(value),
                }
                score, reasons = self._mcp_parameter_score(key, value)
                row["score"] = score
                row["reasons"] = reasons
                params.append(row)
        except Exception:
            pass
        self._mcp_flatten_params(request.get("header") or {}, "header", out=params)
        self._mcp_flatten_params(request.get("data") or {}, "data", out=params)
        response = request.get("response")
        if isinstance(response, dict):
            body = response.get("data", response)
            self._mcp_flatten_params(body, "response", out=params)
        params.sort(key=lambda item: (-item.get("score", 0), item.get("location", ""), item.get("path", "")))
        return params[:300]

    def _mcp_tool_inspect_request_parameters(self, request_id, limit):
        """Inspect captured request parameters and rank suspicious fields."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            rows = self._mcp_run_coro(self._navigator.get_recent_requests(limit), 6.0)
            if not rows:
                return {"ok": True, "request": None, "parameters": [], "count": 0}
            if request_id is None:
                request = rows[-1]
            else:
                request = next((row for row in rows if int(row.get("id", -1)) == request_id), None)
                if not request:
                    return {"ok": False, "error": f"request not found: {request_id}"}
            params = self._mcp_extract_request_parameters(request)
            summary = {
                "id": request.get("id"),
                "time": request.get("time"),
                "route": request.get("route"),
                "method": request.get("method"),
                "url": request.get("url"),
                "status": request.get("status"),
                "statusCode": request.get("statusCode"),
            }
            return {"ok": True, "request": summary, "parameters": params, "count": len(params)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _mcp_collect_runtime_scripts_async(self, wait_seconds=1.5, limit=200):
        """Collect runtime script metadata from CDP Debugger.scriptParsed events."""
        preserve_breakpoints = self._mcp_has_active_breakpoints()
        script_map = {}

        def _on_parsed(data):
            params = data.get("params", {}) if isinstance(data, dict) else {}
            script_id = str(params.get("scriptId", "")).strip()
            if not script_id:
                return
            script_map[script_id] = {
                "script_id": script_id,
                "url": params.get("url", "") or "",
                "start_line": params.get("startLine", 0),
                "start_column": params.get("startColumn", 0),
                "end_line": params.get("endLine", 0),
                "end_column": params.get("endColumn", 0),
                "execution_context_id": params.get("executionContextId"),
                "hash": params.get("hash", "") or "",
            }

        self._engine.on_cdp_event("Debugger.scriptParsed", _on_parsed)
        try:
            if not preserve_breakpoints:
                try:
                    await self._engine.send_cdp_command("Debugger.disable", timeout=3.0)
                    await asyncio.sleep(0.1)
                except Exception:
                    pass
            await self._engine.send_cdp_command("Debugger.enable", timeout=5.0)
            end_at = asyncio.get_event_loop().time() + wait_seconds
            prev_count = -1
            while asyncio.get_event_loop().time() < end_at:
                await asyncio.sleep(0.2)
                if len(script_map) == prev_count and prev_count > 0:
                    break
                prev_count = len(script_map)
        finally:
            self._engine.off_cdp_event("Debugger.scriptParsed", _on_parsed)

        scripts = list(script_map.values())
        scripts.sort(key=lambda item: (0 if item.get("url") else 1, item.get("url", ""), item.get("script_id", "")))
        scripts = scripts[:limit]
        self._mcp_runtime_scripts = {item["script_id"]: item for item in scripts}
        return scripts

    async def _mcp_get_runtime_script_source_async(self, script_id):
        """Read one runtime script source by CDP scriptId."""
        try:
            await self._engine.send_cdp_command("Debugger.enable", timeout=5.0)
        except Exception:
            pass
        resp = await self._engine.send_cdp_command(
            "Debugger.getScriptSource", {"scriptId": script_id}, timeout=8.0)
        return resp.get("result", {}).get("scriptSource", "") if isinstance(resp, dict) else ""

    async def _mcp_prepare_breakpoint_debugger_async(self):
        """Enable Debugger and allow pauses before MCP auto breakpoint operations."""
        await self._engine.send_cdp_command("Debugger.enable", timeout=5.0)
        await self._engine.send_cdp_command(
            "Debugger.setSkipAllPauses",
            {"skip": False},
            timeout=3.0)

    async def _mcp_set_auto_breakpoint_async(self, script_id, url, line_number, column_number, condition):
        """Create one breakpoint by script id or URL through CDP Debugger commands."""
        await self._mcp_prepare_breakpoint_debugger_async()
        if script_id:
            params = {
                "location": {
                    "scriptId": script_id,
                    "lineNumber": max(0, int(line_number) - 1),
                    "columnNumber": max(0, int(column_number)),
                }
            }
            if condition:
                params["condition"] = condition
            return await self._engine.send_cdp_command("Debugger.setBreakpoint", params, timeout=8.0)
        params = {
            "lineNumber": max(0, int(line_number) - 1),
            "url": url,
            "columnNumber": max(0, int(column_number)),
        }
        if condition:
            params["condition"] = condition
        return await self._engine.send_cdp_command("Debugger.setBreakpointByUrl", params, timeout=8.0)

    async def _mcp_resume_execution_async(self, mode):
        """Resume or single-step the paused runtime according to one MCP execution mode."""
        method_map = {
            "resume": "Debugger.resume",
            "step_over": "Debugger.stepOver",
            "step_into": "Debugger.stepInto",
            "step_out": "Debugger.stepOut",
        }
        method = method_map[mode]
        return await self._engine.send_cdp_command(method, timeout=6.0)

    async def _mcp_search_runtime_scripts_async(
            self, query, case_sensitive, max_results, max_scripts, context_chars):
        """Search collected runtime script source for a literal query."""
        scripts = await self._mcp_collect_runtime_scripts_async(1.2, max_scripts)
        needle = query if case_sensitive else query.lower()
        results = []
        scanned = 0
        errors = 0
        for meta in scripts[:max_scripts]:
            if len(results) >= max_results:
                break
            scanned += 1
            script_id = meta.get("script_id", "")
            try:
                resp = await self._engine.send_cdp_command(
                    "Debugger.getScriptSource", {"scriptId": script_id}, timeout=8.0)
                source = resp.get("result", {}).get("scriptSource", "") if isinstance(resp, dict) else ""
            except Exception:
                errors += 1
                continue
            if not source:
                continue
            haystack = source if case_sensitive else source.lower()
            pos = haystack.find(needle)
            step = max(1, len(needle))
            while pos >= 0 and len(results) < max_results:
                start = max(0, pos - context_chars)
                end = min(len(source), pos + len(query) + context_chars)
                results.append({
                    "script_id": script_id,
                    "url": meta.get("url", ""),
                    "index": pos,
                    "line": source.count("\n", 0, pos) + 1,
                    "snippet": source[start:end],
                    "source_length": len(source),
                })
                pos = haystack.find(needle, pos + step)
        return {
            "query": query,
            "case_sensitive": case_sensitive,
            "scanned": scanned,
            "errors": errors,
            "matches": results,
        }

    async def _mcp_trace_parameter_logic_async(
            self, param_name, sample_value, max_scripts, max_results, context_chars):
        """Locate source snippets related to a parameter name or observed value."""
        scripts = await self._mcp_collect_runtime_scripts_async(1.2, max_scripts)
        terms = []
        if param_name:
            terms.append({"kind": "param_name", "value": param_name})
        if sample_value and len(sample_value) >= 4:
            terms.append({"kind": "sample_value", "value": sample_value})
        results = []
        scanned = 0
        errors = 0
        seen = set()
        for meta in scripts[:max_scripts]:
            if len(results) >= max_results:
                break
            scanned += 1
            script_id = meta.get("script_id", "")
            try:
                resp = await self._engine.send_cdp_command(
                    "Debugger.getScriptSource", {"scriptId": script_id}, timeout=8.0)
                source = resp.get("result", {}).get("scriptSource", "") if isinstance(resp, dict) else ""
            except Exception:
                errors += 1
                continue
            if not source:
                continue
            lower_source = source.lower()
            for term in terms:
                if len(results) >= max_results:
                    break
                needle = term["value"].lower()
                pos = lower_source.find(needle)
                step = max(1, len(needle))
                while pos >= 0 and len(results) < max_results:
                    bucket = (script_id, pos // 80, term["kind"])
                    if bucket not in seen:
                        seen.add(bucket)
                        start = max(0, pos - context_chars)
                        end = min(len(source), pos + len(term["value"]) + context_chars)
                        snippet = source[start:end]
                        hints = self._mcp_crypto_hints(snippet)
                        score = len(hints) * 2 + (3 if term["kind"] == "param_name" else 1)
                        results.append({
                            "script_id": script_id,
                            "url": meta.get("url", ""),
                            "match_kind": term["kind"],
                            "match": term["value"],
                            "index": pos,
                            "line": source.count("\n", 0, pos) + 1,
                            "score": score,
                            "crypto_hints": hints,
                            "snippet": snippet,
                            "source_length": len(source),
                        })
                    pos = lower_source.find(needle, pos + step)
        results.sort(key=lambda item: (-item.get("score", 0), item.get("url", ""), item.get("line", 0)))
        return {
            "param_name": param_name,
            "sample_value_used": bool(sample_value and len(sample_value) >= 4),
            "scanned": scanned,
            "errors": errors,
            "matches": results[:max_results],
        }

    async def _mcp_find_crypto_candidates_async(self, max_scripts, max_results, context_chars):
        """Find source snippets with dense crypto/signature hints."""
        scripts = await self._mcp_collect_runtime_scripts_async(1.2, max_scripts)
        terms = self._mcp_crypto_terms()
        candidates = []
        seen = set()
        scanned = 0
        errors = 0
        for meta in scripts[:max_scripts]:
            scanned += 1
            script_id = meta.get("script_id", "")
            try:
                resp = await self._engine.send_cdp_command(
                    "Debugger.getScriptSource", {"scriptId": script_id}, timeout=8.0)
                source = resp.get("result", {}).get("scriptSource", "") if isinstance(resp, dict) else ""
            except Exception:
                errors += 1
                continue
            if not source:
                continue
            lower_source = source.lower()
            for term in terms:
                pos = lower_source.find(term.lower())
                while pos >= 0:
                    bucket = (script_id, pos // max(80, context_chars))
                    if bucket not in seen:
                        seen.add(bucket)
                        start = max(0, pos - context_chars)
                        end = min(len(source), pos + len(term) + context_chars)
                        snippet = source[start:end]
                        hints = self._mcp_crypto_hints(snippet)
                        candidates.append({
                            "script_id": script_id,
                            "url": meta.get("url", ""),
                            "index": pos,
                            "line": source.count("\n", 0, pos) + 1,
                            "score": len(hints),
                            "crypto_hints": hints,
                            "snippet": snippet,
                            "source_length": len(source),
                        })
                    if len(candidates) >= max_results * 4:
                        break
                    pos = lower_source.find(term.lower(), pos + max(1, len(term)))
                if len(candidates) >= max_results * 4:
                    break
            if len(candidates) >= max_results * 4:
                break
        candidates.sort(key=lambda item: (-item.get("score", 0), item.get("url", ""), item.get("line", 0)))
        return {
            "scanned": scanned,
            "errors": errors,
            "candidates": candidates[:max_results],
        }

    def _mcp_tool_list_runtime_scripts(self, wait_seconds, limit):
        """List scripts parsed by the current miniapp runtime."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            scripts = self._mcp_run_coro(
                self._mcp_collect_runtime_scripts_async(wait_seconds, limit),
                wait_seconds + 8.0)
            return {"ok": True, "scripts": scripts, "count": len(scripts)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_get_runtime_script_source(self, script_id, offset, max_chars):
        """Read a bounded source chunk for a runtime script."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            source = self._mcp_run_coro(
                self._mcp_get_runtime_script_source_async(script_id), 12.0)
            total = len(source)
            end = min(total, offset + max_chars)
            meta = getattr(self, "_mcp_runtime_scripts", {}).get(script_id, {})
            return {
                "ok": True,
                "script_id": script_id,
                "url": meta.get("url", ""),
                "offset": offset,
                "returned": max(0, end - offset),
                "total": total,
                "truncated": end < total,
                "source": source[offset:end],
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_set_auto_breakpoint(self, script_id, url, line_number, column_number, condition):
        """Create an MCP automatic breakpoint and return the created breakpoint metadata."""
        reason = self._mcp_require_auto_breakpoint_pause_mode()
        if reason:
            return {"ok": False, "error": reason}
        try:
            self._mcp_attach_breakpoint_listeners()
            response = self._mcp_run_coro(
                self._mcp_set_auto_breakpoint_async(script_id, url, line_number, column_number, condition),
                12.0)
            if isinstance(response, dict) and response.get("error"):
                message = response.get("error", {}).get("message", "set breakpoint failed")
                return {"ok": False, "error": str(message)}
            result = response.get("result", {}) if isinstance(response, dict) else {}
            breakpoint_id = str(result.get("breakpointId", "") or "")
            locations = []
            if isinstance(result.get("actualLocation"), dict):
                locations.append(result["actualLocation"])
            for item in result.get("locations", []) or []:
                if isinstance(item, dict):
                    locations.append(item)
            normalized = []
            for item in locations:
                item_script_id = str(item.get("scriptId", "") or script_id or "")
                meta = self._mcp_runtime_scripts.get(item_script_id, {})
                normalized.append({
                    "script_id": item_script_id,
                    "url": str(meta.get("url", "") or url or ""),
                    "line_number": int(item.get("lineNumber", 0) or 0) + 1,
                    "column_number": int(item.get("columnNumber", 0) or 0) + 1,
                })
            if breakpoint_id:
                self._mcp_breakpoints[breakpoint_id] = {
                    "script_id": script_id,
                    "url": url,
                    "line_number": int(line_number),
                    "column_number": int(column_number),
                    "condition": condition,
                }
            with self._mcp_pause_cv:
                wait_since_seq = self._mcp_pause_seq
                self._mcp_wait_pause_since_seq = wait_since_seq
            return {
                "ok": True,
                "breakpoint_id": breakpoint_id,
                "since_pause_seq": wait_since_seq,
                "line_number": int(line_number),
                "column_number": int(column_number),
                "locations": normalized,
                "raw": response,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_wait_for_pause(self, timeout, since_pause_seq=None):
        """Wait for a Debugger.paused event after user actions trigger an MCP breakpoint."""
        reason = self._mcp_require_auto_breakpoint_pause_mode()
        if reason:
            return {"ok": False, "error": reason}
        try:
            self._mcp_attach_breakpoint_listeners()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        timeout = max(0.1, min(float(timeout or 20.0), 120.0))
        with self._mcp_pause_cv:
            if since_pause_seq in (None, ""):
                since_pause_seq = self._mcp_wait_pause_since_seq
            try:
                since_pause_seq = int(since_pause_seq or 0)
            except (TypeError, ValueError):
                return {"ok": False, "error": "invalid since_pause_seq"}
            if self._mcp_pause_state and int(self._mcp_pause_state.get("pause_seq", 0) or 0) > since_pause_seq:
                self._mcp_wait_pause_since_seq = None
                return {"ok": True, "paused": True, **dict(self._mcp_pause_state)}
            end_at = time.monotonic() + timeout
            while not self._mcp_pause_state or int(self._mcp_pause_state.get("pause_seq", 0) or 0) <= since_pause_seq:
                remaining = end_at - time.monotonic()
                if remaining <= 0:
                    return {"ok": False, "error": "wait for pause timeout"}
                self._mcp_pause_cv.wait(timeout=remaining)
            self._mcp_wait_pause_since_seq = None
            return {"ok": True, "paused": True, **dict(self._mcp_pause_state)}

    def _mcp_tool_resume_execution(self, mode):
        """Resume or single-step execution after a pause caused by an MCP breakpoint."""
        reason = self._mcp_require_auto_breakpoint()
        if reason:
            return {"ok": False, "error": reason}
        mode = str(mode or "resume").strip().lower()
        if mode not in {"resume", "step_over", "step_into", "step_out"}:
            return {"ok": False, "error": f"invalid mode: {mode}"}
        try:
            response = self._mcp_run_coro(self._mcp_resume_execution_async(mode), 8.0)
            if isinstance(response, dict) and response.get("error"):
                message = response.get("error", {}).get("message", "resume execution failed")
                return {"ok": False, "error": str(message)}
            self._mcp_clear_pause_state()
            return {"ok": True, "mode": mode, "raw": response}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_remove_breakpoint(self, breakpoint_id):
        """Remove one previously created breakpoint from the current miniapp runtime."""
        reason = self._mcp_require_auto_breakpoint()
        if reason:
            return {"ok": False, "error": reason}
        breakpoint_id = str(breakpoint_id or "").strip()
        if not breakpoint_id:
            return {"ok": False, "error": "missing breakpoint_id"}
        try:
            response = self._mcp_run_coro(
                self._engine.send_cdp_command("Debugger.removeBreakpoint", {"breakpointId": breakpoint_id}, timeout=6.0),
                8.0)
            if isinstance(response, dict) and response.get("error"):
                message = response.get("error", {}).get("message", "remove breakpoint failed")
                return {"ok": False, "error": str(message)}
            self._mcp_breakpoints.pop(breakpoint_id, None)
            return {"ok": True, "breakpoint_id": breakpoint_id, "raw": response}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_search_runtime_scripts(
            self, query, case_sensitive, max_results, max_scripts, context_chars):
        """Search runtime scripts and return bounded snippets."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            timeout = max(15.0, min(90.0, 8.0 + max_scripts * 0.3))
            result = self._mcp_run_coro(
                self._mcp_search_runtime_scripts_async(
                    query, case_sensitive, max_results, max_scripts, context_chars),
                timeout)
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_trace_parameter_logic(
            self, param_name, sample_value, max_scripts, max_results, context_chars):
        """Trace a request parameter to likely source-generation logic."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            timeout = max(15.0, min(90.0, 8.0 + max_scripts * 0.3))
            result = self._mcp_run_coro(
                self._mcp_trace_parameter_logic_async(
                    param_name, sample_value, max_scripts, max_results, context_chars),
                timeout)
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _mcp_tool_find_crypto_candidates(self, max_scripts, max_results, context_chars):
        """Find likely crypto/signature helper snippets in runtime scripts."""
        reason = self._mcp_require_runtime()
        if reason:
            return {"ok": False, "error": reason}
        try:
            timeout = max(15.0, min(90.0, 8.0 + max_scripts * 0.3))
            result = self._mcp_run_coro(
                self._mcp_find_crypto_candidates_async(max_scripts, max_results, context_chars),
                timeout)
            return {"ok": True, **result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ──────────────────────────────────
    #  业务
    # ──────────────────────────────────

    def _devtools_breakpoints_enabled(self):
        """返回当前是否允许 Chrome DevTools 断点暂停小程序 JS。"""
        if hasattr(self, "_tog_devtools_bp"):
            return self._tog_devtools_bp.isChecked()
        return bool(self._cfg.get("allow_devtools_breakpoints", False))

    def _devtools_skip_all_pauses(self):
        """返回当前是否需要让 CDP 跳过所有暂停点。"""
        return not self._devtools_breakpoints_enabled()

    def _refresh_devtools_breakpoint_status(self):
        """刷新控制台中 DevTools 断点策略的状态展示。"""
        if not hasattr(self, "_devtools_bp_status_lbl"):
            return
        c = _TH[self._tn]
        if self._devtools_breakpoints_enabled():
            self._devtools_bp_status_lbl.setText("允许暂停")
            self._devtools_bp_status_lbl.setStyleSheet(f"color: {c['success']};")
        else:
            self._devtools_bp_status_lbl.setText("跳过暂停")
            self._devtools_bp_status_lbl.setStyleSheet(f"color: {c['warning']};")

    def _on_devtools_breakpoints_toggled(self, checked):
        """处理控制台 DevTools 断点开关变化，并在运行中同步到小程序。"""
        self._refresh_devtools_breakpoint_status()
        self._auto_save()
        if checked:
            self._log_add("info", "[DevTools] 已允许断点暂停")
        else:
            self._log_add("warn", "[DevTools] 已切换为跳过暂停")
        self._apply_devtools_breakpoint_mode()

    def _apply_devtools_breakpoint_mode(self):
        """通过 CDP 将当前断点策略应用到已连接的小程序运行时。"""
        if not self._running or not self._engine or not self._loop or not self._loop.is_running():
            return
        if not getattr(self, "_miniapp_connected", False):
            return
        skip = self._devtools_skip_all_pauses()
        fut = asyncio.run_coroutine_threadsafe(
            self._engine.send_cdp_command(
                "Debugger.setSkipAllPauses", {"skip": skip}, timeout=3.0),
            self._loop)

        def _done(done):
            try:
                done.result()
            except Exception as e:
                self._log_q.put(("warn", f"[DevTools] 断点策略同步失败: {e}"))

        fut.add_done_callback(_done)

    def _copy_devtools_url(self):
        """复制当前 DevTools 调试链接到剪贴板，并短暂显示复制状态。"""
        url = self._devtools_lbl.text()
        if not url.startswith("devtools://"):
            self._set_devtools_copy_button("未生成", False)
            return
        QApplication.clipboard().setText(url)
        self._set_devtools_copy_button("已复制!", True, "success")
        QTimer.singleShot(1500, lambda: (
            self._set_devtools_copy_button("点击复制", True)
        ))
        self._log_add("info", "[gui] DevTools 链接已复制到剪贴板")

    def _set_devtools_copy_button(self, text, enabled, mode="normal"):
        """刷新 DevTools 复制胶囊按钮的文字、可用状态和临时强调色。"""
        btn = getattr(self, "_devtools_copy_hint", None)
        if not btn:
            return
        btn.setText(text)
        btn.setEnabled(enabled)
        btn.setVisible(bool(text))
        if mode == "success":
            c = _TH[self._tn]
            btn.setStyleSheet(
                f"QPushButton#devtools_copy_btn {{ color: {c['success']}; border: 1px solid {c['success']}; }}"
            )
        else:
            btn.setStyleSheet("")

    def _copy_logs(self):
        """复制当前筛选后的运行日志纯文本到剪贴板。"""
        text = "\n".join(txt for _, txt in self._filtered_log_entries()).strip()
        if not text:
            self._log_add("warn", "[日志] 当前没有可复制的日志")
            return
        QApplication.clipboard().setText(text)
        self._log_add("info", "[日志] 已复制全部日志")

    def _export_logs(self):
        """将当前筛选后的运行日志纯文本导出到本地 txt 文件。"""
        text = "\n".join(txt for _, txt in self._filtered_log_entries()).strip()
        if not text:
            self._log_add("warn", "[日志] 当前没有可导出的日志")
            return
        default_path = os.path.join(_BASE_DIR, "first_gui_logs.txt")
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", default_path, "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text + "\n")
            self._log_add("info", f"[日志] 已导出: {path}")
        except Exception as e:
            self._log_add("error", f"[日志] 导出失败: {e}")

    def _do_clear(self):
        """清空控制台和运行日志页面中的日志内容。"""
        self._log_entries.clear()
        if hasattr(self, "_logbox"):
            self._logbox.clear()
        if hasattr(self, "_control_logbox"):
            self._control_logbox.clear()
        if hasattr(self, "_log_count_lbl"):
            self._log_count_lbl.setText("0 条")

    _LOG_MAX_BLOCKS = 500  # 最多保留的日志行数

    def _filtered_log_entries(self):
        """返回符合运行日志页当前关键字和级别筛选条件的日志记录。"""
        kw = ""
        if hasattr(self, "_log_filter_ent"):
            kw = self._log_filter_ent.text().strip().lower()
        lv_filter = ""
        if hasattr(self, "_log_level_combo"):
            lv_filter = self._log_level_combo.currentData() or ""
        out = []
        for lv, txt in self._log_entries:
            if lv_filter and lv != lv_filter:
                continue
            if kw and kw not in txt.lower():
                continue
            out.append((lv, txt))
        return out

    def _log_html(self, lv, txt):
        """按当前主题将单条日志转换为 QTextEdit 可显示的 HTML。"""
        c = _TH[self._tn]
        color_map = {
            "info": c["text2"],
            "error": c["error"],
            "debug": c["text3"],
            "frida": c["accent"],
            "warn": c["warning"],
        }
        color = color_map.get(lv, c["text2"])
        return f'<span style="color:{color}">{txt}</span>'

    def _render_logbox(self):
        """根据当前筛选条件重绘运行日志页面，不影响控制台日志。"""
        box = getattr(self, "_logbox", None)
        if box is None:
            return
        entries = self._filtered_log_entries()
        box.setUpdatesEnabled(False)
        box.clear()
        for lv, txt in entries:
            box.append(self._log_html(lv, txt))
        box.setUpdatesEnabled(True)
        if hasattr(self, "_log_count_lbl"):
            total = len(self._log_entries)
            shown = len(entries)
            self._log_count_lbl.setText(f"{shown} / {total} 条" if shown != total else f"{total} 条")
        active_filter = bool(
            (self._log_filter_ent.text().strip() if hasattr(self, "_log_filter_ent") else "")
            or (self._log_level_combo.currentData() if hasattr(self, "_log_level_combo") else "")
        )
        if hasattr(self, "_btn_clear_log_filter"):
            self._btn_clear_log_filter.setEnabled(active_filter)
        if self._log_autoscroll_enabled():
            sb = box.verticalScrollBar()
            sb.setValue(sb.maximum())

    def _render_control_logbox(self):
        """按当前主题重绘控制台日志，保持控制台日志始终显示全量记录。"""
        box = getattr(self, "_control_logbox", None)
        if box is None:
            return
        box.setUpdatesEnabled(False)
        box.clear()
        for lv, txt in self._log_entries:
            box.append(self._log_html(lv, txt))
        box.setUpdatesEnabled(True)
        sb = box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_log_filter(self):
        """清空运行日志页面的关键字和级别筛选条件。"""
        if hasattr(self, "_log_filter_ent"):
            self._log_filter_ent.clear()
        if hasattr(self, "_log_level_combo"):
            self._log_level_combo.setCurrentIndex(0)
        self._render_logbox()

    def _log_autoscroll_enabled(self):
        """返回运行日志页面是否允许自动滚动到底部。"""
        cb = getattr(self, "_log_autoscroll_cb", None)
        return True if cb is None else cb.isChecked()

    def _log_add(self, lv, txt):
        """记录一条日志，并同步更新控制台日志与运行日志页面。"""
        self._log_entries.append((lv, txt))
        if len(self._log_entries) > self._LOG_MAX_BLOCKS:
            self._log_entries = self._log_entries[-self._LOG_MAX_BLOCKS:]

        control_box = getattr(self, "_control_logbox", None)
        if control_box is not None:
            self._append_log_html(control_box, self._log_html(lv, txt))

        if self._log_matches_filter(lv, txt):
            log_box = getattr(self, "_logbox", None)
            if log_box is not None:
                self._append_log_html(log_box, self._log_html(lv, txt))
        if hasattr(self, "_log_count_lbl"):
            shown = len(self._filtered_log_entries())
            total = len(self._log_entries)
            self._log_count_lbl.setText(f"{shown} / {total} 条" if shown != total else f"{total} 条")

    def _log_matches_filter(self, lv, txt):
        """判断单条日志是否符合运行日志页的当前筛选条件。"""
        kw = self._log_filter_ent.text().strip().lower() if hasattr(self, "_log_filter_ent") else ""
        lv_filter = self._log_level_combo.currentData() if hasattr(self, "_log_level_combo") else ""
        if lv_filter and lv != lv_filter:
            return False
        if kw and kw not in txt.lower():
            return False
        return True

    def _append_log_html(self, box, html):
        """向日志框追加 HTML，并限制 QTextEdit 文档行数。"""
        box.append(html)
        doc = box.document()
        overflow = doc.blockCount() - self._LOG_MAX_BLOCKS
        if overflow > 50:
            cursor = box.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            for _ in range(overflow):
                cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        if box is getattr(self, "_logbox", None) and not self._log_autoscroll_enabled():
            return
        sb = box.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _do_start(self):
        """按控制台配置启动调试引擎，并生成 DevTools 连接地址。"""
        if self._running:
            return
        try:
            cp = int(self._cp_ent.text())
        except ValueError:
            self._log_add("error", "[gui] 端口号无效")
            return
        opts = CliOptions(
            cdp_port=cp,
            debug_main=self._tog_dm.isChecked(),
            debug_frida=self._tog_df.isChecked(),
            allow_devtools_breakpoints=self._devtools_breakpoints_enabled(),
            scripts_dir="",
            script_files=[])
        logger = Logger(opts)
        logger.set_output_callback(lambda lv, tx: self._log_q.put((lv, tx)))
        self._engine = DebugEngine(opts, logger)
        self._navigator = MiniProgramNavigator(self._engine)
        self._auditor = CloudAuditor(self._engine)
        self._engine.on_status_change(lambda s: self._sts_q.put(s))
        self._engine.on_contexts_change(lambda ctxs: self._mcp_q.put(("targets", ctxs)))
        self._loop = asyncio.new_event_loop()
        self._loop_th = threading.Thread(
            target=lambda: (asyncio.set_event_loop(self._loop), self._loop.run_forever()),
            daemon=True)
        self._loop_th.start()
        asyncio.run_coroutine_threadsafe(self._astart(), self._loop)
        self._running = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_fetch.setEnabled(True)
        self._update_control_hook_button()
        url = f"devtools://devtools/bundled/inspector.html?ws=127.0.0.1:{cp}"
        self._devtools_lbl.setText(url)
        self._devtools_lbl.setToolTip(url)
        c = _TH[self._tn]
        self._devtools_lbl.setStyleSheet(f"color: {c['accent']};")
        self._set_devtools_copy_button("点击复制", True)
        self._log_add("info", f"[gui] 浏览器访问: {url}")
        self._update_flow_steps()
        self._hook_refresh()

    async def _astart(self):
        try:
            await self._engine.start()
        except Exception as e:
            self._log_q.put(("error", f"[gui] 启动失败: {e}"))
            QTimer.singleShot(0, self._on_fail)

    def _on_fail(self):
        self._mcp_detach_breakpoint_listeners()
        self._mcp_reset_runtime_script_cache()
        self._running = False
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._update_control_hook_button()
        self._nav_btns(False)
        self._btn_vc_enable.setEnabled(False)
        self._btn_vc_disable.setEnabled(False)
        self._btn_vc_detect.setEnabled(False)
        c = _TH[self._tn]
        self._devtools_lbl.setText("未生成")
        self._devtools_lbl.setToolTip("启动调试后生成 DevTools 调试链接")
        self._devtools_lbl.setStyleSheet(f"color: {c['text3']};")
        self._set_devtools_copy_button("", False)
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._update_flow_steps()
        self._hook_refresh()

    def _do_stop(self):
        if not self._running:
            return
        self._mcp_detach_breakpoint_listeners()
        self._mcp_reset_runtime_script_cache()
        self._running = False
        self._poll_route_stop()
        if self._cloud_scan_active:
            self._cloud_scan_active = False
            if self._cloud_scan_poll_timer:
                self._cloud_scan_poll_timer.stop()
                self._cloud_scan_poll_timer = None
        if self._cancel_ev:
            self._cancel_ev.set()
        if self._engine and self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._engine.stop(), self._loop)
            fut.add_done_callback(lambda _: self._loop.call_soon_threadsafe(self._loop.stop))
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_fetch.setEnabled(False)
        self._update_control_hook_button()
        self._nav_btns(False)
        self._btn_vc_enable.setEnabled(False)
        self._btn_vc_disable.setEnabled(False)
        self._btn_vc_detect.setEnabled(False)
        self._vc_status_lbl.setText("状态: 未连接小程序")
        self._btn_autostop.setEnabled(False)
        self._redirect_guard_on = False
        self._guard_switch.setChecked(False)
        self._guard_label.setText("防跳转: 关闭")
        c = _TH[self._tn]
        self._devtools_lbl.setText("未生成")
        self._devtools_lbl.setToolTip("启动调试后生成 DevTools 调试链接")
        self._devtools_lbl.setStyleSheet(f"color: {c['text3']};")
        self._set_devtools_copy_button("", False)
        # 引擎停止，清除顶部目标信息和运行状态卡片的小程序信息
        self._current_app_name = ""
        self._current_app_id = ""
        self._update_target_badge(False)
        self._app_lbl.setText("AppID: --")
        self._appname_lbl.setText("应用: --")
        self._control_route_lbl.setText("当前路由: --")
        self._mcp_appid = ""
        self._mcp_route = ""
        self._update_mcp_debug_status({"frida": False, "miniapp": False, "devtools": False})
        self._last_sts = {}
        self._update_flow_steps()
        self._hook_refresh()

    def _nav_btns(self, on):
        for b in (self._btn_go, self._btn_relaunch,
                  self._btn_back, self._btn_refresh, self._btn_auto, self._btn_prev,
                  self._btn_next, self._btn_copy_route, self._btn_copy_route_list):
            b.setEnabled(on)
        self._guard_switch.setEnabled(on)

    def _do_fetch(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._afetch(), self._loop)

    async def _afetch(self):
        try:
            await self._navigator.fetch_config()
            self._rte_q.put(("routes", self._navigator.pages, self._navigator.tab_bar_pages))
            self._rte_q.put(("app_info", self._navigator.app_info))
            QTimer.singleShot(0, self._poll_route_start)
            # fetch_config 的 name 可能为空，补充通过 wxFrame 路径获取完整信息
            await self._afetch_app_info()
        except Exception as e:
            self._log_q.put(("error", f"[导航] 获取失败: {e}"))

    async def _afetch_app_info(self):
        """通过 nav_inject 的 wxFrame.__wxConfig 获取小程序名称和appid，用于侧栏显示。"""
        try:
            # 强制重新注入 navigator（重连后 WebView 上下文是全新的）
            await self._navigator._ensure(force=True)
            result = await self._engine.evaluate_js(
                "(function(){"
                "try{"
                "var nav=window.nav;"
                "if(!nav||!nav.wxFrame)return JSON.stringify({err:'no nav'});"
                "var c=nav.wxFrame.__wxConfig||{};"
                "var ai=c.accountInfo||{};"
                "var aa=ai.appAccount||{};"
                "return JSON.stringify({"
                "appid:aa.appId||ai.appId||c.appid||'',"
                "name:aa.nickname||ai.nickname||c.appname||''"
                "})"
                "}catch(e){return JSON.stringify({err:e.message})}"
                "})()",
                timeout=5.0,
            )
            value = None
            if result:
                r = result.get("result", {})
                inner = r.get("result", {})
                value = inner.get("value")
            if value:
                info = json.loads(value)
                if info.get("err"):
                    return
                self._rte_q.put(("app_info", info))
        except Exception:
            pass

    def _delayed_stable_connect(self, gen):
        """连接稳定后再启用按钮和触发后续操作，gen 不匹配说明中间又断过，跳过。"""
        if gen != self._vc_stable_gen:
            return
        if not self._miniapp_connected:
            return
        self._nav_btns(True)
        self._btn_vc_enable.setEnabled(True)
        self._btn_vc_disable.setEnabled(True)
        self._btn_vc_detect.setEnabled(True)
        self._vc_status_lbl.setText("状态: 就绪")
        # 自动检测 vConsole 调试状态
        if self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._avc_detect_debug(), self._loop)
        # 延迟获取侧栏信息
        self._sb_fetch_gen += 1
        fetch_gen = self._sb_fetch_gen
        QTimer.singleShot(1500, lambda: self._delayed_fetch_app_info(fetch_gen))
        # 自动恢复云扫描
        if not self._cloud_scan_active and self._auditor:
            self._cloud_start_scan()
            self._log_add("info", "[云扫描] 小程序连接后自动恢复捕获")

    def _delayed_fetch_app_info(self, gen):
        """延迟调用，只有最后一次触发的 gen 匹配才执行。"""
        if gen != self._sb_fetch_gen:
            return
        if self._miniapp_connected and self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._afetch_app_info(), self._loop)

    def _delayed_clear_app_info(self, gen):
        """延迟清除顶部目标信息，gen 不匹配说明已重连，跳过。"""
        if gen != self._sb_fetch_gen:
            return
        self._current_app_name = ""
        self._current_app_id = ""
        self._update_target_badge(False)
        self._app_lbl.setText("AppID: --")
        self._appname_lbl.setText("应用: --")
        self._control_route_lbl.setText("当前路由: --")

    def _poll_route_start(self):
        if not self._running:
            return
        if self._engine and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._apoll_route(), self._loop)
        self._route_poll_id = QTimer.singleShot(2000, self._poll_route_start)

    def _poll_route_stop(self):
        self._route_poll_id = None

    async def _apoll_route(self):
        try:
            r = await self._navigator.get_current_route()
            self._rte_q.put(("current", r))
            if self._redirect_guard_on:
                blocked = await self._navigator.get_blocked_redirects()
                if blocked:
                    self._rte_q.put(("blocked", blocked))
        except Exception:
            pass

    def _sel_route(self):
        items = self._tree.selectedItems()
        if not items:
            self._log_add("error", "[导航] 请先选择路由")
            return None
        item = items[0]
        return item.data(0, Qt.UserRole)

    def _do_go(self):
        r = self._sel_route()
        if r and self._engine and self._loop:
            if r in self._flat_routes:
                self._nav_route_idx = self._flat_routes.index(r)
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", r, "跳转"), self._loop)

    def _do_relaunch(self):
        r = self._sel_route()
        if r and self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("relaunch_to", r, "重启"), self._loop)

    def _do_back(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._aback(), self._loop)

    async def _anav(self, method, route, desc):
        try:
            await getattr(self._navigator, method)(route)
            self._log_q.put(("info", f"[导航] 已{desc}到: {route}"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] {desc}失败: {e}"))

    async def _aback(self):
        try:
            await self._navigator.navigate_back()
            self._log_q.put(("info", "[导航] 已返回"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 返回失败: {e}"))

    def _do_refresh(self):
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(self._arefresh(), self._loop)

    async def _arefresh(self):
        try:
            result = await self._navigator.refresh_page()
            if result:
                import json as _json
                try:
                    info = _json.loads(result) if isinstance(result, str) else result
                    if isinstance(info, dict):
                        err = info.get("err") or info.get("error")
                        if err or info.get("ok") is False:
                            self._log_q.put(("error", f"[导航] 刷新失败: {err or 'unknown error'}"))
                            return
                        route = info.get("route", "")
                        self._log_q.put(("info", f"[导航] 已刷新页面: /{route}"))
                        return
                except (_json.JSONDecodeError, TypeError):
                    self._log_q.put(("info", "[导航] 已刷新页面"))
            else:
                self._log_q.put(("info", "[导航] 已刷新页面"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 刷新失败: {e}"))

    def _do_autovis(self):
        if not self._navigator or not self._navigator.pages:
            self._log_add("error", "[导航] 请先获取路由")
            return
        self._cancel_ev = asyncio.Event()
        self._btn_auto.setEnabled(False)
        self._btn_autostop.setEnabled(True)
        asyncio.run_coroutine_threadsafe(
            self._aauto(list(self._navigator.pages)), self._loop)

    async def _aauto(self, pages):
        def prog(i, total, route):
            self._rte_q.put(("progress", i, total, route))
        try:
            await self._navigator.auto_visit(
                pages, delay=2.0, on_progress=prog, cancel_event=self._cancel_ev)
        except Exception as e:
            self._log_q.put(("error", f"[导航] 遍历出错: {e}"))
        finally:
            self._rte_q.put(("auto_done",))

    def _do_autostop(self):
        if self._cancel_ev:
            self._cancel_ev.set()
        self._btn_autostop.setEnabled(False)
        self._btn_auto.setEnabled(True)

    def _do_prev(self):
        routes = self._flat_routes or self._all_routes
        if not routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx <= 0:
            self._nav_route_idx = len(routes) - 1
        else:
            self._nav_route_idx -= 1
        route = routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 上一个: {route} ({self._nav_route_idx + 1}/{len(routes)})")
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_next(self):
        routes = self._flat_routes or self._all_routes
        if not routes:
            self._log_add("error", "[导航] 请先获取路由")
            return
        if self._nav_route_idx >= len(routes) - 1:
            self._nav_route_idx = 0
        else:
            self._nav_route_idx += 1
        route = routes[self._nav_route_idx]
        self._select_tree_route(route)
        self._log_add("info", f"[导航] 下一个: {route} ({self._nav_route_idx + 1}/{len(routes)})")
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_manual_go(self):
        route = self._nav_input.text().strip().lstrip("/")
        if not route:
            self._log_add("error", "[导航] 请输入路由路径")
            return
        if self._engine and self._loop:
            asyncio.run_coroutine_threadsafe(
                self._anav("navigate_to", route, "跳转"), self._loop)

    def _do_copy_route(self):
        items = self._tree.selectedItems()
        if not items:
            self._log_add("error", "[导航] 请先选择路由")
            return
        route = items[0].data(0, Qt.UserRole)
        if route:
            QApplication.clipboard().setText(route)
            self._log_add("info", f"[导航] 已复制路由: {route}")

    def _visible_tree_routes(self):
        """收集当前路由树中可见的路由路径，包含筛选后的展示结果。"""
        routes = []
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            route = top.data(0, Qt.UserRole)
            if route:
                routes.append(route)
            for j in range(top.childCount()):
                child_route = top.child(j).data(0, Qt.UserRole)
                if child_route:
                    routes.append(child_route)
        return routes

    def _do_copy_route_list(self):
        """复制当前路由树中正在展示的路由列表。"""
        routes = self._visible_tree_routes()
        if not routes:
            self._log_add("error", "[导航] 当前没有可复制的路由")
            return
        QApplication.clipboard().setText("\n".join(routes))
        self._log_add("info", f"[导航] 已复制 {len(routes)} 条路由")

    def _nav_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        route = item.data(0, Qt.UserRole)
        if not route:
            return
        self._tree.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction("复制路由", lambda: (
            QApplication.clipboard().setText(route),
            self._log_add("info", f"[导航] 已复制: {route}")))
        menu.addSeparator()
        menu.addAction("跳转", lambda: asyncio.run_coroutine_threadsafe(
            self._anav("navigate_to", route, "跳转"), self._loop) if self._engine and self._loop else None)
        menu.addAction("重启到页面", lambda: asyncio.run_coroutine_threadsafe(
            self._anav("relaunch_to", route, "重启"), self._loop) if self._engine and self._loop else None)
        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _do_toggle_guard_switch(self, checked):
        if not self._engine or not self._loop:
            self._guard_switch.blockSignals(True)
            self._guard_switch.setChecked(not checked)
            self._guard_switch.blockSignals(False)
            return
        asyncio.run_coroutine_threadsafe(self._atoggle_guard(checked), self._loop)

    async def _atoggle_guard(self, enable):
        try:
            if enable:
                r = await self._navigator.enable_redirect_guard()
                if r.get("ok"):
                    self._redirect_guard_on = True
                    self._blocked_seen = 0
                    self._log_q.put(("info", "[导航] 防跳转已开启，将拦截 redirectTo/reLaunch"))
                    QTimer.singleShot(0, lambda: self._guard_label.setText("防跳转: 开启"))
                else:
                    self._redirect_guard_on = False
                    self._log_q.put(("error", "[导航] 开启防跳转失败"))
                    QTimer.singleShot(0, self._guard_reset_switch)
            else:
                await self._navigator.disable_redirect_guard()
                self._redirect_guard_on = False
                self._log_q.put(("info", "[导航] 防跳转已关闭"))
                QTimer.singleShot(0, lambda: self._guard_label.setText("防跳转: 关闭"))
        except Exception as e:
            self._log_q.put(("error", f"[导航] 防跳转切换失败: {e}"))
            QTimer.singleShot(0, self._guard_reset_switch)

    def _guard_reset_switch(self):
        self._guard_switch.blockSignals(True)
        self._guard_switch.setChecked(self._redirect_guard_on)
        self._guard_switch.blockSignals(False)
        self._guard_label.setText("防跳转: 开启" if self._redirect_guard_on else "防跳转: 关闭")

    def _update_route_empty_state(self, message=None, count_text=None):
        """根据当前路由树数量刷新空状态提示和路由计数。"""
        if not hasattr(self, "_tree"):
            return
        count = self._tree.topLevelItemCount()
        total = len(self._flat_routes or self._all_routes)
        kw = self._srch_ent.text().strip() if hasattr(self, "_srch_ent") else ""
        if hasattr(self, "_route_count_lbl"):
            self._route_count_lbl.setText(count_text or (f"{total} 条" if total else "0 条"))
        if hasattr(self, "_btn_clear_route_search"):
            self._btn_clear_route_search.setEnabled(bool(kw))
        if hasattr(self, "_nav_hint_lbl"):
            if kw:
                self._nav_hint_lbl.setText(f"正在按「{kw}」筛选路由，清除搜索后可恢复完整路由树。")
            elif total:
                self._nav_hint_lbl.setText(f"已载入 {total} 条路由，可选择路由执行页面操作或自动遍历。")
            else:
                self._nav_hint_lbl.setText("连接小程序并获取路由后，可选择路由执行跳转、重启、遍历和防跳转。")
        if not hasattr(self, "_route_empty_hint"):
            return
        if count:
            self._route_empty_hint.hide()
            return
        if message:
            self._route_empty_hint.setText(message)
        self._route_empty_hint.show()

    def _do_filter(self):
        q = self._srch_ent.text().strip().lower()
        if not q:
            if self._navigator:
                self._fill_tree(self._all_routes, self._navigator.tab_bar_pages)
            elif hasattr(self, "_route_empty_hint"):
                self._update_route_empty_state("连接小程序后点击「获取路由」，路由树会显示在这里。")
            return
        flt = [p for p in self._all_routes if q in p.lower()]
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        for p in flt:
            item = QTreeWidgetItem([p])
            item.setData(0, Qt.UserRole, p)
            self._tree.addTopLevelItem(item)
        self._tree.setUpdatesEnabled(True)
        self._update_route_empty_state("没有匹配的路由。", f"{len(flt)} / {len(self._all_routes)} 条")

    def _clear_route_search(self):
        """清空路由搜索关键字并恢复完整路由树。"""
        if hasattr(self, "_srch_ent"):
            self._srch_ent.clear()
        self._do_filter()

    def _fill_tree(self, pages, tab_bar):
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()
        tabs = set(tab_bar)
        groups = {}
        for p in pages:
            parts = p.split("/")
            g = parts[0] if len(parts) > 1 else "(root)"
            groups.setdefault(g, []).append(p)

        flat = []  # tree visual order for prev/next

        tl = [p for p in pages if p in tabs]
        if tl:
            nd = QTreeWidgetItem(["TabBar"])
            nd.setExpanded(True)
            self._tree.addTopLevelItem(nd)
            for p in tl:
                d = p.split("/")[-1] if "/" in p else p
                child = QTreeWidgetItem([d])
                child.setData(0, Qt.UserRole, p)
                nd.addChild(child)
                flat.append(p)
        for g in sorted(groups):
            nd = QTreeWidgetItem([g])
            self._tree.addTopLevelItem(nd)
            for p in groups[g]:
                if p in tabs:
                    continue
                d = p[len(g) + 1:] if p.startswith(g + "/") else p
                child = QTreeWidgetItem([d])
                child.setData(0, Qt.UserRole, p)
                nd.addChild(child)
                flat.append(p)

        self._flat_routes = flat
        self._tree.setUpdatesEnabled(True)
        self._update_route_empty_state("未获取到路由，请确认小程序已连接。")

        # 默认选中并定位到第一个页面
        if flat and self._nav_route_idx < 0:
            self._nav_route_idx = 0
            self._select_tree_route(flat[0])

    def _select_tree_route(self, route):
        """Select the tree item matching the given route path."""
        for i in range(self._tree.topLevelItemCount()):
            top = self._tree.topLevelItem(i)
            if top.data(0, Qt.UserRole) == route:
                self._tree.setCurrentItem(top)
                self._tree.scrollToItem(top)
                return
            for j in range(top.childCount()):
                child = top.child(j)
                if child.data(0, Qt.UserRole) == route:
                    self._tree.setCurrentItem(child)
                    self._tree.scrollToItem(child)
                    return

    # ──────────────────────────────────
    #  云扫描业务
    # ──────────────────────────────────

    def _cloud_tree_context_menu(self, pos):
        item = self._cloud_tree.itemAt(pos)
        if not item:
            return
        self._cloud_tree.setCurrentItem(item)
        vals = [item.text(i) for i in range(6)]
        menu = QMenu(self)
        full_text = "  |  ".join(vals)
        menu.addAction("复制整行", lambda: QApplication.clipboard().setText(full_text))
        if vals[0]:
            menu.addAction(f"复制 AppID: {vals[0][:30]}",
                           lambda v=vals[0]: QApplication.clipboard().setText(v))
        name_str = vals[2] if len(vals) > 2 else ""
        if name_str:
            menu.addAction(f"复制名称: {name_str[:30]}",
                           lambda: QApplication.clipboard().setText(name_str))
        if len(vals) > 3 and vals[3]:
            menu.addAction("复制参数", lambda v=vals[3]: QApplication.clipboard().setText(v))
        if len(vals) > 4 and vals[4]:
            menu.addAction("复制状态", lambda v=vals[4]: QApplication.clipboard().setText(v))
        menu.addSeparator()
        row_id = id(item)
        if row_id in self._cloud_row_results:
            res = self._cloud_row_results[row_id]
            menu.addAction("查看返回结果",
                           lambda: self._cloud_show_result(name_str, res))
            menu.addSeparator()
        menu.addAction("删除此项", lambda: self._cloud_delete_item(item))
        menu.exec(self._cloud_tree.viewport().mapToGlobal(pos))

    def _cloud_delete_item(self, item):
        """删除当前云扫描记录，并同步清理结果缓存。"""
        vals = tuple(item.text(i) for i in range(6))
        idx = self._cloud_tree.indexOfTopLevelItem(item)
        if idx >= 0:
            self._cloud_tree.takeTopLevelItem(idx)
        self._cloud_all_items = [v for v in self._cloud_all_items if tuple(str(x) for x in v) != vals]
        self._cloud_row_results.pop(id(item), None)
        self._cloud_result_by_vals.pop(vals, None)
        self._cloud_update_status()

    def _cloud_show_result(self, name, result):
        """在手动调用结果区展示选中云函数调用的返回内容。"""
        detail = json.dumps(result, ensure_ascii=False, indent=2, default=str)
        c = _TH[self._tn]
        self._cloud_result.setHtml(f'<span style="color:{c["text1"]}">「{name}」返回结果:\n{detail}</span>')
        self._update_cloud_result_actions()

    def _cloud_copy_result(self):
        """复制云函数手动调用或右键查看区域中的结果文本。"""
        text = self._cloud_result.toPlainText().strip()
        if not text:
            self._log_add("warn", "[云扫描] 当前没有可复制的结果")
            return
        QApplication.clipboard().setText(text)
        self._log_add("info", "[云扫描] 已复制结果")

    def _update_cloud_result_actions(self):
        """根据结果区域内容更新云扫描结果复制按钮状态。"""
        if hasattr(self, "_btn_cloud_copy_result"):
            self._btn_cloud_copy_result.setEnabled(bool(self._cloud_result.toPlainText().strip()))

    def _cloud_update_status(self):
        """刷新云扫描记录计数和空状态提示。"""
        count = self._cloud_tree.topLevelItemCount()
        total = len(self._cloud_all_items)
        kw = self._cloud_search_ent.text().strip() if hasattr(self, "_cloud_search_ent") else ""
        if count < total:
            self._cloud_status_lbl.setText(f"显示: {count} / {total} 条")
        else:
            self._cloud_status_lbl.setText(f"捕获: {count} 条")
        if hasattr(self, "_cloud_filter_count_lbl"):
            self._cloud_filter_count_lbl.setText(f"筛选: {count} / {total}" if kw else "")
        if hasattr(self, "_btn_cloud_copy_visible"):
            self._btn_cloud_copy_visible.setEnabled(count > 0)
        if hasattr(self, "_btn_cloud_clear_search"):
            self._btn_cloud_clear_search.setEnabled(bool(kw))
        if hasattr(self, "_cloud_empty_hint"):
            if count:
                self._cloud_empty_hint.hide()
            else:
                if total:
                    self._cloud_empty_hint.setText("没有匹配的云函数记录。")
                else:
                    self._cloud_empty_hint.setText("等待捕获云函数、数据库、存储或容器调用记录。")
                self._cloud_empty_hint.show()

    def _cloud_filter(self):
        """按关键字过滤云扫描记录，并保留每行的返回结果关联。"""
        kw = self._cloud_search_ent.text().strip().lower()
        self._cloud_tree.clear()
        self._cloud_row_results.clear()
        for vals in self._cloud_all_items:
            if kw and not any(kw in str(v).lower() for v in vals):
                continue
            item = QTreeWidgetItem([str(v) for v in vals])
            self._cloud_tree.addTopLevelItem(item)
            result = self._cloud_result_by_vals.get(tuple(str(v) for v in vals))
            if result is not None:
                self._cloud_row_results[id(item)] = result
        self._cloud_update_status()

    def _cloud_clear_search(self):
        """清空云扫描记录搜索条件并恢复完整记录列表。"""
        if hasattr(self, "_cloud_search_ent"):
            self._cloud_search_ent.clear()
        self._cloud_filter()

    def _cloud_copy_visible_records(self):
        """复制当前表格中可见的云扫描记录。"""
        rows = []
        headers = ["AppID", "类型", "名称", "参数", "状态", "时间"]
        for i in range(self._cloud_tree.topLevelItemCount()):
            item = self._cloud_tree.topLevelItem(i)
            rows.append("\t".join(item.text(col) for col in range(6)))
        if not rows:
            self._log_add("warn", "[云扫描] 当前没有可复制的记录")
            return
        QApplication.clipboard().setText("\t".join(headers) + "\n" + "\n".join(rows))
        self._log_add("info", f"[云扫描] 已复制 {len(rows)} 条记录")

    def _cloud_on_select(self, item):
        """选中云扫描记录时，将函数名和参数同步到手动调用区域。"""
        if item and item.columnCount() >= 4:
            self._cloud_name_ent.setText(item.text(2))
            data_str = item.text(3).strip()
            try:
                json.loads(data_str)
                self._cloud_data_ent.setText(data_str)
            except Exception:
                self._cloud_data_ent.setText("{}")

    def _cloud_ensure_auditor(self):
        if not self._engine or not self._loop or not self._loop.is_running():
            self._log_add("error", "[云扫描] 请先启动调试")
            return False
        if not self._auditor:
            self._auditor = CloudAuditor(self._engine)
        return True

    def _cloud_do_toggle(self):
        if not self._cloud_ensure_auditor():
            return
        if self._cloud_scan_active:
            self._cloud_stop_scan()
        else:
            self._cloud_start_scan()

    def _cloud_start_scan(self):
        if not self._cloud_ensure_auditor():
            return
        self._cloud_scan_active = True
        c = _TH[self._tn]
        self._btn_cloud_toggle.setText("停止捕获")
        self._cloud_scan_lbl.setText("捕获中...")
        self._cloud_scan_lbl.setStyleSheet(f"color: {c['success']};")
        self._log_add("info", "[云扫描] 全局捕获已启动")
        asyncio.run_coroutine_threadsafe(self._acloud_start(), self._loop)
        self._cloud_scan_poll()

    async def _acloud_start(self):
        try:
            await self._auditor.start()
        except Exception as e:
            self._log_q.put(("error", f"[云扫描] Hook 启动异常: {e}"))

    def _cloud_stop_scan(self):
        self._cloud_scan_active = False
        c = _TH[self._tn]
        self._btn_cloud_toggle.setText("开启捕获")
        self._cloud_scan_lbl.setText("已停止")
        self._cloud_scan_lbl.setStyleSheet(f"color: {c['text3']};")
        if self._cloud_scan_poll_timer:
            self._cloud_scan_poll_timer.stop()
            self._cloud_scan_poll_timer = None
        if self._auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auditor.stop(), self._loop)
        self._log_add("info", "[云扫描] 全局捕获已停止")

    def _cloud_scan_poll(self):
        if not self._cloud_scan_active or not self._auditor:
            return
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._acloud_poll(), self._loop)
        self._cloud_scan_poll_timer = QTimer()
        self._cloud_scan_poll_timer.setSingleShot(True)
        self._cloud_scan_poll_timer.timeout.connect(self._cloud_scan_poll)
        self._cloud_scan_poll_timer.start(2000)

    async def _acloud_poll(self):
        try:
            new_calls = await self._auditor.poll()
            if new_calls:
                self._cld_q.put(("new_calls", new_calls))
        except Exception:
            pass

    def _cloud_do_static_scan(self):
        if not self._cloud_ensure_auditor():
            return
        self._btn_cloud_static.setEnabled(False)
        self._log_add("info", "[云扫描] 开始静态扫描 JS 源码...")
        asyncio.run_coroutine_threadsafe(self._acloud_static_scan(), self._loop)

    async def _acloud_static_scan(self):
        try:
            def progress(msg):
                self._log_q.put(("info", f"[云扫描] {msg}"))
            results = await self._auditor.static_scan(on_progress=progress)
            self._cld_q.put(("static_results", results))
        except Exception as e:
            self._log_q.put(("error", f"[云扫描] 静态扫描异常: {e}"))
        finally:
            self._cld_q.put(("static_done",))

    def _cloud_do_clear(self):
        """清空云扫描记录、结果缓存和界面筛选状态。"""
        self._cloud_tree.clear()
        self._cloud_all_items.clear()
        self._cloud_row_results.clear()
        self._cloud_result_by_vals.clear()
        if hasattr(self, "_cloud_search_ent"):
            self._cloud_search_ent.clear()
        if hasattr(self, "_cloud_result"):
            self._cloud_result.clear()
            self._update_cloud_result_actions()
        if self._auditor and self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._auditor.clear(), self._loop)
        self._cloud_update_status()

    def _cloud_do_call(self):
        """校验手动调用参数，并向云扫描后台发起云函数调用。"""
        if not self._cloud_ensure_auditor():
            return
        name = self._cloud_name_ent.text().strip()
        if not name:
            self._cloud_result.setPlainText("请输入函数名")
            self._update_cloud_result_actions()
            return
        try:
            data = json.loads(self._cloud_data_ent.text())
        except (json.JSONDecodeError, TypeError):
            self._cloud_result.setPlainText("参数 JSON 格式错误")
            self._update_cloud_result_actions()
            return
        self._btn_cloud_call.setEnabled(False)
        self._cloud_result.setPlainText(f"正在调用 {name} ...")
        self._update_cloud_result_actions()
        asyncio.run_coroutine_threadsafe(self._acloud_call(name, data), self._loop)

    async def _acloud_call(self, name, data):
        try:
            res = await self._auditor.call_function(name, data)
            self._cld_q.put(("call_result", name, res))
        except Exception as e:
            self._cld_q.put(("call_result", name, {"ok": False, "status": "fail",
                                                    "error": str(e)}))

    def _cloud_do_export(self):
        if not self._auditor:
            self._log_add("error", "[云扫描] 无数据")
            return
        report = self._auditor.export_report(self._cloud_all_items, self._cloud_call_history)
        path = os.path.join(_BASE_DIR, "cloud_audit_report.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            self._log_add("info", f"[云扫描] 报告已导出: {path}")
        except Exception as e:
            self._log_add("error", f"[云扫描] 导出失败: {e}")

    # ──────────────────────────────────
    #  轮询
    # ──────────────────────────────────

    def _tick(self):
        for _ in range(60):  # 每轮最多处理60条日志，防止阻塞UI
            try:
                msg = self._log_q.get_nowait()
            except queue.Empty:
                break
            if isinstance(msg, tuple) and len(msg) == 3 and msg[0] == "__hook_status__":
                _, fn, ok = msg
                self._hook_update_status(fn, ok)
            else:
                lv, tx = msg
                self._log_add(lv, tx)
        last_sts = None
        for _ in range(50):
            try:
                last_sts = self._sts_q.get_nowait()
            except queue.Empty:
                break
        if last_sts is not None:
            self._apply_sts(last_sts)
        for _ in range(50):
            try:
                item = self._rte_q.get_nowait()
            except queue.Empty:
                break
            self._handle_rte(item)
        for _ in range(50):
            try:
                item = self._cld_q.get_nowait()
            except queue.Empty:
                break
            self._handle_cld(item)
        for _ in range(50):
            try:
                item = self._ext_q.get_nowait()
            except queue.Empty:
                break
            self._handle_ext(item)
        for _ in range(50):
            try:
                item = self._mcp_q.get_nowait()
            except queue.Empty:
                break
            self._handle_mcp(item)

    def _handle_mcp(self, item):
        """Apply MCP service events that were queued from background threads."""
        kind = item[0]
        if kind == "log":
            self._mcp_add_log(item[1])
        elif kind == "targets":
            self._refresh_mcp_target_combo(item[1])

    def _apply_sts(self, sts):
        """更新主界面连接状态，并在小程序连接变化时触发相关后台动作。"""
        c = _TH[self._tn]
        self._last_sts = dict(sts)
        is_connected = sts.get("miniapp", False)
        for key, (dot, lb, name) in self._dots.items():
            on = sts.get(key, False)
            dot.set_color(c["success"] if on else c["text4"])
            state_text = "已连接" if on else "未连接"
            lb.setText(f"{name}: {state_text}")
            dot.setToolTip(f"{name}: {state_text}")
            lb.setToolTip(f"{name}: {state_text}")
            lb.setStyleSheet(f"color: {c['success'] if on else c['text2']};")
        self._update_target_badge(is_connected)
        self._update_mcp_debug_status(sts)
        # 断开时立即禁用（除了已有路由时保留导航按钮）
        if not is_connected and self._miniapp_connected:
            if not self._all_routes:
                self._nav_btns(False)
            self._btn_vc_enable.setEnabled(False)
            self._btn_vc_disable.setEnabled(False)
            self._btn_vc_detect.setEnabled(False)
            self._vc_status_lbl.setText("状态: 未连接小程序")
            # 清除注入标记，切换小程序时全局脚本会重新注入
            self._hook_injected.clear()
            self._hook_refresh()
            # 已有路由数据时不清除侧栏信息（短暂断连不影响）
            if not self._all_routes:
                self._sb_fetch_gen += 1
                gen = self._sb_fetch_gen
                QTimer.singleShot(5000, lambda: self._delayed_clear_app_info(gen))
        # 小程序连接时，独立定时器触发全局 Hook 注入（不受 CDP 等状态变化影响）
        if is_connected and not self._miniapp_connected and self._global_hook_scripts:
            self._global_inject_gen += 1
            _gi_gen = self._global_inject_gen
            QTimer.singleShot(1500, lambda: self._do_global_inject(_gi_gen))
        if is_connected and not self._miniapp_connected:
            QTimer.singleShot(700, self._apply_devtools_breakpoint_mode)
        # 连接时延迟启用，等连接稳定（防止重启时反复抖动）
        self._vc_stable_gen += 1
        gen_stable = self._vc_stable_gen
        if is_connected:
            QTimer.singleShot(1500, lambda: self._delayed_stable_connect(gen_stable))
        self._miniapp_connected = is_connected
        self._update_flow_steps(sts)

    def _handle_rte(self, item):
        kind = item[0]
        if kind == "routes":
            _, pages, tab = item
            self._all_routes = list(pages)
            self._fill_tree(pages, tab)
        elif kind == "app_info":
            info = item[1]
            aid = info.get("appid", "")
            aname = info.get("name", "")
            ent = info.get("entry", "")
            if aid and self._current_app_id and aid != self._current_app_id:
                self._mcp_reset_runtime_script_cache()
            self._current_app_name = aname
            self._current_app_id = aid
            self._mcp_appid = aid
            self._update_mcp_debug_status()
            # 运行状态卡片 — appid
            txt = f"AppID: {aid}" if aid else "AppID: --"
            if ent:
                txt += f"  |  入口: {ent}"
            self._app_lbl.setText(txt)
            # 运行状态卡片 — 名称
            if aname:
                self._appname_lbl.setText(f"应用: {aname}")
            else:
                self._appname_lbl.setText("应用: --")
            self._update_target_badge(bool(aname or aid or self._miniapp_connected))
            if hasattr(self, "_control_route_lbl") and ent:
                self._control_route_lbl.setText(f"入口: /{ent}")
        elif kind == "current":
            r = item[1]
            self._mcp_route = r
            self._update_mcp_debug_status()
            self._route_lbl.setText(f"当前路由: /{r}" if r else "当前路由: --")
            if hasattr(self, "_control_route_lbl"):
                self._control_route_lbl.setText(f"当前路由: /{r}" if r else "当前路由: --")
            if r:
                routes = self._flat_routes or self._all_routes
                if r in routes:
                    self._nav_route_idx = routes.index(r)
                    self._select_tree_route(r)
        elif kind == "progress":
            _, i, total, route = item
            if total > 0:
                self._prog.setValue(int((i / total) * 100))
            if route != "done":
                self._select_tree_route(route)
            self._route_lbl.setText(
                f"正在访问: /{route}" if route != "done" else "遍历完成")
        elif kind == "blocked":
            blocked = item[1]
            for b in blocked[self._blocked_seen:]:
                self._log_add("warn",
                    f"[防跳转] 拦截 {b.get('type','')} → {b.get('url','')}  ({b.get('time','')})")
            self._blocked_seen = len(blocked)
        elif kind == "auto_done":
            self._prog.setValue(100)
            self._btn_auto.setEnabled(True)
            self._btn_autostop.setEnabled(False)
            self._log_add("info", "[导航] 遍历完成")
        elif kind == "__vc__":
            _, enable, ok = item
            c = _TH[self._tn]
            if ok:
                if enable:
                    self._vc_status_lbl.setText("状态: 已开启 (重启小程序后生效)")
                    self._vc_status_lbl.setStyleSheet(f"color: {c['success']};")
                else:
                    self._vc_status_lbl.setText("状态: 已关闭 (重启小程序后生效)")
                    self._vc_status_lbl.setStyleSheet(f"color: {c['text3']};")
            else:
                self._vc_status_lbl.setText("状态: 操作失败")
                self._vc_status_lbl.setStyleSheet(f"color: {c['error']};")
            self._btn_vc_enable.setEnabled(True)
            self._btn_vc_disable.setEnabled(True)
            self._btn_vc_detect.setEnabled(True)
        elif kind == "__vc_detect__":
            is_debug = item[1]
            c = _TH[self._tn]
            if is_debug:
                self._vc_status_lbl.setText("状态: 已开启")
                self._vc_status_lbl.setStyleSheet(f"color: {c['success']};")
            else:
                self._vc_status_lbl.setText("状态: 未开启")
                self._vc_status_lbl.setStyleSheet(f"color: {c['text3']};")
            self._btn_vc_detect.setEnabled(True)
        elif kind == "__vc_detect_failed__":
            self._vc_status_lbl.setText("状态: 检测失败")
            self._vc_status_lbl.setStyleSheet(f"color: {_TH[self._tn]['error']};")
            self._btn_vc_detect.setEnabled(True)
            self._log_add("error", f"[调试] 状态检测失败: {item[1]}")

    def _handle_cld(self, item):
        kind = item[0]
        c = _TH[self._tn]
        _type_cn = {"function": "云函数", "storage": "存储", "container": "容器"}
        if kind == "new_calls":
            calls = item[1]
            if calls:
                kw = self._cloud_search_ent.text().strip().lower()
                for call in calls:
                    data_str = json.dumps(call.get("data", {}), ensure_ascii=False)
                    if len(data_str) > 80:
                        data_str = data_str[:77] + "..."
                    ctype = call.get("type", "function")
                    type_label = _type_cn.get(ctype, ctype)
                    if ctype.startswith("db"):
                        type_label = "数据库"
                    status = call.get("status", "")
                    vals = (call.get("appId", ""), type_label,
                            call.get("name", ""), data_str,
                            status, call.get("timestamp", ""))
                    self._cloud_all_items.append(vals)
                    if kw and not any(kw in str(v).lower() for v in vals):
                        continue
                    tree_item = QTreeWidgetItem([str(v) for v in vals])
                    self._cloud_tree.addTopLevelItem(tree_item)
                    result_data = call.get("result") or call.get("error")
                    if result_data is not None:
                        result_record = {
                            "status": status,
                            "result": call.get("result"),
                            "error": call.get("error"),
                            "data": call.get("data"),
                        }
                        self._cloud_result_by_vals[tuple(str(v) for v in vals)] = result_record
                        self._cloud_row_results[id(tree_item)] = result_record
                self._cloud_tree.scrollToBottom()
                self._cloud_update_status()
                self._cloud_scan_lbl.setText(f"捕获中... {len(self._cloud_all_items)} 条")
                self._cloud_scan_lbl.setStyleSheet(f"color: {c['success']};")
        elif kind == "static_results":
            funcs = item[1]
            if funcs:
                kw = self._cloud_search_ent.text().strip().lower()
                for f in funcs:
                    params = ", ".join(f.get("params", [])) or "--"
                    if len(params) > 80:
                        params = params[:77] + "..."
                    ftype = f.get("type", "function")
                    type_label = {"function": "云函数", "storage": "存储",
                                  "database": "数据库"}.get(ftype, ftype)
                    vals = (f.get("appId", ""), f"[静态]{type_label}",
                            f["name"], params, f"x{f.get('count',1)}", "")
                    self._cloud_all_items.append(vals)
                    if kw and not any(kw in str(v).lower() for v in vals):
                        continue
                    tree_item = QTreeWidgetItem([str(v) for v in vals])
                    self._cloud_tree.addTopLevelItem(tree_item)
                self._cloud_tree.scrollToBottom()
                self._cloud_update_status()
                self._log_add("info", f"[云扫描] 静态扫描发现 {len(funcs)} 个云函数引用")
        elif kind == "static_done":
            self._btn_cloud_static.setEnabled(True)
        elif kind == "call_result":
            _, name, res = item
            self._btn_cloud_call.setEnabled(True)
            status = res.get("status", "unknown")
            if status == "success":
                detail = json.dumps(res.get("result", {}), ensure_ascii=False, default=str)
                self._cloud_result.setHtml(
                    f'<span style="color:{c["success"]}">{name} -> 成功:\n{detail}</span>')
            elif status == "fail":
                err = res.get("error", "") or res.get("reason", "未知错误")
                self._cloud_result.setHtml(
                    f'<span style="color:{c["error"]}">{name} -> 失败: {err}</span>')
            else:
                detail = json.dumps(res, ensure_ascii=False, default=str)
                self._cloud_result.setHtml(
                    f'<span style="color:{c["warning"]}">{name} -> {detail}</span>')
            self._update_cloud_result_actions()

    def _handle_ext(self, item):
        kind = item.get("type", "")
        c = _TH[self._tn]
        op = self._ext_current_op  # ("decompile"/"scan", appid) or None

        if kind == "progress":
            done = item.get("done", 0)
            total = item.get("total", 1)
            if total > 0:
                self._ext_prog.setValue(int((done / total) * 100))
            self._ext_status_lbl.setText(f"进度: {done}/{total}")

        elif kind == "log":
            self._ext_log(item.get("msg", ""))

        elif kind == "result":
            data = item.get("data", {})
            if op:
                op_type, appid = op
                if op_type == "decompile":
                    # 反编译完成
                    state = self._ext_app_states.setdefault(appid, {})
                    state["decompiled"] = True
                    decompile_dir = data.get("decompile_dir", "")
                    if decompile_dir:
                        state["decompile_dir"] = decompile_dir
                    extracted = data.get("extracted", 0)
                    self._ext_status_lbl.setText(f"反编译完成! {appid} 提取了 {extracted} 个文件")
                    self._ext_status_lbl.setStyleSheet(f"color: {c['success']};")
                    self._ext_update_app_buttons(appid)
                    # 刷新名称显示（解包后可读取 app-config.json）
                    widgets = self._ext_app_widgets.get(appid, {})
                    if "lbl_name" in widgets:
                        pkgs = state.get("packages", [])
                        output_base = os.path.join(_BASE_DIR, "output")
                        name = self._ext_get_app_name(appid, pkgs, output_base)
                        widgets["lbl_name"].setText(name)

                elif op_type == "scan":
                    # 扫描完成
                    state = self._ext_app_states.setdefault(appid, {})
                    state["scanned"] = True
                    result_dir = data.get("result_dir", "")
                    if result_dir:
                        state["result_dir"] = result_dir
                    findings = data.get("findings", 0)
                    self._ext_status_lbl.setText(f"扫描完成! {appid} 发现 {findings} 条敏感信息")
                    self._ext_status_lbl.setStyleSheet(f"color: {c['success']};")
                    self._ext_update_app_buttons(appid)

        elif kind == "error":
            self._ext_log(f"错误: {item.get('msg', '')}")
            self._ext_status_lbl.setText("出错")
            self._ext_status_lbl.setStyleSheet(f"color: {c['error']};")

        elif kind == "__done__":
            self._ext_proc = None
            prev_op = self._ext_current_op
            self._ext_current_op = None
            self._ext_prog.setValue(100)
            rc = item.get("returncode", -1)
            if rc != 0 and "完成" not in self._ext_status_lbl.text():
                self._ext_status_lbl.setText(f"进程退出 (code={rc})")
                self._ext_status_lbl.setStyleSheet(f"color: {c['error']};")

            # 自动处理链: 反编译完成后 → 自动扫描; 扫描完成后 → 处理下一个
            if prev_op and rc == 0:
                op_type, appid = prev_op
                if op_type == "decompile" and self._tog_auto_scan.isChecked():
                    state = self._ext_app_states.get(appid, {})
                    if state.get("decompiled") and not state.get("scanned"):
                        QTimer.singleShot(500, lambda a=appid: self._ext_do_scan(a))
                        return
                # 继续处理其他未完成的小程序
                QTimer.singleShot(500, self._ext_auto_process_pending)
    # ──────────────────────────────────
    #  退出
    # ──────────────────────────────────

    def closeEvent(self, event):
        self._mcp_detach_breakpoint_listeners()
        if self._mcp_service:
            try:
                self._mcp_service.stop()
            except Exception:
                pass
            self._mcp_service = None
        if self._ext_proc:
            try:
                self._ext_proc.kill()  # 强制杀死子进程
                self._ext_proc.wait(timeout=2)
            except Exception:
                pass
            self._ext_proc = None
        if self._running:
            self._do_stop()
            QTimer.singleShot(400, lambda: QApplication.quit())
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # PyInstaller 打包需要
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)   # Ctrl+C 直接退出

    # Windows 任务栏图标: 设置 AppUserModelID 使其显示自定义图标而非 Python 默认图标
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("spade.first.gui")
        except Exception:
            pass

    app = QApplication(sys.argv)
    _install_app_font()
    app.setFont(QFont(_FN, 9))
    _ico = os.path.join(_BASE_DIR, "icon.png")
    if os.path.exists(_ico):
        app.setWindowIcon(QIcon(_ico))
    window = App()
    window.show()
    sys.exit(app.exec())
