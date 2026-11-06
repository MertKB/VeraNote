# ui/workflow_builder_dialog.py
"""
Workflow Builder dialog wrapper for VeraNote.
Wraps WorkflowBuilderView for modal dialog use if needed.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt
from utils.i18n import t
from utils.icon_manager import get_icon
from ui.workflow_builder_view import ImageDropArea, WorkflowBuilderView


class WorkflowBuilderDialog(QDialog):
    """
    QDialog wrapper that hosts WorkflowBuilderView.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkflowBuilderDialog")
        self.setWindowTitle(t("workflow_builder_title"))

        icon = get_icon("builder", "#8AB4F8", 24)
        if not icon.isNull():
            self.setWindowIcon(icon)

        self.resize(920, 720)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = WorkflowBuilderView(self)
        layout.addWidget(self.view)

        # Expose attributes directly for convenience and test compatibility
        self.drop_area = self.view.drop_area
        self.export_json_btn = self.view.export_json_btn
        self.export_png_btn = self.view.export_png_btn
        self.ckpt_combo = self.view.ckpt_combo
        self.lora_combo = self.view.lora_combo
        self.pos_edit = self.view.pos_edit
        self.neg_edit = self.view.neg_edit
        self.seed_edit = self.view.seed_edit
        self.steps_spin = self.view.steps_spin
        self.cfg_spin = self.view.cfg_spin
        self.denoise_spin = self.view.denoise_spin

    def on_metadata_detected(self, meta: dict):
        self.view.on_metadata_detected(meta)

    def get_form_parameters(self) -> dict:
        return self.view.get_form_parameters()
