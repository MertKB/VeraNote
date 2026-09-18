"""
Note detail section widget for VeraNote Detail Panel.
Encapsulates note editing, thumbnail/display mode selection, corkboard pin toggle,
color swatches, auto-saving, and rich text notes editing.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, 
                             QFileDialog, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QPixmap, QTextCursor
from utils.i18n import t
from .common import ZoomableTextEdit


class NoteSection(QWidget):
    """Encapsulates all note editing, thumbnail setup, corkboard pin, and auto-save."""
    save_note_requested = Signal(int, str, str, str, str, int, bool) # id, title, content, image_path, display_mode, is_fav, is_auto_save
    corkboard_pin_toggled = Signal(int, bool)
    note_color_changed = Signal(int, str)
    delete_note_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.note_data = None
        self.all_models_list = []
        self.current_image_path = ""
        self.initial_note_title = ""
        self.initial_note_content = ""
        self.initial_note_display_mode = ""

        # Auto-Save Debounce Timer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.trigger_auto_save)
        
        self.auto_save_enabled = 1
        self.auto_save_interval = 1.5

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Note Header Widget
        self.note_header_widget = QWidget()
        note_hdr_layout = QVBoxLayout(self.note_header_widget)
        note_hdr_layout.setContentsMargins(0, 0, 0, 0)
        note_hdr_layout.setSpacing(8)

        # Row 1: Note Title
        self.note_title_edit = QLineEdit()
        self.note_title_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.note_title_edit.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border-color: #8AB4F8;
            }
        """)
        self.note_title_edit.textChanged.connect(self.check_changes)
        note_hdr_layout.addWidget(self.note_title_edit)

        # Row 2: Thumbnail and Display Actions
        note_row2 = QWidget()
        note_row2_layout = QHBoxLayout(note_row2)
        note_row2_layout.setContentsMargins(0, 0, 0, 0)
        note_row2_layout.setSpacing(6)

        self.note_thumb_preview = QLabel()
        self.note_thumb_preview.setFixedSize(60, 36)
        self.note_thumb_preview.setAlignment(Qt.AlignCenter)
        self.note_thumb_preview.setStyleSheet("background-color: #131314; border-radius: 6px; border: 1px solid #444746;")
        self.note_thumb_preview.setCursor(Qt.PointingHandCursor)
        self.note_thumb_preview.mousePressEvent = lambda e: self.on_select_note_image()
        note_row2_layout.addWidget(self.note_thumb_preview)

        self.select_note_img_btn = QPushButton(t("detail_select_image"))
        self.select_note_img_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 500;")
        self.select_note_img_btn.clicked.connect(self.on_select_note_image)
        note_row2_layout.addWidget(self.select_note_img_btn)

        self.remove_note_img_btn = QPushButton(t("detail_remove_image"))
        self.remove_note_img_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 500; color: #F28B82;")
        self.remove_note_img_btn.clicked.connect(self.on_remove_note_image)
        note_row2_layout.addWidget(self.remove_note_img_btn)

        note_row2_layout.addStretch()

        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems([t("detail_display_with_image"), t("detail_display_text_only")])
        self.display_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.display_mode_combo.currentTextChanged.connect(self.on_display_mode_changed)
        note_row2_layout.addWidget(self.display_mode_combo)
        note_hdr_layout.addWidget(note_row2)

        # Row 3: Pin Button
        note_row3 = QWidget()
        note_row3_layout = QHBoxLayout(note_row3)
        note_row3_layout.setContentsMargins(0, 4, 0, 4)
        note_row3_layout.setSpacing(6)
        note_row3_layout.addStretch()

        self.pin_corkboard_btn = QPushButton(t("detail_pin_corkboard"))
        self.pin_corkboard_btn.setCursor(Qt.PointingHandCursor)
        self.pin_corkboard_btn.clicked.connect(self.on_toggle_pin_corkboard)
        note_row3_layout.addWidget(self.pin_corkboard_btn)

        note_hdr_layout.addWidget(note_row3)
        layout.addWidget(self.note_header_widget)

        # Notes Title
        self.notes_title = QLabel(t("view_all_notes"))
        self.notes_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.notes_title)

        # Rich text note content editor
        self.notes_edit = ZoomableTextEdit()
        self.notes_edit.setMinimumWidth(0)
        self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_note"))
        self.notes_edit.setMinimumHeight(450)
        self.notes_edit.setMaximumHeight(1500)
        self.notes_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.notes_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.notes_edit)

        # Character Counter Layout
        self.char_count_container = QWidget()
        char_layout = QHBoxLayout(self.char_count_container)
        char_layout.setContentsMargins(0, 0, 4, 0)
        char_layout.addStretch()
        self.char_count_label = QLabel("0 " + t("detail_char_count"))
        self.char_count_label.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: 500;")
        char_layout.addWidget(self.char_count_label)
        layout.addWidget(self.char_count_container)

        # Save & Delete Buttons Container
        self.buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        self.save_btn = QPushButton(t("save_note"))
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton(t("detail_delete_note"))
        self.delete_btn.setObjectName("DeleteNoteBtn")
        self.delete_btn.clicked.connect(self.on_delete_note_clicked)
        buttons_layout.addWidget(self.delete_btn)

        layout.addWidget(self.buttons_container)

    def set_note(self, note_data, all_models=None, auto_save_settings=None):
        self.note_data = note_data
        self.all_models_list = all_models or []

        self.initial_note_title = note_data.get('title', '')
        self.initial_note_content = note_data.get('content', '')
        self.initial_note_display_mode = note_data.get('display_mode', 'WITH_IMAGE')
        self.current_image_path = note_data.get('image_path') or ''

        if auto_save_settings:
            self.auto_save_enabled = int(auto_save_settings.get('enabled', self.auto_save_enabled))
            self.auto_save_interval = float(auto_save_settings.get('interval', self.auto_save_interval))

        # Title
        self.note_title_edit.blockSignals(True)
        if self.note_title_edit.text() != self.initial_note_title:
            pos = self.note_title_edit.cursorPosition()
            self.note_title_edit.setText(self.initial_note_title)
            def restore_title_pos(p=pos):
                if not self.note_title_edit:
                    return
                if p <= len(self.note_title_edit.text()):
                    self.note_title_edit.setCursorPosition(p)
            QTimer.singleShot(10, restore_title_pos)
        self.note_title_edit.blockSignals(False)

        # Content
        self.notes_edit.blockSignals(True)
        if self.notes_edit.toHtml().strip() != self.initial_note_content.strip():
            cursor = self.notes_edit.textCursor()
            anchor = cursor.anchor()
            pos = cursor.position()
            self.notes_edit.setHtml(self.initial_note_content)
            def restore_pos(a=anchor, p=pos):
                if not self.notes_edit:
                    return
                doc_len = self.notes_edit.document().characterCount()
                if a <= doc_len and p <= doc_len:
                    c = self.notes_edit.textCursor()
                    try:
                        c.setPosition(a)
                        c.setPosition(p, QTextCursor.KeepAnchor)
                        self.notes_edit.setTextCursor(c)
                    except Exception:
                        pass
            QTimer.singleShot(10, restore_pos)
        self.notes_edit.blockSignals(False)

        # Display Mode Combo
        self.display_mode_combo.blockSignals(True)
        if self.initial_note_display_mode == 'TEXT_ONLY':
            self.display_mode_combo.setCurrentText(t("detail_display_text_only"))
        else:
            self.display_mode_combo.setCurrentText(t("detail_display_with_image"))
        self.display_mode_combo.blockSignals(False)

        self.save_btn.setEnabled(False)
        self.update_char_count()
        self.update_pin_corkboard_btn_text()
        self.update_image()

    def get_current_note_display_mode(self):
        text = self.display_mode_combo.currentText().strip()
        idx = self.display_mode_combo.currentIndex()
        if idx == 1 or text in ("Sadece Metin", t("detail_display_text_only"), "Text Only"):
            return 'TEXT_ONLY'
        return 'WITH_IMAGE'

    def check_changes(self):
        if not self.note_data:
            return
        self.update_char_count()
        current_title = self.note_title_edit.text().strip()
        current_content = self.notes_edit.toHtml().strip()
        current_disp = self.get_current_note_display_mode()
        has_changed = (
            current_title != self.initial_note_title or 
            current_content != self.initial_note_content or 
            current_disp != self.initial_note_display_mode or 
            self.current_image_path != (self.note_data.get('image_path') or '')
        )
        self.save_btn.setEnabled(has_changed)

        if has_changed and self.auto_save_enabled:
            self.auto_save_timer.start(int(self.auto_save_interval * 1000))
        else:
            self.auto_save_timer.stop()

    def sync_auto_save_settings(self, enabled, interval):
        self.auto_save_enabled = int(enabled)
        self.auto_save_interval = float(interval)
        if not self.auto_save_enabled:
            self.auto_save_timer.stop()

    def trigger_auto_save(self):
        if self.note_data and self.auto_save_enabled:
            title = self.note_title_edit.text().strip()
            content = self.notes_edit.toHtml().strip()
            if not title:
                return
            disp_mode = self.get_current_note_display_mode()
            self.save_note_requested.emit(
                self.note_data['id'], 
                title, 
                content, 
                self.current_image_path, 
                disp_mode,
                self.note_data.get('is_favorite', 0),
                True
            )
            self.initial_note_title = title
            self.initial_note_content = content
            self.initial_note_display_mode = disp_mode
            self.save_btn.setEnabled(False)

    def on_swatch_color_selected(self, color_hex):
        if self.note_data:
            self.note_data['color_hex'] = color_hex
            self.note_color_changed.emit(self.note_data['id'], color_hex)
            title = self.note_title_edit.text().strip()
            content = self.notes_edit.toHtml().strip()
            disp_mode = self.get_current_note_display_mode()
            self.save_note_requested.emit(
                self.note_data['id'],
                title,
                content,
                self.current_image_path,
                disp_mode,
                self.note_data.get('is_favorite', 0),
                True
            )

    def update_pin_corkboard_btn_text(self):
        if not self.note_data or not hasattr(self, 'pin_corkboard_btn'):
            return
        is_pinned = self.note_data.get('is_corkboard', 0) == 1
        if is_pinned:
            self.pin_corkboard_btn.setText(t("detail_unpin_corkboard"))
            self.pin_corkboard_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4B5563;
                    color: #E5E7EB;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6B7280;
                }
            """)
        else:
            self.pin_corkboard_btn.setText(t("detail_pin_corkboard"))
            self.pin_corkboard_btn.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F59E0B;
                }
            """)

    def on_toggle_pin_corkboard(self):
        if not self.note_data:
            return
        note_id = self.note_data.get('id', 0)
        current_pinned = self.note_data.get('is_corkboard', 0) == 1
        new_pinned = not current_pinned
        self.note_data['is_corkboard'] = 1 if new_pinned else 0
        self.update_pin_corkboard_btn_text()
        self.corkboard_pin_toggled.emit(note_id, new_pinned)

    def update_image(self, image_path=None):
        if image_path is not None:
            self.current_image_path = image_path

        path = self.current_image_path
        if self.display_mode_combo.currentText() in ("Sadece Metin", t("detail_display_text_only"), "Text Only"):
            self.note_thumb_preview.setText(t("detail_thumb_text_only"))
            self.note_thumb_preview.setPixmap(QPixmap())
            self.note_thumb_preview.setStyleSheet("color: #9AA0A6; font-size: 10px; background-color: #1E1F20; border-radius: 6px; border: 1px solid #2F2F2F; qproperty-alignment: AlignCenter;")
            return

        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(60, 36, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                cropped = scaled.copy(0, 0, 60, 36)
                self.note_thumb_preview.setPixmap(cropped)
                self.note_thumb_preview.setStyleSheet("border-radius: 6px; background-color: transparent; border: 1px solid #444746; qproperty-alignment: AlignCenter;")
                return

        self.note_thumb_preview.setText(t("detail_thumb_add_image"))
        self.note_thumb_preview.setPixmap(QPixmap())
        self.note_thumb_preview.setStyleSheet("color: #8AB4F8; font-size: 10px; font-weight: bold; background-color: #131314; border-radius: 6px; border: 1px dashed #444746; qproperty-alignment: AlignCenter;")

    def on_select_note_image(self):
        if not self.note_data:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("msg_select_note_image"), "", t("dialog_image_filter")
        )
        if file_path:
            self.current_image_path = file_path
            self.update_image()
            self.check_changes()

    def on_remove_note_image(self):
        if not self.note_data:
            return
        self.current_image_path = ""
        self.update_image()
        self.check_changes()

    def on_save_clicked(self):
        if not self.note_data:
            return
        title = self.note_title_edit.text().strip()
        content = self.notes_edit.toHtml().strip()
        if not title:
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_empty_title_error"), QMessageBox.Ok)
            return
        disp_mode = self.get_current_note_display_mode()
        self.save_note_requested.emit(
            self.note_data['id'], 
            title, 
            content, 
            self.current_image_path, 
            disp_mode,
            self.note_data.get('is_favorite', 0),
            False
        )
        self.initial_note_title = title
        self.initial_note_content = content
        self.initial_note_display_mode = disp_mode
        self.save_btn.setEnabled(False)

    def on_delete_note_clicked(self):
        if not self.note_data:
            return
        reply = QMessageBox.question(
            self, t("detail_delete_note"), t("detail_delete_note_confirm"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_note_requested.emit(self.note_data['id'])

    def update_char_count(self):
        text_len = len(self.notes_edit.toPlainText())
        self.char_count_label.setText(f"{text_len} {t('detail_char_count')}")

    def on_display_mode_changed(self):
        self.update_image()
        self.check_changes()

    def retranslate_ui(self):
        self.note_title_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.select_note_img_btn.setText(t("detail_select_image"))
        self.remove_note_img_btn.setText(t("detail_remove_image"))
        self.notes_title.setText(t("view_all_notes"))
        self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_note"))
        self.save_btn.setText(t("save_note"))
        self.delete_btn.setText(t("detail_delete_note"))

        self.display_mode_combo.blockSignals(True)
        curr_mode_idx = self.display_mode_combo.currentIndex()
        self.display_mode_combo.clear()
        self.display_mode_combo.addItems([t("detail_display_with_image"), t("detail_display_text_only")])
        if curr_mode_idx >= 0:
            self.display_mode_combo.setCurrentIndex(curr_mode_idx)
        self.display_mode_combo.blockSignals(False)

        self.update_pin_corkboard_btn_text()
        self.update_char_count()
