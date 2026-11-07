"""
Settings dialog and custom slider for VeraNote Welcome Screen / Corkboard.
Integrates Layout Mode (Düzen Modu) and Background Editor (Arka Plan Düzenleyici) directly at the top of the dialog.
"""
import os
import shutil
import time
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QCheckBox,
    QSlider, QColorDialog, QComboBox, QApplication,
    QFileDialog, QMenu
)
from PySide6.QtCore import Qt, QObject, QEvent, QPoint
from PySide6.QtGui import QColor
from utils.i18n import t
from ui.corkboard.background_editor import CustomPillSlider, WallpaperThumbnailCard


class AutoSaveOnOutsideClickFilter(QObject):
    """Event filter that automatically accepts and closes the dialog when clicking outside."""
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if getattr(self.dialog, '_child_dialog_open', False):
                return False
            active_modal = QApplication.activeModalWidget()
            if active_modal and active_modal != self.dialog:
                return False
            active_popup = QApplication.activePopupWidget()
            pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
            if active_popup:
                if active_popup.frameGeometry().contains(pos) or self.dialog.frameGeometry().contains(pos):
                    return False
            if not self.dialog.frameGeometry().contains(pos):
                self.dialog.accept()
                return True
        return False


class NoWheelSlider(QSlider):
    """QSlider subclass that ignores mouse wheel events to prevent accidental setting changes while scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class HomePageSettingsDialog(QDialog):
    """
    Comprehensive, scrollable modal dialog for Main Page Settings.
    Features:
    - SECTION 1: Layout Mode (Düzen Modu, Grid Snapping, Guides, Auto Align)
    - SECTION 2: Background Editor (Dosyalarım resim/video, Görünüm, Seçenekler, Kaldır, Dikey, Yatay, Boyut, Parlaklık, Bulanıklık)
    - SECTION 3: Greeting Title Settings
    - SECTION 4: Quick Note Settings
    - SECTION 5: Sticky Notes Settings
    """
    def __init__(self, welcome_screen, parent=None):
        super().__init__(parent or welcome_screen)
        self._child_dialog_open = False
        self._outside_filter = AutoSaveOnOutsideClickFilter(self)
        self.welcome_screen = welcome_screen
        self.highlight_color = getattr(welcome_screen, 'highlight_color', '#8AB4F8')
        self.accent_color = getattr(welcome_screen, 'accent_color', '#1A73E8')
        self.setWindowTitle(t("home_settings_title"))
        self.resize(520, 700)
        self.setMinimumSize(480, 560)
        palette = getattr(welcome_screen, 'theme_palette', {}) or {}
        bg_card = palette.get('bg_card', '#1E1F20')
        bg_input = palette.get('bg_input', '#2D2F31')
        border_col = palette.get('border_color', '#444746')
        card_hover = palette.get('card_hover', '#3C4043')
        text_main = palette.get('text_main', '#E3E3E3')
        text_muted = palette.get('text_muted', '#9AA0A6')

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_card};
                color: {text_main};
                border-radius: 14px;
            }}
            QLabel {{
                color: {text_main};
                font-size: 13px;
            }}
            QLabel#SectionHeader {{
                color: {self.highlight_color};
                font-weight: bold;
                font-size: 14px;
                padding-top: 10px;
                padding-bottom: 2px;
            }}
            QPushButton {{
                background-color: {bg_input};
                color: {text_main};
                border: 1px solid {border_col};
                border-radius: 8px;
                padding: 7px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {card_hover};
                color: #FFFFFF;
                border-color: {self.highlight_color};
            }}
            QPushButton[primary="true"] {{
                background-color: {self.accent_color};
                color: #FFFFFF;
                border-color: {self.highlight_color};
                font-weight: bold;
            }}
            QCheckBox {{
                color: {text_main};
                font-size: 13px;
                font-weight: 500;
                spacing: 8px;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {bg_input};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.highlight_color};
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }}
        """)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(18, 16, 18, 16)
        dialog_layout.setSpacing(10)

        # Header Title
        hdr = QLabel(t("home_settings_title"), self)
        hdr.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.highlight_color}; padding-bottom: 2px;")
        dialog_layout.addWidget(hdr)

        # Scroll Area to prevent squeezing/clipping
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #444746;
                border-radius: 3px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(4, 4, 10, 4)
        layout.setSpacing(14)

        # ========================================================
        # --- SECTION 1: DÜZEN MODU & YERLEŞİM (AT THE VERY TOP) ---
        # ========================================================
        sec1_hdr = QLabel(t("home_layout_mode"), scroll_content)
        sec1_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec1_hdr)

        # Edit Mode Primary Toggle Button
        is_editing = getattr(self.welcome_screen, 'is_edit_mode', False)
        edit_btn_text = t('home_edit_mode_exit') if is_editing else t('home_edit_mode_btn')
        self.edit_mode_btn = QPushButton(edit_btn_text, scroll_content)
        self.edit_mode_btn.setProperty("primary", is_editing)
        self.edit_mode_btn.clicked.connect(self.toggle_edit_mode)
        layout.addWidget(self.edit_mode_btn)

        # Snapping & Grid Dots Row
        grid_opts_layout = QHBoxLayout()
        grid_opts_layout.setSpacing(14)
        self.grid_snap_cb = QCheckBox(t("home_grid_snap"), scroll_content)
        self.grid_snap_cb.setChecked(getattr(self.welcome_screen, 'grid_snap', True))
        self.grid_snap_cb.toggled.connect(self.welcome_screen.toggle_grid_snap)
        grid_opts_layout.addWidget(self.grid_snap_cb)

        self.grid_dots_cb = QCheckBox(t("home_show_grid_dots"), scroll_content)
        self.grid_dots_cb.setChecked(getattr(self.welcome_screen, 'show_grid_dots', True))
        self.grid_dots_cb.toggled.connect(self.welcome_screen.toggle_grid_dots)
        grid_opts_layout.addWidget(self.grid_dots_cb)
        layout.addLayout(grid_opts_layout)

        # Auto Align & Reset Positions
        align_layout = QHBoxLayout()
        align_layout.setSpacing(10)
        self.auto_align_btn = QPushButton(t("home_auto_align"), scroll_content)
        self.auto_align_btn.clicked.connect(self.welcome_screen.auto_align_elements)
        align_layout.addWidget(self.auto_align_btn)

        self.reset_btn = QPushButton(t("corkboard_reset_pos"), scroll_content)
        self.reset_btn.clicked.connect(self.reset_positions)
        align_layout.addWidget(self.reset_btn)
        layout.addLayout(align_layout)

        # Free Canvas vs Grid Buttons
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

        # Screen Resolution Adaptation Mode
        coord_layout = QVBoxLayout()
        coord_layout.setSpacing(4)
        self.coord_mode_lbl = QLabel(t("home_coord_mode_title"), scroll_content)
        self.coord_mode_lbl.setStyleSheet("font-weight: 500; font-size: 12px; color: #C4C7C5; margin-top: 2px;")
        coord_layout.addWidget(self.coord_mode_lbl)

        combo_qss = f"""
            QComboBox {{
                background-color: {bg_input};
                border: 1px solid {border_col};
                border-radius: 8px;
                color: {text_main};
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_card};
                color: {text_main};
                selection-background-color: {self.accent_color};
            }}
        """

        self.coord_mode_combo = QComboBox(scroll_content)
        self.coord_mode_combo.setStyleSheet(combo_qss)
        self.coord_mode_options = [
            ("clamp", t("coord_mode_clamp")),
            ("proportional", t("coord_mode_proportional")),
            ("smart_free", t("coord_mode_smart_free")),
            ("absolute", t("coord_mode_absolute")),
        ]
        for mode_key, mode_text in self.coord_mode_options:
            self.coord_mode_combo.addItem(mode_text, mode_key)

        curr_coord_mode = getattr(self.welcome_screen, 'corkboard_coord_mode', 'clamp')
        for idx, (m_key, _) in enumerate(self.coord_mode_options):
            if m_key == curr_coord_mode:
                self.coord_mode_combo.setCurrentIndex(idx)
                break
        self.coord_mode_combo.currentIndexChanged.connect(self.on_coord_mode_changed)
        coord_layout.addWidget(self.coord_mode_combo)
        layout.addLayout(coord_layout)

        # ========================================================
        # --- SECTION 2: ARKA PLAN DÜZENLEYİCİ (EMBEDDED AT TOP) ---
        # ========================================================
        sec2_hdr = QLabel(t("home_bg_editor_title"), scroll_content)
        sec2_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec2_hdr)

        # Header Row: "Dosyalarım (resim veya video)" and "+ Yeni ekle"
        bg_files_header = QHBoxLayout()
        bg_files_lbl = QLabel(t("home_bg_files_title"), scroll_content)
        bg_files_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        bg_files_header.addWidget(bg_files_lbl)
        bg_files_header.addStretch()

        self.add_wp_btn = QPushButton(t("home_bg_add_new"), scroll_content)
        self.add_wp_btn.setProperty("primary", True)
        self.add_wp_btn.setCursor(Qt.PointingHandCursor)
        self.add_wp_btn.clicked.connect(self.add_new_wallpaper_file)
        bg_files_header.addWidget(self.add_wp_btn)
        layout.addLayout(bg_files_header)

        # Thumbnails Gallery Scroll Area
        self.thumb_scroll_area = QScrollArea(scroll_content)
        self.thumb_scroll_area.setFixedHeight(94)
        self.thumb_scroll_area.setWidgetResizable(True)
        self.thumb_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.thumb_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.thumb_scroll_area.setStyleSheet("""
            QScrollArea {
                background: #18191B;
                border: 1px solid #333538;
                border-radius: 10px;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: #444746;
                border-radius: 2px;
            }
        """)

        self.thumb_container = QWidget()
        self.thumb_container.setStyleSheet("background: transparent;")
        self.thumb_layout = QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(6, 6, 6, 6)
        self.thumb_layout.setSpacing(10)
        self.thumb_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.thumb_scroll_area.setWidget(self.thumb_container)
        layout.addWidget(self.thumb_scroll_area)

        # Action Buttons Row: "Görünüm", "Seçenekler", "Kaldır"
        bg_actions_layout = QHBoxLayout()
        bg_actions_layout.setSpacing(10)

        self.view_btn = QPushButton(t("home_bg_view"), scroll_content)
        self.view_btn.setCursor(Qt.PointingHandCursor)
        self.view_btn.clicked.connect(self.show_view_menu)
        bg_actions_layout.addWidget(self.view_btn)

        self.options_btn = QPushButton(t("home_bg_options"), scroll_content)
        self.options_btn.setCursor(Qt.PointingHandCursor)
        self.options_btn.clicked.connect(self.show_options_menu)
        bg_actions_layout.addWidget(self.options_btn)

        self.remove_btn = QPushButton(t("home_bg_remove"), scroll_content)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(self.remove_active_wallpaper)
        bg_actions_layout.addWidget(self.remove_btn)

        layout.addLayout(bg_actions_layout)

        # Sliders Section: Dikey, Yatay, Boyut, Parlaklık, Bulanıklık
        sliders_box = QVBoxLayout()
        sliders_box.setSpacing(10)

        self.v_slider = self.create_pill_slider_row(
            t("home_bg_vertical"), -100, 100,
            getattr(self.welcome_screen, 'wallpaper_vertical', 0),
            self.on_v_changed, sliders_box, scroll_content
        )

        self.h_slider = self.create_pill_slider_row(
            t("home_bg_horizontal"), -100, 100,
            getattr(self.welcome_screen, 'wallpaper_horizontal', 0),
            self.on_h_changed, sliders_box, scroll_content
        )

        self.scale_slider = self.create_pill_slider_row(
            t("home_bg_scale"), 50, 250,
            getattr(self.welcome_screen, 'wallpaper_scale', 100),
            self.on_scale_changed, sliders_box, scroll_content
        )

        self.brightness_slider = self.create_pill_slider_row(
            t("home_bg_brightness"), 10, 200,
            getattr(self.welcome_screen, 'wallpaper_brightness', 100),
            self.on_brightness_changed, sliders_box, scroll_content
        )

        self.blur_slider = self.create_pill_slider_row(
            t("home_bg_blur"), 0, 30,
            getattr(self.welcome_screen, 'wallpaper_blur', 0),
            self.on_blur_changed, sliders_box, scroll_content
        )

        layout.addLayout(sliders_box)
        self.refresh_thumbnails()

        # ========================================================
        # --- SECTION 3: GREETING TITLE SETTINGS ---
        # ========================================================
        sec3_hdr = QLabel(t("home_title_section"), scroll_content)
        sec3_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec3_hdr)

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
        self.font_family_combo.setStyleSheet(combo_qss)
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

        # Title Font Weight Dropdown
        font_weight_layout = QHBoxLayout()
        self.font_weight_lbl = QLabel(t("home_title_font_weight"), scroll_content)
        font_weight_layout.addWidget(self.font_weight_lbl)

        self.font_weight_combo = QComboBox(scroll_content)
        self.font_weight_combo.setStyleSheet(combo_qss)
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
        selected_idx = 5
        for idx, (label, val) in enumerate(self.weight_map):
            if val == curr_weight:
                selected_idx = idx
                break
        self.font_weight_combo.setCurrentIndex(selected_idx)
        self.font_weight_combo.currentIndexChanged.connect(self.on_font_weight_changed)
        font_weight_layout.addWidget(self.font_weight_combo, 1)
        layout.addLayout(font_weight_layout)

        # Title Font Size Slider
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
        title_size_hdr = QLabel(t("title_size_title"), scroll_content)
        title_size_hdr.setStyleSheet("color: #E3E3E3; font-weight: bold; font-size: 13px; padding-top: 4px;")
        layout.addWidget(title_size_hdr)

        title_w_layout = QHBoxLayout()
        w_text = f"{self.welcome_screen.title_w}px" if self.welcome_screen.title_w > 0 else t("home_auto_fit_text")
        self.title_w_lbl = QLabel(t("title_width_lbl").format(w=w_text), scroll_content)
        title_w_layout.addWidget(self.title_w_lbl)
        self.title_w_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.title_w_slider.setRange(0, 1800)
        self.title_w_slider.setValue(self.welcome_screen.title_w)
        self.title_w_slider.valueChanged.connect(self.on_title_w_changed)
        title_w_layout.addWidget(self.title_w_slider, 1)
        layout.addLayout(title_w_layout)

        title_h_layout = QHBoxLayout()
        h_text = f"{self.welcome_screen.title_h}px" if self.welcome_screen.title_h > 0 else t("home_auto_fit_text")
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
        self.text_color_btn = QPushButton(t("home_title_color_btn"), scroll_content)
        self.text_color_btn.clicked.connect(self.pick_text_color)
        self.outline_color_btn = QPushButton(t("home_title_outline_btn"), scroll_content)
        self.outline_color_btn.clicked.connect(self.pick_outline_color)
        title_colors_layout.addWidget(self.text_color_btn)
        title_colors_layout.addWidget(self.outline_color_btn)
        layout.addLayout(title_colors_layout)

        # Letter Outline Width Slider
        outline_slider_layout = QHBoxLayout()
        self.outline_width_lbl = QLabel(t("home_title_outline_width_lbl").format(width=self.welcome_screen.title_outline_width), scroll_content)
        outline_slider_layout.addWidget(self.outline_width_lbl)
        
        self.outline_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.outline_slider.setRange(0, 8)
        self.outline_slider.setValue(self.welcome_screen.title_outline_width)
        self.outline_slider.valueChanged.connect(self.on_outline_slider_changed)
        outline_slider_layout.addWidget(self.outline_slider, 1)
        layout.addLayout(outline_slider_layout)

        # Title Frame Box Controls
        self.frame_cb = QCheckBox(t("home_title_frame_enable"), scroll_content)
        self.frame_cb.setChecked(self.welcome_screen.title_frame_enabled)
        self.frame_cb.toggled.connect(self.welcome_screen.set_title_frame_enabled)
        layout.addWidget(self.frame_cb)

        frame_colors_layout = QHBoxLayout()
        self.frame_bg_btn = QPushButton(t("home_title_frame_bg_btn"), scroll_content)
        self.frame_bg_btn.clicked.connect(self.pick_frame_bg)
        self.frame_border_btn = QPushButton(t("home_title_frame_border_btn"), scroll_content)
        self.frame_border_btn.clicked.connect(self.pick_frame_border_color)
        frame_colors_layout.addWidget(self.frame_bg_btn)
        frame_colors_layout.addWidget(self.frame_border_btn)
        layout.addLayout(frame_colors_layout)

        # ========================================================
        # --- SECTION 4: QUICK NOTE STYLE SETTINGS ---
        # ========================================================
        sec4_hdr = QLabel(t("qn_style_title"), scroll_content)
        sec4_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec4_hdr)

        self.qn_cb = QCheckBox(t("home_show_quick_note"), scroll_content)
        self.qn_cb.setChecked(self.welcome_screen.quick_note_visible)
        self.qn_cb.toggled.connect(self.welcome_screen.set_quick_note_visible)
        layout.addWidget(self.qn_cb)

        # Quick Note Size Controls
        qn_w_layout = QHBoxLayout()
        self.qn_w_lbl = QLabel(t("qn_width_lbl").format(w=self.welcome_screen.quick_note_w), scroll_content)
        qn_w_layout.addWidget(self.qn_w_lbl)
        self.qn_w_slider = NoWheelSlider(Qt.Horizontal, scroll_content)
        self.qn_w_slider.setRange(220, 800)
        self.qn_w_slider.setValue(self.welcome_screen.quick_note_w)
        self.qn_w_slider.valueChanged.connect(self.on_qn_w_changed)
        qn_w_layout.addWidget(self.qn_w_slider, 1)
        layout.addLayout(qn_w_layout)

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

        # ========================================================
        # --- SECTION 5: STICKY NOTES SETTINGS ---
        # ========================================================
        sec5_hdr = QLabel(t("home_notes_section"), scroll_content)
        sec5_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec5_hdr)

        self.notes_vis_cb = QCheckBox(t("home_show_notes"), scroll_content)
        self.notes_vis_cb.setChecked(self.welcome_screen.corkboard_notes_visible)
        self.notes_vis_cb.toggled.connect(self.welcome_screen.set_corkboard_notes_visible)
        layout.addWidget(self.notes_vis_cb)

        self.show_img_cb = QCheckBox(t("home_show_images"), scroll_content)
        self.show_img_cb.setChecked(self.welcome_screen.corkboard_show_images)
        self.show_img_cb.toggled.connect(self.welcome_screen.set_corkboard_show_images)
        layout.addWidget(self.show_img_cb)

        layout.addStretch()

        scroll.setWidget(scroll_content)
        dialog_layout.addWidget(scroll, 1)

        # Bottom Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_btn = QPushButton(t("home_close_btn"), self)
        close_btn.setMinimumWidth(110)
        close_btn.setProperty("primary", True)
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        dialog_layout.addLayout(close_layout)

    def create_pill_slider_row(self, label_text, min_val, max_val, curr_val, callback, parent_layout, parent_widget):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text, parent_widget)
        lbl.setFixedWidth(75)
        lbl.setStyleSheet("color: #E3E3E3; font-size: 13px; font-weight: 500;")
        row.addWidget(lbl)

        slider = CustomPillSlider(Qt.Horizontal, parent_widget, accent_color=self.accent_color)
        slider.setRange(min_val, max_val)
        slider.setValue(curr_val)
        slider.valueChanged.connect(callback)
        row.addWidget(slider, 1)

        parent_layout.addLayout(row)
        return slider

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowModality(Qt.NonModal)
        self.welcome_screen._settings_dialog_open = True
        if hasattr(self.welcome_screen, 'title_label') and self.welcome_screen.title_label:
            try:
                self.welcome_screen.title_label.size_changed.connect(self._on_canvas_title_resized)
            except Exception:
                pass
        if hasattr(self.welcome_screen, 'corkboard_grid_widget') and self.welcome_screen.corkboard_grid_widget:
            self.welcome_screen.corkboard_grid_widget.update()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._outside_filter)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.welcome_screen._settings_dialog_open = False
        if hasattr(self.welcome_screen, 'title_label') and self.welcome_screen.title_label:
            try:
                self.welcome_screen.title_label.size_changed.disconnect(self._on_canvas_title_resized)
            except Exception:
                pass
        if hasattr(self.welcome_screen, 'corkboard_grid_widget') and self.welcome_screen.corkboard_grid_widget:
            self.welcome_screen.corkboard_grid_widget.update()
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._outside_filter)

    def _on_canvas_title_resized(self, w: int, h: int):
        self.title_w_slider.blockSignals(True)
        self.title_h_slider.blockSignals(True)
        self.title_w_slider.setValue(w)
        self.title_h_slider.setValue(h)
        self.title_w_slider.blockSignals(False)
        self.title_h_slider.blockSignals(False)
        w_text = f"{w}px" if w > 0 else t("home_auto_fit_text")
        h_text = f"{h}px" if h > 0 else t("home_auto_fit_text")
        self.title_w_lbl.setText(t("title_width_lbl").format(w=w_text))
        self.title_h_lbl.setText(t("title_height_lbl").format(h=h_text))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                if not getattr(self, '_child_dialog_open', False):
                    active_modal = QApplication.activeModalWidget()
                    if not active_modal or active_modal == self:
                        self.accept()

    def toggle_edit_mode(self):
        new_edit = not getattr(self.welcome_screen, 'is_edit_mode', False)
        self.welcome_screen.set_edit_mode(new_edit)
        self.edit_mode_btn.setText(t('home_edit_mode_exit') if new_edit else t('home_edit_mode_btn'))
        self.edit_mode_btn.setProperty("primary", new_edit)
        self.edit_mode_btn.style().unpolish(self.edit_mode_btn)
        self.edit_mode_btn.style().polish(self.edit_mode_btn)

    def set_mode(self, mode):
        self.welcome_screen.switch_corkboard_mode(mode)
        self.free_mode_btn.setProperty("primary", mode == "free")
        self.grid_mode_btn.setProperty("primary", mode == "grid")
        for b in (self.free_mode_btn, self.grid_mode_btn):
            b.style().unpolish(b)
            b.style().polish(b)

    def refresh_thumbnails(self):
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        wallpapers = self.welcome_screen.get_wallpapers_list()
        active_wp = self.welcome_screen.wallpaper_path

        for wp_path in wallpapers:
            card = WallpaperThumbnailCard(
                wp_path,
                is_selected=(wp_path == active_wp),
                parent=self.thumb_container,
                accent_color=self.accent_color
            )
            card.clicked.connect(self.on_thumbnail_clicked)
            self.thumb_layout.addWidget(card)

    def on_thumbnail_clicked(self, file_path):
        self.welcome_screen.set_wallpaper(file_path)
        self.welcome_screen.setting_changed.emit("welcome_wallpaper", file_path)
        for i in range(self.thumb_layout.count()):
            card = self.thumb_layout.itemAt(i).widget()
            if isinstance(card, WallpaperThumbnailCard):
                card.set_selected(card.file_path == file_path)

    def add_new_wallpaper_file(self):
        self._child_dialog_open = True
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                t("welcome_wallpaper_dialog"),
                "",
                t("dialog_media_filter")
            )
            if not files:
                return

            dest_dir = self.welcome_screen.get_wallpapers_storage_dir()
            os.makedirs(dest_dir, exist_ok=True)

            last_added = None
            current_list = self.welcome_screen.get_wallpapers_list()

            for f in files:
                f_norm = f.replace("\\", "/")
                filename = os.path.basename(f)
                timestamp = int(time.time() * 1000)
                name, ext = os.path.splitext(filename)
                target_path = os.path.join(dest_dir, f"wp_{timestamp}_{name}{ext}").replace("\\", "/")
                
                try:
                    shutil.copy2(f, target_path)
                    saved_path = target_path
                except Exception:
                    saved_path = f_norm

                if saved_path not in current_list:
                    current_list.append(saved_path)
                last_added = saved_path

            self.welcome_screen.set_wallpapers_list(current_list)
            if last_added:
                self.welcome_screen.set_wallpaper(last_added)
                self.welcome_screen.setting_changed.emit("welcome_wallpaper", last_added)

            self.refresh_thumbnails()
        finally:
            self._child_dialog_open = False

    def remove_active_wallpaper(self):
        active_wp = self.welcome_screen.wallpaper_path
        if not active_wp:
            return

        current_list = self.welcome_screen.get_wallpapers_list()
        if active_wp in current_list:
            current_list.remove(active_wp)

        new_active = current_list[0] if current_list else ""
        self.welcome_screen.set_wallpapers_list(current_list)
        self.welcome_screen.set_wallpaper(new_active)
        self.welcome_screen.setting_changed.emit("welcome_wallpaper", new_active)
        self.refresh_thumbnails()

    def show_view_menu(self):
        self._child_dialog_open = True
        try:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2D2F31;
                    border: 1px solid #444746;
                    border-radius: 8px;
                    color: #E3E3E3;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 16px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #1A73E8;
                    color: #FFFFFF;
                }
            """)
            modes = [
                ("cover", t("home_bg_view_cover")),
                ("contain", t("home_bg_view_contain")),
                ("center", t("home_bg_view_center")),
                ("stretch", t("home_bg_view_stretch")),
            ]
            curr_mode = getattr(self.welcome_screen, 'wallpaper_mode', 'cover')
            for mode_key, mode_title in modes:
                act = menu.addAction(f"✓  {mode_title}" if mode_key == curr_mode else f"    {mode_title}")
                act.triggered.connect(lambda checked=False, m=mode_key: self.set_wallpaper_mode(m))

            pos = self.view_btn.mapToGlobal(QPoint(0, self.view_btn.height() + 4))
            menu.exec(pos)
        finally:
            self._child_dialog_open = False

    def set_wallpaper_mode(self, mode):
        self.welcome_screen.set_wallpaper_mode(mode)

    def show_options_menu(self):
        self._child_dialog_open = True
        try:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2D2F31;
                    border: 1px solid #444746;
                    border-radius: 8px;
                    color: #E3E3E3;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 16px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #1A73E8;
                    color: #FFFFFF;
                }
            """)
            reset_act = menu.addAction(t("home_bg_reset_defaults"))
            reset_act.triggered.connect(self.reset_all_wallpaper_sliders)

            pos = self.options_btn.mapToGlobal(QPoint(0, self.options_btn.height() + 4))
            menu.exec(pos)
        finally:
            self._child_dialog_open = False

    def reset_all_wallpaper_sliders(self):
        self.v_slider.setValue(0)
        self.h_slider.setValue(0)
        self.scale_slider.setValue(100)
        self.brightness_slider.setValue(100)
        self.blur_slider.setValue(0)
        self.welcome_screen.set_wallpaper_adjustments(0, 0, 100, 100, 0)

    def reset_all_sliders(self):
        self.reset_all_wallpaper_sliders()

    def on_v_changed(self, val):
        self.welcome_screen.set_wallpaper_vertical(val)

    def on_h_changed(self, val):
        self.welcome_screen.set_wallpaper_horizontal(val)

    def on_scale_changed(self, val):
        self.welcome_screen.set_wallpaper_scale(val)

    def on_brightness_changed(self, val):
        self.welcome_screen.set_wallpaper_brightness(val)

    def on_blur_changed(self, val):
        self.welcome_screen.set_wallpaper_blur(val)

    def on_font_weight_changed(self, index):
        val = self.font_weight_combo.itemData(index)
        if val:
            self.welcome_screen.set_title_font_weight(val)

    def on_font_slider_changed(self, val):
        self.font_size_lbl.setText(t("home_title_font_size").format(size=val))
        self.welcome_screen.set_title_font_size(val)

    def on_title_w_changed(self, val):
        w_text = f"{val}px" if val > 0 else t("home_auto_fit_text")
        self.title_w_lbl.setText(t("title_width_lbl").format(w=w_text))
        self.welcome_screen.set_title_size(val, self.welcome_screen.title_h)

    def on_title_h_changed(self, val):
        h_text = f"{val}px" if val > 0 else t("home_auto_fit_text")
        self.title_h_lbl.setText(t("title_height_lbl").format(h=h_text))
        self.welcome_screen.set_title_size(self.welcome_screen.title_w, val)

    def auto_fit_title(self):
        self.title_w_slider.blockSignals(True)
        self.title_h_slider.blockSignals(True)
        self.title_w_slider.setValue(0)
        self.title_h_slider.setValue(0)
        self.title_w_slider.blockSignals(False)
        self.title_h_slider.blockSignals(False)
        auto_text = t("home_auto_fit_text")
        self.title_w_lbl.setText(t("title_width_lbl").format(w=auto_text))
        self.title_h_lbl.setText(t("title_height_lbl").format(h=auto_text))
        self.welcome_screen.set_title_size(0, 0)

    def on_qn_w_changed(self, val):
        self.qn_w_lbl.setText(t("qn_width_lbl").format(w=val))
        self.welcome_screen.set_quick_note_size(val, self.welcome_screen.quick_note_h)

    def on_qn_h_changed(self, val):
        self.qn_h_lbl.setText(t("qn_height_lbl").format(h=val))
        self.welcome_screen.set_quick_note_size(self.welcome_screen.quick_note_w, val)

    def on_outline_slider_changed(self, val):
        self.outline_width_lbl.setText(t("home_title_outline_width_lbl").format(width=val))
        self.welcome_screen.set_title_outline_width(val)

    def pick_color_with_transparent(self, initial_color, title):
        self._child_dialog_open = True
        try:
            dialog = QColorDialog(QColor(initial_color if initial_color != 'transparent' else '#FFFFFF'), self)
            dialog.setWindowTitle(title)
            dialog.setOption(QColorDialog.ShowAlphaChannel, True)
            
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
        finally:
            self._child_dialog_open = False

    def pick_text_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_color, t("home_pick_text_color"))
        if c:
            self.welcome_screen.set_title_color(c)

    def pick_outline_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_outline_color, t("home_pick_outline_color"))
        if c:
            self.welcome_screen.set_title_outline_color(c)

    def pick_frame_bg(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_frame_bg, t("home_pick_frame_bg"))
        if c:
            self.welcome_screen.set_title_frame_bg(c)

    def pick_frame_border_color(self):
        c = self.pick_color_with_transparent(self.welcome_screen.title_frame_border_color, t("home_pick_frame_border"))
        if c:
            self.welcome_screen.set_title_frame_border_color(c)

    def pick_qn_bg(self):
        c = self.pick_color_with_transparent(self.welcome_screen.quick_note_bg, t("home_pick_qn_bg"))
        if c:
            self.welcome_screen.set_quick_note_bg(c)

    def pick_qn_border(self):
        c = self.pick_color_with_transparent(self.welcome_screen.quick_note_border_color, t("home_pick_qn_border"))
        if c:
            self.welcome_screen.set_quick_note_border_color(c)

    def on_coord_mode_changed(self, index):
        mode_key = self.coord_mode_combo.itemData(index)
        if mode_key:
            self.welcome_screen.set_corkboard_coord_mode(mode_key)

    def reset_positions(self):
        self.welcome_screen.reset_corkboard_positions()
