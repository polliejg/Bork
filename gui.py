"""Bork — Voice Tool UI (redesigned)."""
import math
import threading
import pyperclip
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QTimer, QPoint, QSize
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QPainterPath, QFont, QFontMetrics
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSpinBox,
    QSystemTrayIcon, QTextEdit, QVBoxLayout, QWidget,
    QGraphicsDropShadowEffect, QStackedWidget,
)

from app_state import AppState, Status
from enhancer import PRESETS, DEFAULT_PRESET, PROVIDERS, CONTEXT_SYSTEM_PROMPT
from workflow_engine import WorkflowEngine

VERSION = "0.2"

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":        "#0B0B0C",    # deep matte black
    "sidebar":   "#161618",    # dark slate
    "surface":   "#1C1C1E",    # card surface
    "surface2":  "#242426",    # input / nested card
    "surface3":  "#2C2C2E",    # hover
    "border":    "#2D2D30",    # standard border
    "border_hi": "#3D3D42",    # stronger border
    "text":      "#FFFFFF",    # pure white
    "text2":     "#A0A0A8",    # secondary
    "dim":       "#56565C",    # muted
    "brand":     "#007AFF",    # electric blue
    "brand_bg":  "#001F40",    # dark blue tint
    "brand2":    "#0055CC",    # deeper blue
    "green":     "#30D158",    # system green
    "red":       "#FF453A",    # system red
    "orange":    "#FF9F0A",    # warm amber (status only)
    "purple":    "#BF5AF2",    # system purple
}

STATUS_META = {
    Status.LOADING:      (C["dim"],   "Loading..."),
    Status.IDLE:         (C["dim"],   "Snoozing"),     # muted grey dot
    Status.RECORDING:    (C["text"],  "Borking..."),   # white glow pulse
    Status.TRANSCRIBING: (C["text2"], "Transcribing"),
    Status.ENHANCING:    (C["brand"], "Enhancing"),
}

STYLESHEET = f"""
/* ── Reset — Inter/Geist font, pure-white text, zero platform bleed ─ */
* {{
    font-family: 'Inter', 'Geist', 'Segoe UI Variable', 'Segoe UI', sans-serif;
    font-size: 13px;
    font-weight: 400;
    color: {C["text"]};
}}
QMainWindow, QDialog {{
    background-color: {C["bg"]};
    color: {C["text"]};
}}
QWidget {{
    background-color: transparent;
    color: {C["text"]};
}}
QLabel {{
    color: {C["text"]};
    background-color: transparent;
    font-weight: 400;
}}
QLabel[class="title"] {{
    font-weight: 600;
}}
QCheckBox, QRadioButton {{
    color: {C["text"]};
    background-color: transparent;
}}
QGroupBox {{
    color: {C["text"]};
    font-weight: 600;
    border: 1px solid {C["border"]};
    border-radius: 8px;
    margin-top: 6px;
    padding-top: 8px;
}}
QTabWidget::pane {{
    background-color: {C["surface"]};
    border: 1px solid {C["border"]};
    border-radius: 0 10px 10px 10px;
}}
QTabBar::tab {{
    background-color: {C["surface2"]};
    color: {C["text2"]};
    padding: 7px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border: 1px solid {C["border"]};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background-color: {C["surface"]};
    color: {C["text"]};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{ color: {C["text"]}; }}
QMenu {{
    background-color: {C["surface2"]};
    border: 1px solid {C["border"]};
    border-radius: 8px;
    color: {C["text"]};
    padding: 4px;
}}
QMenu::item {{
    color: {C["text"]};
    padding: 7px 16px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {C["brand_bg"]};
    color: {C["brand"]};
}}
QMenu::separator {{
    height: 1px;
    background: {C["border"]};
    margin: 4px 8px;
}}
QToolTip {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}}
/* ── Frames ───────────────────────────────────────────────────────── */
QFrame#card {{
    background-color: {C["surface"]};
    border-radius: 12px;
    border: 1px solid {C["border"]};
}}
QFrame#innercard {{
    background-color: rgba(255,255,255,0.03);
    border-radius: 10px;
    border: 1px solid {C["border"]};
}}
QFrame#sep {{
    background-color: {C["border"]};
    border: none;
    max-height: 1px; min-height: 1px;
}}
/* ── Inputs ───────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QTextEdit, QSpinBox {{
    background-color: rgba(255,255,255,0.03);
    border: 1px solid {C["border"]};
    border-radius: 8px;
    padding: 7px 11px;
    color: {C["text"]};
    selection-background-color: {C["brand_bg"]};
    selection-color: {C["text"]};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {C["brand"]};
    background-color: rgba(0,122,255,0.05);
}}
QLineEdit:read-only {{
    color: {C["dim"]};
    background-color: rgba(255,255,255,0.02);
}}
QLineEdit#kbd {{
    font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    font-weight: 500;
    background-color: rgba(255,255,255,0.05);
    border: 1px solid {C["border_hi"]};
    border-bottom: 2px solid {C["border_hi"]};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C["text"]};
    letter-spacing: 0.3px;
}}
QLineEdit#kbd:focus {{
    border-color: {C["brand"]};
    border-bottom-color: {C["brand2"]};
    background-color: rgba(0,122,255,0.06);
}}
QComboBox {{
    color: {C["text"]};
}}
QComboBox::drop-down {{
    border: none;
    border-left: 1px solid {C["border"]};
    width: 26px;
    background: rgba(255,255,255,0.04);
    border-radius: 0 7px 7px 0;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}}
QComboBox::down-arrow {{
    width: 10px; height: 10px;
}}
QComboBox QAbstractItemView {{
    background-color: {C["surface2"]};
    color: {C["text"]};
    border: 1px solid {C["border"]};
    selection-background-color: {C["brand_bg"]};
    selection-color: {C["text"]};
    outline: none;
    padding: 4px;
    border-radius: 8px;
}}
QAbstractItemView {{
    color: {C["text"]};
    background-color: {C["surface2"]};
}}
QSpinBox {{
    color: {C["text"]};
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: rgba(255,255,255,0.06);
    border: none;
    width: 16px;
    border-radius: 4px;
}}
/* ── Buttons ──────────────────────────────────────────────────────── */
QPushButton {{
    background-color: rgba(255,255,255,0.06);
    border: 1px solid {C["border"]};
    border-radius: 8px;
    padding: 8px 16px;
    color: {C["text"]};
    font-weight: 400;
    outline: none;
}}
QPushButton:hover {{
    background-color: rgba(255,255,255,0.10);
    border-color: {C["border_hi"]};
    color: {C["text"]};
}}
QPushButton:pressed {{
    background-color: rgba(255,255,255,0.14);
}}
QPushButton:disabled {{
    color: {C["dim"]};
    border-color: rgba(255,255,255,0.05);
    background-color: rgba(255,255,255,0.02);
}}
/* Primary — Electric Blue, white text, semi-bold */
QPushButton#primary {{
    background-color: {C["brand"]};
    border: none;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
    padding: 11px 24px;
    border-radius: 10px;
    letter-spacing: 0.1px;
}}
QPushButton#primary:hover {{
    background-color: #1A8FFF;
    border: none;
}}
QPushButton#primary:pressed {{
    background-color: {C["brand2"]};
    border: none;
}}
QPushButton#primary:disabled {{
    background-color: {C["surface2"]};
    color: {C["dim"]};
}}
/* Ghost — minimal border, no background */
QPushButton#ghost {{
    background-color: transparent;
    border: 1px solid {C["border"]};
    color: {C["text2"]};
    padding: 5px 12px;
    font-size: 12px;
    border-radius: 7px;
}}
QPushButton#ghost:hover {{
    color: {C["text"]};
    border-color: {C["border_hi"]};
    background-color: rgba(255,255,255,0.05);
}}
QPushButton#ghost_brand {{
    background-color: transparent;
    border: 1px solid {C["brand"]};
    color: {C["brand"]};
    padding: 4px 10px;
    font-size: 11px;
    border-radius: 6px;
}}
QPushButton#ghost_brand:hover {{
    background-color: {C["brand_bg"]};
    color: {C["text"]};
}}
/* Preset pills */
QPushButton#preset {{
    background-color: rgba(255,255,255,0.04);
    border: 1px solid {C["border"]};
    color: {C["text2"]};
    padding: 5px 14px;
    font-size: 12px;
    border-radius: 14px;
}}
QPushButton#preset:hover {{
    color: {C["text"]};
    border-color: {C["border_hi"]};
    background-color: rgba(255,255,255,0.07);
}}
QPushButton#preset_active {{
    background-color: {C["brand_bg"]};
    border: 1px solid {C["brand"]};
    color: {C["text"]};
    padding: 5px 14px;
    font-size: 12px;
    border-radius: 14px;
    font-weight: 600;
}}
/* Danger */
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid rgba(255,69,58,0.50);
    color: {C["red"]};
    padding: 5px 12px;
    font-size: 12px;
    border-radius: 7px;
}}
QPushButton#danger:hover {{
    background-color: rgba(255,69,58,0.10);
    border-color: {C["red"]};
}}
/* ── Sidebar nav ──────────────────────────────────────────────────── */
QPushButton#nav {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    color: {C["text2"]};
    font-size: 13px;
    font-weight: 400;
    text-align: left;
}}
QPushButton#nav:hover {{
    background-color: rgba(255,255,255,0.05);
    color: {C["text"]};
}}
QPushButton#nav_active {{
    background-color: rgba(0,122,255,0.12);
    border: none;
    border-left: 2px solid {C["brand"]};
    border-radius: 8px;
    padding: 9px 12px;
    color: {C["text"]};
    font-size: 13px;
    font-weight: 600;
    text-align: left;
}}
/* ── Misc ─────────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: rgba(255,255,255,0.06);
    border: none;
    border-radius: 3px;
    max-height: 3px;
    min-height: 3px;
}}
QProgressBar::chunk {{
    border-radius: 3px;
    background-color: {C["text"]};
}}
QListWidget {{
    background-color: transparent;
    border: none;
    outline: none;
    color: {C["text"]};
}}
QListWidget::item {{
    color: {C["text"]};
    border-radius: 6px;
    padding: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {C["brand_bg"]};
    color: {C["text"]};
}}
QListWidget::item:hover:!selected {{
    background-color: rgba(255,255,255,0.04);
}}
QScrollBar:vertical {{
    background: transparent; width: 4px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.15);
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255,255,255,0.30);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollArea {{ border: none; }}
"""


