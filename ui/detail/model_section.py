"""
Model detail section widget for VeraNote Detail Panel.
Encapsulates model preview, name, notes, trigger words, and tags.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFileDialog, QSizePolicy, QComboBox)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication
from utils.i18n import t
from .common import ZoomableTextEdit, FlowLayout, TriggerPillButton, TagPillWidget


class ModelSection(QWidget):
    """Encapsulates all model metadata display, trigger words, and tagging."""
    save_model_data_requested = Signal(int, str, str, str) # model_id, name, notes, base_architecture
    add_trigger_requested = Signal(int, str) # model_id, word
    delete_trigger_requested = Signal(int, str) # model_id, word
    add_tag_requested = Signal(int, str) # model_id, tag
    delete_tag_requested = Signal(int, str) # model_id, tag
    image_changed = Signal(int, str) # model_id, file_path
    delete_model_requested = Signal(int) # model_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_data = None
        self.trigger_words = []
        self.current_image_path = ""
        self.initial_name = ""
        self.initial_notes = ""
        self.initial_arch = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Image preview label
        self.image_label = QLabel()
        self.image_label.setFixedHeight(180)
        self.image_label.setMinimumWidth(0)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_label.setStyleSheet("background-color: #131314; border-radius: 8px;")
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.on_image_clicked
        layout.addWidget(self.image_label)

        # Editable Model Name
        self.name_title = QLabel(t("detail_card_title"))
        self.name_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.name_title)

        self.name_edit = QLineEdit()
        self.name_edit.setMinimumWidth(0)
        self.name_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.name_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.name_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.name_edit)

        # Base Architecture Selection
        arch_row = QHBoxLayout()
        self.arch_label = QLabel(t("detail_arch_label") + ":")
        self.arch_label.setObjectName("DetailWordLabel")
        self.arch_label.setStyleSheet("color: #E3E3E3; font-weight: bold; font-size: 12px;")
        arch_row.addWidget(self.arch_label)

        self.arch_combo = QComboBox()
        self.arch_combo.addItems([
            t("detail_arch_auto"),
            "Flux",
            "SDXL",
            "SD 1.5",
            "Pony",
            "SD3",
            "Illustrious",
            "SD 2.1",
            "Diğer"
        ])
        self.arch_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 6px;
                color: #8AB4F8;
                font-weight: bold;
                padding: 4px 10px;
                font-size: 12px;
            }
        """)
        self.arch_combo.currentIndexChanged.connect(self.check_changes)
        arch_row.addWidget(self.arch_combo)
        arch_row.addStretch()
        layout.addLayout(arch_row)

        # File Path Info
        self.path_label = QLabel(t("detail_card_path"))
        self.path_label.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        # Notes Section
        self.notes_title = QLabel(t("detail_notes_title"))
        self.notes_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.notes_title)

        self.notes_edit = ZoomableTextEdit()
        self.notes_edit.setMinimumWidth(0)
        self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_model"))
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(200)
        self.notes_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.notes_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.notes_edit)

        # Save & Delete Buttons Container
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)

        self.save_btn = QPushButton(t("detail_save_changes"))
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton(t("detail_delete_model"))
        self.delete_btn.setObjectName("DeleteNoteBtn")
        self.delete_btn.clicked.connect(self.on_delete_model_clicked)
        buttons_layout.addWidget(self.delete_btn)

        layout.addWidget(buttons_container)

        # --- MODEL TAGS SECTION ---
        self.tags_title = QLabel(t("detail_tags_title"))
        self.tags_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.tags_title)

        self.tags_container = QWidget()
        self.tags_layout = FlowLayout(self.tags_container, spacing=6)
        layout.addWidget(self.tags_container)

        self.new_tag_edit = QLineEdit()
        self.new_tag_edit.setMinimumWidth(0)
        self.new_tag_edit.setPlaceholderText(t("detail_new_tag_placeholder"))
        self.new_tag_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.new_tag_edit.returnPressed.connect(self.on_add_tag)
        layout.addWidget(self.new_tag_edit)

        # --- TRIGGER WORDS SECTION ---
        self.tw_title = QLabel(t("detail_triggers_title"))
        self.tw_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.tw_title)

        add_tw_container = QWidget()
        add_tw_layout = QHBoxLayout(add_tw_container)
        add_tw_layout.setContentsMargins(0, 0, 0, 0)
        self.new_tw_edit = QLineEdit()
        self.new_tw_edit.setMinimumWidth(0)
        self.new_tw_edit.setPlaceholderText(t("detail_new_trigger_placeholder"))
        self.new_tw_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.new_tw_edit.returnPressed.connect(self.on_add_trigger)
        self.add_tw_btn = QPushButton("+ " + t("detail_add_btn"))
        self.add_tw_btn.setStyleSheet("padding: 6px 12px;")
        self.add_tw_btn.clicked.connect(self.on_add_trigger)
        add_tw_layout.addWidget(self.new_tw_edit)
        add_tw_layout.addWidget(self.add_tw_btn)
        layout.addWidget(add_tw_container)

        self.pills_container = QWidget()
        self.pills_layout = FlowLayout(self.pills_container, spacing=6)
        layout.addWidget(self.pills_container)

        self.copy_all_btn = QPushButton(t("detail_copy_all_words"))
        self.copy_all_btn.clicked.connect(self.on_copy_all_clicked)
        layout.addWidget(self.copy_all_btn)

        # --- SAMPLE GENERATION INFO SECTION (from ComfyUI PNG) ---
        self.sample_info_container = QWidget()
        sample_layout = QVBoxLayout(self.sample_info_container)
        sample_layout.setContentsMargins(0, 10, 0, 0)
        sample_layout.setSpacing(6)

        self.sample_title = QLabel(t("detail_sample_prompt_title"))
        self.sample_title.setObjectName("DetailWordLabel")
        sample_layout.addWidget(self.sample_title)

        # Positive prompt box
        self.sample_pos_box = QWidget()
        pos_layout = QVBoxLayout(self.sample_pos_box)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(4)
        pos_hdr = QHBoxLayout()
        self.sample_pos_lbl = QLabel(t("detail_sample_prompt_pos"))
        self.sample_pos_lbl.setStyleSheet("color: #8AB4F8; font-size: 11px; font-weight: bold;")
        pos_hdr.addWidget(self.sample_pos_lbl)
        pos_hdr.addStretch()
        self.copy_sample_pos_btn = QPushButton(t("workflow_copy_prompt"))
        from utils.icon_manager import get_icon
        self.copy_sample_pos_btn.setIcon(get_icon("notes", "#8AB4F8", 12))
        self.copy_sample_pos_btn.setStyleSheet("""
            QPushButton { background-color: #2D2F31; color: #8AB4F8; border: 1px solid #444746; border-radius: 12px; padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background-color: #3C4043; border-color: #8AB4F8; }
        """)
        self.copy_sample_pos_btn.clicked.connect(self.copy_sample_pos)
        pos_hdr.addWidget(self.copy_sample_pos_btn)
        pos_layout.addLayout(pos_hdr)

        self.sample_pos_edit = ZoomableTextEdit()
        self.sample_pos_edit.setReadOnly(True)
        self.sample_pos_edit.setMaximumHeight(85)
        self.sample_pos_edit.setStyleSheet("background-color: #1A1C1E; border: 1px solid #36383B; border-radius: 6px; color: #D1D5DB; font-size: 11px; padding: 4px;")
        pos_layout.addWidget(self.sample_pos_edit)
        sample_layout.addWidget(self.sample_pos_box)

        # Negative prompt box
        self.sample_neg_box = QWidget()
        neg_layout = QVBoxLayout(self.sample_neg_box)
        neg_layout.setContentsMargins(0, 0, 0, 0)
        neg_layout.setSpacing(4)
        neg_hdr = QHBoxLayout()
        self.sample_neg_lbl = QLabel(t("detail_sample_prompt_neg"))
        self.sample_neg_lbl.setStyleSheet("color: #F28B82; font-size: 11px; font-weight: bold;")
        neg_hdr.addWidget(self.sample_neg_lbl)
        neg_hdr.addStretch()
        self.copy_sample_neg_btn = QPushButton(t("workflow_copy_prompt"))
        self.copy_sample_neg_btn.setIcon(get_icon("notes", "#F28B82", 12))
        self.copy_sample_neg_btn.setStyleSheet("""
            QPushButton { background-color: #2D2F31; color: #F28B82; border: 1px solid #444746; border-radius: 12px; padding: 2px 8px; font-size: 11px; }
            QPushButton:hover { background-color: #3C4043; border-color: #F28B82; }
        """)
        self.copy_sample_neg_btn.clicked.connect(self.copy_sample_neg)
        neg_hdr.addWidget(self.copy_sample_neg_btn)
        neg_layout.addLayout(neg_hdr)

        self.sample_neg_edit = ZoomableTextEdit()
        self.sample_neg_edit.setReadOnly(True)
        self.sample_neg_edit.setMaximumHeight(65)
        self.sample_neg_edit.setStyleSheet("background-color: #1A1C1E; border: 1px solid #36383B; border-radius: 6px; color: #D1D5DB; font-size: 11px; padding: 4px;")
        neg_layout.addWidget(self.sample_neg_edit)
        sample_layout.addWidget(self.sample_neg_box)

        layout.addWidget(self.sample_info_container)
        self.sample_info_container.setVisible(False)

    def set_model(self, model_data, trigger_words):
        self.model_data = model_data
        self.trigger_words = trigger_words or []
        self.initial_name = model_data.get('name', '')
        self.initial_notes = model_data.get('notes', '')
        self.current_image_path = model_data.get('image_path') or ""

        arch = model_data.get('base_architecture') or ""
        if not arch:
            from utils.png_parser import detect_base_architecture
            arch = detect_base_architecture([model_data.get('name', ''), model_data.get('file_path', '')])
        self.initial_arch = arch or t("detail_arch_auto")

        self.arch_combo.blockSignals(True)
        idx = self.arch_combo.findText(arch)
        if idx >= 0:
            self.arch_combo.setCurrentIndex(idx)
        else:
            self.arch_combo.setCurrentIndex(0)
        self.arch_combo.blockSignals(False)

        self.name_edit.blockSignals(True)
        self.notes_edit.blockSignals(True)
        self.name_edit.setText(self.initial_name)
        self.notes_edit.setPlainText(self.initial_notes)
        self.name_edit.blockSignals(False)
        self.notes_edit.blockSignals(False)

        self.path_label.setText(f"{t('detail_card_path')} {model_data.get('file_path', '')}")
        self.save_btn.setEnabled(False)

        self.update_image()
        self.update_sample_generation_info()
        self.reload_tags()
        self.reload_pills()

    def check_changes(self):
        if not self.model_data:
            return
        current_name = self.name_edit.text().strip()
        current_notes = self.notes_edit.toPlainText().strip()
        current_arch = self.arch_combo.currentText().strip()
        has_changed = (
            current_name != self.initial_name or 
            current_notes != self.initial_notes or 
            current_arch != self.initial_arch
        )
        self.save_btn.setEnabled(has_changed)

    def on_save_clicked(self):
        if not self.model_data:
            return
        name = self.name_edit.text().strip()
        notes = self.notes_edit.toPlainText().strip()
        current_arch = self.arch_combo.currentText().strip()
        if current_arch == t("detail_arch_auto"):
            from utils.png_parser import detect_base_architecture
            current_arch = detect_base_architecture([name, self.model_data.get('file_path', '')])
        if not name:
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_model_name_empty"), QMessageBox.Ok)
            return
        self.save_model_data_requested.emit(self.model_data['id'], name, notes, current_arch)
        self.initial_name = name
        self.initial_notes = notes
        self.initial_arch = self.arch_combo.currentText().strip()
        self.save_btn.setEnabled(False)

    def on_delete_model_clicked(self):
        if not self.model_data:
            return
        name = self.model_data.get('name', '')
        confirm = QMessageBox.question(
            self,
            t("confirm_delete_models_title"),
            t("detail_delete_model_confirm").format(name=name),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.delete_model_requested.emit(self.model_data['id'])

    def reload_pills(self):
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for word in self.trigger_words:
            pill = TriggerPillButton(word, parent=self)
            pill.clicked.connect(lambda checked=False, w=word: self.on_word_clicked(w))
            pill.delete_requested.connect(lambda w=word: self.on_delete_trigger(w))
            self.pills_layout.addWidget(pill)

        if not self.trigger_words:
            no_word = QLabel(t("detail_no_triggers"))
            no_word.setStyleSheet("color: #9AA0A6; font-style: italic; font-size: 11px;")
            self.pills_layout.addWidget(no_word)
            self.copy_all_btn.setEnabled(False)
        else:
            self.copy_all_btn.setEnabled(True)

    def reload_tags(self):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.model_data.get('tags', []) if self.model_data else []
        for tag in tags:
            tag_pill = TagPillWidget(tag, parent=self)
            tag_pill.delete_requested.connect(self.on_delete_tag)
            self.tags_layout.addWidget(tag_pill)

        if not tags:
            no_tags = QLabel(t("detail_no_tags"))
            no_tags.setStyleSheet("color: #9AA0A6; font-style: italic; font-size: 11px;")
            self.tags_layout.addWidget(no_tags)

    def on_add_tag(self):
        if not self.model_data:
            return
        tag = self.new_tag_edit.text().strip()
        if tag:
            tags = self.model_data.get('tags', [])
            if tag in tags:
                QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_tag_exists"), QMessageBox.Ok)
                return
            self.add_tag_requested.emit(self.model_data['id'], tag)
            self.new_tag_edit.clear()

    def on_delete_tag(self, tag):
        if not self.model_data:
            return
        reply = QMessageBox.question(
            self, t("msg_confirm_remove_tag_title"), t("msg_confirm_remove_tag_text").format(tag=tag),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_tag_requested.emit(self.model_data['id'], tag)

    def on_add_trigger(self):
        if not self.model_data:
            return
        word = self.new_tw_edit.text().strip()
        if word:
            if word in self.trigger_words:
                QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_trigger_exists"), QMessageBox.Ok)
                return
            self.add_trigger_requested.emit(self.model_data['id'], word)
            self.new_tw_edit.clear()

    def on_delete_trigger(self, word):
        if not self.model_data:
            return
        reply = QMessageBox.question(
            self, t("msg_confirm_delete_trigger_title"), t("msg_confirm_delete_trigger_text").format(word=word),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_trigger_requested.emit(self.model_data['id'], word)

    def on_word_clicked(self, word):
        QGuiApplication.clipboard().setText(word)
        win = self.window()
        if win and hasattr(win, 'show_toast'):
            win.show_toast(t("msg_trigger_copied_text").format(word=word), "success")
        else:
            QMessageBox.information(self, t("msg_copied_title"), t("msg_trigger_copied_text").format(word=word), QMessageBox.Ok)

    def on_copy_all_clicked(self):
        if self.trigger_words:
            all_words = ", ".join(self.trigger_words)
            QGuiApplication.clipboard().setText(all_words)
            win = self.window()
            if win and hasattr(win, 'show_toast'):
                win.show_toast(t("msg_all_triggers_copied_text"), "success")
            else:
                QMessageBox.information(self, t("msg_copied_title"), t("msg_all_triggers_copied_text"), QMessageBox.Ok)

    def copy_sample_pos(self):
        text = self.sample_pos_edit.toPlainText().strip()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.copy_sample_pos_btn.setText(t("msg_copied_title"))
            self.copy_sample_pos_btn.setEnabled(False)
            win = self.window()
            if win and hasattr(win, 'show_toast'):
                win.show_toast(t("toast_copied_pos_prompt"), "success")
            QTimer.singleShot(1500, lambda: [self.copy_sample_pos_btn.setText(t("workflow_copy_prompt")), self.copy_sample_pos_btn.setEnabled(True)] if hasattr(self, 'copy_sample_pos_btn') and self.copy_sample_pos_btn else None)

    def copy_sample_neg(self):
        text = self.sample_neg_edit.toPlainText().strip()
        if text:
            QGuiApplication.clipboard().setText(text)
            self.copy_sample_neg_btn.setText(t("msg_copied_title"))
            self.copy_sample_neg_btn.setEnabled(False)
            win = self.window()
            if win and hasattr(win, 'show_toast'):
                win.show_toast(t("toast_copied_neg_prompt"), "success")
            QTimer.singleShot(1500, lambda: [self.copy_sample_neg_btn.setText(t("workflow_copy_prompt")), self.copy_sample_neg_btn.setEnabled(True)] if hasattr(self, 'copy_sample_neg_btn') and self.copy_sample_neg_btn else None)

    def update_sample_generation_info(self):
        from utils.png_parser import extract_comfyui_metadata_from_png
        img_path = self.current_image_path or (self.model_data.get('image_path') if self.model_data else '')
        if img_path and os.path.exists(img_path) and img_path.lower().endswith('.png'):
            try:
                meta = extract_comfyui_metadata_from_png(img_path)
                pos = meta.get('positive_prompt', '').strip()
                neg = meta.get('negative_prompt', '').strip()
                if pos or neg:
                    self.sample_info_container.setVisible(True)
                    self.sample_pos_box.setVisible(bool(pos))
                    self.sample_pos_edit.setPlainText(pos)
                    self.sample_neg_box.setVisible(bool(neg))
                    self.sample_neg_edit.setPlainText(neg)
                    return
            except Exception:
                pass
        self.sample_info_container.setVisible(False)

    def update_image(self, image_path=None):
        if image_path is not None:
            self.current_image_path = image_path
        self.update_sample_generation_info()
        path = self.current_image_path
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                w = max(200, self.image_label.width())
                h = 180
                scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                return
        self.image_label.setText(t("detail_upload_image"))
        self.image_label.setPixmap(QPixmap())
        self.image_label.setStyleSheet("color: #8AB4F8; font-size: 12px; background-color: #131314; border-radius: 8px; border: 2px dashed #444746; qproperty-alignment: AlignCenter;")

    def on_image_clicked(self, event):
        if not self.model_data:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("msg_select_model_image"), "", t("dialog_image_filter")
        )
        if file_path:
            self.image_changed.emit(self.model_data['id'], file_path)

    def retranslate_ui(self):
        self.name_title.setText(t("detail_card_title"))
        self.name_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.arch_label.setText(t("detail_arch_label") + ":")
        self.notes_title.setText(t("detail_notes_title"))
        self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_model"))
        self.save_btn.setText(t("detail_save_changes"))
        self.delete_btn.setText(t("detail_delete_model"))
        self.tags_title.setText(t("detail_tags_title"))
        self.new_tag_edit.setPlaceholderText(t("detail_new_tag_placeholder"))
        self.tw_title.setText(t("detail_triggers_title"))
        self.new_tw_edit.setPlaceholderText(t("detail_new_trigger_placeholder"))
        self.add_tw_btn.setText("+ " + t("detail_add_btn"))
        self.copy_all_btn.setText(t("detail_copy_all_words"))
        if hasattr(self, 'sample_title'):
            self.sample_title.setText(t("detail_sample_prompt_title"))
            self.sample_pos_lbl.setText(t("detail_sample_prompt_pos"))
            self.sample_neg_lbl.setText(t("detail_sample_prompt_neg"))
            self.copy_sample_pos_btn.setText(t("workflow_copy_prompt"))
            self.copy_sample_neg_btn.setText(t("workflow_copy_prompt"))
        if self.model_data:
            self.path_label.setText(f"{t('detail_card_path')} {self.model_data.get('file_path', '')}")
            self.reload_tags()
            self.reload_pills()
