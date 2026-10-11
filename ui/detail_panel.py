"""
DetailPanel Coordinator Widget for VeraNote.
Coordinates model, note, and workflow detail sections via QStackedWidget.
Maintains 100% backward compatibility for all signals, properties, and methods.
"""
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QSizePolicy, QStackedWidget)
from PySide6.QtCore import Signal, Qt, QSize
from utils.i18n import t

from .detail.common import ZoomableTextEdit, FlowLayout, TriggerPillButton, TagPillWidget
from .detail.model_section import ModelSection
from .detail.note_section import NoteSection
from .detail.workflow_section import WorkflowSection


class DetailPanel(QWidget):
    """Modular coordinator panel delegating to ModelSection, NoteSection, or WorkflowSection."""
    close_requested = Signal()
    save_model_data_requested = Signal(int, str, str, str) # model_id, name, notes, base_architecture
    image_changed = Signal(int, str) # model_id, new_image_path
    add_trigger_requested = Signal(int, str) # model_id, word
    delete_trigger_requested = Signal(int, str) # model_id, word
    set_triggers_requested = Signal(int, list) # model_id, triggers_list
    add_tag_requested = Signal(int, str) # model_id, tag_name
    delete_tag_requested = Signal(int, str) # model_id, tag_name
    set_tags_requested = Signal(int, list) # model_id, tags_list
    delete_model_requested = Signal(int) # model_id
    save_note_requested = Signal(int, str, str, str, str, int, bool) # id, title, content, image_path, display_mode, is_fav, is_auto_save
    delete_note_requested = Signal(int) # note_id
    save_workflow_data_requested = Signal(int, str, str, str) # workflow_id, name, description, notes
    delete_workflow_requested = Signal(int) # workflow_id
    workflow_image_changed = Signal(int, str) # workflow_id, new_image_path
    corkboard_pin_toggled = Signal(int, bool)
    note_color_changed = Signal(int, str)
    associate_model_requested = Signal(int, int) # note_id, model_id
    dissociate_model_requested = Signal(int, int) # note_id, model_id
    add_note_tag_requested = Signal(int, str) # note_id, tag
    delete_note_tag_requested = Signal(int, str) # note_id, tag
    clear_note_tags_requested = Signal(int) # note_id
    set_note_notebook_requested = Signal(int, object) # note_id, notebook_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailPanelWidget")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(360)
        
        self.mode = "MODEL" # "MODEL", "NOTE", or "WORKFLOW"
        self.auto_save_settings = {"enabled": 1, "interval": 1.5}
        
        self.init_ui()

    @property
    def model_data(self):
        return self.model_section.model_data

    @model_data.setter
    def model_data(self, val):
        self.model_section.model_data = val

    @property
    def note_data(self):
        return self.note_section.note_data

    @note_data.setter
    def note_data(self, val):
        self.note_section.note_data = val

    @property
    def workflow_data(self):
        return self.workflow_section.workflow_data

    @workflow_data.setter
    def workflow_data(self, val):
        self.workflow_section.workflow_data = val

    @property
    def trigger_words(self):
        return self.model_section.trigger_words

    @trigger_words.setter
    def trigger_words(self, val):
        self.model_section.trigger_words = val

    @property
    def current_image_path(self):
        if self.mode == "MODEL":
            return self.model_section.current_image_path
        elif self.mode == "NOTE":
            return self.note_section.current_image_path
        elif self.mode == "WORKFLOW":
            return self.workflow_section.current_image_path
        return ""

    @current_image_path.setter
    def current_image_path(self, val):
        if self.mode == "MODEL":
            self.model_section.current_image_path = val
        elif self.mode == "NOTE":
            self.note_section.current_image_path = val
        elif self.mode == "WORKFLOW":
            self.workflow_section.current_image_path = val

    def minimumSizeHint(self):
        return QSize(360, 200)

    def sizeHint(self):
        return QSize(360, 800)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 10, 12, 10)
        self.main_layout.setSpacing(10)

        # Header: Title & Close button
        header_layout = QHBoxLayout()
        self.header_label = QLabel(t("detail_header_model"))
        self.header_label.setObjectName("DetailTitle")
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self.close_requested.emit)
        self.close_btn.hide()
        self.main_layout.addLayout(header_layout)

        # Scroll area enclosing the stacked widget
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        scroll_content.setMinimumWidth(0)
        scroll_content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 8, 0)
        self.scroll_layout.setSpacing(10)

        # QStackedWidget containing modular sections
        self.stack = QStackedWidget()

        # 1. Model Section
        self.model_section = ModelSection()
        self.model_section.save_model_data_requested.connect(self.save_model_data_requested.emit)
        self.model_section.add_trigger_requested.connect(self.add_trigger_requested.emit)
        self.model_section.delete_trigger_requested.connect(self.delete_trigger_requested.emit)
        self.model_section.set_triggers_requested.connect(self.set_triggers_requested.emit)
        self.model_section.add_tag_requested.connect(self.add_tag_requested.emit)
        self.model_section.delete_tag_requested.connect(self.delete_tag_requested.emit)
        self.model_section.set_tags_requested.connect(self.set_tags_requested.emit)
        self.model_section.image_changed.connect(self.image_changed.emit)
        self.model_section.delete_model_requested.connect(self.delete_model_requested.emit)
        self.stack.addWidget(self.model_section) # index 0

        # 2. Note Section
        self.note_section = NoteSection()
        self.note_section.save_note_requested.connect(self.save_note_requested.emit)
        self.note_section.corkboard_pin_toggled.connect(self.corkboard_pin_toggled.emit)
        self.note_section.note_color_changed.connect(self.note_color_changed.emit)
        self.note_section.delete_note_requested.connect(self.delete_note_requested.emit)
        self.note_section.associate_model_requested.connect(self.associate_model_requested.emit)
        self.note_section.dissociate_model_requested.connect(self.dissociate_model_requested.emit)
        self.note_section.add_note_tag_requested.connect(self.add_note_tag_requested.emit)
        self.note_section.delete_note_tag_requested.connect(self.delete_note_tag_requested.emit)
        self.note_section.clear_note_tags_requested.connect(self.clear_note_tags_requested.emit)
        self.note_section.set_note_notebook_requested.connect(self.set_note_notebook_requested.emit)
        self.stack.addWidget(self.note_section) # index 1

        # 3. Workflow Section
        self.workflow_section = WorkflowSection()
        self.workflow_section.save_workflow_data_requested.connect(self.save_workflow_data_requested.emit)
        self.workflow_section.delete_workflow_requested.connect(self.delete_workflow_requested.emit)
        self.workflow_section.workflow_image_changed.connect(self.workflow_image_changed.emit)
        self.stack.addWidget(self.workflow_section) # index 2

        self.scroll_layout.addWidget(self.stack)
        self.scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(self.scroll_area)

    def set_model(self, model_data, trigger_words):
        self.mode = "MODEL"
        self.header_label.setText(t("detail_header_model"))
        self.stack.setCurrentIndex(0)
        self.model_section.set_model(model_data, trigger_words)
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

    def set_note(self, note_data, all_models=None, all_notebooks=None):
        self.mode = "NOTE"
        self.header_label.setText(t("detail_header_note"))
        self.stack.setCurrentIndex(1)
        self.note_section.set_note(note_data, all_models, auto_save_settings=self.auto_save_settings, all_notebooks=all_notebooks)
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

    def set_workflow(self, workflow_data):
        self.mode = "WORKFLOW"
        self.header_label.setText(t("detail_header_workflow"))
        self.stack.setCurrentIndex(2)
        self.workflow_section.set_workflow(workflow_data)
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

    def sync_auto_save_settings(self, enabled, interval):
        self.auto_save_settings = {"enabled": int(enabled), "interval": float(interval)}
        self.note_section.sync_auto_save_settings(enabled, interval)

    def update_image(self, image_path=None):
        if self.mode == "MODEL":
            self.model_section.update_image(image_path)
        elif self.mode == "NOTE":
            self.note_section.update_image(image_path)
        elif self.mode == "WORKFLOW":
            self.workflow_section.update_image(image_path)

    def retranslate_ui(self):
        if self.mode == "MODEL":
            self.header_label.setText(t("detail_header_model"))
        elif self.mode == "NOTE":
            self.header_label.setText(t("detail_header_note"))
        elif self.mode == "WORKFLOW":
            self.header_label.setText(t("detail_header_workflow"))
            
        self.model_section.retranslate_ui()
        self.note_section.retranslate_ui()
        self.workflow_section.retranslate_ui()

    def apply_theme(self, palette: dict):
        if not palette:
            return
        if hasattr(self.model_section, 'apply_theme'):
            self.model_section.apply_theme(palette)
        if hasattr(self.note_section, 'apply_theme'):
            self.note_section.apply_theme(palette)
        if hasattr(self.workflow_section, 'apply_theme'):
            self.workflow_section.apply_theme(palette)
