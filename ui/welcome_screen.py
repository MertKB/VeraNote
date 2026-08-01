# ui/welcome_screen.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QStackedWidget, QLineEdit, 
                             QFileDialog, QStyle, QStyleOption, QScrollArea, QFrame, 
                             QGridLayout, QDialog, QCheckBox, QSlider, QMenu, QColorDialog, QComboBox)
from PySide6.QtCore import Signal, Qt, QSize, QPoint, QThreadPool, QRunnable, QObject
from PySide6.QtGui import (QPainter, QImage, QTextDocument, QFontMetrics, QCursor, 
                           QGuiApplication, QPainterPath, QPen, QColor, QPixmap, QFont)
from utils.i18n import t
import database

from utils.cache import THUMBNAIL_CACHE

class ImageLoadWorkerSignals(QObject):
    image_loaded = Signal(QPixmap)

class ImageLoadWorker(QRunnable):
    def __init__(self, image_path, target_w=216, target_h=105):
        super().__init__()
        self.image_path = image_path
        self.target_w = target_w
        self.target_h = target_h
        self.signals = ImageLoadWorkerSignals()

    def run(self):
        if not self.image_path or not os.path.exists(self.image_path):
            return
        img = QImage(self.image_path)
        if img.isNull():
            return
        scaled = img.scaled(self.target_w, self.target_h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        pix = QPixmap.fromImage(scaled)
        THUMBNAIL_CACHE[self.image_path] = pix
        self.signals.image_loaded.emit(pix)


def get_pastel_palette():
    return [
        ("default", "#444746", "#E3E3E3", t("color_default_theme")),  # ⚙️ Tema Rengi (Theme Color)
        ("#FEF08A", "#FACC15", "#713F12", t("color_yellow_original")), # Yellow
        ("#BAE6FD", "#38BDF8", "#0C4A6E", t("color_blue")),            # Blue
        ("#BBF7D0", "#4ADE80", "#14532D", t("color_green")),           # Green
        ("#FBCFE8", "#F472B6", "#831843", t("color_pink")),            # Pink
        ("#FED7AA", "#FB923C", "#7C2D12", t("color_orange")),          # Orange
        ("#E9D5FF", "#C084FC", "#581C87", t("color_purple")),          # Purple
        ("#99F6E4", "#2DD4BF", "#134E4A", t("color_teal")),            # Teal
        ("#1E293B", "#38BDF8", "#F8FAFC", t("color_dark_blue")),       # Dark Blue
        ("#161616", "#2D2D2D", "#FFFFFF", t("color_dark")),            # Dark (Matching user screenshot)
        ("#FFFFFF", "#D1D5DB", "#111827", t("color_white")),           # White
    ]

def get_palette_colors(color_hex):
    if not color_hex or color_hex.lower() in ("default", "none"):
        return "#1E1F20", "#444746", "#E3E3E3"
    for bg, border, text_col, _ in get_pastel_palette():
        if bg and bg.lower() == color_hex.lower():
            return bg, border, text_col
    return color_hex, "#8AB4F8", "#E3E3E3"


class NoWheelSlider(QSlider):
    """QSlider subclass that ignores mouse wheel events to prevent accidental setting changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class QuickNoteCardWidget(QFrame):
    """Simplified, clean Quick Note creation block on the home page with customizable bg, border & resizable size."""
    quick_note_saved = Signal(str, str) # title, content
    position_changed = Signal(int, int) # x, y
    size_changed = Signal(int, int) # w, h

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QuickNoteCard")
        self.setMinimumSize(220, 120)
        self.resize(340, 160)
        self.drag_position = None
        self.is_resizing = False
        self.drag_start_size = QSize()
        self.drag_start_pos = QPoint()
        self.is_locked = False
        self.bg_color = "#1E1F20"
        self.border_color = "#8AB4F8"
        self.setCursor(Qt.PointingHandCursor)
        
        self.update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Text edit (Clean, single writing area)
        self.note_edit = QTextEdit(self)
        self.note_edit.setPlaceholderText(t("welcome_placeholder"))
        self.note_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(45, 47, 49, 0.7);
                border: 1px solid rgba(68, 71, 70, 0.7);
                border-radius: 8px;
                color: #E3E3E3;
                font-size: 12px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.note_edit)

        # Save button at bottom right
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("💾 " + t("workflow_dialog_save"), self)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A73E8;
                color: #FFFFFF;
                font-weight: bold;
                border-radius: 8px;
                padding: 5px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1557B0;
            }
        """)
        self.save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def update_style(self):
        bg = self.bg_color if self.bg_color else "transparent"
        border = self.border_color if self.border_color else "transparent"
        self.setStyleSheet(f"""
            QFrame#QuickNoteCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)

    def on_save(self):
        content = self.note_edit.toPlainText().strip()
        if content:
            lines = content.split('\n')
            title = lines[0][:40] if lines else t("quick_note_title")
            if len(lines[0]) > 40:
                title += "..."
            self.quick_note_saved.emit(title, content)
            self.note_edit.clear()

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.LeftButton:
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
                nw = max(220, min(900, self.drag_start_size.width() + delta.x()))
                nh = max(120, min(700, self.drag_start_size.height() + delta.y()))
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
                self.position_changed.emit(self.x(), self.y())
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.is_locked:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            b_col = self.border_color if (self.border_color and self.border_color != "transparent") else "#8AB4F8"
            painter.setPen(QPen(QColor(b_col), 1.5))
            w, h = self.width(), self.height()
            painter.drawLine(w - 12, h - 4, w - 4, h - 12)
            painter.drawLine(w - 8, h - 4, w - 4, h - 8)
            painter.end()


class CorkboardNoteCard(QFrame):
    """Sticky Note card matching Not Defteri NoteCardWidget appearance with collision-free top-right copy button."""
    clicked = Signal(dict)
    position_changed = Signal(int, int, int, int, int) # note_id, x, y, w, h

    def __init__(self, note_data, color_idx=0, mode="free", show_images=True, parent=None):
        super().__init__(parent)
        self.setObjectName("CorkboardCard")
        self.note_data = note_data
        self.mode = mode
        self.show_images = show_images
        self.drag_position = None
        self.is_resizing = False
        self.drag_start_size = QSize()
        self.drag_start_pos = QPoint()
        self.is_locked = False
        
        w = self.note_data.get('corkboard_w') or 220
        h = self.note_data.get('corkboard_h') or 200
        self.setMinimumSize(160, 140)
        self.resize(w, h)
        self.setCursor(Qt.PointingHandCursor)
        
        self.image_path = self.note_data.get('image_path')
        self.display_mode = self.note_data.get('display_mode', 'WITH_IMAGE')
        
        color_hex = self.note_data.get('color_hex') or "default"
        self.apply_card_color(color_hex)
        
        # Main Layout (Add top margin if NO image to avoid collision with top-right copy button)
        has_img = self.show_images and (self.display_mode == 'WITH_IMAGE') and self.image_path and os.path.exists(self.image_path)
        top_pad = 10 if has_img else 32
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, top_pad, 10, 10)
        self.main_layout.setSpacing(6)
        
        # Image Preview Label
        self.image_label = QLabel(self)
        self.image_label.setObjectName("CorkboardCardImage")
        self.image_label.setFixedHeight(105)
        self.image_label.setScaledContents(True)
        self.image_label.setStyleSheet("border-radius: 8px; background-color: transparent;")
        self.image_label.setVisible(False)
        self.main_layout.addWidget(self.image_label)

        # Title Label
        metrics = QFontMetrics(self.font())
        title_str = self.note_data.get('title', 'Not')
        elided_title = metrics.elidedText(title_str, Qt.ElideRight, 150)
        
        self.title_label = QLabel(elided_title, self)
        self.title_label.setStyleSheet("font-weight: bold; font-size: 13px; background: transparent;")
        self.main_layout.addWidget(self.title_label)

        # Content body
        html_content = self.note_data.get('content', '')
        doc = QTextDocument()
        doc.setHtml(html_content)
        plain_text = doc.toPlainText().strip()
        if len(plain_text) > 110:
            plain_text = plain_text[:110] + "..."
            
        self.content_label = QLabel(plain_text, self)
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.content_label.setStyleSheet("font-size: 11px; line-height: 1.3; background: transparent;")
        self.main_layout.addWidget(self.content_label, 1)

        # Top Overlay Container (ONLY Right Copy Button "📋")
        self.top_overlay_container = QWidget(self)
        top_overlay_layout = QHBoxLayout(self.top_overlay_container)
        top_overlay_layout.setContentsMargins(0, 0, 0, 0)
        top_overlay_layout.addStretch()

        self.copy_btn = QPushButton("📋", self.top_overlay_container)
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setToolTip(t("home_copy_note"))
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 31, 32, 0.85);
                color: #E3E3E3;
                border: 1px solid #444746;
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #1A73E8;
                color: #FFFFFF;
                border-color: #8AB4F8;
            }
        """)
        self.copy_btn.clicked.connect(self.on_copy_text)
        top_overlay_layout.addWidget(self.copy_btn)

        self.update_image_display()
        self.top_overlay_container.raise_()

    def on_copy_text(self):
        html_content = self.note_data.get('content', '')
        doc = QTextDocument()
        doc.setHtml(html_content)
        plain_text = doc.toPlainText().strip()
        QGuiApplication.clipboard().setText(plain_text)
        main_win = self.window()
        if hasattr(main_win, 'statusBar') and main_win.statusBar():
            main_win.statusBar().showMessage(t("home_copied_msg"), 2000)

    def update_image_display(self):
        show_img = self.show_images and (self.display_mode == 'WITH_IMAGE') and self.image_path and os.path.exists(self.image_path)
        top_pad = 10 if show_img else 32
        self.main_layout.setContentsMargins(10, top_pad, 10, 10)
        
        if show_img:
            self.image_label.setVisible(True)
            if self.image_path in THUMBNAIL_CACHE:
                self.image_label.setPixmap(THUMBNAIL_CACHE[self.image_path])
            else:
                worker = ImageLoadWorker(self.image_path, target_w=216, target_h=105)
                worker.signals.image_loaded.connect(lambda pix: self.image_label.setPixmap(pix))
                QThreadPool.globalInstance().start(worker)
        else:
            self.image_label.setVisible(False)

    def apply_card_color(self, color_hex):
        bg, border, text_col = get_palette_colors(color_hex)
        self.note_data['color_hex'] = color_hex
        self.setStyleSheet(f"""
            QFrame#CorkboardCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
            QLabel {{
                color: {text_col};
            }}
        """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if hasattr(self, 'top_overlay_container') and self.top_overlay_container:
            self.top_overlay_container.setGeometry(6, 6, max(80, w - 12), 26)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        copy_act = menu.addAction(t("home_copy_note"))
        copy_act.triggered.connect(self.on_copy_text)
        
        main_win = self.window()
        if main_win and getattr(main_win, 'incognito_active', False):
            menu.addSeparator()
            is_hidden = self.note_data.get('is_hidden', 0) == 1
            if not is_hidden:
                hide_act = menu.addAction(t("menu_hide"))
                hide_act.triggered.connect(lambda: getattr(main_win, 'on_note_hide', lambda d: None)(self.note_data))
            else:
                unhide_act = menu.addAction(t("menu_unhide"))
                unhide_act.triggered.connect(lambda: getattr(main_win, 'on_note_unhide', lambda d: None)(self.note_data))
                
        menu.exec(QCursor.pos())

    def mousePressEvent(self, event):
        if not self.is_locked and self.mode == "free" and event.button() == Qt.LeftButton:
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
        if not self.is_locked and self.mode == "free" and (event.buttons() & Qt.LeftButton):
            if self.is_resizing:
                delta = event.globalPosition().toPoint() - self.drag_start_pos
                nw = max(160, min(600, self.drag_start_size.width() + delta.x()))
                nh = max(140, min(500, self.drag_start_size.height() + delta.y()))
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
        if not self.is_locked and self.mode == "free":
            if self.is_resizing:
                self.is_resizing = False
                self.position_changed.emit(self.note_data.get('id', 0), self.x(), self.y(), self.width(), self.height())
            elif self.drag_position is not None:
                self.drag_position = None
                self.position_changed.emit(self.note_data.get('id', 0), self.x(), self.y(), self.width(), self.height())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.note_data)
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.is_locked and self.mode == "free":
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(QColor("#8AB4F8"), 1.5))
            w, h = self.width(), self.height()
            painter.drawLine(w - 12, h - 4, w - 4, h - 12)
            painter.drawLine(w - 8, h - 4, w - 4, h - 8)
            painter.end()


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


