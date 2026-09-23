"""
Workflow detail section widget for VeraNote Detail Panel.
Encapsulates workflow image preview, workflow name, description,
notes, file path, copying workflow JSON to clipboard, node types analysis,
generation prompt parameters preview, and deletion.
"""
import os
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                             QFileDialog, QSizePolicy)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication
from utils.i18n import t
from utils.workflow_parser import parse_workflow_node_types
from utils.png_parser import extract_comfyui_metadata_from_png
from .common import ZoomableTextEdit, FlowLayout


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
        self.node_widgets = []
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

        # --- NODES USED SECTION ---
        self.nodes_title = QLabel(t("workflow_nodes_title"))
        self.nodes_title.setObjectName("DetailWordLabel")
        layout.addWidget(self.nodes_title)

        self.nodes_container = QWidget()
        self.nodes_layout = FlowLayout(self.nodes_container, spacing=6)
        layout.addWidget(self.nodes_container)

        # --- 1. POSITIVE PROMPT SECTION ---
        self.pos_prompt_container = QWidget()
        pos_layout = QVBoxLayout(self.pos_prompt_container)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(6)

        pos_hdr = QHBoxLayout()
        self.pos_prompt_title = QLabel(t("workflow_pos_prompt"))
        self.pos_prompt_title.setObjectName("DetailWordLabel")
        pos_hdr.addWidget(self.pos_prompt_title)
        pos_hdr.addStretch()

        self.copy_pos_btn = QPushButton("📋 " + t("workflow_copy_prompt"))
        self.copy_pos_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #C2E7FF;
                border: 1px solid #444746;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #8AB4F8;
            }
        """)
        self.copy_pos_btn.clicked.connect(self.copy_positive_prompt)
        pos_hdr.addWidget(self.copy_pos_btn)
        pos_layout.addLayout(pos_hdr)

        self.pos_prompt_edit = ZoomableTextEdit()
        self.pos_prompt_edit.setMinimumWidth(0)
        self.pos_prompt_edit.setReadOnly(True)
        self.pos_prompt_edit.setMinimumHeight(60)
        self.pos_prompt_edit.setMaximumHeight(140)
        self.pos_prompt_edit.setStyleSheet("background-color: #1A1C1E; border: 1px solid #36383B; border-radius: 8px; color: #D1D5DB; font-size: 11px; padding: 6px;")
        pos_layout.addWidget(self.pos_prompt_edit)
        layout.addWidget(self.pos_prompt_container)
        self.pos_prompt_container.setVisible(False)

        # --- 2. NEGATIVE PROMPT SECTION ---
        self.neg_prompt_container = QWidget()
        neg_layout = QVBoxLayout(self.neg_prompt_container)
        neg_layout.setContentsMargins(0, 0, 0, 0)
        neg_layout.setSpacing(6)

        neg_hdr = QHBoxLayout()
        self.neg_prompt_title = QLabel(t("workflow_neg_prompt"))
        self.neg_prompt_title.setObjectName("DetailWordLabel")
        neg_hdr.addWidget(self.neg_prompt_title)
        neg_hdr.addStretch()

        self.copy_neg_btn = QPushButton("📋 " + t("workflow_copy_prompt"))
        self.copy_neg_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #F28B82;
                border: 1px solid #444746;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #F28B82;
            }
        """)
        self.copy_neg_btn.clicked.connect(self.copy_negative_prompt)
        neg_hdr.addWidget(self.copy_neg_btn)
        neg_layout.addLayout(neg_hdr)

        self.neg_prompt_edit = ZoomableTextEdit()
        self.neg_prompt_edit.setMinimumWidth(0)
        self.neg_prompt_edit.setReadOnly(True)
        self.neg_prompt_edit.setMinimumHeight(45)
        self.neg_prompt_edit.setMaximumHeight(100)
        self.neg_prompt_edit.setStyleSheet("background-color: #1A1C1E; border: 1px solid #36383B; border-radius: 8px; color: #D1D5DB; font-size: 11px; padding: 6px;")
        neg_layout.addWidget(self.neg_prompt_edit)
        layout.addWidget(self.neg_prompt_container)
        self.neg_prompt_container.setVisible(False)

        # --- 3. PARAMETERS SECTION (Seed, Steps, CFG, etc.) ---
        self.params_container = QWidget()
        params_layout = QVBoxLayout(self.params_container)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(6)

        params_hdr = QHBoxLayout()
        self.params_title = QLabel(t("workflow_params_title"))
        self.params_title.setObjectName("DetailWordLabel")
        params_hdr.addWidget(self.params_title)
        params_hdr.addStretch()

        self.copy_params_btn = QPushButton("📋 " + t("workflow_copy_params"))
        self.copy_params_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #C2E7FF;
                border: 1px solid #444746;
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #8AB4F8;
            }
        """)
        self.copy_params_btn.clicked.connect(self.copy_all_params)
        params_hdr.addWidget(self.copy_params_btn)
        params_layout.addLayout(params_hdr)

        # Seed row card with dedicated copy button
        self.seed_card = QWidget()
        self.seed_card.setStyleSheet("background-color: #1E2022; border: 1px solid #383B3E; border-radius: 8px;")
        seed_layout = QHBoxLayout(self.seed_card)
        seed_layout.setContentsMargins(10, 4, 8, 4)
        seed_layout.setSpacing(8)

        seed_title_lbl = QLabel("🌱 Seed:")
        seed_title_lbl.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: bold;")
        seed_layout.addWidget(seed_title_lbl)

        self.seed_value_lbl = QLabel("-")
        self.seed_value_lbl.setStyleSheet("color: #E3E3E3; font-size: 12px; font-family: monospace; font-weight: bold;")
        self.seed_value_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        seed_layout.addWidget(self.seed_value_lbl)
        seed_layout.addStretch()

        self.copy_seed_btn = QPushButton("📋")
        self.copy_seed_btn.setToolTip(t("workflow_copy_seed"))
        self.copy_seed_btn.setFixedSize(26, 22)
        self.copy_seed_btn.setCursor(Qt.PointingHandCursor)
        self.copy_seed_btn.setStyleSheet("""
            QPushButton {
                background-color: #2D2F31;
                color: #A8C7FA;
                border: 1px solid #444746;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3C4043;
                border-color: #8AB4F8;
            }
        """)
        self.copy_seed_btn.clicked.connect(self.copy_seed_value)
        seed_layout.addWidget(self.copy_seed_btn)
        params_layout.addWidget(self.seed_card)

        # Other parameters layout (Steps, CFG, Sampler, Scheduler, Denoise)
        self.other_params_widget = QWidget()
        self.other_params_layout = FlowLayout(self.other_params_widget, spacing=6)
        params_layout.addWidget(self.other_params_widget)

        layout.addWidget(self.params_container)
        self.params_container.setVisible(False)

        # --- 4. USED MODELS & LORAS SECTION ---
        self.used_models_container = QWidget()
        models_layout = QVBoxLayout(self.used_models_container)
        models_layout.setContentsMargins(0, 0, 0, 0)
        models_layout.setSpacing(6)

        self.models_title = QLabel(t("workflow_used_models"))
        self.models_title.setObjectName("DetailWordLabel")
        models_layout.addWidget(self.models_title)

        self.models_pills_widget = QWidget()
        self.models_pills_layout = FlowLayout(self.models_pills_widget, spacing=6)
        models_layout.addWidget(self.models_pills_widget)

        layout.addWidget(self.used_models_container)
        self.used_models_container.setVisible(False)

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
        self.update_node_badges()
        self.update_prompt_info()

    def update_node_badges(self):
        # Clear previous node badges
        while self.nodes_layout.count():
            item = self.nodes_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.node_widgets.clear()

        if not self.workflow_data:
            return

        # Determine source for nodes: raw JSON in db or file_path
        src = self.workflow_data.get('workflow_json') or self.workflow_data.get('file_path', '')
        node_counts = parse_workflow_node_types(src)
        
        # If node_counts empty and file is PNG, extract from PNG
        if not node_counts and self.current_image_path and self.current_image_path.lower().endswith('.png'):
            meta = extract_comfyui_metadata_from_png(self.current_image_path)
            if meta.get('workflow'):
                node_counts = parse_workflow_node_types(meta['workflow'])

        if not node_counts:
            lbl = QLabel(t("workflow_no_nodes"))
            lbl.setStyleSheet("color: #71767B; font-size: 11px; font-style: italic;")
            self.nodes_layout.addWidget(lbl)
            self.node_widgets.append(lbl)
            return

        for node_type, count in node_counts[:16]: # Top 16 node types
            pill = QLabel(f"{node_type} ×{count}" if count > 1 else node_type)
            pill.setStyleSheet("""
                QLabel {
                    background-color: #242936;
                    color: #A8C7FA;
                    border: 1px solid #3c4456;
                    border-radius: 10px;
                    padding: 3px 8px;
                    font-size: 11px;
                    font-weight: 500;
                }
            """)
            self.nodes_layout.addWidget(pill)
            self.node_widgets.append(pill)

    def update_prompt_info(self):
        if not self.workflow_data:
            self.pos_prompt_container.setVisible(False)
            self.neg_prompt_container.setVisible(False)
            self.params_container.setVisible(False)
            self.used_models_container.setVisible(False)
            return

        file_path = self.workflow_data.get('file_path', '')
        img_path = self.current_image_path or file_path
        
        meta = {}
        if img_path and os.path.exists(img_path) and img_path.lower().endswith('.png'):
            meta = extract_comfyui_metadata_from_png(img_path)

        # 1. Positive Prompt
        pos = (meta.get('positive_prompt') or '').strip()
        if pos:
            self.pos_prompt_edit.setPlainText(pos)
            self.pos_prompt_container.setVisible(True)
        else:
            self.pos_prompt_edit.clear()
            self.pos_prompt_container.setVisible(False)

        # 2. Negative Prompt
        neg = (meta.get('negative_prompt') or '').strip()
        if neg:
            self.neg_prompt_edit.setPlainText(neg)
            self.neg_prompt_container.setVisible(True)
        else:
            self.neg_prompt_edit.clear()
            self.neg_prompt_container.setVisible(False)

        # 3. Parameters (Seed, Steps, CFG, Sampler, Scheduler, Denoise)
        params = meta.get('sampler_params') or {}
        while self.other_params_layout.count():
            item = self.other_params_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if params:
            seed_val = params.get('seed')
            self.seed_value_lbl.setText(str(seed_val) if seed_val is not None else "-")

            param_labels = [
                ("Steps", params.get('steps')),
                ("CFG", params.get('cfg')),
                ("Sampler", params.get('sampler_name')),
                ("Scheduler", params.get('scheduler')),
                ("Denoise", params.get('denoise'))
            ]
            for label, val in param_labels:
                if val is not None:
                    badge = QLabel(f"{label}: {val}")
                    badge.setStyleSheet("""
                        QLabel {
                            background-color: #282A2C;
                            color: #D1D5DB;
                            border: 1px solid #3C4043;
                            border-radius: 6px;
                            padding: 3px 8px;
                            font-size: 11px;
                        }
                    """)
                    self.other_params_layout.addWidget(badge)
            self.params_container.setVisible(True)
        else:
            self.seed_value_lbl.setText("-")
            self.params_container.setVisible(False)

        # 4. Used Models & LoRAs
        models = meta.get('models') or []
        while self.models_pills_layout.count():
            item = self.models_pills_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if models:
            for m in models:
                pill = QPushButton(f"📦 {m}")
                pill.setCursor(Qt.PointingHandCursor)
                pill.setToolTip(f"{m} (Kopyalamak için tıkla)")
                pill.setStyleSheet("""
                    QPushButton {
                        background-color: #282A2C;
                        color: #C2E7FF;
                        border: 1px solid #3C4043;
                        border-radius: 12px;
                        padding: 3px 10px;
                        font-size: 11px;
                        font-weight: 500;
                    }
                    QPushButton:hover {
                        background-color: #313438;
                        border-color: #8AB4F8;
                    }
                """)
                pill.clicked.connect(lambda _, name=m: self.copy_model_name(name))
                self.models_pills_layout.addWidget(pill)
            self.used_models_container.setVisible(True)
        else:
            self.used_models_container.setVisible(False)

    def copy_positive_prompt(self):
        text = self.pos_prompt_edit.toPlainText().strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        from ui.toast_notification import ToastNotification
        ToastNotification.show_toast(self, t("toast_copied_pos_prompt"), duration=2000)

    def copy_negative_prompt(self):
        text = self.neg_prompt_edit.toPlainText().strip()
        if not text:
            return
        QGuiApplication.clipboard().setText(text)
        from ui.toast_notification import ToastNotification
        ToastNotification.show_toast(self, t("toast_copied_neg_prompt"), duration=2000)

    def copy_seed_value(self):
        seed_txt = self.seed_value_lbl.text().strip()
        if not seed_txt or seed_txt == "-":
            return
        QGuiApplication.clipboard().setText(seed_txt)
        from ui.toast_notification import ToastNotification
        ToastNotification.show_toast(self, f"🌱 Seed {seed_txt}: {t('toast_copied_seed')}", duration=2000)

    def copy_all_params(self):
        file_path = self.workflow_data.get('file_path', '') if self.workflow_data else ''
        img_path = self.current_image_path or file_path
        if img_path and os.path.exists(img_path) and img_path.lower().endswith('.png'):
            meta = extract_comfyui_metadata_from_png(img_path)
            params = meta.get('sampler_params', {})
            if params:
                lines = [f"{k}: {v}" for k, v in params.items()]
                QGuiApplication.clipboard().setText(", ".join(lines))
                from ui.toast_notification import ToastNotification
                ToastNotification.show_toast(self, t("toast_copied_params"), duration=2000)
                return
        seed_txt = self.seed_value_lbl.text().strip()
        if seed_txt and seed_txt != "-":
            QGuiApplication.clipboard().setText(f"Seed: {seed_txt}")
            from ui.toast_notification import ToastNotification
            ToastNotification.show_toast(self, t("toast_copied_params"), duration=2000)

    def copy_model_name(self, model_name):
        clean_name = model_name.replace("LoRA: ", "").strip()
        QGuiApplication.clipboard().setText(clean_name)
        from ui.toast_notification import ToastNotification
        ToastNotification.show_toast(self, f"📋 {clean_name}", duration=2000)

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
            self.update_prompt_info()
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
        self.nodes_title.setText(t("workflow_nodes_title"))
        self.pos_prompt_title.setText(t("workflow_pos_prompt"))
        self.copy_pos_btn.setText("📋 " + t("workflow_copy_prompt"))
        self.neg_prompt_title.setText(t("workflow_neg_prompt"))
        self.copy_neg_btn.setText("📋 " + t("workflow_copy_prompt"))
        self.params_title.setText(t("workflow_params_title"))
        self.copy_params_btn.setText("📋 " + t("workflow_copy_params"))
        self.copy_seed_btn.setToolTip(t("workflow_copy_seed"))
        self.models_title.setText(t("workflow_used_models"))