# ── Paw icon (Bork branding) ──────────────────────────────────────────────────

def _paw_pixmap(size: int, color: str) -> QPixmap:
    """Draw a paw-print icon — swap this function to use a real image file if preferred."""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))

    s = float(size)

    # Main central pad — large rounded ellipse in lower half
    pw, ph = s * 0.48, s * 0.38
    p.drawEllipse(QRectF(s * 0.50 - pw / 2, s * 0.54 - ph / 2, pw, ph))

    # Four toe pads — arranged in an arc above the main pad
    toe_r = s * 0.11
    for tx, ty in [
        (s * 0.20, s * 0.32),
        (s * 0.38, s * 0.18),
        (s * 0.62, s * 0.18),
        (s * 0.80, s * 0.32),
    ]:
        p.drawEllipse(QRectF(tx - toe_r, ty - toe_r, toe_r * 2, toe_r * 2))

    p.end()
    return px


# Keep alias so any future code can call _ghost_pixmap and still get the paw
_ghost_pixmap = _paw_pixmap


# ── Small helpers ─────────────────────────────────────────────────────────────

def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    return f


def _label(text: str, color: str = None, size: int = None, bold: bool = False) -> QLabel:
    lbl = QLabel(text)
    style = ""
    if color:
        style += f"color:{color};"
    if size:
        style += f"font-size:{size}px;"
    if bold:
        style += "font-weight:600;"
    if style:
        lbl.setStyleSheet(style)
    return lbl


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color:{C['dim']}; font-size:10px; font-weight:600; letter-spacing:1.8px;")
    return lbl


def _row(layout: QVBoxLayout, label_text: str, widget: QWidget, label_width: int = 120):
    row = QHBoxLayout()
    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color:{C['text2']}; font-size:12px;")
    lbl.setFixedWidth(label_width)
    row.addWidget(lbl)
    row.addWidget(widget, 1)
    layout.addLayout(row)


def _card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


def _inner_card() -> QFrame:
    f = QFrame()
    f.setObjectName("innercard")
    return f


def _kbd_label(key_text: str) -> QLabel:
    lbl = QLabel(key_text)
    lbl.setStyleSheet(
        f"font-family:'SF Mono','Cascadia Code','Consolas',monospace;"
        f"font-size:11px; font-weight:500; color:{C['text']};"
        f"background:rgba(255,255,255,0.06); border:1px solid {C['border_hi']};"
        f"border-bottom:2px solid {C['border_hi']};"
        f"border-radius:5px; padding:3px 8px;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


# ── PulseAuraWidget ───────────────────────────────────────────────────────────

class PulseAuraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self._color = QColor(C["dim"])
        self._recording = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)

    def set_status(self, color: str, recording: bool):
        self._color = QColor(color)
        self._recording = recording
        if recording:
            self._timer.start()
        else:
            self._timer.stop()
            self._phase = 0.0
        self.update()

    def _tick(self):
        self._phase += 0.12
        if self._phase > math.tau:
            self._phase -= math.tau
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2

        if self._recording:
            for i, (base_r, base_a) in enumerate([(32, 35), (24, 55), (18, 75)]):
                offset = math.sin(self._phase + i * 0.9) * 5
                r = base_r + offset
                col = QColor(self._color)
                col.setAlpha(int(base_a + math.sin(self._phase + i) * 15))
                p.setBrush(col)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        px = _ghost_pixmap(40, self._color.name())
        p.drawPixmap(int(cx - 20), int(cy - 20), px)
        p.end()


# ── StatusBadge ───────────────────────────────────────────────────────────────

class StatusBadge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(C["dim"])
        self._text = "Loading"
        self.setFixedHeight(26)
        self.setMinimumWidth(90)

    def set_status(self, color: str, text: str):
        self._color = QColor(color)
        self._text = text
        self.update()
        self.updateGeometry()

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        return QSize(fm.horizontalAdvance(self._text) + 38, 26)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(self._color)
        bg.setAlpha(30)
        border = QColor(self._color)
        border.setAlpha(120)
        p.setBrush(bg)
        p.setPen(border)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.drawRoundedRect(rect, 13, 13)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(QRectF(9, 8, 10, 10))

        p.setPen(self._color)
        p.setFont(QFont("Segoe UI Variable", 10, QFont.Weight.Bold))
        p.drawText(QRectF(25, 0, self.width() - 30, self.height()),
                   Qt.AlignmentFlag.AlignVCenter, self._text)
        p.end()