class HomePageSettingsDialog(QDialog):
    """Spacious, scrollable modal dialog for Main Page Settings with NoWheelSliders to prevent accidental value changes."""
    def __init__(self, welcome_screen, parent=None):
        super().__init__(parent or welcome_screen)
        self.welcome_screen = welcome_screen
        self.setWindowTitle(t("home_settings_title"))
        self.resize(480, 560)
        self.setMinimumSize(440, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1F20;
                color: #E3E3E3;
                border-radius: 14px;
            }
            QLabel {
                color: #E3E3E3;
                font-size: 13px;
            }
            QLabel#SectionHeader {
                color: #8AB4F8;
                font-weight: bold;
                font-size: 14px;
                padding-top: 6px;
            }
            QPushButton {
                background-color: #2D2F31;
                color: #E3E3E3;
                border: 1px solid #444746;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3C4043;
                color: #FFFFFF;
            }
            QPushButton[primary="true"] {
                background-color: #1A73E8;
                color: #FFFFFF;
                border-color: #8AB4F8;
            }
            QCheckBox {
                color: #E3E3E3;
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2D2F31;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #8AB4F8;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
        """)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(16, 16, 16, 16)
        dialog_layout.setSpacing(12)

        # Header Title
        hdr = QLabel(t("home_settings_title"), self)
        hdr.setStyleSheet("font-size: 18px; font-weight: bold; color: #8AB4F8; padding-bottom: 4px;")
        dialog_layout.addWidget(hdr)

        # Scroll Area to prevent squeezing/clipping
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        # --- SECTION 1: LAYOUT & POSITIONS ---
        sec1_hdr = QLabel("📌 " + t("home_layout_mode"), scroll_content)
        sec1_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec1_hdr)

        # Lock/Unlock Button
        is_locked = self.welcome_screen.positions_locked
        lock_btn_text = t("home_unlock_positions") if is_locked else t("home_lock_positions")
        self.lock_btn = QPushButton(lock_btn_text, scroll_content)
        self.lock_btn.setProperty("primary", is_locked)
        self.lock_btn.clicked.connect(self.toggle_lock)
        layout.addWidget(self.lock_btn)

        # Free Canvas vs Grid
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(10)
        self.free_mode_btn = QPushButton(t("corkboard_mode_free"), scroll_content)
        self.grid_mode_btn = QPushButton(t("corkboard_mode_grid"), scroll_content)

        current_mode = self.welcome_screen.corkboard_mode
        self.free_mode_btn.setProperty("primary", current_mode == "free")
        self.grid_mode_btn.setProperty("primary", current_mode == "grid")

        self.free_mode_btn.clicked.connect(lambda: self.set_mode("free"))
        self.grid_mode_btn.clicked.connect(lambda: self.set_mode("grid"))
        mode_layout.addWidget(self.free_mode_btn)
        mode_layout.addWidget(self.grid_mode_btn)
        layout.addLayout(mode_layout)

        # Align Positions
        self.reset_btn = QPushButton(t("corkboard_reset_pos"), scroll_content)
        self.reset_btn.clicked.connect(self.reset_positions)
        layout.addWidget(self.reset_btn)

        # --- SECTION 2: GREETING TITLE SETTINGS ---
        sec2_hdr = QLabel("✏️ Karşılama Başlığı Ayarları", scroll_content)
        sec2_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec2_hdr)

        # Title Visibility Checkbox
        self.title_cb = QCheckBox(t("home_show_title"), scroll_content)
        self.title_cb.setChecked(self.welcome_screen.title_visible)
        self.title_cb.toggled.connect(self.welcome_screen.set_title_visible)
        layout.addWidget(self.title_cb)

        # Title Font Family Dropdown
        font_family_layout = QHBoxLayout()
        self.font_family_lbl = QLabel(t("home_title_font_family"), scroll_content)
        font_family_layout.addWidget(self.font_family_lbl)
        
        self.font_family_combo = QComboBox(scroll_content)
        self.font_family_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2F31;
                color: #E3E3E3;
                selection-background-color: #1A73E8;
            }
        """)
        font_list = ["Segoe UI", "Arial", "Inter", "Roboto", "Trebuchet MS", "Verdana", "Georgia", "Comic Sans MS", "Courier New", "Impact"]
        curr_font = self.welcome_screen.title_font_family
        if curr_font and curr_font not in font_list:
            font_list.insert(0, curr_font)
        self.font_family_combo.addItems(font_list)
        if curr_font in font_list:
            self.font_family_combo.setCurrentText(curr_font)
        self.font_family_combo.currentTextChanged.connect(self.welcome_screen.set_title_font_family)
        font_family_layout.addWidget(self.font_family_combo, 1)
        layout.addLayout(font_family_layout)

        # Title Font Weight Dropdown (Thin 100 to Black 900)
        font_weight_layout = QHBoxLayout()
        self.font_weight_lbl = QLabel(t("home_title_font_weight"), scroll_content)
        font_weight_layout.addWidget(self.font_weight_lbl)

        self.font_weight_combo = QComboBox(scroll_content)
        self.font_weight_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2F31;
                color: #E3E3E3;
                selection-background-color: #1A73E8;
            }
        """)
        self.weight_map = [
            (t("weight_thin"), 100),
            (t("weight_light"), 300),
            (t("weight_normal"), 400),
            (t("weight_medium"), 500),
            (t("weight_semibold"), 600),
            (t("weight_bold"), 700),
            (t("weight_extrabold"), 800),
            (t("weight_black"), 900),
        ]
        for label, val in self.weight_map:
            self.font_weight_combo.addItem(label, val)

        curr_weight = self.welcome_screen.title_font_weight
        selected_idx = 5 # Default Bold 700
        for idx, (label, val) in enumerate(self.weight_map):
            if val == curr_weight:
                selected_idx = idx
                break
        self.font_weight_combo.setCurrentIndex(selected_idx)
        self.font_weight_combo.currentIndexChanged.connect(self.on_font_weight_changed)
        font_weight_layout.addWidget(self.font_weight_combo, 1)
        layout.addLayout(font_weight_layout)

        # Title Font Size Slider (NoWheelSlider, Range 16 - 120)
        font_size_layout = QHBoxLayout()
        self.font_size_lbl = QLabel(t("home_title_font_size").format(size=self.welcome_screen.title_font_size), scroll_content)
        font_size_layout.addWidget(self.font_size_lbl)
        
        self.font_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.font_slider.setRange(16, 120)
        self.font_slider.setValue(self.welcome_screen.title_font_size)
        self.font_slider.valueChanged.connect(self.on_font_slider_changed)
        font_size_layout.addWidget(self.font_slider, 1)
        layout.addLayout(font_size_layout)

        # Title Box Size Section
        title_size_hdr = QLabel("📐 " + t("title_size_title"), scroll_content)
        title_size_hdr.setStyleSheet("color: #E3E3E3; font-weight: bold; font-size: 13px; padding-top: 4px;")
        layout.addWidget(title_size_hdr)

        title_w_layout = QHBoxLayout()
        w_text = f"{self.welcome_screen.title_w}px" if self.welcome_screen.title_w > 0 else "Otomatik (Auto)"
        self.title_w_lbl = QLabel(t("title_width_lbl").format(w=w_text), scroll_content)
        title_w_layout.addWidget(self.title_w_lbl)
        self.title_w_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.title_w_slider.setRange(0, 1800)
        self.title_w_slider.setValue(self.welcome_screen.title_w)
        self.title_w_slider.valueChanged.connect(self.on_title_w_changed)
        title_w_layout.addWidget(self.title_w_slider, 1)
        layout.addLayout(title_w_layout)

        title_h_layout = QHBoxLayout()
        h_text = f"{self.welcome_screen.title_h}px" if self.welcome_screen.title_h > 0 else "Otomatik (Auto)"
        self.title_h_lbl = QLabel(t("title_height_lbl").format(h=h_text), scroll_content)
        title_h_layout.addWidget(self.title_h_lbl)
        self.title_h_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.title_h_slider.setRange(0, 600)
        self.title_h_slider.setValue(self.welcome_screen.title_h)
        self.title_h_slider.valueChanged.connect(self.on_title_h_changed)
        title_h_layout.addWidget(self.title_h_slider, 1)
        layout.addLayout(title_h_layout)

        self.auto_fit_btn = QPushButton(t("title_auto_fit_btn"), scroll_content)
        self.auto_fit_btn.clicked.connect(self.auto_fit_title)
        layout.addWidget(self.auto_fit_btn)

        # Text Color & Letter Outline Color Buttons
        title_colors_layout = QHBoxLayout()
        self.text_color_btn = QPushButton("🎨 Yazı Rengi", scroll_content)
        self.text_color_btn.clicked.connect(self.pick_text_color)
        self.outline_color_btn = QPushButton("🎨 Harf Çizgisi Rengi", scroll_content)
        self.outline_color_btn.clicked.connect(self.pick_outline_color)
        title_colors_layout.addWidget(self.text_color_btn)
        title_colors_layout.addWidget(self.outline_color_btn)
        layout.addLayout(title_colors_layout)

        # Letter Outline Width Slider (NoWheelSlider)
        outline_slider_layout = QHBoxLayout()
        self.outline_width_lbl = QLabel(f"Harf Dış Çizgisi: {self.welcome_screen.title_outline_width}px", scroll_content)
        outline_slider_layout.addWidget(self.outline_width_lbl)
        
        self.outline_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.outline_slider.setRange(0, 8)
        self.outline_slider.setValue(self.welcome_screen.title_outline_width)
        self.outline_slider.valueChanged.connect(self.on_outline_slider_changed)
        outline_slider_layout.addWidget(self.outline_slider, 1)
        layout.addLayout(outline_slider_layout)

        # Title Frame Box Controls
        self.frame_cb = QCheckBox("Yazı Çerçeve Kutusunu Etkinleştir", scroll_content)
        self.frame_cb.setChecked(self.welcome_screen.title_frame_enabled)
        self.frame_cb.toggled.connect(self.welcome_screen.set_title_frame_enabled)
        layout.addWidget(self.frame_cb)

        frame_colors_layout = QHBoxLayout()
        self.frame_bg_btn = QPushButton("🎨 Kutu Rengi", scroll_content)
        self.frame_bg_btn.clicked.connect(self.pick_frame_bg)
        self.frame_border_btn = QPushButton("🎨 Kutu Kenarlık Rengi", scroll_content)
        self.frame_border_btn.clicked.connect(self.pick_frame_border_color)
        frame_colors_layout.addWidget(self.frame_bg_btn)
        frame_colors_layout.addWidget(self.frame_border_btn)
        layout.addLayout(frame_colors_layout)

        # --- SECTION 3: QUICK NOTE STYLE SETTINGS ---
        sec3_hdr = QLabel("⚡ " + t("qn_style_title"), scroll_content)
        sec3_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec3_hdr)

        self.qn_cb = QCheckBox(t("home_show_quick_note"), scroll_content)
        self.qn_cb.setChecked(self.welcome_screen.quick_note_visible)
        self.qn_cb.toggled.connect(self.welcome_screen.set_quick_note_visible)
        layout.addWidget(self.qn_cb)

        # Quick Note Size Controls
        qn_size_hdr = QLabel("📐 " + t("qn_size_title"), scroll_content)
        qn_size_hdr.setStyleSheet("color: #E3E3E3; font-weight: bold; font-size: 13px; padding-top: 4px;")
        layout.addWidget(qn_size_hdr)

        # Width Slider
        qn_w_layout = QHBoxLayout()
        self.qn_w_lbl = QLabel(t("qn_width_lbl").format(w=self.welcome_screen.quick_note_w), scroll_content)
        qn_w_layout.addWidget(self.qn_w_lbl)
        self.qn_w_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.qn_w_slider.setRange(220, 800)
        self.qn_w_slider.setValue(self.welcome_screen.quick_note_w)
        self.qn_w_slider.valueChanged.connect(self.on_qn_w_changed)
        qn_w_layout.addWidget(self.qn_w_slider, 1)
        layout.addLayout(qn_w_layout)

        # Height Slider
        qn_h_layout = QHBoxLayout()
        self.qn_h_lbl = QLabel(t("qn_height_lbl").format(h=self.welcome_screen.quick_note_h), scroll_content)
        qn_h_layout.addWidget(self.qn_h_lbl)
        self.qn_h_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.qn_h_slider.setRange(120, 600)
        self.qn_h_slider.setValue(self.welcome_screen.quick_note_h)
        self.qn_h_slider.valueChanged.connect(self.on_qn_h_changed)
        qn_h_layout.addWidget(self.qn_h_slider, 1)
        layout.addLayout(qn_h_layout)

        qn_colors_layout = QHBoxLayout()
        self.qn_bg_btn = QPushButton(t("qn_bg_btn"), scroll_content)
        self.qn_bg_btn.clicked.connect(self.pick_qn_bg)
        self.qn_border_btn = QPushButton(t("qn_border_btn"), scroll_content)
        self.qn_border_btn.clicked.connect(self.pick_qn_border)
        qn_colors_layout.addWidget(self.qn_bg_btn)
        qn_colors_layout.addWidget(self.qn_border_btn)
        layout.addLayout(qn_colors_layout)

        # --- SECTION 4: STICKY NOTES SETTINGS ---
        sec4_hdr = QLabel("📌 Yapışkan Notlar (Sticky Notes)", scroll_content)
        sec4_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec4_hdr)

        self.notes_vis_cb = QCheckBox("Notları Göster", scroll_content)
        self.notes_vis_cb.setChecked(self.welcome_screen.corkboard_notes_visible)
        self.notes_vis_cb.toggled.connect(self.welcome_screen.set_corkboard_notes_visible)
        layout.addWidget(self.notes_vis_cb)

        self.show_img_cb = QCheckBox("Görselleri Göster", scroll_content)
        self.show_img_cb.setChecked(self.welcome_screen.corkboard_show_images)
        self.show_img_cb.toggled.connect(self.welcome_screen.set_corkboard_show_images)
        layout.addWidget(self.show_img_cb)

        # --- SECTION 5: WALLPAPER ---
        sec5_hdr = QLabel("🖼️ " + t("home_wallpaper_section"), scroll_content)
        sec5_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec5_hdr)

        wp_layout = QHBoxLayout()
        wp_layout.setSpacing(10)
        self.wallpaper_btn = QPushButton(t("welcome_wallpaper_btn"), scroll_content)
        self.wallpaper_btn.clicked.connect(self.select_wallpaper)
        self.remove_wp_btn = QPushButton(t("home_remove_wallpaper"), scroll_content)
        self.remove_wp_btn.clicked.connect(self.remove_wallpaper)
        wp_layout.addWidget(self.wallpaper_btn)
        wp_layout.addWidget(self.remove_wp_btn)
        layout.addLayout(wp_layout)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        dialog_layout.addWidget(scroll, 1)

        # Bottom Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton(t("home_close_btn"), self)
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        dialog_layout.addLayout(close_layout)

    def toggle_lock(self):
        new_locked = not self.welcome_screen.positions_locked
        self.welcome_screen.set_positions_locked(new_locked)
        self.lock_btn.setText(t("home_unlock_positions") if new_locked else t("home_lock_positions"))
        self.lock_btn.setProperty("primary", new_locked)
        self.lock_btn.style().unpolish(self.lock_btn)
        self.lock_btn.style().polish(self.lock_btn)

    def set_mode(self, mode):
        self.welcome_screen.switch_corkboard_mode(mode)
        self.free_mode_btn.setProperty("primary", mode == "free")
        self.grid_mode_btn.setProperty("primary", mode == "grid")
        for b in (self.free_mode_btn, self.grid_mode_btn):
            b.style().unpolish(b)
            b.style().polish(b)

    def on_font_weight_changed(self, index):
        val = self.font_weight_combo.itemData(index)
        if val:
            self.welcome_screen.set_title_font_weight(val)

    def on_font_slider_changed(self, val):
        self.font_size_lbl.setText(t("home_title_font_size").format(size=val))
        self.welcome_screen.set_title_font_size(val)

    def on_title_w_changed(self, val):
        w_text = f"{val}px" if val > 0 else "Otomatik (Auto)"
        self.title_w_lbl.setText(t("title_width_lbl").format(w=w_text))
        self.welcome_screen.set_title_size(val, self.welcome_screen.title_h)

    def on_title_h_changed(self, val):
        h_text = f"{val}px" if val > 0 else "Otomatik (Auto)"
        self.title_h_lbl.setText(t("title_height_lbl").format(h=h_text))
        self.welcome_screen.set_title_size(self.welcome_screen.title_w, val)

    def auto_fit_title(self):
        self.title_w_slider.setValue(0)
        self.title_h_slider.setValue(0)
        self.welcome_screen.set_title_size(0, 0)

    def on_qn_w_changed(self, val):
        self.qn_w_lbl.setText(t("qn_width_lbl").format(w=val))
        self.welcome_screen.set_quick_note_size(val, self.welcome_screen.quick_note_h)

    def on_qn_h_changed(self, val):
        self.qn_h_lbl.setText(t("qn_height_lbl").format(h=val))
        self.welcome_screen.set_quick_note_size(self.welcome_screen.quick_note_w, val)

    def on_outline_slider_changed(self, val):
        self.outline_width_lbl.setText(f"Harf Dış Çizgisi: {val}px")
        self.welcome_screen.set_title_outline_width(val)

    def pick_color_with_transparent(self, initial_color, title):
        dialog = QColorDialog(QColor(initial_color if initial_color != 'transparent' else '#FFFFFF'), self)
        dialog.setWindowTitle(title)
        dialog.setOption(QColorDialog.ShowAlphaChannel, True)
        
        # Add Saydam (Transparent) custom button
        trans_btn = QPushButton(t("make_transparent"), dialog)
        dialog.layout().addWidget(trans_btn)
        
        res_color = [None]
        def set_trans():
            res_color[0] = "transparent"
            dialog.accept()
            
        trans_btn.clicked.connect(set_trans)
        
        if dialog.exec():
            if res_color[0] == "transparent":
                return "transparent"
            col = dialog.currentColor()
            if col.alpha() == 0:
                return "transparent"
            return col.name(QColor.HexArgb) if col.alpha() < 255 else col.name()
        return None

    def pick_text_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_color, "Yazı Rengi Seç")
        if c:
            self.welcome_screen.set_title_color(c)

    def pick_outline_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_outline_color, "Harf Çizgi Rengi Seç")
        if c:
            self.welcome_screen.set_title_outline_color(c)

    def pick_frame_bg(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_frame_bg, "Kutu Arka Plan Rengi Seç")
        if c:
            self.welcome_screen.set_title_frame_bg(c)

    def pick_frame_border_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_frame_border_color, "Kutu Kenarlık Rengi Seç")
        if c:
            self.welcome_screen.set_title_frame_border_color(c)

    def pick_qn_bg(self):
        c = self.pick_color_with_transparent(self.welcome_screen.quick_note_bg, "Hızlı Not Arka Plan Rengi Seç")
        if c:
            self.welcome_screen.set_quick_note_bg(c)

    def pick_qn_border(self):
        c = self.pick_color_with_transparent(self.welcome_screen.quick_note_border_color, "Hızlı Not Kenarlık Rengi Seç")
        if c:
            self.welcome_screen.set_quick_note_border_color(c)

    def reset_positions(self):
        self.welcome_screen.reset_corkboard_positions()

    def select_wallpaper(self):
        self.welcome_screen.select_wallpaper()

    def remove_wallpaper(self):
        self.welcome_screen.set_wallpaper("")
        self.welcome_screen.wallpaper_selected.emit("")


class WelcomeScreen(QWidget):
    quick_note_saved = Signal(str, str) # title, content
    paste_corkboard_requested = Signal(str, str) # title, content
    corkboard_unpin_requested = Signal(int) # note_id
    corkboard_position_changed = Signal(int, int, int, int, int) # note_id, x, y, w, h
    title_position_changed = Signal(int, int) # x, y
    quick_note_position_changed = Signal(int, int) # x, y
    positions_locked_changed = Signal(bool)
    note_open_requested = Signal(int) # note_id
    title_changed = Signal(str)
    wallpaper_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WelcomeWidget")
        self.wallpaper_path = ""
        self.corkboard_cards = []
        self.corkboard_notes = []
        self.corkboard_mode = database.get_setting("corkboard_mode", "free")
        self.quick_note_widget = None
        
        self.positions_locked = database.get_setting("home_positions_locked", "0") == "1"
        self.title_visible = database.get_setting("welcome_title_visible", "1") == "1"
        self.title_font_size = int(database.get_setting("welcome_title_font_size", "28"))
        self.title_font_family = database.get_setting("welcome_title_font_family", "Segoe UI")
        self.title_font_weight = int(database.get_setting("welcome_title_font_weight", "700"))
        self.title_w = int(database.get_setting("welcome_title_w", "0"))
        self.title_h = int(database.get_setting("welcome_title_h", "0"))
        self.title_color = database.get_setting("welcome_title_color", "#E3E3E3")
        self.title_outline_color = database.get_setting("welcome_title_outline_color", "#000000")
        self.title_outline_width = int(database.get_setting("welcome_title_outline_width", "0"))
        self.title_frame_enabled = database.get_setting("welcome_title_frame_enabled", "1") == "1"
        self.title_frame_bg = database.get_setting("welcome_title_frame_bg", "rgba(32, 33, 36, 0.75)")
        self.title_frame_border_color = database.get_setting("welcome_title_frame_border_color", "#8AB4F8")
        
        self.quick_note_visible = database.get_setting("quick_note_visible", "1") == "1"
        self.quick_note_bg = database.get_setting("quick_note_bg", "#1E1F20")
        self.quick_note_border_color = database.get_setting("quick_note_border_color", "#8AB4F8")
        self.quick_note_w = int(database.get_setting("quick_note_w", "340"))
        self.quick_note_h = int(database.get_setting("quick_note_h", "160"))

        self.corkboard_notes_visible = database.get_setting("corkboard_notes_visible", "1") == "1"
        self.corkboard_show_images = database.get_setting("corkboard_show_images", "1") == "1"
        
        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Outer Scroll Container
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Full Page Free Canvas Container
        self.corkboard_grid_widget = QWidget(self.scroll_content)
        self.corkboard_grid_widget.setStyleSheet("background: transparent;")
        self.corkboard_grid_widget.setMinimumHeight(800)
        
        self.title_label = EditableLabel(t("welcome_title_default"), parent=self.corkboard_grid_widget)
        self.title_label.text_changed.connect(self.title_changed.emit)
        self.title_label.position_changed.connect(self.on_title_position_changed)
        self.title_label.size_changed.connect(self.on_title_size_changed)
        self.apply_title_settings()

        self.corkboard_grid_layout = QGridLayout(self.corkboard_grid_widget)
        self.corkboard_grid_layout.setContentsMargins(0, 0, 0, 0)
        self.corkboard_grid_layout.setSpacing(14)
        self.corkboard_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        content_layout.addWidget(self.corkboard_grid_widget)

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # Bottom Right Single Dedicated Settings Button
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addStretch()

        self.home_settings_btn = QPushButton(t("home_settings_btn"), self)
        self.home_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(45, 47, 49, 0.85);
                color: #8AB4F8;
                border: 1px solid #8AB4F8;
                border-radius: 16px;
                padding: 7px 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(26, 115, 232, 0.95);
                color: #FFFFFF;
            }
        """)
        self.home_settings_btn.clicked.connect(self.open_home_settings_dialog)
        footer_layout.addWidget(self.home_settings_btn)

        main_layout.addLayout(footer_layout)

    def apply_title_settings(self):
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.is_locked = self.positions_locked
            self.title_label.font_size = self.title_font_size
            self.title_label.font_family = self.title_font_family
            self.title_label.font_weight = self.title_font_weight
            self.title_label.text_color = self.title_color
            self.title_label.outline_color = self.title_outline_color
            self.title_label.outline_width = self.title_outline_width
            self.title_label.frame_enabled = self.title_frame_enabled
            self.title_label.frame_bg = self.title_frame_bg
            self.title_label.frame_border_color = self.title_frame_border_color
            self.title_label.update_title_styling()
            self.title_label.setVisible(self.title_visible)

            # Auto-calculate geometry if custom size is 0 or unconfigured
            font = QFont(self.title_font_family, self.title_font_size)
            font.setWeight(QFont.Weight(self.title_font_weight) if hasattr(QFont, 'Weight') else self.title_font_weight)
            metrics = QFontMetrics(font)
            text_str = self.title_label.label.text()
            auto_w = max(450, metrics.horizontalAdvance(text_str) + 60)
            auto_h = max(50, metrics.height() + 24)

            curr_w = self.title_w if self.title_w > 0 else auto_w
            curr_h = self.title_h if self.title_h > 0 else auto_h

            curr_pos = self.title_label.pos()
            self.title_label.setGeometry(curr_pos.x(), curr_pos.y(), curr_w, curr_h)

    def set_positions_locked(self, locked):
        self.positions_locked = locked
        database.set_setting("home_positions_locked", "1" if locked else "0")
        self.positions_locked_changed.emit(locked)
        
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.is_locked = locked
            tx = database.get_setting("welcome_title_x")
            if (tx is None or tx == "") and self.title_label.x() >= 0:
                self.on_title_position_changed(self.title_label.x(), self.title_label.y())
        if self.quick_note_widget:
            self.quick_note_widget.is_locked = locked
            qx = database.get_setting("quick_note_x")
            if (qx is None or qx == "") and self.quick_note_widget.x() >= 0:
                self.on_quick_note_position_changed(self.quick_note_widget.x(), self.quick_note_widget.y())
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.is_locked = locked

    def set_title_visible(self, visible):
        self.title_visible = visible
        database.set_setting("welcome_title_visible", "1" if visible else "0")
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setVisible(visible)

    def set_title_font_size(self, font_size):
        self.title_font_size = font_size
        database.set_setting("welcome_title_font_size", font_size)
        self.apply_title_settings()

    def set_title_font_family(self, font_family):
        self.title_font_family = font_family
        database.set_setting("welcome_title_font_family", font_family)
        self.apply_title_settings()

    def set_title_font_weight(self, font_weight):
        self.title_font_weight = font_weight
        database.set_setting("welcome_title_font_weight", font_weight)
        self.apply_title_settings()

    def set_title_size(self, w, h):
        self.title_w = w
        self.title_h = h
        database.set_setting("welcome_title_w", w)
        database.set_setting("welcome_title_h", h)
        self.apply_title_settings()

    def on_title_size_changed(self, w, h):
        self.title_w = w
        self.title_h = h
        database.set_setting("welcome_title_w", w)
        database.set_setting("welcome_title_h", h)

    def set_quick_note_size(self, w, h):
        self.quick_note_w = w
        self.quick_note_h = h
        database.set_setting("quick_note_w", w)
        database.set_setting("quick_note_h", h)
        if self.quick_note_widget:
            self.quick_note_widget.resize(w, h)

    def on_quick_note_size_changed(self, w, h):
        self.quick_note_w = w
        self.quick_note_h = h
        database.set_setting("quick_note_w", w)
        database.set_setting("quick_note_h", h)

    def set_title_color(self, color_hex):
        self.title_color = color_hex
        database.set_setting("welcome_title_color", color_hex)
        self.apply_title_settings()

    def set_title_outline_color(self, color_hex):
        self.title_outline_color = color_hex
        database.set_setting("welcome_title_outline_color", color_hex)
        self.apply_title_settings()

    def set_title_outline_width(self, width):
        self.title_outline_width = width
        database.set_setting("welcome_title_outline_width", width)
        self.apply_title_settings()

    def set_title_frame_enabled(self, enabled):
        self.title_frame_enabled = enabled
        database.set_setting("welcome_title_frame_enabled", "1" if enabled else "0")
        self.apply_title_settings()

    def set_title_frame_bg(self, bg_color):
        self.title_frame_bg = bg_color
        database.set_setting("welcome_title_frame_bg", bg_color)
        self.apply_title_settings()

    def set_title_frame_border_color(self, border_color):
        self.title_frame_border_color = border_color
        database.set_setting("welcome_title_frame_border_color", border_color)
        self.apply_title_settings()

    def set_title_outline_color(self, color_hex):
        self.title_outline_color = color_hex
        database.set_setting("welcome_title_outline_color", color_hex)
        self.apply_title_settings()

    def set_title_outline_width(self, width):
        self.title_outline_width = width
        database.set_setting("welcome_title_outline_width", width)
        self.apply_title_settings()

    def set_title_frame_enabled(self, enabled):
        self.title_frame_enabled = enabled
        database.set_setting("welcome_title_frame_enabled", "1" if enabled else "0")
        self.apply_title_settings()

    def set_title_frame_bg(self, bg_color):
        self.title_frame_bg = bg_color
        database.set_setting("welcome_title_frame_bg", bg_color)
        self.apply_title_settings()

    def set_title_frame_border_color(self, border_color):
        self.title_frame_border_color = border_color
        database.set_setting("welcome_title_frame_border_color", border_color)
        self.apply_title_settings()

    def set_quick_note_visible(self, visible):
        self.quick_note_visible = visible
        database.set_setting("quick_note_visible", "1" if visible else "0")
        if self.quick_note_widget:
            self.quick_note_widget.setVisible(visible)

    def set_quick_note_bg(self, bg_color):
        self.quick_note_bg = bg_color
        database.set_setting("quick_note_bg", bg_color)
        if self.quick_note_widget:
            self.quick_note_widget.bg_color = bg_color
            self.quick_note_widget.update_style()

    def set_quick_note_border_color(self, border_color):
        self.quick_note_border_color = border_color
        database.set_setting("quick_note_border_color", border_color)
        if self.quick_note_widget:
            self.quick_note_widget.border_color = border_color
            self.quick_note_widget.update_style()

    def set_corkboard_notes_visible(self, visible):
        self.corkboard_notes_visible = visible
        database.set_setting("corkboard_notes_visible", "1" if visible else "0")
        for card in self.corkboard_cards:
            card.setVisible(visible)

    def set_corkboard_show_images(self, show_images):
        self.corkboard_show_images = show_images
        database.set_setting("corkboard_show_images", "1" if show_images else "0")
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.show_images = show_images
                card.update_image_display()

    def open_home_settings_dialog(self):
        dialog = HomePageSettingsDialog(self)
        dialog.exec()

    def on_title_position_changed(self, x, y):
        if x >= 0 and y >= 0:
            database.set_setting("welcome_title_x", x)
            database.set_setting("welcome_title_y", y)
            if hasattr(self, 'title_label') and self.title_label and self.corkboard_mode == "free":
                self.title_label.move(x, y)

    def on_quick_note_position_changed(self, x, y):
        database.set_setting("quick_note_x", x)
        database.set_setting("quick_note_y", y)

    def switch_corkboard_mode(self, mode):
        self.corkboard_mode = mode
        database.set_setting("corkboard_mode", mode)
        self.render_corkboard()

    def reset_corkboard_positions(self):
        viewport_w = max(600, self.scroll_area.viewport().width())
        # Reset title
        tx = max(10, (viewport_w - 450) // 2)
        ty = 20
        self.title_label.move(tx, ty)
        self.on_title_position_changed(tx, ty)

        # Reset quick note
        qx = max(10, (viewport_w - 340) // 2)
        qy = 90
        if self.quick_note_widget:
            self.quick_note_widget.move(qx, qy)
            self.on_quick_note_position_changed(qx, qy)

        columns = max(1, viewport_w // 220)
        for i, card in enumerate(self.corkboard_cards):
            if isinstance(card, CorkboardNoteCard):
                row = i // columns
                col = i % columns
                x = col * 214
                y = 280 + row * 194
                card.note_data['corkboard_x'] = x
                card.note_data['corkboard_y'] = y
                database.update_corkboard_geometry(card.note_data.get('id', 0), x, y, 200, 180)
                self.corkboard_position_changed.emit(card.note_data.get('id', 0), x, y, 200, 180)
        
        self.switch_corkboard_mode("free")

    def set_corkboard_notes(self, notes):
        self.corkboard_notes = notes
        self.render_corkboard()

    def render_corkboard(self):
        # Clear existing layout references & cards
        if hasattr(self, 'corkboard_grid_layout') and self.corkboard_grid_layout:
            if hasattr(self, 'title_label') and self.title_label:
                self.corkboard_grid_layout.removeWidget(self.title_label)
            if hasattr(self, 'quick_note_widget') and self.quick_note_widget:
                self.corkboard_grid_layout.removeWidget(self.quick_note_widget)
            for card in self.corkboard_cards:
                self.corkboard_grid_layout.removeWidget(card)
                card.setParent(None)
                card.deleteLater()
        self.corkboard_cards.clear()

        # Add Title Label
        if not hasattr(self, 'title_label') or not self.title_label:
            self.title_label = EditableLabel(t("welcome_title_default"), parent=self.corkboard_grid_widget)
            self.title_label.text_changed.connect(self.title_changed.emit)
            self.title_label.position_changed.connect(self.on_title_position_changed)
        
        self.apply_title_settings()

        # Add Movable Quick Note Widget
        if self.quick_note_widget is not None:
            self.quick_note_widget.setParent(None)
            self.quick_note_widget.deleteLater()

        self.quick_note_widget = QuickNoteCardWidget(parent=self.corkboard_grid_widget)
        self.quick_note_widget.resize(self.quick_note_w, self.quick_note_h)
        self.quick_note_widget.quick_note_saved.connect(self.quick_note_saved.emit)
        self.quick_note_widget.position_changed.connect(self.on_quick_note_position_changed)
        self.quick_note_widget.size_changed.connect(self.on_quick_note_size_changed)
        self.quick_note_widget.is_locked = self.positions_locked
        self.quick_note_widget.bg_color = self.quick_note_bg
        self.quick_note_widget.border_color = self.quick_note_border_color
        self.quick_note_widget.update_style()
        self.quick_note_widget.setVisible(self.quick_note_visible)

        notes = self.corkboard_notes

        if self.corkboard_mode == "free":
            self.corkboard_grid_widget.setMinimumHeight(900)
            viewport_w = max(900, self.width(), self.scroll_area.viewport().width())
            
            font = QFont(self.title_font_family, self.title_font_size)
            font.setWeight(QFont.Weight(self.title_font_weight) if hasattr(QFont, 'Weight') else self.title_font_weight)
            metrics = QFontMetrics(font)
            text_str = self.title_label.label.text()
            auto_w = max(450, metrics.horizontalAdvance(text_str) + 60)
            auto_h = max(50, metrics.height() + 24)

            title_w = self.title_w if self.title_w > 0 else auto_w
            title_h = self.title_h if self.title_h > 0 else auto_h
            
            tx_saved = database.get_setting("welcome_title_x")
            ty_saved = database.get_setting("welcome_title_y")
            
            if tx_saved is None or tx_saved == "" or int(tx_saved) <= 0:
                title_x = max(20, (viewport_w - title_w) // 2)
                title_y = 30
                self.on_title_position_changed(title_x, title_y)
            else:
                title_x = int(tx_saved)
                title_y = int(ty_saved) if (ty_saved is not None and ty_saved != "" and int(ty_saved) >= 0) else 30
            
            self.title_label.setParent(self.corkboard_grid_widget)
            self.title_label.setGeometry(title_x, title_y, title_w, title_h)
            self.title_label.setVisible(self.title_visible)

            # Place Quick Note Card
            qn_w = self.quick_note_w
            qx_saved = database.get_setting("quick_note_x")
            qy_saved = database.get_setting("quick_note_y")
            qn_x = int(qx_saved) if (qx_saved is not None and qx_saved != "") else max(10, (viewport_w - qn_w) // 2)
            qn_y = int(qy_saved) if (qy_saved is not None and qy_saved != "") else 90

            self.quick_note_widget.move(qn_x, qn_y)

            columns = max(1, viewport_w // 220)
            max_y = max(title_y + title_h + 20, qn_y + 180, 300)
            
            for i, note in enumerate(notes):
                card = CorkboardNoteCard(note, color_idx=i, mode="free", show_images=self.corkboard_show_images, parent=self.corkboard_grid_widget)
                card.is_locked = self.positions_locked
                card.position_changed.connect(self.corkboard_position_changed.emit)
                card.clicked.connect(lambda data: self.note_open_requested.emit(data.get('id', 0)))
                card.setVisible(self.corkboard_notes_visible)
                
                cx = note.get('corkboard_x', 0)
                cy = note.get('corkboard_y', 0)
                if cx == 0 and cy == 0:
                    cx = (i % columns) * 214
                    cy = 300 + (i // columns) * 194
                
                max_y = max(max_y, cy + card.height() + 20)
                card.move(cx, cy)
                self.corkboard_cards.append(card)

            self.corkboard_grid_widget.setMinimumHeight(max_y + 200)
        else:
            # Grid Mode
            self.corkboard_grid_widget.setMinimumHeight(0)
            self.corkboard_grid_layout.addWidget(self.title_label, 0, 0, 1, -1, Qt.AlignCenter)
            self.corkboard_grid_layout.addWidget(self.quick_note_widget, 1, 0, 1, -1, Qt.AlignCenter)

            columns = max(1, self.scroll_area.viewport().width() // 220)
            for i, note in enumerate(notes):
                card = CorkboardNoteCard(note, color_idx=i, mode="grid", show_images=self.corkboard_show_images, parent=self.corkboard_grid_widget)
                card.is_locked = self.positions_locked
                card.clicked.connect(lambda data: self.note_open_requested.emit(data.get('id', 0)))
                card.setVisible(self.corkboard_notes_visible)
                row = 2 + (i // columns)
                col = i % columns
                self.corkboard_grid_layout.addWidget(card, row, col)
                self.corkboard_cards.append(card)

    def select_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("welcome_wallpaper_dialog"), "", "Resim Dosyaları (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.wallpaper_selected.emit(file_path)

    def set_wallpaper(self, image_path):
        if image_path:
            self.wallpaper_path = image_path.replace("\\", "/")
        else:
            self.wallpaper_path = ""
        self.update()

    def set_welcome_title(self, title):
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setText(title)

    def retranslate_ui(self):
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.retranslate_ui()
        if hasattr(self, 'home_settings_btn'):
            self.home_settings_btn.setText(t("home_settings_btn"))

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        if self.wallpaper_path and os.path.exists(self.wallpaper_path):
            image = QImage(self.wallpaper_path)
            if not image.isNull():
                scaled_image = image.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                x = (scaled_image.width() - self.width()) // 2
                y = (scaled_image.height() - self.height()) // 2
                painter.drawImage(0, 0, scaled_image, x, y, self.width(), self.height())
        
        painter.end()
