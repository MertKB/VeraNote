# ui/agenda/routine_manager_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QLineEdit, QComboBox, QCheckBox, 
                              QScrollArea, QFrame, QWidget)
from PySide6.QtCore import Qt, Signal
from utils.i18n import t

PRIORITY_CONFIG = {
    0: {"name_key": "agenda_priority_low", "bg": "#1E293B", "text": "#94A3B8", "border": "#334155"},
    1: {"name_key": "agenda_priority_normal", "bg": "#064E3B", "text": "#34D399", "border": "#059669"},
    2: {"name_key": "agenda_priority_high", "bg": "#78350F", "text": "#FBBF24", "border": "#D97706"},
    3: {"name_key": "agenda_priority_urgent", "bg": "#7F1D1D", "text": "#F87171", "border": "#DC2626"},
}

class RoutineItemWidget(QFrame):
    """Row item representing a single recurring routine."""
    toggle_requested = Signal(int, int)   # routine_id, is_active
    delete_requested = Signal(int)        # routine_id

    def __init__(self, routine_data: dict, parent=None):
        super().__init__(parent)
        self.routine_data = routine_data
        self.routine_id = routine_data.get('id')
        self.setObjectName("RoutineItemWidget")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        is_active = bool(self.routine_data.get('is_active', 1))

        # Active Toggle Checkbox
        self.active_check = QCheckBox()
        self.active_check.setChecked(is_active)
        self.active_check.setToolTip(t("agenda_routine_status_active") if is_active else t("agenda_routine_status_inactive"))
        self.active_check.setCursor(Qt.PointingHandCursor)
        self.active_check.toggled.connect(self._on_toggled)
        layout.addWidget(self.active_check)

        # Title Label
        self.title_label = QLabel(self.routine_data.get('title', ''))
        self.title_label.setWordWrap(True)
        self._apply_title_style(is_active)
        layout.addWidget(self.title_label, 1)

        # Frequency Badge
        freq = self.routine_data.get('frequency', 'daily')
        freq_text = t("agenda_routine_freq_daily") if freq == 'daily' else t("agenda_routine_freq_weekdays")
        freq_badge = QLabel(freq_text)
        freq_badge.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            border: 1px solid #0284C7;
            border-radius: 9px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: bold;
        """)
        layout.addWidget(freq_badge)

        # Priority Badge
        priority = self.routine_data.get('priority', 1)
        cfg = PRIORITY_CONFIG.get(priority, PRIORITY_CONFIG[1])
        priority_badge = QLabel(t(cfg["name_key"]))
        priority_badge.setStyleSheet(f"""
            background-color: {cfg['bg']};
            color: {cfg['text']};
            border: 1px solid {cfg['border']};
            border-radius: 9px;
            padding: 2px 7px;
            font-size: 10px;
            font-weight: bold;
        """)
        layout.addWidget(priority_badge)

        # Delete Button
        self.delete_btn = QPushButton()
        from utils.icon_manager import get_icon
        self.delete_btn.setIcon(get_icon("trash", "#C02E26", 14))
        self.delete_btn.setToolTip(t("agenda_routine_delete_tooltip"))
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
                background-color: #DC2626;
                color: #FFFFFF;
            }
        """)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.routine_id))
        layout.addWidget(self.delete_btn)

        self.setStyleSheet("""
            QFrame {
                background-color: #1E1F22;
                border: 1px solid #2F3136;
                border-radius: 8px;
            }
            QFrame:hover {
                border-color: #4B5563;
            }
        """)

    def _apply_title_style(self, is_active: bool):
        if is_active:
            self.title_label.setStyleSheet("color: #E3E3E3; font-size: 13px; font-weight: 500;")
        else:
            self.title_label.setStyleSheet("color: #71717A; font-size: 13px; text-decoration: line-through;")

    def _on_toggled(self, checked: bool):
        self._apply_title_style(checked)
        self.toggle_requested.emit(self.routine_id, 1 if checked else 0)


