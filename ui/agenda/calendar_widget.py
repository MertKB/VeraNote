# ui/agenda/calendar_widget.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QCalendarWidget,
    QPushButton, QLabel, QFrame, QProgressBar, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QTextCharFormat
from utils.i18n import t

# ---------------------------------------------------------------------------
# Centralized Default Calendar Theming Configuration
# ---------------------------------------------------------------------------
DEFAULT_CALENDAR_THEME = {
    # Cell Backgrounds
    "cell_bg_normal": "transparent",
    "cell_bg_other_month": "transparent",
    "cell_bg_hover": "#25272C",
    "cell_bg_today": "transparent",
    
    # Selection
    "selection_bg": "#4338CA",         # Accent fill
    "selection_border": "#818CF8",     # Accent border
    "selection_text": "#FFFFFF",       # Selected day text
    
    # Today Indicator
    "today_border": "#60A5FA",
    
    # Day Number Texts
    "text_weekday": "#CBD5E1",         # Soft light slate for Mon-Fri
    "text_weekend": "#FB7185",         # Soft rose/coral for Sat-Sun (not harsh red)
    "text_other_month": "#52525B",     # Dimmed slate for out-of-month days
    
    # Column Headers (Mon-Sun)
    "header_weekday": "#9AA0A6",       # Muted gray for Mon-Fri headers
    "header_weekend": "#F472B6",       # Gentle rose tone for Sat-Sun headers
    
    # Status Dots / Accents
    "dot_pending_tasks": "#F59E0B",    # Amber
    "dot_completed_tasks": "#10B981",  # Emerald Green
    "dot_daily_note": "#38BDF8",       # Light Sky Blue
}


