# ui/settings_dialog.py
import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox,
                             QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox, QWidget, QColorDialog,
                             QApplication, QGridLayout, QScrollArea, QFrame, QMessageBox,
                             QKeySequenceEdit)
from PySide6.QtCore import Qt, QObject, QEvent, Signal
from PySide6.QtGui import QColor, QKeySequence
from utils.i18n import t, get_lang
from database import DEFAULT_SHORTCUTS

DEFAULT_CUSTOM_COLORS = {
    "bg_main": "#131314",
    "bg_card": "#1E1F22",
    "border_color": "#2F3136",
    "bg_sidebar": "#18191B",
    "bg_input": "#282A2E",
    "accent_color": "#1A73E8",
    "highlight_color": "#8AB4F8",
    "border_focus": "#8AB4F8",
    "card_selected": "#192231",
    "text_main": "#E3E3E3",
    "text_muted": "#9AA0A6",
    "cal_weekend_color": "#FB7185"
}

CUSTOM_PRESETS = [
    ("custom_preset_default", {
        "bg_main": "#131314",
        "bg_card": "#1E1F22",
        "border_color": "#2F3136",
        "bg_sidebar": "#18191B",
        "bg_input": "#282A2E",
        "accent_color": "#1A73E8",
        "highlight_color": "#8AB4F8",
        "border_focus": "#8AB4F8",
        "card_selected": "#192231",
        "text_main": "#E3E3E3",
        "text_muted": "#9AA0A6",
        "cal_weekend_color": "#FB7185"
    }),
    ("custom_preset_amoled", {
        "bg_main": "#18191C",
        "bg_card": "#0F1012",
        "border_color": "#26282B",
        "bg_sidebar": "#141517",
        "bg_input": "#222428",
        "accent_color": "#3B82F6",
        "highlight_color": "#60A5FA",
        "border_focus": "#60A5FA",
        "card_selected": "#141E2E",
        "text_main": "#F1F3F5",
        "text_muted": "#909296",
        "cal_weekend_color": "#F87171"
    }),
    ("custom_preset_midnight", {
        "bg_main": "#120E16",
        "bg_card": "#1D1625",
        "border_color": "#33253E",
        "bg_sidebar": "#17121C",
        "bg_input": "#2A2033",
        "accent_color": "#A061D8",
        "highlight_color": "#D7AEF5",
        "border_focus": "#D7AEF5",
        "card_selected": "#281838",
        "text_main": "#EAE5ED",
        "text_muted": "#B5A9BC",
        "cal_weekend_color": "#E879F9"
    }),
    ("custom_preset_emerald", {
        "bg_main": "#0C1410",
        "bg_card": "#13201A",
        "border_color": "#1D3329",
        "bg_sidebar": "#0E1813",
        "bg_input": "#182B23",
        "accent_color": "#10B981",
        "highlight_color": "#34D399",
        "border_focus": "#34D399",
        "card_selected": "#112B20",
        "text_main": "#E6F4EA",
        "text_muted": "#829B8C",
        "cal_weekend_color": "#6EE7B7"
    }),
    ("custom_preset_espresso", {
        "bg_main": "#191512",
        "bg_card": "#221C18",
        "border_color": "#362C26",
        "bg_sidebar": "#1D1814",
        "bg_input": "#2E2620",
        "accent_color": "#D97706",
        "highlight_color": "#FBBF24",
        "border_focus": "#FBBF24",
        "card_selected": "#2E2018",
        "text_main": "#F5EBE6",
        "text_muted": "#A8988F",
        "cal_weekend_color": "#F59E0B"
    })
]

COLOR_ATTRIBUTES = [
    ("bg_main", "custom_theme_bg", "custom_theme_bg_tooltip"),
    ("bg_card", "custom_theme_card", "custom_theme_card_tooltip"),
    ("border_color", "custom_theme_border", "custom_theme_border_tooltip"),
    ("bg_sidebar", "custom_theme_sidebar", "custom_theme_sidebar_tooltip"),
    ("bg_input", "custom_theme_input", "custom_theme_input_tooltip"),
    ("accent_color", "custom_theme_accent", "custom_theme_accent_tooltip"),
    ("highlight_color", "custom_theme_highlight", "custom_theme_highlight_tooltip"),
    ("border_focus", "custom_theme_border_focus", "custom_theme_border_focus_tooltip"),
    ("card_selected", "custom_theme_card_selected", "custom_theme_card_selected_tooltip"),
    ("text_main", "custom_theme_text_main", "custom_theme_text_main_tooltip"),
    ("text_muted", "custom_theme_text_muted", "custom_theme_text_muted_tooltip"),
    ("cal_weekend_color", "custom_theme_cal_weekend", "custom_theme_cal_weekend_tooltip"),
]


