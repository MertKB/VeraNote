"""
Toast / Snackbar notification widget for VeraNote.
Provides non-blocking, self-dismissing status notifications with smooth fade animations.
"""
from typing import Optional, List
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect, QFrame
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QPoint
from PySide6.QtGui import QColor

# Window -> List[ToastWidget] tracking for stacking
_window_toasts: dict[QWidget, List['ToastWidget']] = {}


class ToastWidget(QFrame):
    """
    Floating toast notification displayed in the bottom-right corner of a parent window.
    """
    TYPE_COLORS = {
        "success": ("#34A853", "✓"),
        "info": ("#8AB4F8", "ℹ"),
        "warning": ("#FBBC04", "⚠"),
        "error": ("#EA4335", "✖")
    }

    def __init__(self, parent: QWidget, message: str, toast_type: str = "info", duration_ms: int = 2800):
        # Attach to the top-level window so it floats over tabs and views
        target_parent = parent.window() if parent else None
        super().__init__(target_parent)
        self.target_parent = target_parent
        self.duration_ms = duration_ms
        self.is_closing = False

        accent_color, icon_char = self.TYPE_COLORS.get(toast_type.lower(), self.TYPE_COLORS["info"])

        # Frame setup
        self.setObjectName("ToastWidget")
        self.setStyleSheet(f"""
            QFrame#ToastWidget {{
                background-color: #202124;
                border: 1px solid #3c4043;
                border-left: 4px solid {accent_color};
                border-radius: 8px;
            }}
            QLabel#ToastIcon {{
                color: {accent_color};
                font-size: 15px;
                font-weight: bold;
                padding-right: 2px;
            }}
            QLabel#ToastText {{
                color: #E8EAED;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton#ToastClose {{
                background: transparent;
                border: none;
                color: #9AA0A6;
                font-size: 14px;
                font-weight: bold;
                padding: 0 4px;
                margin-left: 8px;
            }}
            QPushButton#ToastClose:hover {{
                color: #FFFFFF;
                background-color: #303134;
                border-radius: 4px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(8)

        # Icon
        self.icon_label = QLabel(icon_char)
        self.icon_label.setObjectName("ToastIcon")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # Text
        self.text_label = QLabel(message)
        self.text_label.setObjectName("ToastText")
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("ToastClose")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.clicked.connect(self.dismiss)
        layout.addWidget(self.close_btn)

        self.adjustSize()
        # Constrain width
        max_w = min(420, max(260, self.sizeHint().width()))
        self.setFixedWidth(max_w)
        self.adjustSize()

        # Opacity effect for animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)

        # Auto dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.dismiss)

        # Stacking tracking
        if self.target_parent:
            if self.target_parent not in _window_toasts:
                _window_toasts[self.target_parent] = []
            _window_toasts[self.target_parent].append(self)
            self.target_parent.installEventFilter(self)

        self.reposition()
        self.show()
        self.raise_()

        # Fade in
        self.fade_in()

    def reposition(self):
        """Positions this toast based on its index in the window's toast stack."""
        if not self.target_parent:
            return

        toasts = _window_toasts.get(self.target_parent, [self])
        try:
            index_from_bottom = toasts.index(self)
        except ValueError:
            index_from_bottom = 0

        # Calculate Y offset from bottom
        bottom_margin = 24
        right_margin = 24
        spacing = 8

        # Accumulate heights of all toasts below this one
        y_offset = bottom_margin
        for t in toasts[:index_from_bottom]:
            y_offset += t.height() + spacing

        target_x = self.target_parent.width() - self.width() - right_margin
        target_y = self.target_parent.height() - self.height() - y_offset

        self.move(max(10, target_x), max(10, target_y))

    def eventFilter(self, watched, event):
        if watched == self.target_parent and event.type() == QEvent.Type.Resize:
            self.reposition()
        return super().eventFilter(watched, event)

    def fade_in(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(180)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self.dismiss_timer.start(self.duration_ms))
        self.anim.start()

    def dismiss(self):
        if self.is_closing:
            return
        self.is_closing = True
        self.dismiss_timer.stop()

        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(200)
        self.fade_out_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self._on_fade_out_finished)
        self.fade_out_anim.start()

    def _on_fade_out_finished(self):
        if self.target_parent and self.target_parent in _window_toasts:
            try:
                _window_toasts[self.target_parent].remove(self)
                if not _window_toasts[self.target_parent]:
                    del _window_toasts[self.target_parent]
                else:
                    # Reposition remaining toasts
                    for remaining in _window_toasts[self.target_parent]:
                        remaining.reposition()
            except ValueError:
                pass
        self.close()
        self.deleteLater()


def show_toast(parent: QWidget, message: str, toast_type: str = "info", duration_ms: int = 2800) -> ToastWidget:
    """Helper function to create and show a toast notification."""
    return ToastWidget(parent, message, toast_type, duration_ms)