class CustomCalendarWidget(QCalendarWidget):
    """
    Subclassed QCalendarWidget with:
    1. Dynamic theme configuration (colors for cells, weekends, weekdays, selection).
    2. Overridden paintCell ensuring weekend detection without hardcoded pure red.
    3. Status dots indicating pending tasks, completed tasks, and daily notes.
    """
    def __init__(self, parent=None, theme_config: dict = None):
        super().__init__(parent)
        self.setObjectName("AgendaCalendarWidget")
        self.indicators = {}  # date_str -> {'has_note': bool, 'pending_tasks': int, 'completed_tasks': int}
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setGridVisible(False)
        
        # Load theme configuration
        self.theme = dict(DEFAULT_CALENDAR_THEME)
        if theme_config:
            self.theme.update(theme_config)
        self._apply_header_formats()

    def set_theme_config(self, theme_config: dict):
        """Update active calendar colors dynamically and repaint."""
        if not theme_config:
            return
        self.theme.update(theme_config)
        self._apply_header_formats()
        self.update()

    def _apply_header_formats(self):
        """Apply weekday & weekend header colors based on active theme configuration."""
        weekday_fmt = QTextCharFormat()
        weekday_fmt.setForeground(QColor(self.theme.get("header_weekday", "#9AA0A6")))

        weekend_fmt = QTextCharFormat()
        weekend_fmt.setForeground(QColor(self.theme.get("header_weekend", "#F472B6")))

        # Qt: 1 = Monday ... 5 = Friday, 6 = Saturday, 7 = Sunday
        for day in (Qt.Monday, Qt.Tuesday, Qt.Wednesday, Qt.Thursday, Qt.Friday):
            self.setWeekdayTextFormat(day, weekday_fmt)
        self.setWeekdayTextFormat(Qt.Saturday, weekend_fmt)
        self.setWeekdayTextFormat(Qt.Sunday, weekend_fmt)

    def set_indicators(self, indicators: dict):
        """Update indicators and repaint cells."""
        self.indicators = indicators or {}
        self.update()

    def paintCell(self, painter: QPainter, rect, date: QDate):
        """
        Custom cell painting ensuring theme colors are strictly honored:
        - Non-interfering background
        - Selected day pill highlight
        - Today highlight border
        - Configurable weekday vs. weekend text colors
        - Multi-indicator dots near the bottom
        """
        is_current_month = (date.month() == self.monthShown() and date.year() == self.yearShown())
        today = QDate.currentDate()
        is_today = (date == today)
        is_selected = (date == self.selectedDate())
        is_weekend = (date.dayOfWeek() in (6, 7))

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Custom Cell Background
        if not is_current_month:
            bg_col = QColor(self.theme.get("cell_bg_other_month", "transparent"))
            if bg_col.alpha() > 0:
                painter.fillRect(rect, bg_col)
        else:
            bg_col = QColor(self.theme.get("cell_bg_normal", "transparent"))
            if bg_col.alpha() > 0:
                painter.fillRect(rect, bg_col)

        # 2. Selected Date Pill Highlight
        if is_selected:
            pill_rect = rect.adjusted(3, 3, -3, -3)
            sel_border = QColor(self.theme.get("selection_border", "#818CF8"))
            sel_bg = QColor(self.theme.get("selection_bg", "#4338CA"))
            painter.setPen(QPen(sel_border, 1.5))
            painter.setBrush(QBrush(sel_bg))
            painter.drawRoundedRect(pill_rect, 7, 7)

            # Draw day number in crisp selection text color
            painter.setPen(QColor(self.theme.get("selection_text", "#FFFFFF")))
            f = painter.font()
            f.setBold(True)
            painter.setFont(f)
            text_rect = rect.adjusted(0, -3, 0, -3)
            painter.drawText(text_rect, Qt.AlignCenter, str(date.day()))

        # 3. Non-Selected Date Cell
        else:
            # Subtle highlight border for Today
            if is_today:
                pen = QPen(QColor(self.theme.get("today_border", "#60A5FA")), 1.5, Qt.SolidLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

            # Determine Day Number Text Color from Theme Config
            if not is_current_month:
                text_col = QColor(self.theme.get("text_other_month", "#52525B"))
            elif is_weekend:
                text_col = QColor(self.theme.get("text_weekend", "#FB7185"))
            else:
                text_col = QColor(self.theme.get("text_weekday", "#CBD5E1"))

            painter.setPen(text_col)
            f = painter.font()
            f.setBold(is_today)
            painter.setFont(f)
            text_rect = rect.adjusted(0, -3, 0, -3)
            painter.drawText(text_rect, Qt.AlignCenter, str(date.day()))

        # 4. Status Dots (Indicators) near bottom of cell
        date_str = date.toString("yyyy-MM-dd")
        info = self.indicators.get(date_str)
        if info:
            has_note = info.get('has_note', False)
            pending_count = info.get('pending_tasks', 0)
            completed_count = info.get('completed_tasks', 0)

            dots = []
            if pending_count > 0:
                dots.append(QColor(self.theme.get("dot_pending_tasks", "#F59E0B")))
            if has_note:
                dots.append(QColor(self.theme.get("dot_daily_note", "#38BDF8")))
            elif completed_count > 0 and pending_count == 0:
                dots.append(QColor(self.theme.get("dot_completed_tasks", "#10B981")))

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


# ---------------------------------------------------------------------------
# Monthly Summary & Metrics Panel (2x2 Compact Cards)
# ---------------------------------------------------------------------------
class MonthlySummaryPanel(QFrame):
    """
    Compact 2x2 grid panel displayed below the calendar and status legend.
    Shows monthly progress, active days, streak, and overall score for the selected month.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaMonthlySummaryPanel")
        self.current_year = QDate.currentDate().year()
        self.current_month = QDate.currentDate().month()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Header Title
        self.header_label = QLabel(t("agenda_monthly_summary_title"))
        self.header_label.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;")
        main_layout.addWidget(self.header_label)

        # 2x2 Grid Layout
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(6)

        # Card 1: Task Completion
        self.card_tasks = QFrame()
        self.card_tasks.setObjectName("AgendaMetricCard")
        tasks_layout = QVBoxLayout(self.card_tasks)
        tasks_layout.setContentsMargins(6, 6, 6, 6)
        tasks_layout.setSpacing(2)

        self.lbl_tasks_title = QLabel(f"🎯 {t('agenda_metric_tasks')}")
        self.lbl_tasks_title.setObjectName("AgendaMetricTitle")
        self.lbl_tasks_val = QLabel("0/0 - %0")
        self.lbl_tasks_val.setObjectName("AgendaMetricValue")
        
        self.tasks_progress = QProgressBar()
        self.tasks_progress.setObjectName("AgendaMetricProgress")
        self.tasks_progress.setFixedHeight(4)
        self.tasks_progress.setTextVisible(False)
        self.tasks_progress.setRange(0, 100)
        self.tasks_progress.setValue(0)

        tasks_layout.addWidget(self.lbl_tasks_title)
        tasks_layout.addWidget(self.lbl_tasks_val)
        tasks_layout.addWidget(self.tasks_progress)
        grid.addWidget(self.card_tasks, 0, 0)

        # Card 2: Active Note Days
        self.card_notes = QFrame()
        self.card_notes.setObjectName("AgendaMetricCard")
        notes_layout = QVBoxLayout(self.card_notes)
        notes_layout.setContentsMargins(6, 6, 6, 6)
        notes_layout.setSpacing(2)

        self.lbl_notes_title = QLabel(f"📝 {t('agenda_metric_notes')}")
        self.lbl_notes_title.setObjectName("AgendaMetricTitle")
        self.lbl_notes_val = QLabel(f"0/30 {t('agenda_days_unit')}")
        self.lbl_notes_val.setObjectName("AgendaMetricValue")
        self.lbl_notes_sub = QLabel("%0 Aktif")
        self.lbl_notes_sub.setObjectName("AgendaMetricSub")

        notes_layout.addWidget(self.lbl_notes_title)
        notes_layout.addWidget(self.lbl_notes_val)
        notes_layout.addWidget(self.lbl_notes_sub)
        grid.addWidget(self.card_notes, 0, 1)

        # Card 3: Streak (Kesintisiz Seri)
        self.card_streak = QFrame()
        self.card_streak.setObjectName("AgendaMetricCard")
        streak_layout = QVBoxLayout(self.card_streak)
        streak_layout.setContentsMargins(6, 6, 6, 6)
        streak_layout.setSpacing(2)

        self.lbl_streak_title = QLabel(f"🔥 {t('agenda_metric_streak')}")
        self.lbl_streak_title.setObjectName("AgendaMetricTitle")
        self.lbl_streak_val = QLabel(f"0 {t('agenda_streak_unit')}")
        self.lbl_streak_val.setObjectName("AgendaMetricValue")
        self.lbl_streak_sub = QLabel("Aralıksız Seri")
        self.lbl_streak_sub.setObjectName("AgendaMetricSub")

        streak_layout.addWidget(self.lbl_streak_title)
        streak_layout.addWidget(self.lbl_streak_val)
        streak_layout.addWidget(self.lbl_streak_sub)
        grid.addWidget(self.card_streak, 1, 0)

        # Card 4: Monthly Productivity / Score
        self.card_prod = QFrame()
        self.card_prod.setObjectName("AgendaMetricCard")
        prod_layout = QVBoxLayout(self.card_prod)
        prod_layout.setContentsMargins(6, 6, 6, 6)
        prod_layout.setSpacing(2)

        self.lbl_prod_title = QLabel(f"⚡ {t('agenda_metric_productivity')}")
        self.lbl_prod_title.setObjectName("AgendaMetricTitle")
        self.lbl_prod_val = QLabel("%0")
        self.lbl_prod_val.setObjectName("AgendaMetricValue")
        self.lbl_prod_sub = QLabel(f"Aylık {t('agenda_score_badge')}")
        self.lbl_prod_sub.setObjectName("AgendaMetricSub")

        prod_layout.addWidget(self.lbl_prod_title)
        prod_layout.addWidget(self.lbl_prod_val)
        prod_layout.addWidget(self.lbl_prod_sub)
        grid.addWidget(self.card_prod, 1, 1)

        main_layout.addLayout(grid)

    def set_stats(self, stats: dict):
        """Update metrics from stats dictionary."""
        if not stats:
            return

        total_tasks = stats.get('total_tasks', 0)
        completed_tasks = stats.get('completed_tasks', 0)
        rate = stats.get('completion_rate', 0)
        active_notes = stats.get('active_note_days', 0)
        days_in_month = stats.get('days_in_month', 30)
        streak = stats.get('streak_days', 0)
        score = stats.get('productivity_score', 0)

        # 1. Tasks
        self.lbl_tasks_val.setText(f"{completed_tasks}/{total_tasks} - %{rate}")
        self.tasks_progress.setValue(rate)

        # 2. Notes
        self.lbl_notes_val.setText(f"{active_notes}/{days_in_month} {t('agenda_days_unit')}")
        note_pct = int((active_notes / days_in_month) * 100) if days_in_month > 0 else 0
        self.lbl_notes_sub.setText(f"%{note_pct} Katılım")

        # 3. Streak
        self.lbl_streak_val.setText(f"{streak} {t('agenda_streak_unit')}")
        if streak >= 7:
            self.lbl_streak_sub.setText("Harika Gidiyorsun! 🔥")
        elif streak > 0:
            self.lbl_streak_sub.setText("Aktif Seri Devam")
        else:
            self.lbl_streak_sub.setText("Yeni Seri Başlat")

        # 4. Productivity
        self.lbl_prod_val.setText(f"%{score}")
        if score >= 80:
            self.lbl_prod_sub.setText("Yüksek Başarı 🏆")
        elif score >= 50:
            self.lbl_prod_sub.setText("İyi İlerleme ✨")
        else:
            self.lbl_prod_sub.setText("Geliştirilebilir 📈")

    def update_monthly_stats(self, year: int, month: int, stats: dict = None):
        """Slot / helper called when month changes or when stats are updated."""
        self.current_year = year
        self.current_month = month
        if stats:
            self.set_stats(stats)

    def retranslate_ui(self):
        """Retranslate static texts upon language change."""
        self.header_label.setText(t("agenda_monthly_summary_title"))
        self.lbl_tasks_title.setText(f"🎯 {t('agenda_metric_tasks')}")
        self.lbl_notes_title.setText(f"📝 {t('agenda_metric_notes')}")
        self.lbl_streak_title.setText(f"🔥 {t('agenda_metric_streak')}")
        self.lbl_prod_title.setText(f"⚡ {t('agenda_metric_productivity')}")


# ---------------------------------------------------------------------------
# Upcoming Tasks & Events Mini Panel
# ---------------------------------------------------------------------------
class UpcomingTasksPanel(QFrame):
    """
    Minimal upcoming tasks panel for the next 2-3 days.
    Shows date badge, priority dot, task title, and allows clicking
    to select that date in the agenda.
    """
    date_selected = Signal(str)              # When user clicks an item to view that date
    task_toggle_requested = Signal(int, int) # task_id, is_completed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UpcomingTasksPanel")
        self.upcoming_tasks = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(f"⏳ {t('agenda_upcoming_title')}")
        self.title_label.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;")

        self.badge_label = QLabel(t('agenda_upcoming_subtitle'))
        self.badge_label.setObjectName("UpcomingDateBadge")

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.badge_label)
        layout.addLayout(header_layout)

        # Items Layout (Container for task rows)
        self.items_widget = QWidget()
        self.items_layout = QVBoxLayout(self.items_widget)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(4)
        layout.addWidget(self.items_widget)

        # Empty Label
        self.empty_label = QLabel(f"☕ {t('agenda_upcoming_empty')}")
        self.empty_label.setObjectName("UpcomingEmptyLabel")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

    def set_tasks(self, tasks: list):
        self.upcoming_tasks = tasks or []
        # Clear existing item widgets
        while self.items_layout.count() > 0:
            item = self.items_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.upcoming_tasks:
            self.empty_label.show()
            self.items_widget.hide()
            self.badge_label.setText(t('agenda_upcoming_subtitle'))
            return

        self.empty_label.hide()
        self.items_widget.show()
        self.badge_label.setText(t('agenda_upcoming_count').format(count=len(self.upcoming_tasks)))

        import datetime
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)

        priority_colors = {
            3: "#EF4444",  # Urgent
            2: "#F59E0B",  # High
            1: "#3B82F6",  # Normal
            0: "#9CA3AF",  # Low
        }

        for task in self.upcoming_tasks:
            card = QFrame()
            card.setObjectName("UpcomingTaskItemWidget")
            card.setCursor(Qt.PointingHandCursor)
            row_l = QHBoxLayout(card)
            row_l.setContentsMargins(6, 4, 6, 4)
            row_l.setSpacing(6)

            # Date Badge
            task_date_str = task.get('due_date') or task.get('daily_note_date') or ""
            date_badge_text = task_date_str
            try:
                dt = datetime.date.fromisoformat(task_date_str)
                if dt == today:
                    date_badge_text = t("agenda_upcoming_today")
                elif dt == tomorrow:
                    date_badge_text = t("agenda_upcoming_tomorrow")
                else:
                    date_badge_text = f"{dt.day:02d}.{dt.month:02d}"
            except Exception:
                pass

            date_lbl = QLabel(date_badge_text)
            date_lbl.setObjectName("UpcomingDateBadge")
            row_l.addWidget(date_lbl)

            # Priority dot
            prio = task.get('priority', 1)
            prio_color = priority_colors.get(prio, "#3B82F6")
            prio_dot = QLabel()
            prio_dot.setFixedSize(6, 6)
            prio_dot.setStyleSheet(f"background-color: {prio_color}; border-radius: 3px;")
            row_l.addWidget(prio_dot)

            # Task Title
            title_text = task.get('title', '')
            title_lbl = QLabel(title_text)
            title_lbl.setStyleSheet("color: #E3E3E3; font-size: 12px; font-weight: 500;")
            title_lbl.setToolTip(title_text)
            row_l.addWidget(title_lbl, 1)

            # Mouse click handler to jump to that date
            def make_click_handler(target_date):
                return lambda event: self.date_selected.emit(target_date)

            if task_date_str:
                card.mousePressEvent = make_click_handler(task_date_str)

            self.items_layout.addWidget(card)

    def retranslate_ui(self):
        self.title_label.setText(f"⏳ {t('agenda_upcoming_title')}")
        self.empty_label.setText(f"☕ {t('agenda_upcoming_empty')}")
        if not self.upcoming_tasks:
            self.badge_label.setText(t('agenda_upcoming_subtitle'))
        else:
            self.badge_label.setText(t('agenda_upcoming_count').format(count=len(self.upcoming_tasks)))


# ---------------------------------------------------------------------------
# Calendar Sidebar Panel Container (Vertically Resizable via QSplitter)
# ---------------------------------------------------------------------------
class CalendarPanel(QFrame):
    """
    Calendar sidebar panel containing:
    - Top Section: CustomCalendarWidget, Today button, Legend.
    - Bottom Section (in QScrollArea): MonthlySummaryPanel & UpcomingTasksPanel.
    - Connected by an interactive vertical QSplitter so the user can easily
      expand or shrink the calendar vs. summary/upcoming areas vertically!
    """
    date_selected = Signal(str)                  # ISO date 'YYYY-MM-DD'
    month_changed = Signal(int, int)             # year, month
    monthly_stats_requested = Signal(int, int)   # year, month
    upcoming_date_selected = Signal(str)         # Clicked date in upcoming list
    task_toggle_requested = Signal(int, int)     # task_id, is_completed

    def __init__(self, parent=None, theme_config: dict = None):
        super().__init__(parent)
        self.setObjectName("AgendaSectionContainer")
        self._initial_theme = theme_config
        self.init_ui()
        self.setup_midnight_timer()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(0)

        # Vertical Splitter: allows user to freely adjust vertical height
        self.vertical_splitter = QSplitter(Qt.Vertical, self)
        self.vertical_splitter.setObjectName("AgendaVerticalSplitter")
        self.vertical_splitter.setHandleWidth(8)

        # --- 1. Top Section: Calendar Widget & Action Bar ---
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0, 0, 0, 4)
        top_layout.setSpacing(8)

        # Header Title
        self.title_label = QLabel(t("agenda_calendar_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 15px; font-weight: bold; padding: 2px 4px;")
        top_layout.addWidget(self.title_label)

        # Calendar Widget
        self.calendar = CustomCalendarWidget(self.top_widget, theme_config=self._initial_theme)
        self.calendar.clicked.connect(self._on_cell_clicked)
        self.calendar.currentPageChanged.connect(self._on_page_changed)
        top_layout.addWidget(self.calendar)

        # Today Button & Action Bar
        action_layout = QHBoxLayout()
        action_layout.setContentsMargins(2, 0, 2, 0)
        action_layout.setSpacing(8)

        self.today_btn = QPushButton(f"🎯  {t('agenda_today_btn')}")
        self.today_btn.setObjectName("NewLibBtn")
        self.today_btn.setFixedHeight(32)
        self.today_btn.setCursor(Qt.PointingHandCursor)
        self.today_btn.clicked.connect(self.go_to_today)
        action_layout.addWidget(self.today_btn)
        top_layout.addLayout(action_layout)

        # Indicators Legend
        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(4, 0, 4, 0)
        legend_layout.setSpacing(10)

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
        top_layout.addLayout(legend_layout)

        self.vertical_splitter.addWidget(self.top_widget)

        # --- 2. Bottom Section: Monthly Summary & Upcoming List in ScrollArea ---
        self.bottom_scroll_area = QScrollArea()
        self.bottom_scroll_area.setObjectName("AgendaLeftScrollArea")
        self.bottom_scroll_area.setWidgetResizable(True)
        self.bottom_scroll_area.setFrameShape(QFrame.NoFrame)
        self.bottom_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.bottom_content = QWidget()
        bottom_content_layout = QVBoxLayout(self.bottom_content)
        bottom_content_layout.setContentsMargins(0, 4, 0, 0)
        bottom_content_layout.setSpacing(8)

        # Monthly Summary & Metrics Panel
        self.summary_panel = MonthlySummaryPanel(self.bottom_content)
        bottom_content_layout.addWidget(self.summary_panel)

        # Upcoming Tasks Panel (Next 2-3 Days)
        self.upcoming_panel = UpcomingTasksPanel(self.bottom_content)
        self.upcoming_panel.date_selected.connect(self._on_upcoming_date_selected)
        self.upcoming_panel.task_toggle_requested.connect(self.task_toggle_requested.emit)
        bottom_content_layout.addWidget(self.upcoming_panel)

        bottom_content_layout.addStretch()
        self.bottom_scroll_area.setWidget(self.bottom_content)
        self.vertical_splitter.addWidget(self.bottom_scroll_area)

        # Splitter behavior & initial proportioning
        self.vertical_splitter.setCollapsible(0, False)
        self.vertical_splitter.setCollapsible(1, False)
        self.vertical_splitter.setStretchFactor(0, 0)
        self.vertical_splitter.setStretchFactor(1, 1)
        self.vertical_splitter.setSizes([330, 360])

        root_layout.addWidget(self.vertical_splitter)

    def set_theme_config(self, theme_config: dict):
        """Forward theme configuration dictionary to calendar."""
        self.calendar.set_theme_config(theme_config)

    def set_monthly_stats(self, stats: dict):
        """Update the metrics cards in MonthlySummaryPanel."""
        self.summary_panel.set_stats(stats)

    def set_upcoming_tasks(self, tasks: list):
        """Update the upcoming tasks mini list."""
        self.upcoming_panel.set_tasks(tasks)

    def update_monthly_stats(self, year: int, month: int, stats: dict = None):
        """Update month or trigger stats update."""
        self.summary_panel.update_monthly_stats(year, month, stats)
        if stats is None:
            self.monthly_stats_requested.emit(year, month)

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

    def _on_upcoming_date_selected(self, date_str: str):
        self.select_date(date_str)
        self.date_selected.emit(date_str)
        self.upcoming_date_selected.emit(date_str)

    def _on_page_changed(self, year: int, month: int):
        self.month_changed.emit(year, month)
        self.monthly_stats_requested.emit(year, month)
        self.summary_panel.update_monthly_stats(year, month)

    def go_to_today(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.calendar.setCurrentPage(today.year(), today.month())
        self.date_selected.emit(today.toString("yyyy-MM-dd"))

    def set_indicators(self, indicators: dict):
        self.calendar.set_indicators(indicators)
        if indicators and hasattr(self, 'summary_panel'):
            total_tasks = sum(v.get('pending_tasks', 0) + v.get('completed_tasks', 0) for v in indicators.values())
            completed_tasks = sum(v.get('completed_tasks', 0) for v in indicators.values())
            active_notes = sum(1 for v in indicators.values() if v.get('has_note', False))
            curr_qdate = self.calendar.selectedDate()
            num_days = curr_qdate.daysInMonth() if hasattr(curr_qdate, 'daysInMonth') else 30
            rate = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            
            preview_stats = {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': rate,
                'active_note_days': active_notes,
                'days_in_month': num_days,
                'streak_days': 0,
                'productivity_score': rate
            }
            self.summary_panel.set_stats(preview_stats)

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
        self.summary_panel.retranslate_ui()
        self.upcoming_panel.retranslate_ui()

