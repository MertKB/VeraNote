# ui/agenda/daily_note_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QFrame
from PySide6.QtCore import Qt, Signal, QTimer
from utils.i18n import t, format_localized_date

class DailyNotePanel(QFrame):
    """
    Middle panel of the Agenda: Markdown editor for Daily Notes
    with localized header, autosave debounce timer (500ms), and status feedback.
    """
    note_autosave_requested = Signal(str, str)  # date_str, content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AgendaSectionContainer")
        self.current_date = ""
        self._is_programmatic_change = False

        self.init_ui()
        self.setup_debounce_timer()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header Bar: Localized Date Title & Autosave status
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.date_title_label = QLabel()
        self.date_title_label.setStyleSheet("color: #E3E3E3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(self.date_title_label)

        header_layout.addStretch()

        self.status_label = QLabel(t("agenda_status_saved"))
        self.status_label.setStyleSheet("color: #9AA0A6; font-size: 12px; font-weight: 500;")
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        # Markdown Text Editor
        self.editor = QTextEdit()
        self.editor.setObjectName("DailyNoteEditor")
        self.editor.setPlaceholderText(t("agenda_daily_note_placeholder"))
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor)

    def setup_debounce_timer(self):
        """500ms debounce timer for seamless non-blocking autosave."""
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(500)
        self.debounce_timer.timeout.connect(self._trigger_autosave)

    def _on_text_changed(self):
        if self._is_programmatic_change:
            return
        if not self.current_date:
            return

        self.status_label.setText(t("agenda_status_saving"))
        self.status_label.setStyleSheet("color: #F59E0B; font-size: 12px; font-weight: 500;")
        self.debounce_timer.start()

    def _trigger_autosave(self):
        content = self.editor.toPlainText()
        self.status_label.setText(t("agenda_status_saved"))
        self.status_label.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 500;")
        self.note_autosave_requested.emit(self.current_date, content)

    def load_note(self, date_str: str, content: str):
        """Load a daily note for date without firing autosave debounce."""
        # Flush any pending autosave for previous date before switching
        if self.debounce_timer.isActive() and self.current_date and self.current_date != date_str:
            self.debounce_timer.stop()
            self._trigger_autosave()

        self.current_date = date_str
        self.date_title_label.setText(format_localized_date(date_str))

        self._is_programmatic_change = True
        try:
            self.editor.setPlainText(content or "")
        finally:
            self._is_programmatic_change = False

        self.status_label.setText(t("agenda_status_saved"))
        self.status_label.setStyleSheet("color: #9AA0A6; font-size: 12px; font-weight: 500;")

    def flush_save(self):
        """Flush any pending changes immediately (e.g. before app closing or switching views)."""
        if self.debounce_timer.isActive() and self.current_date:
            self.debounce_timer.stop()
            self._trigger_autosave()

    def retranslate_ui(self):
        self.editor.setPlaceholderText(t("agenda_daily_note_placeholder"))
        if self.current_date:
            self.date_title_label.setText(format_localized_date(self.current_date))
        if not self.debounce_timer.isActive():
            self.status_label.setText(t("agenda_status_saved"))
