# ui/settings_dialog.py
import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
                             QCheckBox, QDoubleSpinBox, QComboBox, QWidget, QColorDialog,
                             QApplication, QGridLayout, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtGui import QColor
from utils.i18n import t, get_lang

DEFAULT_CUSTOM_COLORS = {
    "bg_main": "#131314",
    "bg_card": "#1E1F22",
    "border_color": "#2F3136",
    "bg_sidebar": "#18191B",
    "bg_input": "#282A2E",
    "accent_color": "#1A73E8",
    "text_main": "#E3E3E3",
    "text_muted": "#9AA0A6"
}

CUSTOM_PRESETS = [
    ("custom_preset_default", {
        "bg_main": "#131314",
        "bg_card": "#1E1F22",
        "border_color": "#2F3136",
        "bg_sidebar": "#18191B",
        "bg_input": "#282A2E",
        "accent_color": "#1A73E8",
        "text_main": "#E3E3E3",
        "text_muted": "#9AA0A6"
    }),
    ("custom_preset_amoled", {
        "bg_main": "#18191C",
        "bg_card": "#0F1012",
        "border_color": "#26282B",
        "bg_sidebar": "#141517",
        "bg_input": "#222428",
        "accent_color": "#3B82F6",
        "text_main": "#F1F3F5",
        "text_muted": "#909296"
    }),
    ("custom_preset_midnight", {
        "bg_main": "#120E16",
        "bg_card": "#1D1625",
        "border_color": "#33253E",
        "bg_sidebar": "#17121C",
        "bg_input": "#2A2033",
        "accent_color": "#A061D8",
        "text_main": "#EAE5ED",
        "text_muted": "#B5A9BC"
    }),
    ("custom_preset_emerald", {
        "bg_main": "#0C1410",
        "bg_card": "#13201A",
        "border_color": "#1D3329",
        "bg_sidebar": "#0E1813",
        "bg_input": "#182B23",
        "accent_color": "#10B981",
        "text_main": "#E6F4EA",
        "text_muted": "#829B8C"
    }),
    ("custom_preset_espresso", {
        "bg_main": "#191512",
        "bg_card": "#221C18",
        "border_color": "#362C26",
        "bg_sidebar": "#1D1814",
        "bg_input": "#2E2620",
        "accent_color": "#D97706",
        "text_main": "#F5EBE6",
        "text_muted": "#A8988F"
    })
]

COLOR_ATTRIBUTES = [
    ("bg_main", "custom_theme_bg", "custom_theme_bg_tooltip"),
    ("bg_card", "custom_theme_card", "custom_theme_card_tooltip"),
    ("border_color", "custom_theme_border", "custom_theme_border_tooltip"),
    ("bg_sidebar", "custom_theme_sidebar", "custom_theme_sidebar_tooltip"),
    ("bg_input", "custom_theme_input", "custom_theme_input_tooltip"),
    ("accent_color", "custom_theme_accent", "custom_theme_accent_tooltip"),
    ("text_main", "custom_theme_text_main", "custom_theme_text_main_tooltip"),
    ("text_muted", "custom_theme_text_muted", "custom_theme_text_muted_tooltip"),
]