# ── StatusDot ────────────────────────────────────────────────────────────────

class StatusDot(QWidget):
    def __init__(self, size=10, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size + 4, size + 4)
        self._color = QColor(C["dim"])

    def set_color(self, hex_color: str):
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, self._size, self._size)
        p.end()


# ── TranscriptCard ────────────────────────────────────────────────────────────

class TranscriptCard(QWidget):
    def __init__(self, text: str, on_copy=None, on_insert=None, parent=None):
        super().__init__(parent)
        self._text = text
        self._hovered = False
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.ArrowCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(6)

        self._lbl = QLabel()
        self._lbl.setStyleSheet(
            f"color:{C['text']}; background:transparent; font-size:12px;")
        fm = QFontMetrics(self._lbl.font())
        elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, 300)
        self._lbl.setText(elided)
        self._lbl.setToolTip(text)
        layout.addWidget(self._lbl, 1)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setObjectName("ghost")
        self._copy_btn.setFixedSize(48, 24)
        self._copy_btn.setStyleSheet(
            f"QPushButton {{ font-size:11px; padding:0 6px; border-radius:5px;"
            f" color:{C['text2']}; background:transparent;"
            f" border:1px solid rgba(255,255,255,0.10); }}"
            f"QPushButton:hover {{ color:{C['text']}; border-color:rgba(0,122,255,0.55);"
            f" background:rgba(0,122,255,0.08); }}")
        self._copy_btn.hide()

        self._insert_btn = QPushButton("Insert")
        self._insert_btn.setObjectName("ghost_brand")
        self._insert_btn.setFixedSize(52, 24)
        self._insert_btn.setStyleSheet(
            f"QPushButton {{ font-size:11px; padding:0 6px; border-radius:5px;"
            f" border:1px solid {C['brand']}; color:{C['brand']}; background:transparent; }}"
            f"QPushButton:hover {{ background:{C['brand_bg']}; }}")
        self._insert_btn.hide()

        layout.addWidget(self._copy_btn)
        layout.addWidget(self._insert_btn)

        if on_copy:
            self._copy_btn.clicked.connect(on_copy)
        if on_insert:
            self._insert_btn.clicked.connect(on_insert)

    def enterEvent(self, event):
        self._hovered = True
        self._copy_btn.show()
        self._insert_btn.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._copy_btn.hide()
        self._insert_btn.hide()
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _):
        from PyQt6.QtGui import QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hovered:
            p.setBrush(QColor(255, 255, 255, 10))
            p.setPen(QPen(QColor(255, 255, 255, 35), 1))
        else:
            p.setBrush(QColor(C["surface2"]))
            p.setPen(QPen(QColor(C["border"]), 1))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 10, 10)
        p.end()


# ── Workflow dialog ───────────────────────────────────────────────────────────

