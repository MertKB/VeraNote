"""
Welcome Screen for VeraNote.
Provides a free-form / grid corkboard with sticky notes, customizable greeting title, quick note widget, and wallpaper background.
Features an interactive On-Canvas Layout Mode (Düzen Modu) and live Background Editor with scale, offsets, brightness and blur.
"""
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QScrollArea, QGridLayout, QStyle, QStyleOption, QFileDialog,
    QMenu
)
from PySide6.QtCore import Signal, Qt, QSize, QPoint
from PySide6.QtGui import QPainter, QImage, QPixmap, QFontMetrics, QFont, QPen, QColor
from PIL import Image, ImageEnhance, ImageFilter

from utils.i18n import t
from utils.icon_manager import get_icon

from ui.corkboard import (
    CorkboardNoteCard, QuickNoteCardWidget, EditableLabel, HomePageSettingsDialog,
    BackgroundEditorDialog, ImageLoadWorker, ImageLoadWorkerSignals,
    get_pastel_palette, get_palette_colors
)

__all__ = [
    "WelcomeScreen",
    "CorkboardNoteCard",
    "QuickNoteCardWidget",
    "EditableLabel",
    "HomePageSettingsDialog",
    "BackgroundEditorDialog",
    "ImageLoadWorker",
    "ImageLoadWorkerSignals",
    "get_pastel_palette",
    "get_palette_colors",
]


