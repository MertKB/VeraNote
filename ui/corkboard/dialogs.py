"""
Settings dialog and custom slider for VeraNote Welcome Screen / Corkboard.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QWidget, QCheckBox, 
                             QSlider, QColorDialog, QComboBox, QApplication)
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QColor
from utils.i18n import t


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
    """Spacious, scrollable modal dialog for Main Page Settings with NoWheelSliders to prevent accidental value changes."""
    def __init__(self, welcome_screen, parent=None):
        super().__init__(parent or welcome_screen)
        self._child_dialog_open = False
        self._outside_filter = AutoSaveOnOutsideClickFilter(self)
        self.welcome_screen = welcome_screen
        self.highlight_color = getattr(welcome_screen, 'highlight_color', '#8AB4F8')
        self.accent_color = getattr(welcome_screen, 'accent_color', '#1A73E8')
        self.setWindowTitle(t("home_settings_title"))
        self.resize(480, 560)
        self.setMinimumSize(440, 500)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #1E1F20;
                color: #E3E3E3;
                border-radius: 14px;
            }}
            QLabel {{
                color: #E3E3E3;
                font-size: 13px;
            }}
            QLabel#SectionHeader {{
                color: {self.highlight_color};
                font-weight: bold;
                font-size: 14px;
                padding-top: 6px;
            }}
            QPushButton {{
                background-color: #2D2F31;
                color: #E3E3E3;
                border: 1px solid #444746;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #3C4043;
                color: #FFFFFF;
            }}
            QPushButton[primary="true"] {{
                background-color: {self.accent_color};
                color: #FFFFFF;
                border-color: {self.highlight_color};
            }}
            QCheckBox {{
                color: #E3E3E3;
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: #2D2F31;
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
        dialog_layout.setContentsMargins(16, 16, 16, 16)
        dialog_layout.setSpacing(12)

        # Header Title
        hdr = QLabel(t("home_settings_title"), self)
        hdr.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.highlight_color}; padding-bottom: 4px;")
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
        sec1_hdr = QLabel(t("home_layout_mode"), scroll_content)
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

        # Screen Resolution Adaptation Mode
        coord_layout = QVBoxLayout()
        coord_layout.setSpacing(4)
        self.coord_mode_lbl = QLabel(t("home_coord_mode_title"), scroll_content)
        self.coord_mode_lbl.setStyleSheet("font-weight: 500; font-size: 12px; color: #C4C7C5; margin-top: 4px;")
        coord_layout.addWidget(self.coord_mode_lbl)

        combo_qss = f"""
            QComboBox {{
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #2D2F31;
                color: #E3E3E3;
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

        # Align Positions
        self.reset_btn = QPushButton(t("corkboard_reset_pos"), scroll_content)
        self.reset_btn.clicked.connect(self.reset_positions)
        layout.addWidget(self.reset_btn)

        # --- SECTION 2: GREETING TITLE SETTINGS ---
        sec2_hdr = QLabel(t("home_title_section"), scroll_content)
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

        # Title Font Weight Dropdown (Thin 100 to Black 900)
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

        # Letter Outline Width Slider (NoWheelSlider)
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

        # --- SECTION 3: QUICK NOTE STYLE SETTINGS ---
        sec3_hdr = QLabel(t("qn_style_title"), scroll_content)
        sec3_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec3_hdr)

        self.qn_cb = QCheckBox(t("home_show_quick_note"), scroll_content)
        self.qn_cb.setChecked(self.welcome_screen.quick_note_visible)
        self.qn_cb.toggled.connect(self.welcome_screen.set_quick_note_visible)
        layout.addWidget(self.qn_cb)

        # Quick Note Size Controls
        qn_size_hdr = QLabel(t("qn_size_title"), scroll_content)
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
        sec4_hdr = QLabel(t("home_notes_section"), scroll_content)
        sec4_hdr.setObjectName("SectionHeader")
        layout.addWidget(sec4_hdr)

        self.notes_vis_cb = QCheckBox(t("home_show_notes"), scroll_content)
        self.notes_vis_cb.setChecked(self.welcome_screen.corkboard_notes_visible)
        self.notes_vis_cb.toggled.connect(self.welcome_screen.set_corkboard_notes_visible)
        layout.addWidget(self.notes_vis_cb)

        self.show_img_cb = QCheckBox(t("home_show_images"), scroll_content)
        self.show_img_cb.setChecked(self.welcome_screen.corkboard_show_images)
        self.show_img_cb.toggled.connect(self.welcome_screen.set_corkboard_show_images)
        layout.addWidget(self.show_img_cb)

        # --- SECTION 5: WALLPAPER ---
        sec5_hdr = QLabel(t("home_wallpaper_section"), scroll_content)
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

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowModality(Qt.NonModal)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._outside_filter)

    def hideEvent(self, event):
        super().hideEvent(event)
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._outside_filter)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                if not getattr(self, '_child_dialog_open', False):
                    active_modal = QApplication.activeModalWidget()
                    if not active_modal or active_modal == self:
                        self.accept()

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
        w_text = f"{val}px" if val > 0 else t("home_auto_fit_text")
        self.title_w_lbl.setText(t("title_width_lbl").format(w=w_text))
        self.welcome_screen.set_title_size(val, self.welcome_screen.title_h)

    def on_title_h_changed(self, val):
        h_text = f"{val}px" if val > 0 else t("home_auto_fit_text")
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

    def select_wallpaper(self):
        self._child_dialog_open = True
        try:
            self.welcome_screen.select_wallpaper()
        finally:
            self._child_dialog_open = False

    def remove_wallpaper(self):
        self.welcome_screen.set_wallpaper("")
        self.welcome_screen.wallpaper_selected.emit("")