class WorkflowDialog(QDialog):
    def __init__(self, workflow: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Workflow" if workflow else "New Workflow")
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(STYLESHEET + f"""
            QDialog {{
                background-color: {C["surface"]};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(30, 28, 30, 28)

        layout.addWidget(_section_label("Name"))
        self._name = QLineEdit(workflow.get("name", "") if workflow else "")
        layout.addWidget(self._name)

        layout.addWidget(_section_label("Trigger phrases — one per line"))
        self._phrases = QTextEdit()
        self._phrases.setMaximumHeight(88)
        if workflow:
            self._phrases.setPlainText("\n".join(workflow.get("phrases", [])))
        layout.addWidget(self._phrases)

        layout.addWidget(_section_label("Action type"))
        self._action_type = QComboBox()
        self._action_type.addItems(["exec", "keys", "type_text"])
        layout.addWidget(self._action_type)

        layout.addWidget(_section_label("Command / keys (comma-separated) / text"))
        self._command = QLineEdit()
        if workflow and workflow.get("actions"):
            a = workflow["actions"][0]
            t = a.get("type", "exec")
            self._action_type.setCurrentText(t)
            if t == "exec":
                self._command.setText(a.get("command", ""))
            elif t == "keys":
                self._command.setText(", ".join(a.get("keys", [])))
            elif t == "type_text":
                self._command.setText(a.get("text", ""))
        layout.addWidget(self._command)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("ghost")
        save = QPushButton("Save")
        save.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addWidget(save)
        layout.addLayout(btns)

    def get_workflow(self) -> dict:
        phrases = [p.strip() for p in self._phrases.toPlainText().splitlines() if p.strip()]
        atype = self._action_type.currentText()
        cmd = self._command.text().strip()
        action: dict = {"type": atype}
        if atype == "exec":
            action["command"] = cmd
        elif atype == "keys":
            action["keys"] = [k.strip() for k in cmd.split(",")]
        elif atype == "type_text":
            action["text"] = cmd
        return {"name": self._name.text().strip(), "phrases": phrases, "actions": [action]}


# ── Context popup ─────────────────────────────────────────────────────────────

class ContextPopup(QWidget):
    """Floating top-right chat popup for context-mode Q&A."""

    _sig_answer = pyqtSignal(str)
    _sig_error  = pyqtSignal(str)
    _sig_busy   = pyqtSignal(bool)

    def __init__(self, context_text: str, question: str, answer: str,
                 messages: list, enhancer, ai_cfg: dict, parent=None):
        super().__init__(parent)
        self._enhancer = enhancer
        self._ai_cfg   = ai_cfg
        self._messages = list(messages)
        self._drag_pos = QPoint()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(400)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self._build_ui(context_text, question, answer)
        self._sig_answer.connect(self._on_answer)
        self._sig_error.connect(self._on_error)
        self._sig_busy.connect(self._on_busy)
        self._position_top_right()

    def _build_ui(self, context_text: str, question: str, answer: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        self._container = QFrame()
        self._container.setObjectName("popupcontainer")
        self._container.setStyleSheet(f"""
            QFrame#popupcontainer {{
                background-color: {C["surface"]};
                border: 1px solid rgba(0,122,255,0.30);
                border-radius: 14px;
            }}
        """)

        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet(
            f"background:{C['surface2']}; border-radius:14px 14px 0 0;")
        title_bar.setFixedHeight(44)
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(14, 0, 10, 0)

        ghost_lbl = QLabel()
        ghost_lbl.setPixmap(_ghost_pixmap(18, C["brand"]))
        ghost_lbl.setFixedSize(18, 18)
        tb.addWidget(ghost_lbl)
        tb.addSpacing(6)

        title = QLabel("Bork")
        title.setStyleSheet(
            f"font-weight:bold; font-size:13px; color:{C['text']}; background:transparent;")
        tb.addWidget(title)
        tb.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:none;
                color:{C['text2']}; font-size:14px; border-radius:6px;
            }}
            QPushButton:hover {{ background:{C['surface3']}; color:{C['text']}; }}
        """)
        close_btn.clicked.connect(self.close)
        tb.addWidget(close_btn)
        inner.addWidget(title_bar)

        # Context snippet
        ctx_w = QWidget()
        ctx_w.setStyleSheet(f"background:{C['bg']}; margin:0;")
        ctx_l = QHBoxLayout(ctx_w)
        ctx_l.setContentsMargins(14, 8, 14, 8)
        bar = QFrame()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background:{C['brand']}; border-radius:2px;")
        ctx_l.addWidget(bar)
        ctx_l.addSpacing(8)
        ctx_lbl = QLabel(context_text[:200] + ("…" if len(context_text) > 200 else ""))
        ctx_lbl.setStyleSheet(
            f"color:{C['dim']}; font-size:11px; background:transparent;")
        ctx_lbl.setWordWrap(True)
        ctx_l.addWidget(ctx_lbl, 1)
        inner.addWidget(ctx_w)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C['border']};")
        inner.addWidget(sep)

        # Chat scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setMinimumHeight(120)
        self._scroll.setMaximumHeight(380)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background:{C['surface']}; border:none; }}")

        self._chat_widget = QWidget()
        self._chat_widget.setStyleSheet(f"background:{C['surface']};")
        self._chat_layout = QVBoxLayout(self._chat_widget)
        self._chat_layout.setContentsMargins(14, 12, 14, 12)
        self._chat_layout.setSpacing(12)
        self._chat_layout.addStretch()

        self._scroll.setWidget(self._chat_widget)
        inner.addWidget(self._scroll, 1)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{C['border']};")
        inner.addWidget(sep2)

        # Input bar
        input_bar = QWidget()
        input_bar.setStyleSheet(
            f"background:{C['surface2']}; border-radius:0 0 14px 14px;")
        ib = QHBoxLayout(input_bar)
        ib.setContentsMargins(12, 10, 12, 12)
        ib.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask a follow-up question…")
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background:{C['bg']}; border:1px solid {C['border']};
                border-radius:8px; padding:8px 12px;
                color:{C['text']}; font-size:13px;
            }}
            QLineEdit:focus {{ border-color:{C['brand']}; }}
        """)
        self._input.returnPressed.connect(self._send_followup)

        send_btn = QPushButton("↑")
        send_btn.setFixedSize(36, 36)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background:{C['brand']}; border:none; border-radius:8px;
                color:#FFFFFF; font-size:16px; font-weight:bold;
            }}
            QPushButton:hover {{ background:#1A8FFF; }}
            QPushButton:disabled {{ background:{C['surface2']}; color:{C['dim']}; }}
        """)
        send_btn.clicked.connect(self._send_followup)
        self._send_btn = send_btn

        ib.addWidget(self._input, 1)
        ib.addWidget(send_btn)
        inner.addWidget(input_bar)

        outer.addWidget(self._container)

        self._add_message("assistant", answer)

    def _add_message(self, role: str, text: str):
        msg = QWidget()
        msg.setStyleSheet("background:transparent;")
        ml = QVBoxLayout(msg)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(3)

        role_lbl = QLabel("You" if role == "user" else "Bork")
        role_lbl.setStyleSheet(
            f"color:{C['dim'] if role == 'user' else C['brand']};"
            f"font-size:10px; font-weight:bold; letter-spacing:1px;"
            f"background:transparent;")
        ml.addWidget(role_lbl)

        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if role == "user":
            style = f"color:{C['text2']}; font-size:13px; background:transparent;"
        else:
            style = (
                f"color:{C['text']}; font-size:13px;"
                f"background:rgba(0,122,255,0.08);"
                f"border-radius:10px; padding:10px 12px;"
                f"border:1px solid rgba(0,122,255,0.25);")
        bubble.setStyleSheet(style)
        ml.addWidget(bubble)

        # Copy / Insert buttons on assistant messages
        if role == "assistant":
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 4, 0, 0)
            btn_row.setSpacing(6)
            btn_row.addStretch()

            copy_btn = QPushButton("Copy")
            copy_btn.setFixedHeight(24)
            copy_btn.setStyleSheet(
                f"QPushButton {{ font-size:11px; padding:0 10px; border-radius:5px;"
                f" color:{C['text2']}; background:transparent;"
                f" border:1px solid rgba(255,255,255,0.10); }}"
                f"QPushButton:hover {{ color:{C['text']}; border-color:rgba(0,122,255,0.55);"
                f" background:rgba(0,122,255,0.08); }}")
            copy_btn.clicked.connect(lambda: pyperclip.copy(text))

            insert_btn = QPushButton("Insert")
            insert_btn.setFixedHeight(24)
            insert_btn.setStyleSheet(
                f"QPushButton {{ font-size:11px; padding:0 10px; border-radius:5px;"
                f" border:1px solid {C['brand']}; color:{C['brand']}; background:transparent; }}"
                f"QPushButton:hover {{ background:{C['brand_bg']}; }}")

            def _insert(t=text):
                pyperclip.copy(t)
                self.close()
                QTimer.singleShot(150, lambda: __import__("pyautogui").hotkey("ctrl", "v"))

            insert_btn.clicked.connect(_insert)

            btn_row.addWidget(copy_btn)
            btn_row.addWidget(insert_btn)
            ml.addLayout(btn_row)

        self._chat_layout.insertWidget(self._chat_layout.count() - 1, msg)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _add_typing_indicator(self):
        self._typing = QLabel("Bork is thinking…")
        self._typing.setStyleSheet(
            f"color:{C['dim']}; font-size:12px; font-style:italic;"
            f"background:transparent; padding:4px 0;")
        self._chat_layout.insertWidget(self._chat_layout.count() - 1, self._typing)
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _remove_typing_indicator(self):
        if hasattr(self, "_typing") and self._typing:
            self._typing.deleteLater()
            self._typing = None

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _send_followup(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._input.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._add_message("user", text)
        self._add_typing_indicator()
        self._messages.append({"role": "user", "content": text})
        threading.Thread(target=self._query, args=(text,), daemon=True).start()

    def _query(self, _text: str):
        from enhancer import resolve_provider_config
        try:
            provider, api_url, api_key = resolve_provider_config(self._ai_cfg)
            model = self._ai_cfg.get("model", "")
            if not model:
                self._sig_error.emit("No model configured.")
                return
            ctx_prompt = self._ai_cfg.get("context_system_prompt", CONTEXT_SYSTEM_PROMPT)
            answer = self._enhancer.chat(
                self._messages, model, ctx_prompt,
                provider, api_url, api_key)
            self._messages.append({"role": "assistant", "content": answer})
            self._sig_answer.emit(answer)
        except Exception as e:
            self._sig_error.emit(str(e))

    def _on_answer(self, answer: str):
        self._remove_typing_indicator()
        self._add_message("assistant", answer)
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._input.setFocus()

    def _on_error(self, error: str):
        self._remove_typing_indicator()
        self._add_message("assistant", f"Error: {error}")
        self._input.setEnabled(True)
        self._send_btn.setEnabled(True)

    def _on_busy(self, busy: bool):
        self._input.setEnabled(not busy)
        self._send_btn.setEnabled(not busy)

    def _position_top_right(self):
        geo = QApplication.primaryScreen().availableGeometry()
        self.adjustSize()
        self.move(geo.right() - self.width() - 20, geo.top() + 20)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()


# ── Main window ───────────────────────────────────────────────────────────────

class VoiceToolWindow(QMainWindow):
    _sig_status    = pyqtSignal(object)
    _sig_level     = pyqtSignal(float)
    _sig_history   = pyqtSignal()
    _sig_ai_status = pyqtSignal(bool)
    _sig_ai_models = pyqtSignal(list, str)
    _sig_context   = pyqtSignal(str, str, str, list)

    def __init__(self, state: AppState, config: dict, workflow_engine: WorkflowEngine,
                 on_settings_save, on_refresh_models, on_start_ollama):
        super().__init__()
        self.app_state         = state
        self.config            = config
        self.workflow_engine   = workflow_engine
        self.on_settings_save  = on_settings_save
        self.on_refresh_models = on_refresh_models
        self.on_start_ollama   = on_start_ollama
        self._history: list[str] = []
        self._preset_btns: dict[str, QPushButton] = {}
        self._context_popup = None
        self._enhancer_ref  = None  # set by main.py after creation

        self.setWindowTitle("Bork")
        self.setWindowIcon(QIcon(_paw_pixmap(32, C["brand"])))
        self.setFixedSize(700, 720)
        # Apply to QApplication so all child widgets — including popups and
        # native item views — inherit the palette and don't fall back to
        # the platform's black-on-white defaults.
        QApplication.instance().setStyleSheet(STYLESHEET)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        central = QWidget()
        central.setStyleSheet(f"background-color:{C['bg']};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_sidebar(root)
        self._build_content(root)
        self._build_tray()

        self._sig_status.connect(self._on_status)
        self._sig_level.connect(self._on_level)
        self._sig_history.connect(self._rebuild_history)
        self._sig_ai_status.connect(self._on_ai_status)
        self._sig_ai_models.connect(self._on_ai_models)
        self._sig_context.connect(self._on_show_context)

        state.on_status_change(lambda s: self._sig_status.emit(s))

        # Navigate to Home page initially
        self._navigate(0)

    # ── Sidebar ──────────────────────────────────────────────────────────────

    def _build_sidebar(self, root_layout: QHBoxLayout):
        sidebar = QWidget()
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet(
            f"background:{C['sidebar']};"
            f"border-right:1px solid rgba(255,255,255,0.05);")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 16)
        layout.setSpacing(4)

        # Logo area
        logo_row = QHBoxLayout()
        logo_row.setSpacing(8)
        ghost_lbl = QLabel()
        ghost_lbl.setPixmap(_ghost_pixmap(24, C["brand"]))
        ghost_lbl.setFixedSize(24, 24)
        logo_row.addWidget(ghost_lbl)
        title_lbl = QLabel("Bork")
        title_lbl.setStyleSheet(
            f"font-size:18px; font-weight:bold; color:{C['text']}; letter-spacing:-0.3px;")
        logo_row.addWidget(title_lbl)
        logo_row.addStretch()
        layout.addLayout(logo_row)
        layout.addSpacing(20)

        # Nav buttons
        self._nav_buttons: list[QPushButton] = []
        nav_items = [
            ("  Home",      "🏠"),
            ("  AI Settings", "✦"),
            ("  Settings",  "⚙"),
            ("  Workflows", "⚡"),
        ]
        for i, (label, _icon) in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setObjectName("nav")
            btn.setCheckable(False)
            btn.clicked.connect(lambda checked, idx=i: self._navigate(idx))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()

        # Version badge
        ver_lbl = QLabel(f"v{VERSION}")
        ver_lbl.setStyleSheet(f"color:{C['dim']}; font-size:11px;")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_lbl)

        root_layout.addWidget(sidebar)

    def _navigate(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setObjectName("nav_active" if i == index else "nav")
            btn.setStyle(btn.style())
        # Show footer only on AI Settings (1) and Settings (2) pages
        self._footer.setVisible(index in (1, 2))

    # ── Content area ─────────────────────────────────────────────────────────

    def _build_content(self, root_layout: QHBoxLayout):
        content = QWidget()
        content.setStyleSheet(f"background:{C['bg']};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{C['bg']};")

        self._stack.addWidget(self._build_home_page())
        self._stack.addWidget(self._build_ai_page())
        self._stack.addWidget(self._build_settings_page())
        self._stack.addWidget(self._build_workflows_page())

        vbox.addWidget(self._stack, 1)

        # Footer with Save button (only visible on AI Settings and Settings pages)
        self._footer = QWidget()
        self._footer.setFixedHeight(60)
        self._footer.setStyleSheet(
            f"background:{C['surface']};"
            f"border-top:1px solid rgba(255,255,255,0.05);")
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        lbl = QLabel("Save changes to this page")
        lbl.setStyleSheet(f"color:{C['dim']}; font-size:12px;")
        footer_layout.addWidget(lbl)
        footer_layout.addStretch()
        self._save_btn = QPushButton("Save & Apply")
        self._save_btn.setObjectName("primary")
        self._save_btn.setFixedWidth(140)
        self._save_btn.clicked.connect(self._save_settings)
        footer_layout.addWidget(self._save_btn)

        vbox.addWidget(self._footer)
        root_layout.addWidget(content, 1)

    # ── Home page ─────────────────────────────────────────────────────────────

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background:{C['bg']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 20)
        layout.setSpacing(14)

        # Status card
        status_card = _card()
        status_card.setStyleSheet(
            f"QFrame#card {{ background:{C['surface']}; border-radius:12px;"
            f"border:1px solid rgba(255,255,255,0.06); }}")
        sc_layout = QHBoxLayout(status_card)
        sc_layout.setContentsMargins(16, 14, 16, 14)
        sc_layout.setSpacing(16)

        # Left: PulseAuraWidget
        self._pulse_aura = PulseAuraWidget()
        sc_layout.addWidget(self._pulse_aura)

        # Right: status badge + hotkey hints
        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setContentsMargins(0, 0, 0, 0)

        self._status_badge = StatusBadge()
        self._status_badge.set_status(C["dim"], "Loading...")
        right_col.addWidget(self._status_badge)

        # Hotkey hints row
        rk = self.config["hotkeys"].get("record_key", "right ctrl")
        ek = self.config["hotkeys"].get("enhance_key", "right alt")

        hints_row = QHBoxLayout()
        hints_row.setSpacing(6)
        hints_row.setContentsMargins(0, 0, 0, 0)
        self._kbd_record = _kbd_label(rk)
        rec_lbl = _label(" record", C["dim"], 11)
        hints_row.addWidget(self._kbd_record)
        hints_row.addWidget(rec_lbl)
        hints_row.addSpacing(10)
        self._kbd_enhance = _kbd_label(f"{rk} + {ek}")
        enh_lbl = _label(" enhance", C["dim"], 11)
        hints_row.addWidget(self._kbd_enhance)
        hints_row.addWidget(enh_lbl)
        hints_row.addStretch()
        right_col.addLayout(hints_row)

        # Mic level bar
        self._level_bar = QProgressBar()
        self._level_bar.setRange(0, 100)
        self._level_bar.setValue(0)
        self._level_bar.setTextVisible(False)
        self._level_bar.hide()
        right_col.addWidget(self._level_bar)

        sc_layout.addLayout(right_col, 1)
        layout.addWidget(status_card)

        # History header row
        hist_header = QHBoxLayout()
        hist_lbl = _label("Recent Transcriptions", C["text2"], 12, bold=True)
        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("ghost")
        self._clear_btn.setFixedHeight(26)
        self._clear_btn.clicked.connect(self._clear_history)
        hist_header.addWidget(hist_lbl, 1)
        hist_header.addWidget(self._clear_btn)
        layout.addLayout(hist_header)

        # History scroll area
        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setStyleSheet(
            f"QScrollArea {{ border:1px solid rgba(255,255,255,0.07); border-radius:10px;"
            f"background:rgba(255,255,255,0.02); }}")

        self._history_container = QWidget()
        self._history_container.setStyleSheet(f"background:{C['surface']};")
        self._history_layout = QVBoxLayout(self._history_container)
        self._history_layout.setContentsMargins(8, 8, 8, 8)
        self._history_layout.setSpacing(4)
        self._history_layout.addStretch()

        self._history_scroll.setWidget(self._history_container)
        layout.addWidget(self._history_scroll, 1)

        return page

    # ── AI Settings page ──────────────────────────────────────────────────────

    def _build_ai_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background:{C['bg']};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{C['bg']}; }}")

        w = QWidget()
        w.setStyleSheet(f"background:{C['bg']};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        ai_cfg = self.config.get("ai_enhancement", {})
        current_provider = ai_cfg.get("provider", "ollama")

        # Page title
        layout.addWidget(_label("AI Settings", C["text"], 16, bold=True))
        layout.addSpacing(2)

        # Provider card
        layout.addWidget(_section_label("Provider"))
        prov_card = _inner_card()
        prov_layout = QVBoxLayout(prov_card)
        prov_layout.setContentsMargins(14, 12, 14, 12)
        prov_layout.setSpacing(10)

        prov_top = QHBoxLayout()
        self._provider = QComboBox()
        for pid, pdef in PROVIDERS.items():
            self._provider.addItem(pdef.label, userData=pid)
        idx = self._provider.findData(current_provider)
        if idx >= 0:
            self._provider.setCurrentIndex(idx)
        prov_top.addWidget(self._provider, 1)
        prov_top.addSpacing(8)

        self._test_conn_btn = QPushButton("Test")
        self._test_conn_btn.setObjectName("ghost")
        self._test_conn_btn.setFixedSize(52, 30)
        self._test_conn_btn.setToolTip("Test connection to the selected provider")
        self._test_conn_btn.clicked.connect(self._on_refresh_models)
        prov_top.addWidget(self._test_conn_btn)
        prov_top.addSpacing(8)

        self._ai_dot = StatusDot(10)
        self._ai_status_lbl = QLabel("—")
        self._ai_status_lbl.setStyleSheet(f"color:{C['dim']}; font-size:12px;")
        prov_top.addWidget(self._ai_dot)
        prov_top.addWidget(self._ai_status_lbl)
        prov_layout.addLayout(prov_top)

        saved_url = (ai_cfg.get("providers", {}).get(current_provider, {}).get(
            "api_url", "") or PROVIDERS.get(current_provider, PROVIDERS["custom"]).default_url)
        self._api_url = QLineEdit(saved_url)
        self._api_url.setPlaceholderText("API base URL")
        _row(prov_layout, "API URL", self._api_url, 80)

        saved_key = ai_cfg.get("providers", {}).get(current_provider, {}).get("api_key", "")
        self._api_key = QLineEdit(saved_key)
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText("Paste API key here")
        _row(prov_layout, "API key", self._api_key, 80)

        self._start_ollama_row = QWidget()
        sor_layout = QHBoxLayout(self._start_ollama_row)
        sor_layout.setContentsMargins(0, 0, 0, 0)
        sor_layout.addStretch()
        self._start_btn = QPushButton("Start Ollama")
        self._start_btn.setObjectName("ghost")
        self._start_btn.clicked.connect(self._on_start_ollama)
        sor_layout.addWidget(self._start_btn)
        prov_layout.addWidget(self._start_ollama_row)
        layout.addWidget(prov_card)

        # Model card
        layout.addWidget(_section_label("Model"))
        model_card = _inner_card()
        model_layout = QHBoxLayout(model_card)
        model_layout.setContentsMargins(14, 10, 14, 10)
        self._ai_model = QComboBox()
        self._ai_model.addItem("(none)")
        self._ai_model.setCurrentText(ai_cfg.get("model", "") or "(none)")
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("ghost")
        refresh_btn.clicked.connect(self._on_refresh_models)
        model_layout.addWidget(self._ai_model, 1)
        model_layout.addWidget(refresh_btn)
        layout.addWidget(model_card)

        # Enhancement Prompt card
        layout.addWidget(_section_label("Enhancement Prompt"))
        prompt_card = _inner_card()
        prompt_layout = QVBoxLayout(prompt_card)
        prompt_layout.setContentsMargins(14, 12, 14, 12)
        prompt_layout.setSpacing(10)

        enh_desc = QLabel(
            "Used when you hold Enhance key + Record. Rewrites your dictation before pasting.")
        enh_desc.setStyleSheet(f"color:{C['dim']}; font-size:11px;")
        enh_desc.setWordWrap(True)
        prompt_layout.addWidget(enh_desc)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(6)
        current_preset = ai_cfg.get("preset", DEFAULT_PRESET)
        for preset_name in PRESETS:
            btn = QPushButton(preset_name)
            is_active = preset_name == current_preset
            btn.setObjectName("preset_active" if is_active else "preset")
            btn.clicked.connect(lambda _, n=preset_name: self._on_preset_click(n))
            preset_row.addWidget(btn)
            self._preset_btns[preset_name] = btn
        preset_row.addStretch()
        prompt_layout.addLayout(preset_row)

        self._system_prompt = QTextEdit()
        self._system_prompt.setPlainText(ai_cfg.get("system_prompt", ""))
        self._system_prompt.setMinimumHeight(80)
        self._system_prompt.setMaximumHeight(110)
        self._system_prompt.setPlaceholderText(
            "System prompt sent to the AI before your transcription…")
        prompt_layout.addWidget(self._system_prompt)
        layout.addWidget(prompt_card)

        # Context Mode Prompt card
        layout.addWidget(_section_label("Context Mode Prompt"))
        ctx_prompt_card = _inner_card()
        ctx_prompt_layout = QVBoxLayout(ctx_prompt_card)
        ctx_prompt_layout.setContentsMargins(14, 12, 14, 12)
        ctx_prompt_layout.setSpacing(8)

        ctx_desc = QLabel(
            "Used when you highlight text and then Record. The AI answers your voice "
            "question about the selected text.")
        ctx_desc.setStyleSheet(f"color:{C['dim']}; font-size:11px;")
        ctx_desc.setWordWrap(True)
        ctx_prompt_layout.addWidget(ctx_desc)

        self._context_prompt = QTextEdit()
        self._context_prompt.setPlainText(
            ai_cfg.get("context_system_prompt", CONTEXT_SYSTEM_PROMPT))
        self._context_prompt.setMinimumHeight(70)
        self._context_prompt.setMaximumHeight(100)
        self._context_prompt.setPlaceholderText("System prompt for context mode Q&A…")
        ctx_prompt_layout.addWidget(self._context_prompt)
        layout.addWidget(ctx_prompt_card)

        layout.addStretch()
        scroll.setWidget(w)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self._provider.currentIndexChanged.connect(self._on_provider_change)
        self._on_provider_change(self._provider.currentIndex())
        return page

    # ── Settings page ─────────────────────────────────────────────────────────

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background:{C['bg']};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{C['bg']}; }}")

        w = QWidget()
        w.setStyleSheet(f"background:{C['bg']};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        self._entries: dict[str, QLineEdit | QComboBox] = {}

        layout.addWidget(_label("Settings", C["text"], 16, bold=True))
        layout.addSpacing(2)

        # Hotkeys section
        layout.addWidget(_section_label("Hotkeys"))
        hk_card = _inner_card()
        hk_layout = QVBoxLayout(hk_card)
        hk_layout.setContentsMargins(14, 12, 14, 12)
        hk_layout.setSpacing(10)

        record_key_val = self.config["hotkeys"].get("record_key", "right ctrl")
        enhance_key_val = self.config["hotkeys"].get("enhance_key", "right alt")

        self._record_key_edit = QLineEdit(record_key_val)
        self._record_key_edit.setObjectName("kbd")
        _row(hk_layout, "Record key", self._record_key_edit, 120)
        self._entries["record_key"] = self._record_key_edit

        self._enhance_key_edit = QLineEdit(enhance_key_val)
        self._enhance_key_edit.setObjectName("kbd")
        _row(hk_layout, "Enhance key", self._enhance_key_edit, 120)
        self._entries["enhance_key"] = self._enhance_key_edit

        layout.addWidget(hk_card)

        # Transcription section
        layout.addWidget(_section_label("Transcription"))
        tr_card = _inner_card()
        tr_layout = QVBoxLayout(tr_card)
        tr_layout.setContentsMargins(14, 12, 14, 12)
        tr_layout.setSpacing(10)

        self._whisper_model = QComboBox()
        self._whisper_model.addItems(["tiny", "base", "small", "medium", "large"])
        self._whisper_model.setCurrentText(self.config["transcription"]["model"])
        _row(tr_layout, "Whisper model", self._whisper_model, 120)

        self._restart_note = QLabel("⚠  Restart required to apply model change")
        self._restart_note.setStyleSheet(
            f"color:#fbbf24; font-size:11px; padding-left:128px;")
        self._restart_note.hide()
        self._whisper_model.currentTextChanged.connect(lambda _: self._restart_note.show())
        tr_layout.addWidget(self._restart_note)

        lang = QLineEdit(self.config["transcription"]["language"])
        _row(tr_layout, "Language", lang, 120)
        self._entries["language"] = lang
        layout.addWidget(tr_card)

        # Output section
        layout.addWidget(_section_label("Output"))
        out_card = _inner_card()
        out_layout = QVBoxLayout(out_card)
        out_layout.setContentsMargins(14, 12, 14, 12)
        out_layout.setSpacing(8)
        self._output_mode = QComboBox()
        self._output_mode.addItems(["type", "clipboard"])
        self._output_mode.setCurrentText(self.config["output"]["mode"])
        _row(out_layout, "Mode", self._output_mode, 120)
        note = QLabel("type — auto-pastes  ·  clipboard — copies only")
        note.setStyleSheet(f"color:{C['dim']}; font-size:11px; padding-left:128px;")
        out_layout.addWidget(note)
        layout.addWidget(out_card)

        layout.addStretch()
        scroll.setWidget(w)

        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)
        return page

    # ── Workflows page ────────────────────────────────────────────────────────

    def _build_workflows_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background:{C['bg']};")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)

        layout.addWidget(_label("Workflows", C["text"], 16, bold=True))
        layout.addSpacing(2)

        # Threshold
        layout.addWidget(_section_label("Match threshold"))
        thresh_card = _inner_card()
        thresh_layout = QHBoxLayout(thresh_card)
        thresh_layout.setContentsMargins(14, 10, 14, 10)
        thresh_lbl = QLabel("Higher = stricter matching (recommended 70–80)")
        thresh_lbl.setStyleSheet(f"color:{C['text2']}; font-size:12px;")
        thresh_layout.addWidget(thresh_lbl)
        thresh_layout.addStretch()
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(0, 100)
        self._threshold_spin.setValue(self.workflow_engine.threshold)
        self._threshold_spin.setFixedWidth(64)
        thresh_layout.addWidget(self._threshold_spin)
        layout.addWidget(thresh_card)

        # Workflow list
        layout.addWidget(_section_label("Workflows"))
        self._wf_list = QListWidget()
        self._wf_list.setStyleSheet(
            f"QListWidget {{ background:rgba(255,255,255,0.04); border-radius:10px;"
            f"border:1px solid rgba(255,255,255,0.08); padding:4px; color:{C['text']}; }}"
            f"QListWidget::item {{ padding:6px 8px; color:{C['text']}; }}"
            f"QListWidget::item:selected {{ background:{C['brand_bg']}; color:{C['brand']}; }}"
            f"QListWidget::item:hover:!selected {{ background:rgba(0,122,255,0.07); }}")
        self._rebuild_wf_list()
        layout.addWidget(self._wf_list, 1)

        btn_row = QHBoxLayout()
        add_btn  = QPushButton("+ Add")
        edit_btn = QPushButton("Edit")
        del_btn  = QPushButton("Delete")
        del_btn.setObjectName("danger")
        for b in (add_btn, edit_btn):
            b.setObjectName("ghost")
        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addStretch()
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        add_btn.clicked.connect(self._add_workflow)
        edit_btn.clicked.connect(self._edit_workflow)
        del_btn.clicked.connect(self._delete_workflow)
        return page

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _build_tray(self):
        self._tray = QSystemTrayIcon(QIcon(_ghost_pixmap(32, C["dim"])), self)
        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu {{ background:{C['surface']}; border:1px solid rgba(0,122,255,0.25);"
            f"border-radius:8px; padding:4px; color:{C['text']}; }}"
            f"QMenu::item {{ padding:8px 16px; border-radius:4px; color:{C['text']}; }}"
            f"QMenu::item:selected {{ background:{C['brand_bg']}; color:{C['brand']}; }}")
        open_a = menu.addAction("Open Bork")
        menu.addSeparator()
        quit_a = menu.addAction("Quit")
        open_a.triggered.connect(self.show_window)
        quit_a.triggered.connect(QApplication.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(
            lambda r: self.show_window()
            if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        self._tray.show()

    # ── Signal slots ──────────────────────────────────────────────────────────

    def _on_status(self, status: Status):
        color, text = STATUS_META.get(status, (C["dim"], str(status)))
        self._status_badge.set_status(color, text)
        self._pulse_aura.set_status(color, recording=(status == Status.RECORDING))
        self._tray.setIcon(QIcon(_ghost_pixmap(32, color)))
        if status == Status.RECORDING:
            self._level_bar.show()
        else:
            self._level_bar.hide()
            if status == Status.IDLE:
                self._level_bar.setValue(0)

    def _on_level(self, level: float):
        self._level_bar.setValue(int(level * 100))

    def _on_ai_status(self, connected: bool):
        self._reset_test_btn()
        if connected:
            self._ai_dot.set_color(C["green"])
            self._ai_status_lbl.setText("Connected")
            self._ai_status_lbl.setStyleSheet(f"color:{C['green']}; font-size:12px;")
            self._start_btn.setEnabled(False)
        else:
            self._ai_dot.set_color(C["red"])
            self._ai_status_lbl.setText("Not connected")
            self._ai_status_lbl.setStyleSheet(f"color:{C['red']}; font-size:12px;")
            provider = self._provider.currentData()
            self._start_btn.setEnabled(provider == "ollama")
            self._start_btn.setText("Start Ollama")

    def _on_ai_models(self, models: list, selected: str):
        self._ai_model.clear()
        if models:
            self._ai_model.addItems(models)
            self._ai_model.setCurrentText(selected if selected in models else models[0])
        else:
            self._ai_model.addItem("(none)")

    # ── Public API ────────────────────────────────────────────────────────────

    def set_ollama_status(self, connected: bool):
        self._sig_ai_status.emit(connected)

    def set_ollama_models(self, models: list[str], selected: str):
        self._sig_ai_models.emit(models, selected)

    def refresh_history(self, history: list[str]):
        self._history = history
        self._sig_history.emit()

    def update_level(self, level: float):
        self._sig_level.emit(level)

    def show_context_popup(self, context_text: str, question: str,
                           answer: str, messages: list):
        self._sig_context.emit(context_text, question, answer, messages)

    def _on_show_context(self, context_text: str, question: str,
                         answer: str, messages: list):
        if self._context_popup:
            self._context_popup.close()
        self._context_popup = ContextPopup(
            context_text, question, answer, messages,
            self._enhancer_ref,
            self.config.get("ai_enhancement", {}),
        )
        self._context_popup.show()

    # ── History helpers ───────────────────────────────────────────────────────

    def _make_transcript_card(self, text: str) -> TranscriptCard:
        def do_copy():
            pyperclip.copy(text)

        def do_insert():
            from output import send_text
            mode = self.config.get("output", {}).get("mode", "type")
            send_text(text, mode=mode)

        return TranscriptCard(text, do_copy, do_insert)

    def _rebuild_history(self):
        while self._history_layout.count() > 1:
            item = self._history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for text in self._history:
            card = self._make_transcript_card(text)
            self._history_layout.insertWidget(self._history_layout.count() - 1, card)

    def _clear_history(self):
        self._history.clear()
        self.app_state.clear_history()
        self._rebuild_history()

    # ── UI actions ────────────────────────────────────────────────────────────

    def _on_provider_change(self, _index: int):
        provider = self._provider.currentData()
        pdef = PROVIDERS.get(provider, PROVIDERS["custom"])

        prov_cfgs = self.config.get("ai_enhancement", {}).get("providers", {})
        prov_data = prov_cfgs.get(provider, {})
        url = prov_data.get("api_url", "") or pdef.default_url
        key = prov_data.get("api_key", "")

        self._api_url.setText(url)
        self._api_url.setReadOnly(not pdef.url_editable)
        self._api_key.setText(key)

        if pdef.requires_key:
            self._api_key.setPlaceholderText("Paste API key here")
            self._api_key.setEnabled(True)
        else:
            self._api_key.setPlaceholderText("No key required")
            self._api_key.setEnabled(False)

        self._start_ollama_row.setVisible(provider == "ollama")

        # Update in-memory config so the connection test uses the right provider
        ai = self.config.setdefault("ai_enhancement", {})
        ai["provider"] = provider
        ai.setdefault("providers", {}).setdefault(provider, {})["api_url"] = url

        # Reset connection status and auto-test
        self._ai_dot.set_color(C["dim"])
        self._ai_status_lbl.setText("Testing...")
        self._ai_status_lbl.setStyleSheet(f"color:{C['dim']}; font-size:12px;")
        threading.Thread(target=self.on_refresh_models, daemon=True).start()

    def _on_preset_click(self, preset_name: str):
        for name, btn in self._preset_btns.items():
            btn.setObjectName("preset_active" if name == preset_name else "preset")
            btn.setStyle(btn.style())
        if preset_name != "Custom" and PRESETS.get(preset_name):
            self._system_prompt.setPlainText(PRESETS[preset_name])

    def _on_refresh_models(self):
        self._ai_dot.set_color(C["brand"])
        self._ai_status_lbl.setText("Testing...")
        self._ai_status_lbl.setStyleSheet(f"color:{C['brand']}; font-size:12px;")
        self._test_conn_btn.setEnabled(False)
        self._test_conn_btn.setText("...")
        threading.Thread(target=self._do_refresh_models, daemon=True).start()

    def _do_refresh_models(self):
        self.on_refresh_models()
        # Re-enable button on main thread via signal (on_refresh_models calls
        # set_ollama_status which emits _sig_ai_status, handled in _on_ai_status)

    def _reset_test_btn(self):
        self._test_conn_btn.setEnabled(True)
        self._test_conn_btn.setText("Test")

    def _on_start_ollama(self):
        self._start_btn.setEnabled(False)
        self._start_btn.setText("Starting…")
        threading.Thread(target=self.on_start_ollama, daemon=True).start()

    def _save_settings(self):
        # Hotkeys / transcription / output
        self.config["hotkeys"]["record_key"]     = self._entries["record_key"].text().strip()
        self.config["hotkeys"]["enhance_key"]    = self._entries["enhance_key"].text().strip()
        self.config["transcription"]["model"]    = self._whisper_model.currentText()
        self.config["transcription"]["language"] = self._entries["language"].text().strip()
        self.config["output"]["mode"]            = self._output_mode.currentText()

        # AI
        provider = self._provider.currentData()
        ai = self.config.setdefault("ai_enhancement", {})
        ai["provider"] = provider
        sel = self._ai_model.currentText()
        ai["model"]    = "" if sel == "(none)" else sel
        ai["preset"]   = next(
            (n for n, b in self._preset_btns.items()
             if b.objectName() == "preset_active"), DEFAULT_PRESET)
        ai["system_prompt"]         = self._system_prompt.toPlainText().strip()
        ai["context_system_prompt"] = self._context_prompt.toPlainText().strip()

        providers_block = ai.setdefault("providers", {})
        pdata = providers_block.setdefault(provider, {})
        pdata["api_url"] = self._api_url.text().strip()
        pdata["api_key"] = self._api_key.text().strip()

        # Workflows
        self.workflow_engine.threshold = self._threshold_spin.value()
        self.workflow_engine.save()

        # Update hotkey hint labels on Home page
        rk = self.config["hotkeys"]["record_key"]
        ek = self.config["hotkeys"]["enhance_key"]
        self._kbd_record.setText(rk)
        self._kbd_enhance.setText(f"{rk} + {ek}")
        self._restart_note.hide()

        self._save_btn.setText("Saved!")
        threading.Thread(target=self.on_settings_save, args=(self.config,),
                         daemon=True).start()
        QTimer.singleShot(1500, lambda: self._save_btn.setText("Save & Apply"))

    # ── Workflow CRUD ─────────────────────────────────────────────────────────

    def _rebuild_wf_list(self):
        self._wf_list.clear()
        for wf in self.workflow_engine.workflows:
            phrases = ", ".join(wf.get("phrases", [])[:2])
            item = QListWidgetItem(f"  {wf['name']}  —  {phrases}")
            item.setData(Qt.ItemDataRole.UserRole, wf)
            self._wf_list.addItem(item)

    def _add_workflow(self):
        dlg = WorkflowDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            wf = dlg.get_workflow()
            if wf["name"]:
                self.workflow_engine.workflows.append(wf)
                self.workflow_engine.save()
                self._rebuild_wf_list()

    def _edit_workflow(self):
        item = self._wf_list.currentItem()
        if not item:
            return
        wf  = item.data(Qt.ItemDataRole.UserRole)
        idx = self.workflow_engine.workflows.index(wf)
        dlg = WorkflowDialog(workflow=wf, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.workflow_engine.workflows[idx] = dlg.get_workflow()
            self.workflow_engine.save()
            self._rebuild_wf_list()

    def _delete_workflow(self):
        item = self._wf_list.currentItem()
        if not item:
            return
        self.workflow_engine.workflows.remove(item.data(Qt.ItemDataRole.UserRole))
        self.workflow_engine.save()
        self._rebuild_wf_list()

    # ── Window behaviour ──────────────────────────────────────────────────────

    def closeEvent(self, event):
        QApplication.quit()

    def show_window(self):
        self.show()
        self.raise_()
        self.activateWindow()
