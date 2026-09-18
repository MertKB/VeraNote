"""
Corkboard cards and Quick Note widgets for VeraNote Welcome Screen.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QFrame, QMenu)
from PySide6.QtCore import Signal, Qt, QSize, QPoint, QThreadPool, QRunnable, QObject
from PySide6.QtGui import (QPainter, QImage, QTextDocument, QFontMetrics, QCursor, 
                           QGuiApplication, QPen, QColor, QPixmap)
from utils.i18n import t
from utils.cache import THUMBNAIL_CACHE


class ImageLoadWorkerSignals(QObject):
    image_loaded = Signal(str, object) # path, QImage


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
        try:
            img = QImage(self.image_path)
            if not img.isNull():
                scaled = img.scaled(
                    self.target_w, self.target_h,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                self.signals.image_loaded.emit(self.image_path, scaled)
        except Exception:
            pass


def get_pastel_palette():
    return [
        ("default", "#444746", "#E3E3E3", t("color_default_theme")),
        ("#FEF08A", "#FACC15", "#713F12", t("color_yellow_original")),
        ("#BAE6FD", "#38BDF8", "#0C4A6E", t("color_blue")),
        ("#BBF7D0", "#4ADE80", "#14532D", t("color_green")),
        ("#FBCFE8", "#F472B6", "#831843", t("color_pink")),
        ("#FED7AA", "#FB923C", "#7C2D12", t("color_orange")),
        ("#E9D5FF", "#C084FC", "#581C87", t("color_purple")),
        ("#99F6E4", "#2DD4BF", "#134E4A", t("color_teal")),
        ("#1E293B", "#38BDF8", "#F8FAFC", t("color_dark_blue")),
        ("#161616", "#2D2D2D", "#FFFFFF", t("color_dark")),
        ("#FFFFFF", "#D1D5DB", "#111827", t("color_white")),
    ]


def get_palette_colors(color_hex):
    if not color_hex or color_hex.lower() in ("default", "none"):
        return "#1E1F20", "#444746", "#E3E3E3"
    for bg, border, text_col, _ in get_pastel_palette():
        if bg and bg.lower() == color_hex.lower():
            return bg, border, text_col
    return color_hex, "#8AB4F8", "#E3E3E3"


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

    def retranslate_ui(self):
        self.note_edit.setPlaceholderText(t("welcome_placeholder"))
        self.save_btn.setText("💾 " + t("workflow_dialog_save"))

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
        if hasattr(main_win, 'show_toast'):
            main_win.show_toast(t("toast_copied"), "success")
        elif hasattr(main_win, 'statusBar') and main_win.statusBar():
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
                def on_loaded(path, qimg):
                    if getattr(self, 'image_path', '') == path and qimg and not qimg.isNull():
                        pix = QPixmap.fromImage(qimg)
                        THUMBNAIL_CACHE[path] = pix
                        self.image_label.setPixmap(pix)
                worker.signals.image_loaded.connect(on_loaded)
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
