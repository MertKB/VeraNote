"""
Workflow detail section widget for VeraNote Detail Panel.
Encapsulates workflow image preview, workflow name, description,
notes, file path, copying workflow JSON to clipboard, and deletion.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                             QFileDialog, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication
from utils.i18n import t
from .common import ZoomableTextEdit


class WorkflowSection(QWidget):
    """Encapsulates all workflow metadata display, JSON copying, and editing."""
    save_workflow_data_requested = Signal(int, str, str, str) # id, name, description, notes
    delete_workflow_requested = Signal(int) # workflow_id
    workflow_image_changed = Signal(int, str) # workflow_id, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.workflow_data = None
        self.current_image_path = ""
        self.initial_workflow_name = ""
        self.initial_workflow_description = ""
        self.initial_workflow_notes = ""
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Image preview
        self.image_label = QLabel()
        self.image_label.setFixedHeight(180)
        self.image_label.setMinimumWidth(0)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_label.setStyleSheet("background-color: #131314; border-radius: 8px;")
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.on_image_clicked
        layout.addWidget(self.image_label)

        # Name Title & Input
        self.name_title = QLabel(t("detail_workflow_name"))
        self.name_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.name_title)

        self.name_edit = QLineEdit()
        self.name_edit.setMinimumWidth(0)
        self.name_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.name_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.name_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.name_edit)

        # Path Label
        self.path_label = QLabel(t("detail_card_path"))
        self.path_label.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        # Copy to Clipboard Button
        self.copy_clip_btn = QPushButton("📋 " + t("detail_copy_clipboard"))
        self.copy_clip_btn.setObjectName("CopyClipBtn")
        self.copy_clip_btn.clicked.connect(self.copy_workflow_to_clipboard)
        layout.addWidget(self.copy_clip_btn)

        # Workflow Description
        self.workflow_desc_title = QLabel(t("detail_workflow_desc"))
        self.workflow_desc_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.workflow_desc_title)

        self.workflow_desc_edit = QTextEdit()
        self.workflow_desc_edit.setFixedHeight(60)
        self.workflow_desc_edit.setPlaceholderText(t("detail_workflow_desc_placeholder"))
        self.workflow_desc_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.workflow_desc_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.workflow_desc_edit)

        # Workflow Notes
        self.notes_title = QLabel(t("detail_workflow_notes"))
        self.notes_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.notes_title)

        self.notes_edit = ZoomableTextEdit()
        self.notes_edit.setMinimumWidth(0)
        self.notes_edit.setPlaceholderText(t("detail_workflow_notes_ph"))
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(200)
        self.notes_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.notes_edit.textChanged.connect(self.check_changes)
        layout.addWidget(self.notes_edit)

        # Save & Delete Buttons Container
        self.buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        self.save_btn = QPushButton(t("detail_save_workflow"))
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton(t("detail_delete_workflow"))
        self.delete_btn.setObjectName("DeleteNoteBtn")
        self.delete_btn.clicked.connect(self.on_delete_workflow_clicked)
        buttons_layout.addWidget(self.delete_btn)

        layout.addWidget(self.buttons_container)

    def set_workflow(self, workflow_data):
        self.workflow_data = workflow_data
        self.initial_workflow_name = workflow_data.get('name', '')
        self.initial_workflow_description = workflow_data.get('description', '')
        self.initial_workflow_notes = workflow_data.get('notes', '')
        self.current_image_path = workflow_data.get('image_path') or ""

        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.initial_workflow_name)
        self.name_edit.blockSignals(False)

        self.workflow_desc_edit.blockSignals(True)
        self.workflow_desc_edit.setPlainText(self.initial_workflow_description)
        self.workflow_desc_edit.blockSignals(False)

        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(self.initial_workflow_notes)
        self.notes_edit.blockSignals(False)

        self.path_label.setText(f"{t('detail_card_path')} {workflow_data.get('file_path', '')}")

        self.save_btn.setEnabled(False)
        self.update_image()

    def check_changes(self):
        if not self.workflow_data:
            return
        current_name = self.name_edit.text().strip()
        current_desc = self.workflow_desc_edit.toPlainText().strip()
        current_notes = self.notes_edit.toPlainText().strip()
        has_changed = (
            current_name != self.initial_workflow_name or
            current_desc != self.initial_workflow_description or
            current_notes != self.initial_workflow_notes or
            self.current_image_path != (self.workflow_data.get('image_path') or '')
        )
        self.save_btn.setEnabled(has_changed)

    def update_image(self, image_path=None):
        if image_path is not None:
            self.current_image_path = image_path

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

        self.image_label.setText("🧩\n" + t("detail_select_image"))
        self.image_label.setPixmap(QPixmap())
        self.image_label.setStyleSheet("color: #8AB4F8; font-size: 12px; background-color: #131314; border-radius: 8px; border: 2px dashed #444746; qproperty-alignment: AlignCenter;")

    def on_image_clicked(self, event):
        if not self.workflow_data:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("dialog_select_workflow_image"), "", t("dialog_image_filter")
        )
        if file_path:
            self.current_image_path = file_path
            self.update_image()
            self.workflow_image_changed.emit(self.workflow_data['id'], file_path)
            self.check_changes()

    def copy_workflow_to_clipboard(self):
        if not self.workflow_data:
            return
        
        # Try database column workflow_json first
        workflow_json = self.workflow_data.get('workflow_json')
        if workflow_json:
            try:
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(workflow_json)
                self.copy_clip_btn.setText(t("msg_copied_title") + "! ✓")
                self.copy_clip_btn.setEnabled(False)
                win = self.window()
                if win and hasattr(win, 'show_toast'):
                    win.show_toast(t("toast_copied"), "success")
                QTimer.singleShot(1500, lambda: [self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard")), self.copy_clip_btn.setEnabled(True)] if hasattr(self, 'copy_clip_btn') and self.copy_clip_btn else None)
                return
            except Exception as e:
                QMessageBox.critical(self, t("msg_copy_error_title"), t("msg_file_read_error").format(error=e))
                return

        # Fallback to reading file_path
        file_path = self.workflow_data.get('file_path', '')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_file_not_found").format(path=file_path))
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(content)
            self.copy_clip_btn.setText(t("msg_copied_title") + "! ✓")
            self.copy_clip_btn.setEnabled(False)
            win = self.window()
            if win and hasattr(win, 'show_toast'):
                win.show_toast(t("toast_copied"), "success")
            QTimer.singleShot(1500, lambda: [self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard")), self.copy_clip_btn.setEnabled(True)] if hasattr(self, 'copy_clip_btn') and self.copy_clip_btn else None)
        except Exception as e:
            QMessageBox.critical(self, t("msg_copy_error_title"), t("msg_file_read_error").format(error=e))

    def on_save_clicked(self):
        if not self.workflow_data:
            return
        name = self.name_edit.text().strip()
        desc = self.workflow_desc_edit.toPlainText().strip()
        notes = self.notes_edit.toPlainText().strip()
        if not name:
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_workflow_name_empty"), QMessageBox.Ok)
            return
        self.save_workflow_data_requested.emit(self.workflow_data['id'], name, desc, notes)
        self.initial_workflow_name = name
        self.initial_workflow_description = desc
        self.initial_workflow_notes = notes
        self.save_btn.setEnabled(False)

    def on_delete_workflow_clicked(self):
        if not self.workflow_data:
            return
        reply = QMessageBox.question(
            self, t("detail_delete_workflow"), t("detail_delete_workflow_confirm"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_workflow_requested.emit(self.workflow_data['id'])

    def retranslate_ui(self):
        self.name_title.setText(t("detail_workflow_name"))
        self.name_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.path_label.setText(t("detail_card_path"))
        self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard"))
        self.workflow_desc_title.setText(t("detail_workflow_desc"))
        self.workflow_desc_edit.setPlaceholderText(t("detail_workflow_desc_placeholder"))
        self.notes_title.setText(t("detail_workflow_notes"))
        self.save_btn.setText(t("detail_save_workflow"))
        self.delete_btn.setText(t("detail_delete_workflow"))
