"""
Welcome Screen for VeraNote.
Provides a free-form / grid corkboard with sticky notes, customizable greeting title, quick note widget, and wallpaper background.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QScrollArea, QGridLayout, QStyle, QStyleOption, QFileDialog)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QPainter, QImage, QFontMetrics, QFont
from utils.i18n import t

from ui.corkboard import (
    CorkboardNoteCard, QuickNoteCardWidget, EditableLabel, HomePageSettingsDialog,
    ImageLoadWorker, ImageLoadWorkerSignals, get_pastel_palette, get_palette_colors
)

__all__ = [
    "WelcomeScreen",
    "CorkboardNoteCard",
    "QuickNoteCardWidget",
    "EditableLabel",
    "HomePageSettingsDialog",
    "ImageLoadWorker",
    "ImageLoadWorkerSignals",
    "get_pastel_palette",
    "get_palette_colors",
]


class WelcomeScreen(QWidget):
    """
    Main home page view presenting a customizable Corkboard canvas.
    Fully isolated from database layer; communicates via Qt Signals.
    """
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
    setting_changed = Signal(str, str) # setting_key, setting_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WelcomeWidget")
        self.wallpaper_path = ""
        self.corkboard_cards = []
        self.corkboard_notes = []
        self.corkboard_mode = "free"
        self.quick_note_widget = None
        
        # Default layout & title states (can be updated via load_settings)
        self.positions_locked = False
        self.title_visible = True
        self.title_font_size = 28
        self.title_font_family = "Segoe UI"
        self.title_font_weight = 700
        self.title_w = 0
        self.title_h = 0
        self.title_color = "#E3E3E3"
        self.title_outline_color = "#000000"
        self.title_outline_width = 0
        self.title_frame_enabled = True
        self.title_frame_bg = "rgba(32, 33, 36, 0.75)"
        self.title_frame_border_color = "#8AB4F8"
        
        self.quick_note_visible = True
        self.quick_note_bg = "#1E1F20"
        self.quick_note_border_color = "#8AB4F8"
        self.quick_note_w = 340
        self.quick_note_h = 160

        self.corkboard_notes_visible = True
        self.corkboard_show_images = True
        self.corkboard_coord_mode = "clamp" # "clamp", "proportional", "smart_free", "absolute"
        self._last_viewport_w = 0

        self.saved_title_x = None
        self.saved_title_y = None
        self.saved_qn_x = None
        self.saved_qn_y = None
        
        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def load_settings(self, settings: dict):
        """Populates home screen preferences from settings dictionary cleanly without direct DB querying."""
        if not settings:
            return
        self.corkboard_mode = settings.get("corkboard_mode", self.corkboard_mode)
        self.corkboard_coord_mode = settings.get("corkboard_coord_mode", "clamp")
        self.positions_locked = settings.get("home_positions_locked", "0") == "1"
        self.title_visible = settings.get("welcome_title_visible", "1") == "1"
        self.title_font_size = int(settings.get("welcome_title_font_size", "28"))
        self.title_font_family = settings.get("welcome_title_font_family", "Segoe UI")
        self.title_font_weight = int(settings.get("welcome_title_font_weight", "700"))
        self.title_w = int(settings.get("welcome_title_w", "0"))
        self.title_h = int(settings.get("welcome_title_h", "0"))
        self.title_color = settings.get("welcome_title_color", "#E3E3E3")
        self.title_outline_color = settings.get("welcome_title_outline_color", "#000000")
        self.title_outline_width = int(settings.get("welcome_title_outline_width", "0"))
        self.title_frame_enabled = settings.get("welcome_title_frame_enabled", "1") == "1"
        self.title_frame_bg = settings.get("welcome_title_frame_bg", "rgba(32, 33, 36, 0.75)")
        self.title_frame_border_color = settings.get("welcome_title_frame_border_color", "#8AB4F8")
        
        self.quick_note_visible = settings.get("quick_note_visible", "1") == "1"
        self.quick_note_bg = settings.get("quick_note_bg", "#1E1F20")
        self.quick_note_border_color = settings.get("quick_note_border_color", "#8AB4F8")
        self.quick_note_w = int(settings.get("quick_note_w", "340"))
        self.quick_note_h = int(settings.get("quick_note_h", "160"))

        self.corkboard_notes_visible = settings.get("corkboard_notes_visible", "1") == "1"
        self.corkboard_show_images = settings.get("corkboard_show_images", "1") == "1"

        self.saved_title_x = settings.get("welcome_title_x")
        self.saved_title_y = settings.get("welcome_title_y")
        self.saved_qn_x = settings.get("quick_note_x")
        self.saved_qn_y = settings.get("quick_note_y")

        self.apply_title_settings()
        if self.quick_note_widget:
            self.quick_note_widget.is_locked = self.positions_locked
            self.quick_note_widget.bg_color = self.quick_note_bg
            self.quick_note_widget.border_color = self.quick_note_border_color
            self.quick_note_widget.update_style()
            self.quick_note_widget.setVisible(self.quick_note_visible)

        self.render_corkboard()

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
            self.title_label.setVisible(self.title_visible)
            self.title_label.update_title_styling()

    def set_positions_locked(self, locked):
        self.positions_locked = locked
        self.setting_changed.emit("home_positions_locked", "1" if locked else "0")
        self.positions_locked_changed.emit(locked)
        
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.is_locked = locked
        if self.quick_note_widget:
            self.quick_note_widget.is_locked = locked
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.is_locked = locked

    def set_title_visible(self, visible):
        self.title_visible = visible
        self.setting_changed.emit("welcome_title_visible", "1" if visible else "0")
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setVisible(visible)

    def set_title_font_size(self, font_size):
        self.title_font_size = font_size
        self.setting_changed.emit("welcome_title_font_size", str(font_size))
        self.apply_title_settings()

    def set_title_font_family(self, font_family):
        self.title_font_family = font_family
        self.setting_changed.emit("welcome_title_font_family", font_family)
        self.apply_title_settings()

    def set_title_font_weight(self, font_weight):
        self.title_font_weight = font_weight
        self.setting_changed.emit("welcome_title_font_weight", str(font_weight))
        self.apply_title_settings()

    def set_title_size(self, w, h):
        self.title_w = w
        self.title_h = h
        self.setting_changed.emit("welcome_title_w", str(w))
        self.setting_changed.emit("welcome_title_h", str(h))
        self.apply_title_settings()

    def on_title_size_changed(self, w, h):
        self.title_w = w
        self.title_h = h
        self.setting_changed.emit("welcome_title_w", str(w))
        self.setting_changed.emit("welcome_title_h", str(h))

    def set_quick_note_size(self, w, h):
        self.quick_note_w = w
        self.quick_note_h = h
        self.setting_changed.emit("quick_note_w", str(w))
        self.setting_changed.emit("quick_note_h", str(h))
        if self.quick_note_widget:
            self.quick_note_widget.resize(w, h)

    def on_quick_note_size_changed(self, w, h):
        self.quick_note_w = w
        self.quick_note_h = h
        self.setting_changed.emit("quick_note_w", str(w))
        self.setting_changed.emit("quick_note_h", str(h))

    def set_title_color(self, color_hex):
        self.title_color = color_hex
        self.setting_changed.emit("welcome_title_color", color_hex)
        self.apply_title_settings()

    def set_title_outline_color(self, color_hex):
        self.title_outline_color = color_hex
        self.setting_changed.emit("welcome_title_outline_color", color_hex)
        self.apply_title_settings()

    def set_title_outline_width(self, width):
        self.title_outline_width = width
        self.setting_changed.emit("welcome_title_outline_width", str(width))
        self.apply_title_settings()

    def set_title_frame_enabled(self, enabled):
        self.title_frame_enabled = enabled
        self.setting_changed.emit("welcome_title_frame_enabled", "1" if enabled else "0")
        self.apply_title_settings()

    def set_title_frame_bg(self, bg_color):
        self.title_frame_bg = bg_color
        self.setting_changed.emit("welcome_title_frame_bg", bg_color)
        self.apply_title_settings()

    def set_title_frame_border_color(self, border_color):
        self.title_frame_border_color = border_color
        self.setting_changed.emit("welcome_title_frame_border_color", border_color)
        self.apply_title_settings()

    def set_quick_note_visible(self, visible):
        self.quick_note_visible = visible
        self.setting_changed.emit("quick_note_visible", "1" if visible else "0")
        if self.quick_note_widget:
            self.quick_note_widget.setVisible(visible)

    def set_quick_note_bg(self, bg_color):
        self.quick_note_bg = bg_color
        self.setting_changed.emit("quick_note_bg", bg_color)
        if self.quick_note_widget:
            self.quick_note_widget.bg_color = bg_color
            self.quick_note_widget.update_style()

    def set_quick_note_border_color(self, border_color):
        self.quick_note_border_color = border_color
        self.setting_changed.emit("quick_note_border_color", border_color)
        if self.quick_note_widget:
            self.quick_note_widget.border_color = border_color
            self.quick_note_widget.update_style()

    def set_corkboard_notes_visible(self, visible):
        self.corkboard_notes_visible = visible
        self.setting_changed.emit("corkboard_notes_visible", "1" if visible else "0")
        for card in self.corkboard_cards:
            card.setVisible(visible)

    def set_corkboard_show_images(self, show_images):
        self.corkboard_show_images = show_images
        self.setting_changed.emit("corkboard_show_images", "1" if show_images else "0")
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.show_images = show_images
                card.update_image_display()

    def open_home_settings_dialog(self):
        dialog = HomePageSettingsDialog(self)
        dialog.exec()

    def on_title_position_changed(self, x, y):
        if x >= 0 and y >= 0:
            self.saved_title_x = str(x)
            self.saved_title_y = str(y)
            self.setting_changed.emit("welcome_title_x", str(x))
            self.setting_changed.emit("welcome_title_y", str(y))
            if hasattr(self, 'title_label') and self.title_label and self.corkboard_mode == "free":
                self.title_label.move(x, y)

    def on_quick_note_position_changed(self, x, y):
        self.saved_qn_x = str(x)
        self.saved_qn_y = str(y)
        self.setting_changed.emit("quick_note_x", str(x))
        self.setting_changed.emit("quick_note_y", str(y))

    def set_corkboard_coord_mode(self, mode):
        self.corkboard_coord_mode = mode
        self.setting_changed.emit("corkboard_coord_mode", mode)
        self.adapt_positions_to_viewport()

    def switch_corkboard_mode(self, mode):
        self.corkboard_mode = mode
        self.setting_changed.emit("corkboard_mode", mode)
        self.render_corkboard()

    def adapt_positions_to_viewport(self):
        """Adapts element positions based on the selected corkboard_coord_mode."""
        if self.corkboard_mode != "free":
            return

        viewport_w = self.scroll_area.viewport().width()
        if viewport_w <= 100:
            viewport_w = max(900, self.width())

        old_w = getattr(self, '_last_viewport_w', 0)
        self._last_viewport_w = viewport_w

        mode = getattr(self, 'corkboard_coord_mode', 'clamp')
        if mode == "absolute":
            return # Keep untouched

        # --- 1. Title Label ---
        if hasattr(self, 'title_label') and self.title_label:
            tw = self.title_label.width()
            th = self.title_label.height()
            tx = self.title_label.x()
            ty = self.title_label.y()

            if mode == "smart_free":
                # Center horizontally
                tx = max(10, (viewport_w - tw) // 2)
            elif mode == "proportional" and old_w > 100 and old_w != viewport_w:
                ratio = tx / float(old_w)
                tx = int(ratio * viewport_w)
                tx = max(10, min(tx, max(10, viewport_w - tw - 10)))
            elif mode == "clamp":
                if tx + tw > viewport_w - 10:
                    tx = max(10, viewport_w - tw - 10)

            self.title_label.move(tx, ty)

        # --- 2. Quick Note Widget ---
        if hasattr(self, 'quick_note_widget') and self.quick_note_widget:
            qw = self.quick_note_widget.width()
            qh = self.quick_note_widget.height()
            qx = self.quick_note_widget.x()
            qy = self.quick_note_widget.y()

            if mode == "smart_free":
                qx = max(10, (viewport_w - qw) // 2)
            elif mode == "proportional" and old_w > 100 and old_w != viewport_w:
                ratio = qx / float(old_w)
                qx = int(ratio * viewport_w)
                qx = max(10, min(qx, max(10, viewport_w - qw - 10)))
            elif mode == "clamp":
                if qx + qw > viewport_w - 10:
                    qx = max(10, viewport_w - qw - 10)

            self.quick_note_widget.move(qx, qy)

        # --- 3. Corkboard Sticky Note Cards ---
        columns = max(1, (viewport_w - 10) // 220)
        for i, card in enumerate(self.corkboard_cards):
            if not isinstance(card, CorkboardNoteCard):
                continue
            cw = card.width()
            cx = card.x()
            cy = card.y()

            if mode == "smart_free":
                # Align within auto-spread columns if pushed outside
                if cx + cw > viewport_w - 10:
                    col = i % columns
                    row = i // columns
                    cx = col * 214
                    cy = max(cy, 300 + row * 194)
            elif mode == "proportional" and old_w > 100 and old_w != viewport_w:
                ratio = cx / float(old_w)
                cx = int(ratio * viewport_w)
                cx = max(10, min(cx, max(10, viewport_w - cw - 10)))
            elif mode == "clamp":
                if cx + cw > viewport_w - 10:
                    cx = max(10, viewport_w - cw - 10)

            card.move(cx, cy)
            card.note_data['corkboard_x'] = cx
            card.note_data['corkboard_y'] = cy

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
            
            tx_saved = self.saved_title_x
            ty_saved = self.saved_title_y
            
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
            qx_saved = self.saved_qn_x
            qy_saved = self.saved_qn_y
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
            self, t("welcome_wallpaper_dialog"), "", t("dialog_image_filter")
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
        if hasattr(self, 'quick_note_card') and self.quick_note_card:
            self.quick_note_card.retranslate_ui()
        if hasattr(self, 'home_settings_btn'):
            self.home_settings_btn.setText(t("home_settings_btn"))
        if hasattr(self, 'corkboard_notes') and self.corkboard_notes:
            self.render_corkboard(self.corkboard_notes)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapt_positions_to_viewport()