class WelcomeScreen(QWidget):
    """
    Main home page view presenting a customizable Corkboard canvas.
    Fully isolated from database layer; communicates via Qt Signals.
    Supports in-place Layout Mode (Düzen Modu) and advanced Wallpaper Adjustments.
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
        
        # Wallpaper states & adjustments
        self.wallpaper_path = ""
        self.wallpaper_mode = "cover"  # "cover", "contain", "center", "stretch"
        self.wallpaper_vertical = 0    # -100 to 100
        self.wallpaper_horizontal = 0  # -100 to 100
        self.wallpaper_scale = 100     # 50 to 250 %
        self.wallpaper_brightness = 100# 10 to 200 %
        self.wallpaper_blur = 0        # 0 to 30 px
        self.wallpapers_list = []
        self._cached_bg_pixmap = None
        self._cached_bg_key = None
        self._source_wallpaper_img = None
        self._source_wallpaper_path = None

        # Corkboard & Layout states
        self.corkboard_cards = []
        self.corkboard_notes = []
        self.corkboard_mode = "free"
        self.quick_note_widget = None
        
        # Interactive Layout Mode states
        self.is_edit_mode = False
        self.grid_snap = True
        self.grid_size = 20
        self.show_grid_dots = True
        self.positions_locked = True  # Locked by default in normal view mode

        # Title states
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
        
        # Quick note states
        self.quick_note_visible = True
        self.quick_note_bg = "#1E1F20"
        self.quick_note_border_color = "#8AB4F8"
        self.quick_note_w = 340
        self.quick_note_h = 160

        # Sticky notes states
        self.corkboard_notes_visible = True
        self.corkboard_show_images = True
        self.corkboard_coord_mode = "clamp"
        self._last_viewport_w = 0

        self.saved_title_x = None
        self.saved_title_y = None
        self.saved_qn_x = None
        self.saved_qn_y = None
        
        self.highlight_color = "#8AB4F8"
        self.accent_color = "#1A73E8"

        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def load_settings(self, settings: dict, render: bool = True):
        """Populates home screen preferences from settings dictionary cleanly without direct DB querying."""
        if not settings:
            return
        self.corkboard_mode = settings.get("corkboard_mode", self.corkboard_mode)
        self.corkboard_coord_mode = settings.get("corkboard_coord_mode", "clamp")
        self.positions_locked = settings.get("home_positions_locked", "1") == "1"
        self.grid_snap = settings.get("home_grid_snap", "1") == "1"
        self.show_grid_dots = settings.get("home_show_grid_dots", "1") == "1"

        # Wallpaper adjustments
        self.wallpaper_mode = settings.get("welcome_wallpaper_mode", self.wallpaper_mode)
        self.wallpaper_vertical = int(settings.get("welcome_wallpaper_vertical", str(self.wallpaper_vertical)))
        self.wallpaper_horizontal = int(settings.get("welcome_wallpaper_horizontal", str(self.wallpaper_horizontal)))
        self.wallpaper_scale = int(settings.get("welcome_wallpaper_scale", str(self.wallpaper_scale)))
        self.wallpaper_brightness = int(settings.get("welcome_wallpaper_brightness", str(self.wallpaper_brightness)))
        self.wallpaper_blur = int(settings.get("welcome_wallpaper_blur", str(self.wallpaper_blur)))

        raw_wp_list = settings.get("welcome_wallpapers_list", "")
        if raw_wp_list:
            try:
                self.wallpapers_list = json.loads(raw_wp_list)
            except Exception:
                self.wallpapers_list = []

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

        if render:
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

        # Floating On-Canvas Layout Toolbar (Visible only in Edit Mode)
        self.init_edit_toolbar()

        # Footer Actions: "Ana Sayfa Ayarları"
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(10)
        footer_layout.addStretch()

        self.edit_mode_toggle_btn = None

        # Settings Button
        self.home_settings_btn = QPushButton(f"  {t('home_settings_btn')}", self)
        self.home_settings_btn.setIcon(get_icon("settings", self.highlight_color, 16))
        self.home_settings_btn.setIconSize(QSize(16, 16))
        self.home_settings_btn.setToolTip(t("home_settings_title"))
        self.home_settings_btn.setCursor(Qt.PointingHandCursor)
        self.home_settings_btn.clicked.connect(self.open_home_settings_dialog)
        footer_layout.addWidget(self.home_settings_btn)

        self.update_footer_styles()
        main_layout.addLayout(footer_layout)

    def init_edit_toolbar(self):
        """Creates the floating glassmorphic toolbar for on-canvas layout editing."""
        self.edit_toolbar = QWidget(self)
        self.edit_toolbar.setObjectName("EditModeToolbar")
        self.edit_toolbar.hide()

        tb_layout = QHBoxLayout(self.edit_toolbar)
        tb_layout.setContentsMargins(12, 6, 12, 6)
        tb_layout.setSpacing(8)

        # 1. Status Badge
        badge = QLabel(t('home_edit_mode_badge'), self.edit_toolbar)
        badge.setObjectName("Badge")
        tb_layout.addWidget(badge)

        # Separator line
        sep1 = QWidget(self.edit_toolbar)
        sep1.setFixedSize(1, 20)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.15);")
        tb_layout.addWidget(sep1)

        # 2. Background Editor Button
        self.tb_bg_btn = QPushButton(t('home_bg_editor_btn'), self.edit_toolbar)
        self.tb_bg_btn.setCursor(Qt.PointingHandCursor)
        self.tb_bg_btn.clicked.connect(self.open_background_editor)
        tb_layout.addWidget(self.tb_bg_btn)

        # 3. Snap to Grid Toggle
        self.tb_snap_btn = QPushButton(t('home_grid_snap'), self.edit_toolbar)
        self.tb_snap_btn.setCheckable(True)
        self.tb_snap_btn.setChecked(self.grid_snap)
        self.tb_snap_btn.setCursor(Qt.PointingHandCursor)
        self.tb_snap_btn.toggled.connect(self.toggle_grid_snap)
        tb_layout.addWidget(self.tb_snap_btn)

        # 4. Grid Guides Toggle
        self.tb_dots_btn = QPushButton(t('home_show_grid_dots'), self.edit_toolbar)
        self.tb_dots_btn.setCheckable(True)
        self.tb_dots_btn.setChecked(self.show_grid_dots)
        self.tb_dots_btn.setCursor(Qt.PointingHandCursor)
        self.tb_dots_btn.toggled.connect(self.toggle_grid_dots)
        tb_layout.addWidget(self.tb_dots_btn)

        # 5. Auto Align / Smart Tiling Button
        self.tb_align_btn = QPushButton(t('home_auto_align'), self.edit_toolbar)
        self.tb_align_btn.setCursor(Qt.PointingHandCursor)
        self.tb_align_btn.clicked.connect(self.auto_align_elements)
        tb_layout.addWidget(self.tb_align_btn)

        # 6. Components Toggle Menu
        self.tb_components_btn = QPushButton(t('home_components_menu'), self.edit_toolbar)
        self.tb_components_btn.setCursor(Qt.PointingHandCursor)
        self.tb_components_btn.clicked.connect(self.show_components_menu)
        tb_layout.addWidget(self.tb_components_btn)

        # 7. Advanced Settings
        self.tb_settings_btn = QPushButton(t('home_settings_btn'), self.edit_toolbar)
        self.tb_settings_btn.setCursor(Qt.PointingHandCursor)
        self.tb_settings_btn.clicked.connect(self.open_home_settings_dialog)
        tb_layout.addWidget(self.tb_settings_btn)

        # Separator line
        sep2 = QWidget(self.edit_toolbar)
        sep2.setFixedSize(1, 20)
        sep2.setStyleSheet("background-color: rgba(255, 255, 255, 0.15);")
        tb_layout.addWidget(sep2)

        # 8. Finish / Save Button
        self.tb_done_btn = QPushButton(t('home_edit_mode_exit'), self.edit_toolbar)
        self.tb_done_btn.setObjectName("DoneBtn")
        self.tb_done_btn.setCursor(Qt.PointingHandCursor)
        self.tb_done_btn.clicked.connect(self.toggle_edit_mode)
        tb_layout.addWidget(self.tb_done_btn)

        self.update_toolbar_styles()

    def update_toolbar_styles(self):
        if not hasattr(self, 'edit_toolbar'):
            return
        self.edit_toolbar.setStyleSheet(f"""
            QWidget#EditModeToolbar {{
                background-color: rgba(26, 27, 30, 0.94);
                border: 1px solid rgba(138, 180, 248, 0.4);
                border-radius: 18px;
            }}
            QPushButton {{
                background-color: #26282B;
                color: #E3E3E3;
                border: 1px solid #3C4043;
                border-radius: 12px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #33363B;
                color: #FFFFFF;
                border-color: {self.highlight_color};
            }}
            QPushButton:checked {{
                background-color: rgba(26, 115, 232, 0.25);
                color: {self.highlight_color};
                border-color: {self.accent_color};
                font-weight: bold;
            }}
            QPushButton#DoneBtn {{
                background-color: {self.accent_color};
                color: #FFFFFF;
                border: 1px solid {self.highlight_color};
                font-weight: bold;
                padding: 6px 14px;
            }}
            QPushButton#DoneBtn:hover {{
                background-color: #1557B0;
            }}
            QLabel#Badge {{
                color: {self.highlight_color};
                font-weight: bold;
                font-size: 11px;
                padding: 4px 8px;
                background-color: rgba(138, 180, 248, 0.15);
                border-radius: 8px;
            }}
        """)

    def update_footer_styles(self):
        active_edit = getattr(self, 'is_edit_mode', False)
        edit_bg = self.accent_color if active_edit else "rgba(45, 47, 49, 0.85)"
        edit_col = "#FFFFFF" if active_edit else self.highlight_color
        edit_border = self.highlight_color if active_edit else self.highlight_color

        if hasattr(self, 'edit_mode_toggle_btn') and self.edit_mode_toggle_btn:
            self.edit_mode_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {edit_bg};
                    color: {edit_col};
                    border: 1px solid {edit_border};
                    border-radius: 16px;
                    padding: 7px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.accent_color};
                    color: #FFFFFF;
                }}
            """)

        palette = getattr(self, 'theme_palette', {}) or {}
        bg_btn = palette.get('bg_input', 'rgba(45, 47, 49, 0.85)')
        border_btn = palette.get('border_color', self.highlight_color)
        hover_btn = palette.get('card_hover', self.accent_color)
        text_btn = palette.get('text_main', '#FFFFFF')

        if hasattr(self, 'home_settings_btn'):
            self.home_settings_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_btn};
                    color: {self.highlight_color};
                    border: 1px solid {border_btn};
                    border-radius: 16px;
                    padding: 7px 16px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {hover_btn};
                    color: {text_btn};
                    border-color: {self.highlight_color};
                }}
            """)

    def position_edit_toolbar(self):
        """Positions the floating toolbar centered at top."""
        if hasattr(self, 'edit_toolbar') and self.edit_toolbar.isVisible():
            tb_w = self.edit_toolbar.sizeHint().width()
            tb_h = self.edit_toolbar.sizeHint().height()
            x = (self.width() - tb_w) // 2
            y = 12
            self.edit_toolbar.setGeometry(max(10, x), y, tb_w, max(42, tb_h))
            self.edit_toolbar.raise_()

    def toggle_edit_mode(self):
        self.set_edit_mode(not self.is_edit_mode)

    def set_edit_mode(self, enabled: bool):
        self.is_edit_mode = enabled
        self.set_positions_locked(not enabled)

        # Update cards and widgets with grid settings
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.grid_snap = self.grid_snap
                card.grid_size = self.grid_size
                card.update()

        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.grid_snap = self.grid_snap
            self.title_label.grid_size = self.grid_size
            self.title_label.update()

        if self.quick_note_widget:
            self.quick_note_widget.grid_snap = self.grid_snap
            self.quick_note_widget.grid_size = self.grid_size
            self.quick_note_widget.update()

        if hasattr(self, 'edit_toolbar'):
            self.edit_toolbar.setVisible(enabled)
            if enabled:
                self.position_edit_toolbar()

        if hasattr(self, 'edit_mode_toggle_btn') and self.edit_mode_toggle_btn:
            if enabled:
                self.edit_mode_toggle_btn.setText(t('home_edit_mode_exit'))
            else:
                self.edit_mode_toggle_btn.setText(t('home_edit_mode_btn'))
            self.update_footer_styles()

        self.update()

    def toggle_grid_snap(self, enabled: bool):
        self.grid_snap = enabled
        self.setting_changed.emit("home_grid_snap", "1" if enabled else "0")
        for card in self.corkboard_cards:
            if isinstance(card, CorkboardNoteCard):
                card.grid_snap = enabled
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.grid_snap = enabled
        if self.quick_note_widget:
            self.quick_note_widget.grid_snap = enabled

    def toggle_grid_dots(self, enabled: bool):
        self.show_grid_dots = enabled
        self.setting_changed.emit("home_show_grid_dots", "1" if enabled else "0")
        self.update()

    def auto_align_elements(self):
        """Cleanly aligns and tiles all widgets onto the canvas snapping to 20px grid."""
        viewport_w = max(600, self.scroll_area.viewport().width())
        grid = self.grid_size

        # 1. Align Title at top center
        tw = self.title_w if self.title_w > 0 else max(400, self.title_label.width())
        th = self.title_h if self.title_h > 0 else max(44, self.title_label.height())
        tx = max(20, (viewport_w - tw) // 2)
        tx = round(tx / grid) * grid
        ty = 20
        self.title_label.setGeometry(tx, ty, tw, th)
        self.on_title_position_changed(tx, ty)

        # 2. Align Quick Note below Title
        qw = self.quick_note_w
        qh = self.quick_note_h
        qx = max(20, (viewport_w - qw) // 2)
        qx = round(qx / grid) * grid
        qy = ty + th + 20
        qy = round(qy / grid) * grid
        if self.quick_note_widget:
            self.quick_note_widget.setGeometry(qx, qy, qw, qh)
            self.on_quick_note_position_changed(qx, qy)

        # 3. Align Corkboard Sticky Notes in responsive columns
        start_y = qy + qh + 30 if self.quick_note_visible else ty + th + 30
        start_y = round(start_y / grid) * grid

        card_w = 220
        card_h = 200
        gutter_x = 20
        gutter_y = 20

        cols = max(1, (viewport_w - 40) // (card_w + gutter_x))
        total_grid_w = cols * card_w + (cols - 1) * gutter_x
        start_x = max(20, (viewport_w - total_grid_w) // 2)
        start_x = round(start_x / grid) * grid

        max_y = start_y
        for i, card in enumerate(self.corkboard_cards):
            if isinstance(card, CorkboardNoteCard):
                col = i % cols
                row = i // cols
                cx = start_x + col * (card_w + gutter_x)
                cy = start_y + row * (card_h + gutter_y)
                card.resize(card_w, card_h)
                card.move(cx, cy)
                card.note_data['corkboard_x'] = cx
                card.note_data['corkboard_y'] = cy
                card.note_data['corkboard_w'] = card_w
                card.note_data['corkboard_h'] = card_h
                self.corkboard_position_changed.emit(card.note_data.get('id', 0), cx, cy, card_w, card_h)
                max_y = max(max_y, cy + card_h + 20)

        self.corkboard_grid_widget.setMinimumHeight(max_y + 100)
        self.update()

    def show_components_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self.accent_color};
                color: #FFFFFF;
            }}
        """)

        # 1. Title Checkbox
        act_title = menu.addAction(t("home_show_title"))
        act_title.setCheckable(True)
        act_title.setChecked(self.title_visible)
        act_title.toggled.connect(self.set_title_visible)

        # 2. Quick Note Checkbox
        act_qn = menu.addAction(t("home_show_quick_note"))
        act_qn.setCheckable(True)
        act_qn.setChecked(self.quick_note_visible)
        act_qn.toggled.connect(self.set_quick_note_visible)

        # 3. Sticky Notes Checkbox
        act_notes = menu.addAction(t("home_show_notes"))
        act_notes.setCheckable(True)
        act_notes.setChecked(self.corkboard_notes_visible)
        act_notes.toggled.connect(self.set_corkboard_notes_visible)

        # 4. Images on Notes Checkbox
        act_img = menu.addAction(t("home_show_images"))
        act_img.setCheckable(True)
        act_img.setChecked(self.corkboard_show_images)
        act_img.toggled.connect(self.set_corkboard_show_images)

        btn = getattr(self, 'tb_components_btn', self)
        pos = btn.mapToGlobal(QPoint(0, btn.height() + 4))
        menu.exec(pos)

    def open_background_editor(self):
        self.open_home_settings_dialog()

    def open_home_settings_dialog(self):
        dialog = HomePageSettingsDialog(self)
        dialog.exec()

    def get_wallpapers_storage_dir(self):
        d = os.path.join(os.path.expanduser("~"), ".veranote_data", "wallpapers")
        os.makedirs(d, exist_ok=True)
        return d

    def get_wallpapers_list(self):
        if not hasattr(self, 'wallpapers_list') or not self.wallpapers_list:
            res = []
            if self.wallpaper_path and os.path.exists(self.wallpaper_path):
                res.append(self.wallpaper_path)
            
            storage_dir = self.get_wallpapers_storage_dir()
            if os.path.exists(storage_dir):
                for f in os.listdir(storage_dir):
                    p = os.path.join(storage_dir, f).replace("\\", "/")
                    if p not in res and os.path.isfile(p):
                        res.append(p)
            
            proj_images = os.path.abspath("images")
            if os.path.exists(proj_images):
                for f in os.listdir(proj_images):
                    if "wallpaper" in f.lower():
                        p = os.path.join(proj_images, f).replace("\\", "/")
                        if p not in res:
                            res.append(p)
                            
            self.wallpapers_list = res
        return self.wallpapers_list

    def set_wallpapers_list(self, wp_list):
        self.wallpapers_list = wp_list
        self.setting_changed.emit("welcome_wallpapers_list", json.dumps(wp_list))

    def set_wallpaper_vertical(self, val):
        self.wallpaper_vertical = val
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_vertical", str(val))
        self.update()

    def set_wallpaper_horizontal(self, val):
        self.wallpaper_horizontal = val
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_horizontal", str(val))
        self.update()

    def set_wallpaper_scale(self, val):
        self.wallpaper_scale = val
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_scale", str(val))
        self.update()

    def set_wallpaper_brightness(self, val):
        self.wallpaper_brightness = val
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_brightness", str(val))
        self.update()

    def set_wallpaper_blur(self, val):
        self.wallpaper_blur = val
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_blur", str(val))
        self.update()

    def set_wallpaper_mode(self, mode):
        self.wallpaper_mode = mode
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_mode", mode)
        self.update()

    def set_wallpaper_adjustments(self, v, h, scale, brightness, blur):
        self.wallpaper_vertical = v
        self.wallpaper_horizontal = h
        self.wallpaper_scale = scale
        self.wallpaper_brightness = brightness
        self.wallpaper_blur = blur
        self._cached_bg_key = None
        self.setting_changed.emit("welcome_wallpaper_vertical", str(v))
        self.setting_changed.emit("welcome_wallpaper_horizontal", str(h))
        self.setting_changed.emit("welcome_wallpaper_scale", str(scale))
        self.setting_changed.emit("welcome_wallpaper_brightness", str(brightness))
        self.setting_changed.emit("welcome_wallpaper_blur", str(blur))
        self.update()

    def render_wallpaper_pixmap(self, target_w, target_h):
        """Processes and transforms the wallpaper using PIL with high-speed BoxBlur and Brightness enhancement."""
        if not self.wallpaper_path or not os.path.exists(self.wallpaper_path):
            return None
        
        try:
            if self._source_wallpaper_img is None or self._source_wallpaper_path != self.wallpaper_path:
                with Image.open(self.wallpaper_path) as raw_img:
                    self._source_wallpaper_img = raw_img.convert('RGB')
                self._source_wallpaper_path = self.wallpaper_path
            orig_img = self._source_wallpaper_img
            orig_w, orig_h = orig_img.size
            if orig_w <= 0 or orig_h <= 0 or target_w <= 0 or target_h <= 0:
                return None
                
            scale = max(0.2, self.wallpaper_scale / 100.0)
            mode = getattr(self, 'wallpaper_mode', 'cover')
            
            if mode == 'stretch':
                dw = int(target_w * scale)
                dh = int(target_h * scale)
            elif mode == 'contain':
                r = min(target_w / orig_w, target_h / orig_h) * scale
                dw = max(1, int(orig_w * r))
                dh = max(1, int(orig_h * r))
            elif mode == 'center':
                dw = max(1, int(orig_w * scale))
                dh = max(1, int(orig_h * scale))
            else: # cover
                r = max(target_w / orig_w, target_h / orig_h) * scale
                dw = max(1, int(orig_w * r))
                dh = max(1, int(orig_h * r))
                
            resized = orig_img.resize((dw, dh), Image.Resampling.BILINEAR)
            
            base_x = (dw - target_w) // 2
            base_y = (dh - target_h) // 2
            
            shift_x = int((self.wallpaper_horizontal / 100.0) * (dw // 2))
            shift_y = int((self.wallpaper_vertical / 100.0) * (dh // 2))
            
            paste_x = -(base_x + shift_x)
            paste_y = -(base_y + shift_y)
            
            canvas = Image.new('RGB', (target_w, target_h), (20, 20, 22))
            canvas.paste(resized, (paste_x, paste_y))
            
            blur_val = getattr(self, 'wallpaper_blur', 0)
            if blur_val > 0:
                canvas = canvas.filter(ImageFilter.BoxBlur(blur_val))
                
            brightness_pct = getattr(self, 'wallpaper_brightness', 100)
            if brightness_pct != 100:
                canvas = ImageEnhance.Brightness(canvas).enhance(brightness_pct / 100.0)
                
            data = canvas.tobytes("raw", "RGB")
            qimg = QImage(data, target_w, target_h, target_w * 3, QImage.Format_RGB888)
            return QPixmap.fromImage(qimg.copy())
        except Exception as e:
            print("Error rendering transformed wallpaper:", e)
            return None

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
            return

        # 1. Title Label
        if hasattr(self, 'title_label') and self.title_label:
            tw = self.title_label.width()
            th = self.title_label.height()
            tx = self.title_label.x()
            ty = self.title_label.y()

            if mode == "smart_free":
                tx = max(10, (viewport_w - tw) // 2)
            elif mode == "proportional" and old_w > 100 and old_w != viewport_w:
                ratio = tx / float(old_w)
                tx = int(ratio * viewport_w)
                tx = max(10, min(tx, max(10, viewport_w - tw - 10)))
            elif mode == "clamp":
                if tx + tw > viewport_w - 10:
                    tx = max(10, viewport_w - tw - 10)

            self.title_label.move(tx, ty)

        # 2. Quick Note Widget
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

        # 3. Sticky Note Cards
        columns = max(1, (viewport_w - 10) // 220)
        for i, card in enumerate(self.corkboard_cards):
            if not isinstance(card, CorkboardNoteCard):
                continue
            cw = card.width()
            cx = card.x()
            cy = card.y()

            if mode == "smart_free":
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
        tx = max(10, (viewport_w - 450) // 2)
        ty = 20
        self.title_label.move(tx, ty)
        self.on_title_position_changed(tx, ty)

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
        if (
            self.quick_note_widget is not None
            and hasattr(self, 'corkboard_notes')
            and self.corkboard_notes == notes
            and len(self.corkboard_cards) == len(notes)
        ):
            return
        self.corkboard_notes = notes
        self._corkboard_dirty = False
        self.render_corkboard()

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, '_corkboard_dirty', False) or (self.corkboard_notes and len(self.corkboard_cards) != len(self.corkboard_notes)):
            self._corkboard_dirty = False
            self.render_corkboard()
        self.position_edit_toolbar()

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
        self.title_label.grid_snap = self.grid_snap
        self.title_label.grid_size = self.grid_size

        # Add Movable Quick Note Widget (reuse existing instance when available)
        if self.quick_note_widget is None:
            self.quick_note_widget = QuickNoteCardWidget(
                parent=self.corkboard_grid_widget,
                highlight_color=self.highlight_color,
                accent_color=self.accent_color
            )
            self.quick_note_widget.quick_note_saved.connect(self.quick_note_saved.emit)
            self.quick_note_widget.position_changed.connect(self.on_quick_note_position_changed)
            self.quick_note_widget.size_changed.connect(self.on_quick_note_size_changed)
        else:
            self.quick_note_widget.setParent(self.corkboard_grid_widget)
            self.quick_note_widget.highlight_color = self.highlight_color
            self.quick_note_widget.accent_color = self.accent_color
            if hasattr(self.quick_note_widget, 'retranslate_ui'):
                self.quick_note_widget.retranslate_ui()

        self.quick_note_widget.resize(self.quick_note_w, self.quick_note_h)
        self.quick_note_widget.is_locked = self.positions_locked
        self.quick_note_widget.grid_snap = self.grid_snap
        self.quick_note_widget.grid_size = self.grid_size
        self.quick_note_widget.bg_color = self.quick_note_bg
        self.quick_note_widget.border_color = self.quick_note_border_color if self.quick_note_border_color else self.highlight_color
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
                card = CorkboardNoteCard(
                    note, color_idx=i, mode="free",
                    show_images=self.corkboard_show_images,
                    parent=self.corkboard_grid_widget,
                    highlight_color=self.highlight_color,
                    accent_color=self.accent_color
                )
                card.is_locked = self.positions_locked
                card.grid_snap = self.grid_snap
                card.grid_size = self.grid_size
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
                card = CorkboardNoteCard(
                    note, color_idx=i, mode="grid",
                    show_images=self.corkboard_show_images,
                    parent=self.corkboard_grid_widget,
                    highlight_color=self.highlight_color,
                    accent_color=self.accent_color
                )
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
            self.set_wallpaper(file_path)
            self.wallpaper_selected.emit(file_path)

    def set_wallpaper(self, image_path):
        if image_path:
            self.wallpaper_path = image_path.replace("\\", "/")
            if self.wallpaper_path not in self.get_wallpapers_list():
                self.wallpapers_list.append(self.wallpaper_path)
                self.set_wallpapers_list(self.wallpapers_list)
        else:
            self.wallpaper_path = ""
        self._cached_bg_key = None
        self._source_wallpaper_img = None
        self.update()

    def set_welcome_title(self, title):
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.setText(title)

    def retranslate_ui(self):
        if hasattr(self, 'title_label') and self.title_label:
            self.title_label.retranslate_ui()
        if hasattr(self, 'quick_note_widget') and self.quick_note_widget:
            self.quick_note_widget.retranslate_ui()
        if hasattr(self, 'edit_mode_toggle_btn') and self.edit_mode_toggle_btn:
            if self.is_edit_mode:
                self.edit_mode_toggle_btn.setText(t('home_edit_mode_exit'))
            else:
                self.edit_mode_toggle_btn.setText(t('home_edit_mode_btn'))
        if hasattr(self, 'home_settings_btn'):
            self.home_settings_btn.setText(f"  {t('home_settings_btn')}")
            self.home_settings_btn.setIcon(get_icon("settings", self.highlight_color, 16))
        if hasattr(self, 'corkboard_notes') and self.corkboard_notes:
            self.render_corkboard()
        self.update_toolbar_styles()

    def apply_theme(self, palette: dict):
        if not palette:
            return
        self.theme_palette = palette
        self.highlight_color = palette.get("highlight_color", palette.get("border_focus", "#8AB4F8"))
        self.accent_color = palette.get("accent_color", "#1A73E8")

        self.update_footer_styles()
        self.update_toolbar_styles()

        if hasattr(self, 'quick_note_widget') and self.quick_note_widget:
            self.quick_note_widget.apply_theme(self.highlight_color, self.accent_color)
        for card in getattr(self, 'corkboard_cards', []):
            if isinstance(card, CorkboardNoteCard):
                card.highlight_color = self.highlight_color
                card.accent_color = self.accent_color
                card.copy_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(30, 31, 32, 0.85);
                        color: #E3E3E3;
                        border: 1px solid #444746;
                        border-radius: 10px;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 2px 6px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.accent_color};
                        color: #FFFFFF;
                        border-color: {self.highlight_color};
                    }}
                """)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, painter, self)

        # Transformed Wallpaper Rendering with Caching
        if self.wallpaper_path and os.path.exists(self.wallpaper_path):
            cache_key = (
                self.wallpaper_path, self.width(), self.height(),
                self.wallpaper_mode, self.wallpaper_vertical, self.wallpaper_horizontal,
                self.wallpaper_scale, self.wallpaper_brightness, self.wallpaper_blur
            )
            if getattr(self, '_cached_bg_key', None) != cache_key or getattr(self, '_cached_bg_pixmap', None) is None:
                self._cached_bg_pixmap = self.render_wallpaper_pixmap(self.width(), self.height())
                self._cached_bg_key = cache_key
                
            if self._cached_bg_pixmap and not self._cached_bg_pixmap.isNull():
                painter.drawPixmap(0, 0, self._cached_bg_pixmap)

        # Draw Grid Dots if in Edit Mode
        if self.is_edit_mode and getattr(self, 'show_grid_dots', True):
            painter.setPen(QPen(QColor(138, 180, 248, 55), 1.5))
            grid_s = getattr(self, 'grid_size', 20)
            w = self.width()
            h = self.height()
            for x in range(grid_s, w, grid_s):
                for y in range(grid_s, h, grid_s):
                    painter.drawPoint(x, y)

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adapt_positions_to_viewport()
        self.position_edit_toolbar()
