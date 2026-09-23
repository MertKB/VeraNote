# ui/agenda/agenda_view.py
from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal
from ui.agenda.calendar_widget import CalendarPanel
from ui.agenda.daily_note_panel import DailyNotePanel
from ui.agenda.tasks_panel import TasksPanel

class AgendaView(QWidget):
    """
    Main Agenda View containing 3 panels in a responsive QSplitter:
    - Left: CalendarPanel (QCalendarWidget with cell dots, Today button, midnight rollover)
    - Center: DailyNotePanel (Markdown editor with 500ms debounce autosave)
    - Right: TasksPanel (Task cards with checkbox toggle, priority badges, quick add)
    """
    date_selected = Signal(str)                  # ISO date 'YYYY-MM-DD'
    month_changed = Signal(int, int)             # year, month
    monthly_stats_requested = Signal(int, int)   # year, month
    note_autosave_requested = Signal(str, str)    # date_str, content
    task_add_requested = Signal(str, int, str)   # title, priority, due_date
    task_toggle_requested = Signal(int, int)     # task_id, is_completed
    task_delete_requested = Signal(int)          # task_id
    clear_completed_requested = Signal(str)      # date_str
    routines_dialog_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaPanel")
        self.current_date = ""

        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)

        # 3-Panel Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setObjectName("AgendaSplitter")
        self.splitter.setHandleWidth(6)

        # 1. Left: Calendar Panel
        self.calendar_panel = CalendarPanel(self)
        self.calendar_panel.date_selected.connect(self._on_calendar_date_selected)
        self.calendar_panel.month_changed.connect(self.month_changed.emit)
        self.calendar_panel.monthly_stats_requested.connect(self.monthly_stats_requested.emit)
        self.calendar_panel.upcoming_date_selected.connect(self._on_calendar_date_selected)
        self.calendar_panel.task_toggle_requested.connect(self.task_toggle_requested.emit)

        # 2. Middle: Daily Note Panel
        self.daily_note_panel = DailyNotePanel(self)
        self.daily_note_panel.note_autosave_requested.connect(self.note_autosave_requested.emit)

        # 3. Right: Tasks Panel
        self.tasks_panel = TasksPanel(self)
        self.tasks_panel.task_add_requested.connect(self.task_add_requested.emit)
        self.tasks_panel.task_toggle_requested.connect(self.task_toggle_requested.emit)
        self.tasks_panel.task_delete_requested.connect(self.task_delete_requested.emit)
        self.tasks_panel.clear_completed_requested.connect(self.clear_completed_requested.emit)
        self.tasks_panel.routines_dialog_requested.connect(self.routines_dialog_requested.emit)

        self.splitter.addWidget(self.calendar_panel)
        self.splitter.addWidget(self.daily_note_panel)
        self.splitter.addWidget(self.tasks_panel)

        # Set stretch factors: Calendar (0), Note (1, flex), Tasks (0)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.splitter.setCollapsible(2, False)

        # Initial sizes
        self.splitter.setSizes([300, 560, 340])

        main_layout.addWidget(self.splitter)

    def _on_calendar_date_selected(self, date_str: str):
        # Flush pending note save on previous date if any
        self.daily_note_panel.flush_save()
        self.current_date = date_str
        self.date_selected.emit(date_str)

    def set_date_data(self, date_str: str, note_content: str, tasks_list: list):
        """Update both middle (Daily Note) and right (Tasks) panels for the selected date."""
        self.current_date = date_str
        self.calendar_panel.select_date(date_str)
        self.daily_note_panel.load_note(date_str, note_content)
        self.tasks_panel.set_tasks(tasks_list, date_str)

    def set_indicators(self, indicators: dict):
        """Update calendar cell dots for month."""
        self.calendar_panel.set_indicators(indicators)

    def set_monthly_stats(self, stats: dict):
        """Update the metrics cards in the calendar's monthly summary panel."""
        self.calendar_panel.set_monthly_stats(stats)

    def set_calendar_theme(self, theme_config: dict):
        """Update the calendar's theme colors dynamically."""
        self.calendar_panel.set_theme_config(theme_config)

    def set_upcoming_tasks(self, tasks_list: list):
        """Update upcoming tasks mini list in calendar panel."""
        self.calendar_panel.set_upcoming_tasks(tasks_list)

    def set_tasks(self, tasks_list: list, date_str: str = None):
        """Update only the tasks panel (e.g. after adding, deleting, toggling tasks)."""
        target_date = date_str or self.current_date
        self.tasks_panel.set_tasks(tasks_list, target_date)

    def flush_pending_saves(self):
        """Flush any pending note save before changing views or closing."""
        self.daily_note_panel.flush_save()

    def retranslate_ui(self):
        self.calendar_panel.retranslate_ui()
        self.daily_note_panel.retranslate_ui()
        self.tasks_panel.retranslate_ui()
