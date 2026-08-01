# ui/settings_dialog.py
import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
                             QCheckBox, QDoubleSpinBox, QComboBox, QWidget, QColorDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
import database
from utils.i18n import t, get_lang

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.custom_colors = {
            "bg_main": "#131314",
            "bg_card": "#1E1F20",
            "accent_color": "#1A73E8"
        }
        self.setWindowTitle(t("settings_title"))
        self.setMinimumWidth(520)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Title
        self.title_lbl = QLabel(t("settings_paths"))
        self.title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #E3E3E3;")
        layout.addWidget(self.title_lbl)

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
        layout.addLayout(lora_layout)

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
        layout.addLayout(ckpt_layout)

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
        self.theme_combo.addItem("Koyu Gece" if get_lang() == "tr" else "Dark Night", "Koyu Gece")
        self.theme_combo.addItem("Derin Mor" if get_lang() == "tr" else "Deep Purple", "Derin Mor")
        self.theme_combo.addItem("Okyanus Mavisi" if get_lang() == "tr" else "Ocean Blue", "Okyanus Mavisi")
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
        custom_colors_layout = QHBoxLayout(self.custom_colors_widget)
        custom_colors_layout.setContentsMargins(110, 0, 0, 0)
        custom_colors_layout.setSpacing(10)
        
        self.bg_main_btn = QPushButton(t("custom_theme_bg"))
        self.bg_main_btn.clicked.connect(lambda: self.pick_color("bg_main", self.bg_main_btn))
        
        self.bg_card_btn = QPushButton(t("custom_theme_card"))
        self.bg_card_btn.clicked.connect(lambda: self.pick_color("bg_card", self.bg_card_btn))
        
        self.accent_btn = QPushButton(t("custom_theme_accent"))
        self.accent_btn.clicked.connect(lambda: self.pick_color("accent_color", self.accent_btn))
        
        custom_colors_layout.addWidget(self.bg_main_btn)
        custom_colors_layout.addWidget(self.bg_card_btn)
        custom_colors_layout.addWidget(self.accent_btn)
        custom_colors_layout.addStretch()
        
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

        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def select_lora_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, t("settings_select_lora"))
        if dir_path:
            self.lora_path_edit.setText(dir_path)

    def select_ckpt_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, t("settings_select_ckpt"))
        if dir_path:
            self.ckpt_path_edit.setText(dir_path)

    def on_theme_changed(self):
        is_custom = self.theme_combo.currentData() == "Özel Tema"
        self.custom_colors_widget.setVisible(is_custom)

    def pick_color(self, attr_name, button):
        current_color = self.custom_colors.get(attr_name, "#131314")
        color = QColorDialog.getColor(QColor(current_color), self, t("settings_theme_custom"))
        if color.isValid():
            hex_color = color.name().upper()
            self.custom_colors[attr_name] = hex_color
            self.update_color_button_style(button, hex_color)

    def update_color_button_style(self, button, hex_color):
        is_light = self.is_light_color(hex_color)
        text_color = "#000000" if is_light else "#FFFFFF"
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                color: {text_color};
                border: 1px solid #444746;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: #8AB4F8;
            }}
        """)

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
        # 1. Database size
        db_path = database.DB_NAME
        db_size = 0
        if os.path.exists(db_path):
            try:
                db_size = os.path.getsize(db_path)
            except Exception:
                pass
                
        # 2. Local images and saved workflows size
        assets_size = 0
        
        # A. Walk through the private data directory (excluding database file)
        veranote_data_dir = database.db_dir
        if os.path.exists(veranote_data_dir):
            try:
                for root, dirs, files in os.walk(veranote_data_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if os.path.exists(filepath) and filepath != db_path:
                            assets_size += os.path.getsize(filepath)
            except Exception:
                pass
                
        # B. Walk through workspace images/ folder if exists
        workspace_images = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "images")
        if os.path.exists(workspace_images):
            try:
                for root, dirs, files in os.walk(workspace_images):
                    for file in files:
                        filepath = os.path.join(root, file)
                        if os.path.exists(filepath):
                            assets_size += os.path.getsize(filepath)
            except Exception:
                pass
                
        def format_size(size):
            if size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
                
        return format_size(db_size), format_size(assets_size), format_size(db_size + assets_size)

    def get_settings(self):
        return {
            'lora_path': self.lora_path_edit.text().strip(),
            'ckpt_path': self.ckpt_path_edit.text().strip(),
            'auto_save_enabled': 1 if self.autosave_check.isChecked() else 0,
            'auto_save_interval': self.interval_spin.value(),
            'theme': self.theme_combo.currentData(),
            'lang': self.lang_combo.currentData(),
            'custom_theme_colors': self.custom_colors
        }

    def set_settings(self, lora_path, ckpt_path, auto_save_enabled, auto_save_interval, theme, lang, custom_colors_data=None):
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
                
        self.update_color_button_style(self.bg_main_btn, self.custom_colors["bg_main"])
        self.update_color_button_style(self.bg_card_btn, self.custom_colors["bg_card"])
        self.update_color_button_style(self.accent_btn, self.custom_colors["accent_color"])

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
        
        self.bg_main_btn.setText(t("custom_theme_bg"))
        self.bg_card_btn.setText(t("custom_theme_card"))
        self.accent_btn.setText(t("custom_theme_accent"))
        
        # Re-populate theme combo box items dynamically
        self.theme_combo.blockSignals(True)
        curr_val = self.theme_combo.currentData()
        self.theme_combo.clear()
        self.theme_combo.addItem("Koyu Gece" if get_lang() == "tr" else "Dark Night", "Koyu Gece")
        self.theme_combo.addItem("Derin Mor" if get_lang() == "tr" else "Deep Purple", "Derin Mor")
        self.theme_combo.addItem("Okyanus Mavisi" if get_lang() == "tr" else "Ocean Blue", "Okyanus Mavisi")
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