class AutoSaveOnOutsideClickFilter(QObject):
    """Event filter that automatically accepts (saves) and closes the dialog when clicking outside."""
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


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._child_dialog_open = False
        self._outside_filter = AutoSaveOnOutsideClickFilter(self)
        self.custom_colors = dict(DEFAULT_CUSTOM_COLORS)
        self.color_buttons = {}
        self.preset_buttons = []
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(560)
        
        # Responsive height calculation for FHD / scaled displays
        screen = QApplication.primaryScreen()
        if screen:
            avail_h = screen.availableGeometry().height()
            target_h = min(720, max(480, int(avail_h * 0.82)))
            self.resize(580, target_h)
        else:
            self.resize(580, 640)
            
        self.init_ui()

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

    def wheelEvent(self, event):
        if hasattr(self, 'scroll_area') and self.scroll_area:
            self.scroll_area.wheelEvent(event)
        else:
            super().wheelEvent(event)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Scroll Area for all settings content
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("SettingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea#SettingsScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea#SettingsScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("SettingsContentWidget")
        self.content_widget.setStyleSheet("QWidget#SettingsContentWidget { background: transparent; }")
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ComfyUI Section
        self.comfyui_section_lbl = QLabel(t("settings_comfyui_section"))
        self.comfyui_section_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E3E3E3;")
        layout.addWidget(self.comfyui_section_lbl)

        self.comfyui_enable_check = QCheckBox(t("settings_comfyui_enable"))
        self.comfyui_enable_check.setStyleSheet("color: #E3E3E3; font-weight: 500;")
        self.comfyui_enable_check.setChecked(True)
        self.comfyui_enable_check.toggled.connect(self.on_comfyui_toggled)
        layout.addWidget(self.comfyui_enable_check)

        self.comfyui_desc_lbl = QLabel(t("settings_comfyui_desc"))
        self.comfyui_desc_lbl.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.comfyui_desc_lbl.setWordWrap(True)
        layout.addWidget(self.comfyui_desc_lbl)

        # ComfyUI Paths Container
        self.comfyui_paths_widget = QWidget()
        comfyui_paths_layout = QVBoxLayout(self.comfyui_paths_widget)
        comfyui_paths_layout.setContentsMargins(0, 4, 0, 0)
        comfyui_paths_layout.setSpacing(12)

        # Title
        self.title_lbl = QLabel(t("settings_paths"))
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #C2E7FF;")
        comfyui_paths_layout.addWidget(self.title_lbl)

        # LoRA Path Section
        lora_layout = QVBoxLayout()
        self.lora_lbl = QLabel(t("settings_lora_path"))
        self.lora_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        lora_layout.addWidget(self.lora_lbl)

        lora_input_layout = QHBoxLayout()
        self.lora_path_edit = QLineEdit()
        self.lora_path_edit.setPlaceholderText("...")
        self.lora_btn = QPushButton(t("settings_browse"))
        self.lora_btn.clicked.connect(self.select_lora_path)
        lora_input_layout.addWidget(self.lora_path_edit)
        lora_input_layout.addWidget(self.lora_btn)
        lora_layout.addLayout(lora_input_layout)
        comfyui_paths_layout.addLayout(lora_layout)

        # Checkpoint Path Section
        ckpt_layout = QVBoxLayout()
        self.ckpt_lbl = QLabel(t("settings_ckpt_path"))
        self.ckpt_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        ckpt_layout.addWidget(self.ckpt_lbl)

        ckpt_input_layout = QHBoxLayout()
        self.ckpt_path_edit = QLineEdit()
        self.ckpt_path_edit.setPlaceholderText("...")
        self.ckpt_btn = QPushButton(t("settings_browse"))
        self.ckpt_btn.clicked.connect(self.select_ckpt_path)
        ckpt_input_layout.addWidget(self.ckpt_path_edit)
        ckpt_input_layout.addWidget(self.ckpt_btn)
        ckpt_layout.addLayout(ckpt_input_layout)
        comfyui_paths_layout.addLayout(ckpt_layout)

        layout.addWidget(self.comfyui_paths_widget)

        # Auto-Save Settings Section
        autosave_layout = QVBoxLayout()
        self.autosave_lbl = QLabel(t("settings_autosave"))
        self.autosave_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E3E3E3; margin-top: 10px;")
        autosave_layout.addWidget(self.autosave_lbl)

        self.autosave_check = QCheckBox(t("settings_autosave_enable"))
        self.autosave_check.setStyleSheet("color: #E3E3E3;")
        autosave_layout.addWidget(self.autosave_check)

        interval_layout = QHBoxLayout()
        self.interval_lbl = QLabel(t("settings_interval"))
        self.interval_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 120.0)
        self.interval_spin.setSingleStep(0.5)
        self.interval_spin.setDecimals(1)
        self.interval_spin.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 6px;
                color: #E3E3E3;
                padding: 4px;
            }
        """)
        
        interval_layout.addWidget(self.interval_lbl)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        autosave_layout.addLayout(interval_layout)
        layout.addLayout(autosave_layout)

        # General Settings Section (Theme & Language)
        general_layout = QVBoxLayout()
        self.general_lbl = QLabel(t("settings"))
        self.general_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E3E3E3; margin-top: 10px;")
        general_layout.addWidget(self.general_lbl)
        
        # Theme Combobox
        theme_row = QHBoxLayout()
        self.theme_lbl = QLabel(t("settings_theme"))
        self.theme_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem(t("theme_dark_night"), "Koyu Gece")
        self.theme_combo.addItem(t("theme_deep_purple"), "Derin Mor")
        self.theme_combo.addItem(t("theme_ocean_blue"), "Okyanus Mavisi")
        self.theme_combo.addItem(t("settings_theme_custom"), "Özel Tema")
        self.theme_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 6px;
                color: #E3E3E3;
                padding: 4px 8px;
                min-width: 150px;
            }
        """)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        
        theme_row.addWidget(self.theme_lbl)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        general_layout.addLayout(theme_row)

        # Custom Theme Color Buttons Widget
        self.custom_colors_widget = QWidget()
        custom_colors_layout = QVBoxLayout(self.custom_colors_widget)
        custom_colors_layout.setContentsMargins(0, 6, 0, 8)
        custom_colors_layout.setSpacing(8)

        # Presets Bar
        presets_bar = QHBoxLayout()
        presets_bar.setSpacing(6)
        self.presets_lbl = QLabel(t("custom_theme_presets") + ":")
        self.presets_lbl.setStyleSheet("color: #C2E7FF; font-size: 11px; font-weight: bold;")
        presets_bar.addWidget(self.presets_lbl)

        self.preset_buttons = []
        for tr_key, p_colors in CUSTOM_PRESETS:
            p_btn = QPushButton(t(tr_key))
            p_btn.setCursor(Qt.PointingHandCursor)
            p_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2D2F31;
                    color: #E3E3E3;
                    border: 1px solid #444746;
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3C4043;
                    border-color: #8AB4F8;
                    color: #FFFFFF;
                }
            """)
            p_btn.clicked.connect(lambda checked=False, c=p_colors: self.apply_preset(c))
            presets_bar.addWidget(p_btn)
            self.preset_buttons.append((p_btn, tr_key))

        presets_bar.addStretch()
        custom_colors_layout.addLayout(presets_bar)

        # Color Pickers Grid (4 rows x 2 columns)
        colors_grid = QGridLayout()
        colors_grid.setHorizontalSpacing(10)
        colors_grid.setVerticalSpacing(8)

        for idx, (attr_name, label_key, tooltip_key) in enumerate(COLOR_ATTRIBUTES):
            btn = QPushButton()
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, a=attr_name, b=btn: self.pick_color(a, b))
            self.color_buttons[attr_name] = btn
            row = idx // 2
            col = idx % 2
            colors_grid.addWidget(btn, row, col)

        # Backward compatibility aliases
        self.bg_main_btn = self.color_buttons["bg_main"]
        self.bg_card_btn = self.color_buttons["bg_card"]
        self.accent_btn = self.color_buttons["accent_color"]

        custom_colors_layout.addLayout(colors_grid)
        general_layout.addWidget(self.custom_colors_widget)
        self.custom_colors_widget.setVisible(False)
        
        # Language Combobox
        lang_row = QHBoxLayout()
        self.lang_lbl = QLabel(t("settings_lang"))
        self.lang_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Türkçe", "tr")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 6px;
                color: #E3E3E3;
                padding: 4px 8px;
                min-width: 150px;
            }
        """)
        lang_row.addWidget(self.lang_lbl)
        lang_row.addWidget(self.lang_combo)
        lang_row.addStretch()
        general_layout.addLayout(lang_row)
        
        layout.addLayout(general_layout)

        # Storage Info Section
        storage_layout = QVBoxLayout()
        self.storage_lbl = QLabel(t("settings_storage_title"))
        self.storage_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E3E3E3; margin-top: 10px;")
        storage_layout.addWidget(self.storage_lbl)
        
        db_sz, assets_sz, tot_sz = self.get_storage_sizes()
        self.storage_info_lbl = QLabel(
            t("settings_storage_info").format(db=db_sz, assets=assets_sz, total=tot_sz)
        )
        self.storage_info_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        storage_layout.addWidget(self.storage_info_lbl)
        layout.addLayout(storage_layout)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area, 1)

        # Fixed bottom action bar (Always visible!)
        bottom_bar = QWidget(self)
        bottom_bar.setObjectName("SettingsBottomBar")
        bottom_bar.setStyleSheet("""
            QWidget#SettingsBottomBar {
                background-color: rgba(20, 21, 23, 0.95);
                border-top: 1px solid rgba(255, 255, 255, 0.08);
            }
        """)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 10, 20, 10)

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        bottom_layout.addWidget(self.button_box)

        root_layout.addWidget(bottom_bar, 0)

    def select_lora_path(self):
        self._child_dialog_open = True
        try:
            dir_path = QFileDialog.getExistingDirectory(self, t("settings_select_lora"))
            if dir_path:
                self.lora_path_edit.setText(dir_path)
        finally:
            self._child_dialog_open = False

    def select_ckpt_path(self):
        self._child_dialog_open = True
        try:
            dir_path = QFileDialog.getExistingDirectory(self, t("settings_select_ckpt"))
            if dir_path:
                self.ckpt_path_edit.setText(dir_path)
        finally:
            self._child_dialog_open = False

    def on_comfyui_toggled(self, checked):
        self.comfyui_paths_widget.setVisible(checked)

    def on_theme_changed(self):
        is_custom = self.theme_combo.currentData() == "Özel Tema"
        self.custom_colors_widget.setVisible(is_custom)

    def apply_preset(self, preset_colors):
        self.custom_colors.update(preset_colors)
        self.update_color_buttons()

    def pick_color(self, attr_name, button):
        self._child_dialog_open = True
        try:
            current_color = self.custom_colors.get(attr_name, DEFAULT_CUSTOM_COLORS.get(attr_name, "#131314"))
            color = QColorDialog.getColor(QColor(current_color), self, t("settings_theme_custom"))
            if color.isValid():
                hex_color = color.name().upper()
                self.custom_colors[attr_name] = hex_color
                self.update_color_buttons()
        finally:
            self._child_dialog_open = False

    def update_color_buttons(self):
        for attr_name, label_key, tooltip_key in COLOR_ATTRIBUTES:
            btn = self.color_buttons.get(attr_name)
            if not btn:
                continue
            hex_color = self.custom_colors.get(attr_name, DEFAULT_CUSTOM_COLORS.get(attr_name, "#131314"))
            label_text = t(label_key)
            tooltip_text = t(tooltip_key)
            btn.setText(f"{label_text}: {hex_color}")
            btn.setToolTip(f"{tooltip_text} ({hex_color})")
            
            is_light = self.is_light_color(hex_color)
            text_color = "#101010" if is_light else "#FFFFFF"
            border_color = "rgba(0, 0, 0, 0.45)" if is_light else "rgba(255, 255, 255, 0.35)"
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    color: {text_color};
                    border: 1px solid {border_color};
                    border-radius: 8px;
                    padding: 7px 12px;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: left;
                }}
                QPushButton:hover {{
                    border: 2px solid #8AB4F8;
                }}
            """)

    def update_color_button_style(self, button=None, hex_color=None):
        self.update_color_buttons()

    def is_light_color(self, hex_color):
        hex_color = hex_color.lstrip('#')
        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            # YIQ formula
            yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
            return yiq >= 128
        except Exception:
            return False

    def get_storage_sizes(self):
        try:
            import database
            return database.get_storage_stats()
        except Exception:
            return "0 KB", "0 KB", "0 KB"

    def get_settings(self):
        return {
            'comfyui_enabled': 1 if self.comfyui_enable_check.isChecked() else 0,
            'lora_path': self.lora_path_edit.text().strip(),
            'ckpt_path': self.ckpt_path_edit.text().strip(),
            'auto_save_enabled': 1 if self.autosave_check.isChecked() else 0,
            'auto_save_interval': self.interval_spin.value(),
            'theme': self.theme_combo.currentData(),
            'lang': self.lang_combo.currentData(),
            'custom_theme_colors': self.custom_colors
        }

    def set_settings(self, lora_path, ckpt_path, auto_save_enabled, auto_save_interval, theme, lang, custom_colors_data=None, comfyui_enabled=1):
        self.comfyui_enable_check.setChecked(bool(comfyui_enabled))
        self.comfyui_paths_widget.setVisible(bool(comfyui_enabled))
        self.lora_path_edit.setText(lora_path)
        self.ckpt_path_edit.setText(ckpt_path)
        self.autosave_check.setChecked(bool(auto_save_enabled))
        self.interval_spin.setValue(float(auto_save_interval))
        
        # Load custom theme colors
        if custom_colors_data:
            if isinstance(custom_colors_data, str):
                try:
                    custom_colors_data = json.loads(custom_colors_data)
                except Exception:
                    pass
            if isinstance(custom_colors_data, dict):
                self.custom_colors.update(custom_colors_data)
                
        self.update_color_buttons()

        # Select items in combos
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
            
        idx_lang = self.lang_combo.findData(lang)
        if idx_lang >= 0:
            self.lang_combo.setCurrentIndex(idx_lang)
            
        self.on_theme_changed()

    def retranslate_ui(self):
        self.setWindowTitle(t("settings_title"))
        self.comfyui_section_lbl.setText(t("settings_comfyui_section"))
        self.comfyui_enable_check.setText(t("settings_comfyui_enable"))
        self.comfyui_desc_lbl.setText(t("settings_comfyui_desc"))
        self.title_lbl.setText(t("settings_paths"))
        self.lora_lbl.setText(t("settings_lora_path"))
        self.lora_btn.setText(t("settings_browse"))
        self.ckpt_lbl.setText(t("settings_ckpt_path"))
        self.ckpt_btn.setText(t("settings_browse"))
        self.autosave_lbl.setText(t("settings_autosave"))
        self.autosave_check.setText(t("settings_autosave_enable"))
        self.interval_lbl.setText(t("settings_interval"))
        self.general_lbl.setText(t("settings"))
        self.theme_lbl.setText(t("settings_theme"))
        self.lang_lbl.setText(t("settings_lang"))
        
        if hasattr(self, 'presets_lbl'):
            self.presets_lbl.setText(t("custom_theme_presets") + ":")
        for p_btn, tr_key in getattr(self, 'preset_buttons', []):
            p_btn.setText(t(tr_key))
        self.update_color_buttons()
        
        # Re-populate theme combo box items dynamically
        self.theme_combo.blockSignals(True)
        curr_val = self.theme_combo.currentData()
        self.theme_combo.clear()
        self.theme_combo.addItem(t("theme_dark_night"), "Koyu Gece")
        self.theme_combo.addItem(t("theme_deep_purple"), "Derin Mor")
        self.theme_combo.addItem(t("theme_ocean_blue"), "Okyanus Mavisi")
        self.theme_combo.addItem(t("settings_theme_custom"), "Özel Tema")
        idx = self.theme_combo.findData(curr_val)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)
        
        # Storage Info
        self.storage_lbl.setText(t("settings_storage_title"))
        db_sz, assets_sz, tot_sz = self.get_storage_sizes()
        self.storage_info_lbl.setText(
            t("settings_storage_info").format(db=db_sz, assets=assets_sz, total=tot_sz)
        )
