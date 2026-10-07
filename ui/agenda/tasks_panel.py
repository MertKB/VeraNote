# ui/agenda/tasks_panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QComboBox, QCheckBox, 
                             QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from utils.i18n import t

PRIORITY_CONFIG = {
    0: {"name_key": "agenda_priority_low", "bg": "#1E293B", "text": "#94A3B8", "border": "#334155"},
    1: {"name_key": "agenda_priority_normal", "bg": "#064E3B", "text": "#34D399", "border": "#059669"},
    2: {"name_key": "agenda_priority_high", "bg": "#78350F", "text": "#FBBF24", "border": "#D97706"},
    3: {"name_key": "agenda_priority_urgent", "bg": "#7F1D1D", "text": "#F87171", "border": "#DC2626"},
}

class TaskCardWidget(QFrame):
    """Card widget for a single task item."""
    toggle_requested = Signal(int, int)  # task_id, is_completed
    delete_requested = Signal(int)       # task_id

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.task_id = task_data.get('id')
        self.setObjectName("TaskItemWidget")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        is_completed = bool(self.task_data.get('is_completed', 0))

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(is_completed)
        self.checkbox.setCursor(Qt.PointingHandCursor)
        self.checkbox.toggled.connect(self._on_toggled)
        layout.addWidget(self.checkbox)

        # Title
        self.title_label = QLabel(self.task_data.get('title', ''))
        self.title_label.setWordWrap(True)
        self._apply_title_style(is_completed)
        layout.addWidget(self.title_label, 1)

        # Priority Pill
        priority = self.task_data.get('priority', 1)
        cfg = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG[1])
        self.priority_pill = QLabel(t(cfg["name_key"]))
        self.priority_pill.setObjectName("PriorityPill")
        self.priority_pill.setStyleSheet(f"""
            background-color: {cfg['bg']};
            color: {cfg['text']};
            border: 1px solid {cfg['border']};
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        layout.addWidget(self.priority_pill)

        # Delete Button
        self.delete_btn = QPushButton()
        from utils.icon_manager import get_icon
        self.delete_btn.setIcon(get_icon("trash", "#C02E26", 14))
        self.delete_btn.setObjectName("TaskDeleteBtn")
        self.delete_btn.setToolTip(t("agenda_delete_task_tooltip"))
        self.delete_btn.setFixedSize(26, 26)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3B1818;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.task_id))
        layout.addWidget(self.delete_btn)

        self.setProperty("completed", "true" if is_completed else "false")

    def _apply_title_style(self, is_completed: bool):
        font = self.title_label.font()
        font.setStrikeOut(is_completed)
        self.title_label.setFont(font)
        if is_completed:
            self.title_label.setStyleSheet("color: #71717A; font-size: 13px;")
        else:
            self.title_label.setStyleSheet("color: #E3E3E3; font-size: 13px; font-weight: 500;")

    def _on_toggled(self, checked: bool):
        new_val = 1 if checked else 0
        self._apply_title_style(checked)
        self.setProperty("completed", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.toggle_requested.emit(self.task_id, new_val)


class TasksPanel(QFrame):
    """
    Right panel: Task management for the selected day,
    with checkbox completion toggle, priority badges, routines management,
    clear completed tasks, and fixed bottom quick-add bar.
    """
    task_add_requested = Signal(str, int, str)   # title, priority, due_date
    task_toggle_requested = Signal(int, int)     # task_id, is_completed
    task_delete_requested = Signal(int)          # task_id
    clear_completed_requested = Signal(str)      # date_str
    routines_dialog_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaSectionContainer")
        self.current_date = ""
        self.tasks_list = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Title, Count Badge & Action Buttons
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.title_label = QLabel(t("agenda_tasks_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 15px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        self.count_badge = QLabel("0")
        self.count_badge.setObjectName("AllNotesBadge")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setFixedSize(26, 20)
        header_layout.addWidget(self.count_badge)

        header_layout.addStretch()

        # Clear Completed Tasks Button
        self.clear_completed_btn = QPushButton(t("agenda_clear_completed_btn"))
        self.clear_completed_btn.setToolTip(t("agenda_clear_completed_tooltip"))
        self.clear_completed_btn.setCursor(Qt.PointingHandCursor)
        self.clear_completed_btn.setFixedHeight(26)
        self.clear_completed_btn.setStyleSheet("""
            QPushButton {
                background-color: #282A2E;
                color: #94A3B8;
                border: 1px solid #3F4248;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3B1818;
                color: #F87171;
                border-color: #7F1D1D;
            }
        """)
        self.clear_completed_btn.clicked.connect(self._on_clear_completed_clicked)
        header_layout.addWidget(self.clear_completed_btn)

        # Routines Management Button
        self.routines_btn = QPushButton(t("agenda_routines_btn"))
        self.routines_btn.setToolTip(t("agenda_routines_desc"))
        self.routines_btn.setCursor(Qt.PointingHandCursor)
        self.routines_btn.setFixedHeight(26)
        self.routines_btn.setStyleSheet("""
            QPushButton {
                background-color: #312E81;
                color: #A5B4FC;
                border: 1px solid #4338CA;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3730A3;
                color: #FFFFFF;
                border-color: #6366F1;
            }
        """)
        self.routines_btn.clicked.connect(self.routines_dialog_requested.emit)
        header_layout.addWidget(self.routines_btn)

        layout.addLayout(header_layout)

        # Scroll Area for Task Cards (Stretches to fill space)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        self.tasks_container = QWidget()
        self.tasks_container.setStyleSheet("background: transparent;")
        self.tasks_layout = QVBoxLayout(self.tasks_container)
        self.tasks_layout.setContentsMargins(0, 4, 0, 4)
        self.tasks_layout.setSpacing(8)

        # Empty State Label inside container
        self.empty_label = QLabel(t("agenda_tasks_empty"))
        self.empty_label.setStyleSheet("color: #71717A; font-size: 13px; font-style: italic; padding: 40px 10px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.tasks_layout.addWidget(self.empty_label)

        self.tasks_layout.addStretch()

        self.scroll_area.setWidget(self.tasks_container)
        layout.addWidget(self.scroll_area, 1)

        # Quick Add Bar as Fixed Footer at Bottom
        quick_add_frame = QFrame()
        quick_add_frame.setStyleSheet("""
            QFrame {
                background-color: #1E1F22;
                border: 1px solid #2F3136;
                border-radius: 8px;
                padding: 4px;
            }
        """)
        quick_add_layout = QHBoxLayout(quick_add_frame)
        quick_add_layout.setContentsMargins(6, 4, 6, 4)
        quick_add_layout.setSpacing(8)

        # Task Title Input
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText(t("agenda_task_input_placeholder"))
        self.input_edit.setStyleSheet("background: transparent; border: none; color: #E3E3E3; font-size: 13px;")
        self.input_edit.returnPressed.connect(self._on_add_clicked)
        quick_add_layout.addWidget(self.input_edit, 1)

        # Priority Dropdown
        self.priority_combo = QComboBox()
        self.priority_combo.setStyleSheet("""
            QComboBox {
                background-color: #282A2E;
                color: #E3E3E3;
                border: 1px solid #3F4248;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self._populate_priority_combo()
        quick_add_layout.addWidget(self.priority_combo)

        # Add Button
        self.add_btn = QPushButton(t("agenda_add_task_btn"))
        self.add_btn.setObjectName("NewNoteBtn")
        self.add_btn.setFixedHeight(28)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_clicked)
        quick_add_layout.addWidget(self.add_btn)

        layout.addWidget(quick_add_frame)

    def _populate_priority_combo(self):
        self.priority_combo.clear()
        self.priority_combo.addItem(t('agenda_priority_normal'), 1)
        self.priority_combo.addItem(t('agenda_priority_low'), 0)
        self.priority_combo.addItem(t('agenda_priority_high'), 2)
        self.priority_combo.addItem(t('agenda_priority_urgent'), 3)
        self.priority_combo.setCurrentIndex(0)

    def _on_add_clicked(self):
        title = self.input_edit.text().strip()
        if not title:
            return
        priority = self.priority_combo.currentData()
        if priority is None:
            priority = 1
        due_date = self.current_date
        self.input_edit.clear()
        self.task_add_requested.emit(title, priority, due_date)

    def _on_clear_completed_clicked(self):
        from PySide6.QtWidgets import QMessageBox
        has_completed = any(t_item.get('is_completed', 0) for t_item in self.tasks_list)
        if not has_completed:
            return
        reply = QMessageBox.question(
            self,
            t("agenda_clear_completed_btn"),
            t("agenda_clear_completed_confirm"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.clear_completed_requested.emit(self.current_date)

    def set_tasks(self, tasks: list, current_date: str):
        """Populate the task list for the selected date."""
        self.current_date = current_date
        self.tasks_list = tasks or []

        # Remove existing task cards (keep empty_label at index 0 and stretch at end)
        # We find and delete all TaskCardWidget children
        for child in self.tasks_container.findChildren(TaskCardWidget):
            child.deleteLater()

        # Update count badge
        self.count_badge.setText(str(len(self.tasks_list)))

        # Update Clear Completed button state/visibility
        has_completed = any(t_item.get('is_completed', 0) for t_item in self.tasks_list)
        self.clear_completed_btn.setEnabled(has_completed)
        self.clear_completed_btn.setToolTip(t("agenda_clear_completed_tooltip") if has_completed else "")

        if not self.tasks_list:
            self.empty_label.show()
        else:
            self.empty_label.hide()
            for task_data in self.tasks_list:
                card = TaskCardWidget(task_data)
                card.toggle_requested.connect(self.task_toggle_requested.emit)
                card.delete_requested.connect(self._on_card_delete_requested)
                # Insert before the bottom stretch
                self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, card)

    def _on_card_delete_requested(self, task_id: int):
        self.task_delete_requested.emit(task_id)

    def retranslate_ui(self):
        self.title_label.setText(t("agenda_tasks_title"))
        self.empty_label.setText(t("agenda_tasks_empty"))
        self.input_edit.setPlaceholderText(t("agenda_task_input_placeholder"))
        self.add_btn.setText(t("agenda_add_task_btn"))
        self.clear_completed_btn.setText(t("agenda_clear_completed_btn"))
        self.routines_btn.setText(t("agenda_routines_btn"))
        self.routines_btn.setToolTip(t("agenda_routines_desc"))
        curr_idx = self.priority_combo.currentIndex()
        self._populate_priority_combo()
        if 0 <= curr_idx < self.priority_combo.count():
            self.priority_combo.setCurrentIndex(curr_idx)
