"""
Title rendering and inline editing widgets for VeraNote Welcome Screen.
"""
from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QStackedWidget
from PySide6.QtCore import Signal, Qt, QSize, QPoint
from PySide6.QtGui import (QPainter, QFontMetrics, QPainterPath, QPen, QColor, QFont)
from utils.i18n import t


class OutlinedLabel(QLabel):
    """Custom QLabel with clean letter fill & outline stroke painting, supporting full transparency and custom font family & weight."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.text_color = "#E3E3E3"
        self.outline_color = "#000000"
        self.outline_width = 0
        self.font_family = "Segoe UI"
        self.font_weight = 700

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        font = self.font()
        if self.font_family:
            font.setFamily(self.font_family)
        font.setWeight(QFont.Weight(self.font_weight) if hasattr(QFont, 'Weight') else self.font_weight)
        painter.setFont(font)
        
        metrics = QFontMetrics(font)
        text = self.text()
        rect = self.rect()
        
        x = (rect.width() - metrics.horizontalAdvance(text)) // 2 if self.alignment() & Qt.AlignCenter else 0
        y = (rect.height() + metrics.ascent() - metrics.descent()) // 2
        
        path = QPainterPath()
        path.addText(x, y, font, text)

        # 1. Stroke Outline if enabled
        if self.outline_width > 0 and self.outline_color and self.outline_color.lower() != "transparent":
            pen = QPen(QColor(self.outline_color), self.outline_width * 2)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.strokePath(path, pen)

        # 2. Fill Text Interior if text_color is valid & not transparent
        if self.text_color and self.text_color.lower() != "transparent":
            painter.fillPath(path, QColor(self.text_color))

        painter.end()


class EditableLabel(QStackedWidget):
    """A label that turns into a QLineEdit when double clicked, for title editing, and is resizable."""
    text_changed = Signal(str)
    position_changed = Signal(int, int) # x, y
    size_changed = Signal(int, int) # w, h

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.drag_position = None
        self.is_resizing = False
        self.drag_start_size = QSize()
        self.drag_start_pos = QPoint()
        self.is_locked = False
        self.font_size = 28
        self.font_family = "Segoe UI"
        self.font_weight = 700
        self.text_color = "#E3E3E3"
        self.outline_color = "#000000"
        self.outline_width = 0
        self.frame_enabled = True
        self.frame_bg = "rgba(32, 33, 36, 0.75)"
        self.frame_border_color = "#8AB4F8"
        self.frame_border_width = 1
        
        self.setCursor(Qt.PointingHandCursor)

        self.label = OutlinedLabel(text, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("WelcomeTitle")
        
        self.edit = QLineEdit(text, self)
        self.edit.setAlignment(Qt.AlignCenter)
        self.edit.setObjectName("WelcomeTitleEdit")
        
        self.addWidget(self.label)
        self.addWidget(self.edit)
        
        self.update_title_styling()
        
        self.edit.returnPressed.connect(self.save_text)
        self.edit.focusOutEvent = self.on_focus_out
        self.label.mouseDoubleClickEvent = self.on_double_click
        self.label.setToolTip(t("welcome_title_tooltip"))

    def update_title_styling(self):
        self.label.text_color = self.text_color
        self.label.outline_color = self.outline_color
        self.label.outline_width = self.outline_width
        self.label.font_family = self.font_family
        self.label.font_weight = self.font_weight
        
        if self.frame_enabled:
            bg = self.frame_bg if self.frame_bg else "transparent"
            border = self.frame_border_color if self.frame_border_color else "transparent"
            frame_qss = f"background-color: {bg}; border: {self.frame_border_width}px solid {border}; border-radius: 12px; padding: 6px 16px;"
        else:
            frame_qss = "background-color: transparent; border: none; padding: 4px;"
            
        self.setStyleSheet(f"""
            QStackedWidget {{
                {frame_qss}
            }}
        """)
        font_family_css = f"'{self.font_family}', sans-serif" if self.font_family else "sans-serif"
        self.label.setStyleSheet(f"font-size: {self.font_size}px; font-weight: {self.font_weight}; font-family: {font_family_css};")
        self.edit.setStyleSheet(f"""
            QLineEdit#WelcomeTitleEdit {{
                font-size: {self.font_size}px;
                font-weight: {self.font_weight};
                font-family: {font_family_css};
                color: {self.text_color if self.text_color != 'transparent' else '#E3E3E3'};
                background-color: #202124;
                border: 1px solid #8AB4F8;
                border-radius: 8px;
                padding: 6px;
                min-width: 350px;
            }}
        """)
        self.label.update()

    def on_double_click(self, event):
        self.edit.setText(self.label.text())
        self.setCurrentIndex(1)
        self.edit.setFocus()
        self.edit.selectAll()

    def on_focus_out(self, event):
        self.save_text()
        super(QLineEdit, self.edit).focusOutEvent(event)

    def save_text(self):
        if self.currentIndex() == 1:
            new_text = self.edit.text().strip()
            if new_text:
                self.label.setText(new_text)
                self.text_changed.emit(new_text)
            self.setCurrentIndex(0)

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton and self.currentIndex() == 0:
            pos = event.position().toPoint()
            if pos.x() >= self.width() - 20 and pos.y() >= self.height() - 20:
                self.is_resizing = True
                self.drag_start_size = self.size()
                self.drag_start_pos = event.globalPosition().toPoint()
            else:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.raise_()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_locked and (event.buttons() & Qt.LeftButton):
            if self.is_resizing:
                delta = event.globalPosition().toPoint() - self.drag_start_pos
                nw = max(200, min(1800, self.drag_start_size.width() + delta.x()))
                nh = max(40, min(600, self.drag_start_size.height() + delta.y()))
                self.resize(nw, nh)
            elif self.drag_position is not None:
                new_pos = event.globalPosition().toPoint() - self.drag_position
                nx = max(0, new_pos.x())
                ny = max(0, new_pos.y())
                self.move(nx, ny)
                if self.parent():
                    req_w = nx + self.width() + 40
                    req_h = ny + self.height() + 40
                    pw = max(self.parent().width(), req_w)
                    ph = max(self.parent().height(), req_h)
                    if req_w > self.parent().width() or req_h > self.parent().height():
                        self.parent().setMinimumSize(pw, ph)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.is_locked:
            if self.is_resizing:
                self.is_resizing = False
                self.size_changed.emit(self.width(), self.height())
            elif self.drag_position is not None:
                self.drag_position = None
                if self.x() >= 0:
                    self.position_changed.emit(self.x(), self.y())
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.is_locked:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            border_col = self.frame_border_color if (self.frame_border_color and self.frame_border_color != 'transparent') else "#8AB4F8"
            painter.setPen(QPen(QColor(border_col), 1.5))
            w, h = self.width(), self.height()
            painter.drawLine(w - 12, h - 4, w - 4, h - 12)
            painter.drawLine(w - 8, h - 4, w - 4, h - 8)
            painter.end()

    def setText(self, text):
        self.label.setText(text)
        self.edit.setText(text)

    def retranslate_ui(self):
        self.label.setToolTip(t("welcome_title_tooltip"))