class RoutineManagerDialog(QDialog):
    """
    Modal dialog to view, add, toggle, and delete recurring routines.
    Completely isolated from database layer; communicates via Qt Signals.
    """
    routine_add_requested = Signal(str, str, int)    # title, frequency, priority
    routine_toggle_requested = Signal(int, int)      # routine_id, is_active
    routine_delete_requested = Signal(int)           # routine_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("agenda_routines_dialog_title"))
        self.setMinimumSize(540, 480)
        self.resize(580, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #18191C;
                color: #E3E3E3;
            }
        """)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Header Title and Description
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title_lbl = QLabel(t('agenda_routines_dialog_title'))
        title_lbl.setStyleSheet("color: #E3E3E3; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(title_lbl)

        desc_lbl = QLabel(t("agenda_routines_desc"))
        desc_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        header_layout.addWidget(desc_lbl)

        main_layout.addLayout(header_layout)

        # Scroll Area for Routines List
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: 1px solid #2F3136;
                border-radius: 8px;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
        """)

        self.list_container = QWidget()
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Empty State Label
        self.empty_label = QLabel(t("agenda_routine_empty"))
        self.empty_label.setStyleSheet("color: #71717A; font-size: 12px; font-style: italic; padding: 24px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.empty_label)

        # Add Routine Form Box
        add_frame = QFrame()
        add_frame.setStyleSheet("""
            QFrame {
                background-color: #1E1F22;
                border: 1px solid #2F3136;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        add_layout = QVBoxLayout(add_frame)
        add_layout.setContentsMargins(8, 8, 8, 8)
        add_layout.setSpacing(8)

        # Row 1: Routine Title
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(t("agenda_routine_title_placeholder"))
        self.title_input.setStyleSheet("""
            QLineEdit {
                background-color: #282A2E;
                color: #E3E3E3;
                border: 1px solid #3F4248;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
            }
        """)
        self.title_input.returnPressed.connect(self._on_add_clicked)
        add_layout.addWidget(self.title_input)

        # Row 2: Frequency, Priority, and Add Button
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(8)

        self.freq_combo = QComboBox()
        self.freq_combo.setStyleSheet("""
            QComboBox {
                background-color: #282A2E;
                color: #E3E3E3;
                border: 1px solid #3F4248;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
        """)
        self.freq_combo.addItem(t('agenda_routine_freq_daily'), "daily")
        self.freq_combo.addItem(t('agenda_routine_freq_weekdays'), "weekdays")
        row2_layout.addWidget(self.freq_combo)

        self.priority_combo = QComboBox()
        self.priority_combo.setStyleSheet("""
            QComboBox {
                background-color: #282A2E;
                color: #E3E3E3;
                border: 1px solid #3F4248;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
        """)
        self.priority_combo.addItem(t('agenda_priority_normal'), 1)
        self.priority_combo.addItem(t('agenda_priority_low'), 0)
        self.priority_combo.addItem(t('agenda_priority_high'), 2)
        self.priority_combo.addItem(t('agenda_priority_urgent'), 3)
        row2_layout.addWidget(self.priority_combo)

        row2_layout.addStretch()

        self.add_btn = QPushButton(t("agenda_routine_add_btn"))
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedHeight(30)
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366F1;
                color: #FFFFFF;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        self.add_btn.clicked.connect(self._on_add_clicked)
        row2_layout.addWidget(self.add_btn)

        add_layout.addLayout(row2_layout)
        main_layout.addWidget(add_frame)

        # Footer Buttons
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        close_btn = QPushButton(t("agenda_close_btn"))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2F3136;
                color: #E3E3E3;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
            }
            QPushButton:hover {
                background-color: #3F4248;
            }
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        main_layout.addLayout(footer_layout)

    def set_routines(self, routines: list):
        """Populate the dialog with routine items."""
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not routines:
            self.empty_label.show()
            self.scroll_area.hide()
        else:
            self.empty_label.hide()
            self.scroll_area.show()

            for r_data in routines:
                item_widget = RoutineItemWidget(r_data, self)
                item_widget.toggle_requested.connect(self.routine_toggle_requested.emit)
                item_widget.delete_requested.connect(self.routine_delete_requested.emit)
                self.list_layout.insertWidget(self.list_layout.count() - 1, item_widget)

    def _on_add_clicked(self):
        title = self.title_input.text().strip()
        if not title:
            return
        freq = self.freq_combo.currentData() or "daily"
        priority = self.priority_combo.currentData()
        if priority is None:
            priority = 1
        self.title_input.clear()
        self.routine_add_requested.emit(title, freq, priority)