class AutoSaveOnOutsideClickFilter(QObject):
    """Event filter that automatically accepts (saves) and closes the dialog when clicking outside."""
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if getattr(self.dialog, '_is_closing', False) or getattr(self.dialog, '_child_dialog_open', False):
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
    backup_exported = Signal(str)
    backup_restored = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_closing = False
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

    def accept(self):
        self._is_closing = True
        super().accept()

    def reject(self):
        self._is_closing = True
        super().reject()

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
            if getattr(self, '_is_closing', False):
                return
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
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #E3E3E3;")
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
        self.presets_lbl.setStyleSheet("color: #E3E3E3; font-size: 11px; font-weight: bold;")
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
        self.highlight_btn = self.color_buttons.get("highlight_color")

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

        # Sidebar Notebooks Limit
        nb_limit_row = QHBoxLayout()
        self.sidebar_nb_lbl = QLabel(t("settings_sidebar_notebooks_limit"))
        self.sidebar_nb_lbl.setStyleSheet("color: #9AA0A6; font-size: 12px;")
        self.sidebar_nb_combo = QComboBox()
        self.sidebar_nb_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 6px;
                color: #E3E3E3;
                padding: 4px 10px;
                min-width: 90px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left-width: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #2D2F31;
                color: #E3E3E3;
                selection-background-color: #3C4043;
                selection-color: #FFFFFF;
                border: 1px solid #444746;
            }
        """)
        self.populate_sidebar_nb_combo(5)
        # Compatibility aliases
        self.sidebar_nb_spin = self.sidebar_nb_combo
        self.sidebar_nb_combo.value = lambda: int(self.sidebar_nb_combo.currentData() if self.sidebar_nb_combo.currentData() is not None else 5)
        self.sidebar_nb_combo.setValue = lambda v: self.populate_sidebar_nb_combo(v)
        
        nb_limit_row.addWidget(self.sidebar_nb_lbl)
        nb_limit_row.addWidget(self.sidebar_nb_combo)
        nb_limit_row.addStretch()
        general_layout.addLayout(nb_limit_row)
        
        layout.addLayout(general_layout)

        # Keyboard Shortcuts Section
        shortcuts_layout = QVBoxLayout()
        self.shortcuts_lbl = QLabel(t("settings_shortcuts_section"))
        self.shortcuts_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E3E3E3; margin-top: 10px;")
        shortcuts_layout.addWidget(self.shortcuts_lbl)

        self.shortcuts_desc_lbl = QLabel(t("settings_shortcuts_desc"))
        self.shortcuts_desc_lbl.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.shortcuts_desc_lbl.setWordWrap(True)
        shortcuts_layout.addWidget(self.shortcuts_desc_lbl)

        # Shortcuts Grid
        self.shortcuts_widget = QWidget()
        shortcuts_grid = QGridLayout(self.shortcuts_widget)
        shortcuts_grid.setContentsMargins(0, 4, 0, 4)
        shortcuts_grid.setHorizontalSpacing(16)
        shortcuts_grid.setVerticalSpacing(8)

        self.shortcut_items = [
            ("nav_back", "shortcut_nav_back"),
            ("nav_forward", "shortcut_nav_forward"),
            ("new_note", "shortcut_new_note"),
            ("search", "shortcut_search"),
            ("incognito", "shortcut_incognito"),
            ("select_all", "shortcut_select_all"),
            ("settings", "shortcut_settings"),
        ]

        self.shortcut_edits = {}
        self.shortcut_labels = {}

        for row_idx, (s_key, tr_key) in enumerate(self.shortcut_items):
            lbl = QLabel(t(tr_key))
            lbl.setStyleSheet("color: #E3E3E3; font-size: 12px;")
            edit = QKeySequenceEdit()
            edit.setStyleSheet("""
                QKeySequenceEdit {
                    background-color: #2D2F31;
                    border: 1px solid #444746;
                    border-radius: 6px;
                    color: #E3E3E3;
                    padding: 4px 8px;
                    font-size: 12px;
                    min-width: 140px;
                }
                QKeySequenceEdit:focus {
                    border: 1px solid #8AB4F8;
                    background-color: #35383B;
                }
            """)
            def _make_validator(k, ed):
                def _on_seq_changed(seq):
                    s_str = seq.toString()
                    if s_str in ("Backspace", "Delete"):
                        ed.setKeySequence(QKeySequence(DEFAULT_SHORTCUTS.get(k, "")))
                        ed.setToolTip(t("shortcut_backspace_warning"))
                    else:
                        ed.setToolTip("")
                return _on_seq_changed
            edit.keySequenceChanged.connect(_make_validator(s_key, edit))

            shortcuts_grid.addWidget(lbl, row_idx, 0)
            shortcuts_grid.addWidget(edit, row_idx, 1)
            self.shortcut_labels[s_key] = (lbl, tr_key)
            self.shortcut_edits[s_key] = edit

        shortcuts_layout.addWidget(self.shortcuts_widget)

        # Reset Shortcuts Button
        reset_bar = QHBoxLayout()
        self.reset_shortcuts_btn = QPushButton(t("shortcut_reset_defaults"))
        self.reset_shortcuts_btn.setCursor(Qt.PointingHandCursor)
        self.reset_shortcuts_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #9AA0A6;
                border: 1px solid #444746;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                color: #E3E3E3;
                border-color: #C4C7C5;
            }
        """)
        self.reset_shortcuts_btn.clicked.connect(self.reset_shortcuts_to_defaults)
        reset_bar.addWidget(self.reset_shortcuts_btn)
        reset_bar.addStretch()
        shortcuts_layout.addLayout(reset_bar)

        layout.addLayout(shortcuts_layout)

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

        # Backup & Restore Actions
        self.backup_desc_lbl = QLabel(t("settings_backup_desc"))
        self.backup_desc_lbl.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.backup_desc_lbl.setWordWrap(True)
        storage_layout.addWidget(self.backup_desc_lbl)

        backup_btn_layout = QHBoxLayout()
        backup_btn_layout.setSpacing(10)

        self.export_backup_btn = QPushButton(t("settings_backup_export"))
        self.export_backup_btn.setCursor(Qt.PointingHandCursor)
        self.export_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #E3E3E3;
                border: 1px solid #444746;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #C4C7C5;
            }
        """)
        self.export_backup_btn.clicked.connect(self.on_export_backup)
        backup_btn_layout.addWidget(self.export_backup_btn)

        self.import_backup_btn = QPushButton(t("settings_backup_import"))
        self.import_backup_btn.setCursor(Qt.PointingHandCursor)
        self.import_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #FBBF24;
                border: 1px solid #444746;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #F59E0B;
            }
        """)
        self.import_backup_btn.clicked.connect(self.on_import_backup)
        backup_btn_layout.addWidget(self.import_backup_btn)
        backup_btn_layout.addStretch()

        storage_layout.addLayout(backup_btn_layout)
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

    def populate_sidebar_nb_combo(self, selected_val=5):
        if not hasattr(self, 'sidebar_nb_combo'):
            return
        self.sidebar_nb_combo.blockSignals(True)
        self.sidebar_nb_combo.clear()

        options = [
            (0, f"0 ({t('settings_sidebar_notebooks_none')})"),
            (1, "1"),
            (2, "2"),
            (3, "3"),
            (4, "4"),
            (5, "5"),
            (6, "6"),
            (7, "7"),
            (8, "8"),
            (9, "9"),
            (10, "10"),
            (15, "15"),
            (20, "20"),
            (25, "25"),
            (30, "30"),
            (50, "50"),
            (999, t("settings_sidebar_notebooks_all"))
        ]

        found = False
        try:
            target_val = int(selected_val) if selected_val is not None else 5
        except (ValueError, TypeError):
            target_val = 5

        for val, label in options:
            self.sidebar_nb_combo.addItem(label, val)
            if target_val == val:
                found = True

        if not found and selected_val is not None:
            self.sidebar_nb_combo.addItem(str(selected_val), target_val)

        idx = self.sidebar_nb_combo.findData(target_val)
        if idx >= 0:
            self.sidebar_nb_combo.setCurrentIndex(idx)
        else:
            self.sidebar_nb_combo.setCurrentIndex(5)
        self.sidebar_nb_combo.blockSignals(False)

    def get_storage_sizes(self):
        try:
            import database
            return database.get_storage_stats()
        except Exception:
            return "0 KB", "0 KB", "0 KB"

    def reset_shortcuts_to_defaults(self):
        for key, edit in getattr(self, 'shortcut_edits', {}).items():
            def_seq = DEFAULT_SHORTCUTS.get(key, "")
            edit.setKeySequence(QKeySequence(def_seq))

    def get_shortcuts(self):
        res = {}
        for key, edit in getattr(self, 'shortcut_edits', {}).items():
            seq_str = edit.keySequence().toString()
            if not seq_str or seq_str in ("Backspace", "Delete"):
                seq_str = DEFAULT_SHORTCUTS.get(key, "")
            res[key] = seq_str
        return res

    def set_shortcuts(self, shortcuts_dict):
        if not isinstance(shortcuts_dict, dict):
            shortcuts_dict = {}
        for key, edit in getattr(self, 'shortcut_edits', {}).items():
            val = shortcuts_dict.get(key, DEFAULT_SHORTCUTS.get(key, ""))
            if val in ("Backspace", "Delete"):
                val = DEFAULT_SHORTCUTS.get(key, "")
            edit.setKeySequence(QKeySequence(val))

    def get_settings(self):
        return {
            'comfyui_enabled': 1 if self.comfyui_enable_check.isChecked() else 0,
            'lora_path': self.lora_path_edit.text().strip(),
            'ckpt_path': self.ckpt_path_edit.text().strip(),
            'auto_save_enabled': 1 if self.autosave_check.isChecked() else 0,
            'auto_save_interval': self.interval_spin.value(),
            'theme': self.theme_combo.currentData(),
            'lang': self.lang_combo.currentData(),
            'custom_theme_colors': self.custom_colors,
            'sidebar_notebooks_limit': int(self.sidebar_nb_combo.currentData() if (hasattr(self, 'sidebar_nb_combo') and self.sidebar_nb_combo.currentData() is not None) else 5),
            'shortcuts': self.get_shortcuts()
        }

    def set_settings(self, lora_path, ckpt_path, auto_save_enabled, auto_save_interval, theme, lang, custom_colors_data=None, comfyui_enabled=1, sidebar_notebooks_limit=5, shortcuts=None):
        self.comfyui_enable_check.setChecked(bool(comfyui_enabled))
        self.comfyui_paths_widget.setVisible(bool(comfyui_enabled))
        self.lora_path_edit.setText(lora_path)
        self.ckpt_path_edit.setText(ckpt_path)
        self.autosave_check.setChecked(bool(auto_save_enabled))
        self.interval_spin.setValue(float(auto_save_interval))
        if hasattr(self, 'sidebar_nb_combo'):
            self.populate_sidebar_nb_combo(sidebar_notebooks_limit if sidebar_notebooks_limit is not None else 5)
        
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

        # Load shortcuts
        if shortcuts is not None:
            self.set_shortcuts(shortcuts)

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
        if hasattr(self, 'sidebar_nb_lbl'):
            self.sidebar_nb_lbl.setText(t("settings_sidebar_notebooks_limit"))
        if hasattr(self, 'sidebar_nb_combo'):
            curr_val = self.sidebar_nb_combo.currentData()
            self.populate_sidebar_nb_combo(curr_val)
        
        if hasattr(self, 'presets_lbl'):
            self.presets_lbl.setText(t("custom_theme_presets") + ":")
        for p_btn, tr_key in getattr(self, 'preset_buttons', []):
            p_btn.setText(t(tr_key))
        self.update_color_buttons()

        # Shortcuts Section
        if hasattr(self, 'shortcuts_lbl'):
            self.shortcuts_lbl.setText(t("settings_shortcuts_section"))
        if hasattr(self, 'shortcuts_desc_lbl'):
            self.shortcuts_desc_lbl.setText(t("settings_shortcuts_desc"))
        if hasattr(self, 'reset_shortcuts_btn'):
            self.reset_shortcuts_btn.setText(t("shortcut_reset_defaults"))
        for s_key, (lbl, tr_key) in getattr(self, 'shortcut_labels', {}).items():
            lbl.setText(t(tr_key))
        
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
        if hasattr(self, 'backup_desc_lbl'):
            self.backup_desc_lbl.setText(t("settings_backup_desc"))
        if hasattr(self, 'export_backup_btn'):
            self.export_backup_btn.setText(t("settings_backup_export"))
        if hasattr(self, 'import_backup_btn'):
            self.import_backup_btn.setText(t("settings_backup_import"))

    def on_export_backup(self):
        import database
        import datetime
        self._child_dialog_open = True
        try:
            today_str = datetime.date.today().isoformat()
            default_fn = f"veranote_backup_{today_str}.zip"
            target_path, _ = QFileDialog.getSaveFileName(
                self, t("settings_backup_export"), default_fn, "ZIP Archive (*.zip)"
            )
            if target_path:
                if database.export_backup_zip(target_path):
                    QMessageBox.information(
                        self, t("msg_saved_title"),
                        t("settings_backup_success").format(path=target_path)
                    )
                    self.backup_exported.emit(target_path)
                else:
                    QMessageBox.critical(self, t("msg_copy_error_title"), "Backup export failed.")
        finally:
            self._child_dialog_open = False

    def on_import_backup(self):
        import database
        self._child_dialog_open = True
        try:
            source_path, _ = QFileDialog.getOpenFileName(
                self, t("settings_backup_import"), "", "ZIP Archive (*.zip)"
            )
            if source_path:
                reply = QMessageBox.question(
                    self, t("settings_backup_import"),
                    t("settings_restore_confirm"),
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    if database.import_backup_zip(source_path):
                        QMessageBox.information(
                            self, t("msg_saved_title"),
                            t("settings_restore_success")
                        )
                        self.backup_restored.emit(source_path)
                        self.accept()
                    else:
                        QMessageBox.critical(self, t("msg_copy_error_title"), "Restore failed.")
        finally:
            self._child_dialog_open = False
