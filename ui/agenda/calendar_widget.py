# ui/agenda/calendar_widget.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, QDate, Signal, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont
from utils.i18n import t

class CustomCalendarWidget(QCalendarWidget):
    """
    Subclassed QCalendarWidget that overrides paintCell to show dots/indicators
    for days that have daily notes or pending tasks.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaCalendarWidget")
        self.indicators = {}  # date_str -> {'has_note': bool, 'pending_tasks': int, 'completed_tasks': int}
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setGridVisible(False)

    def set_indicators(self, indicators: dict):
        """Update indicators and repaint cells."""
        self.indicators = indicators or {}
        self.update()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        # 1. Base calendar cell rendering
        super().paintCell(painter, rect, date)

        date_str = date.toString("yyyy-MM-dd")
        today = QDate.currentDate()
        is_today = (date == today)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Subtle highlight border for Today if not currently selected
        if is_today and date != self.selectedDate():
            pen = QPen(QColor("#60A5FA"), 1.5, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

        # Visual Indicators (Dots) near bottom of cell
        info = self.indicators.get(date_str)
        if info:
            has_note = info.get('has_note', False)
            pending_count = info.get('pending_tasks', 0)
            completed_count = info.get('completed_tasks', 0)

            dots = []
            if pending_count > 0:
                dots.append(QColor("#F59E0B"))  # Amber for pending tasks
            if has_note:
                dots.append(QColor("#38BDF8"))  # Light Blue for daily notes
            elif completed_count > 0 and pending_count == 0:
                dots.append(QColor("#10B981"))  # Emerald Green for all completed

            if dots:
                dot_size = 4.5
                spacing = 3.0
                total_w = len(dots) * dot_size + (len(dots) - 1) * spacing
                start_x = rect.center().x() - total_w / 2.0
                y = rect.bottom() - 5.5

                painter.setPen(Qt.NoPen)
                for i, color in enumerate(dots):
                    painter.setBrush(QBrush(color))
                    x = start_x + i * (dot_size + spacing)
                    painter.drawEllipse(QRectF(x, y, dot_size, dot_size))

        painter.restore()


class CalendarPanel(QFrame):
    """
    Calendar sidebar panel containing the custom calendar, Today button,
    legend and midnight timer for date rollover.
    """
    date_selected = Signal(str)        # ISO date 'YYYY-MM-DD'
    month_changed = Signal(int, int)   # year, month

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaSectionContainer")
        self.init_ui()
        self.setup_midnight_timer()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Title
        self.title_label = QLabel(t("agenda_calendar_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 15px; font-weight: bold; padding: 2px 4px;")
        layout.addWidget(self.title_label)

        # Calendar Widget
        self.calendar = CustomCalendarWidget(self)
        self.calendar.clicked.connect(self._on_cell_clicked)
        self.calendar.currentPageChanged.connect(self._on_page_changed)
        layout.addWidget(self.calendar)

        # Today Button & Action Bar
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(4, 4, 4, 4)
        action_layout.setSpacing(8)

        self.today_btn = QPushButton(f"🎯  {t('agenda_today_btn')}")
        self.today_btn.setObjectName("NewLibBtn")
        self.today_btn.setFixedHeight(34)
        self.today_btn.setCursor(Qt.PointingHandCursor)
        self.today_btn.clicked.connect(self.go_to_today)
        action_layout.addWidget(self.today_btn)

        layout.addLayout(action_layout)

        # Indicators Legend
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(6, 2, 6, 2)
        legend_layout.setSpacing(12)

        def make_legend_item(color_hex, label_text):
            row = QHBoxLayout()
            row.setSpacing(5)
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color_hex}; border-radius: 4px;")
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #9AA0A6; font-size: 11px;")
            row.addWidget(dot)
            row.addWidget(lbl)
            return row

        self.legend_task_lbl = make_legend_item("#F59E0B", t("agenda_tasks_title"))
        self.legend_note_lbl = make_legend_item("#38BDF8", t("agenda_daily_note_title"))

        legend_layout.addLayout(self.legend_task_lbl)
        legend_layout.addLayout(self.legend_note_lbl)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        layout.addStretch()

    def setup_midnight_timer(self):
        """Lightweight timer checking for midnight date change every 60 seconds."""
        self._last_date = QDate.currentDate()
        self.midnight_timer = QTimer(self)
        self.midnight_timer.setInterval(60000)
        self.midnight_timer.timeout.connect(self._check_midnight_rollover)
        self.midnight_timer.start()

    def _check_midnight_rollover(self):
        current = QDate.currentDate()
        if current != self._last_date:
            self._last_date = current
            self.calendar.update()
            if self.calendar.selectedDate() == self._last_date.addDays(-1):
                self.go_to_today()

    def _on_cell_clicked(self, date: QDate):
        self.date_selected.emit(date.toString("yyyy-MM-dd"))

    def _on_page_changed(self, year: int, month: int):
        self.month_changed.emit(year, month)

    def go_to_today(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.calendar.setCurrentPage(today.year(), today.month())
        self.date_selected.emit(today.toString("yyyy-MM-dd"))

    def set_indicators(self, indicators: dict):
        self.calendar.set_indicators(indicators)

    def select_date(self, date_str: str):
        try:
            qdate = QDate.fromString(date_str, "yyyy-MM-dd")
            if qdate.isValid():
                self.calendar.setSelectedDate(qdate)
                self.calendar.setCurrentPage(qdate.year(), qdate.month())
        except Exception:
            pass

    def get_selected_date_str(self) -> str:
        return self.calendar.selectedDate().toString("yyyy-MM-dd")

    def retranslate_ui(self):
        self.title_label.setText(t("agenda_calendar_title"))
        self.today_btn.setText(f"🎯  {t('agenda_today_btn')}")
