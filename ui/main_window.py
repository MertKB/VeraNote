from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QStackedWidget, QSplitter, QTextEdit, QLineEdit, 
                             QPushButton, QLabel, QMessageBox, QDockWidget, QApplication)
from PySide6.QtCore import Slot, Qt, Signal, QTimer, QEvent, QObject
from PySide6.QtGui import QIcon, QKeySequence
from ui.sidebar import Sidebar
from ui.welcome_screen import WelcomeScreen
from ui.library_view import LibraryView
from ui.detail_panel import DetailPanel
from ui.notes_view import NotesView
from ui.workflow_view import WorkflowView
from ui.agenda import AgendaView
from ui.notebooks_view import NotebooksView
from ui.styles import STYLE_SHEET
from utils.i18n import t

class NavigationEventFilter(QObject):
    """Filters application-wide events for mouse and keyboard Back / Forward navigation commands."""
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, obj, event):
        etype = event.type()
        if etype == QEvent.MouseButtonPress:
            btn = event.button()
            if btn == Qt.BackButton:
                self.main_window.navigate_back()
                return True
            elif btn == Qt.ForwardButton:
                self.main_window.navigate_forward()
                return True
        elif etype == QEvent.KeyPress:
            # Check for Back command (Qt.Key_Back, Alt+Left, or QKeySequence.Back)
            if event.matches(QKeySequence.Back) or (event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_Left) or event.key() == Qt.Key_Back:
                from PySide6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit
                if isinstance(obj, (QLineEdit, QTextEdit, QPlainTextEdit)) and event.key() == Qt.Key_Back:
                    pass
                else:
                    self.main_window.navigate_back()
                    return True
            elif event.matches(QKeySequence.Forward) or (event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_Right) or event.key() == Qt.Key_Forward:
                self.main_window.navigate_forward()
                return True
        return super().eventFilter(obj, event)

class ResettableDockWidget(QDockWidget):
    """Custom QDockWidget with styled background that cleanly notifies main window on close."""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._main_win = parent
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.topLevelChanged.connect(self._on_top_level_changed)

    def _on_top_level_changed(self, floating):
        self._wire_close_btn()
        if self._main_win and hasattr(self._main_win, 'styleSheet'):
            sheet = self._main_win.styleSheet()
            if sheet:
                self.setStyleSheet(sheet)

    def _wire_close_btn(self):
        for b in self.findChildren(object):
            if b.objectName() == "qt_dockwidget_closebutton":
                b.installEventFilter(self)
                try:
                    b.clicked.disconnect()
                except Exception:
                    pass
                b.clicked.connect(self.close_dock)

    def eventFilter(self, obj, event):
        if obj.objectName() == "qt_dockwidget_closebutton":
            if event.type() == QEvent.MouseButtonRelease:
                if obj.rect().contains(event.position().toPoint()):
                    self.close_dock()
                    return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._wire_close_btn()

    def close_dock(self):
        self.hide()
        main_win = self._main_win or self.parent()
        if main_win and hasattr(main_win, "hide_detail_panel"):
            main_win.hide_detail_panel()

    def closeEvent(self, event):
        super().closeEvent(event)
        main_win = self._main_win or self.parent()
        if main_win and hasattr(main_win, "hide_detail_panel"):
            main_win.hide_detail_panel()

class NoteEditor(QWidget):
    save_requested = Signal(object, str, str) # note_id (int/None), title, content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.note_id = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        self.header_label = QLabel(t("view_all_notes"))
        self.header_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.header_label)

        # Title Input
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.title_edit.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #1E1F20; border: 1px solid #444746; padding: 10px; border-radius: 8px;")
        layout.addWidget(self.title_edit)

        # Content Input
        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText(t("detail_notes_placeholder_note"))
        self.content_edit.setStyleSheet("font-size: 14px; background-color: #1E1F20; border: 1px solid #444746; padding: 12px; border-radius: 8px;")
        layout.addWidget(self.content_edit)

        # Actions
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton(t("save_note"))
        self.save_btn.setObjectName("NewNoteBtn") # Blue styled
        self.save_btn.clicked.connect(self.on_save_clicked)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def retranslate_ui(self):
        self.header_label.setText(t("view_all_notes"))
        self.title_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.content_edit.setPlaceholderText(t("detail_notes_placeholder_note"))
        self.save_btn.setText(t("save_note"))

    def load_note(self, note_id, title, content):
        self.note_id = note_id
        self.title_edit.setText(title)
        self.content_edit.setPlainText(content)

    def clear_note(self):
        self.note_id = None
        self.title_edit.clear()
        self.content_edit.clear()

    def on_save_clicked(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        if not title:
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_empty_title_error"), QMessageBox.Ok)
            return
        self.save_requested.emit(self.note_id, title, content)


class MainWindow(QMainWindow):
    # Pass signals through MainWindow to controller
    save_note_signal = Signal(object, str, str) # id, title, content
    save_note_new_signal = Signal(int, str, str, str, str, int, bool) # id, title, content, image_path, display_mode, is_fav, is_auto_save
    delete_note_signal = Signal(int)
    save_model_data_signal = Signal(int, str, str, str) # model_id, name, notes, base_architecture
    add_trigger_signal = Signal(int, str) # model_id, word
    delete_trigger_signal = Signal(int, str) # model_id, word
    set_triggers_signal = Signal(int, list) # model_id, triggers_list
    scan_library_signal = Signal(str)
    settings_requested_signal = Signal()
    image_changed_signal = Signal(int, str)
    favorite_toggled_signal = Signal(int, bool)
    note_favorite_toggled_signal = Signal(int, bool)
    note_clicked_signal = Signal(dict)
    note_associate_model_signal = Signal(int, int)
    note_dissociate_model_signal = Signal(int, int)
    add_tag_signal = Signal(int, str)
    delete_tag_signal = Signal(int, str)
    set_tags_signal = Signal(int, list)
    save_workflow_data_signal = Signal(int, str, str, str) # id, name, description, notes
    delete_workflow_signal = Signal(int)
    workflow_image_changed_signal = Signal(int, str)
    workflow_clicked_signal = Signal(dict)
    add_workflow_signal = Signal(int, str, str, str, str)
    workflow_favorite_toggled_signal = Signal(int, bool)
    model_hide_signal = Signal(dict)
    model_unhide_signal = Signal(dict)
    workflow_hide_signal = Signal(dict)
    workflow_unhide_signal = Signal(dict)
    note_hide_signal = Signal(dict)
    note_unhide_signal = Signal(dict)
    bulk_add_tag_signal = Signal(list)
    bulk_remove_tag_signal = Signal(list)
    bulk_favorite_signal = Signal(list, bool)
    bulk_delete_signal = Signal(list)
    delete_model_signal = Signal(int)
    file_dropped_signal = Signal(str)
    add_note_tag_signal = Signal(int, str)
    delete_note_tag_signal = Signal(int, str)
    clear_note_tags_signal = Signal(int)
    set_note_notebook_signal = Signal(int, object)
    notebook_selected_signal = Signal(int, str)
    all_notebooks_requested_signal = Signal()
    new_notebook_signal = Signal()
    rename_notebook_signal = Signal(int, str)
    delete_notebook_signal = Signal(int, str)
    bulk_delete_notebooks_signal = Signal(list)
    notes_scope_changed_signal = Signal(str)

    def __init__(self):
        super().__init__()
        import os
        self.setWindowTitle(t("app_title"))
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1200, 800)
        self.setMinimumSize(960, 600)
        self.setAcceptDrops(True)

        self._nav_history = []
        self._nav_forward = []
        self._nav_navigating = False

        self.init_ui()
        self.setStyleSheet(STYLE_SHEET)

    def init_ui(self):
        # Central splitter separating Sidebar and Central area
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(4)

        # Sidebar (Static fixed layout)
        self.sidebar = Sidebar()
        self.splitter.addWidget(self.sidebar)

        # Main Central Stacked Area
        self.center_stack = QStackedWidget()
        
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.quick_note_saved.connect(self.on_quick_note_saved)

        self.library_view = LibraryView()
        self.library_view.model_clicked.connect(self.on_model_clicked)
        self.library_view.scan_requested.connect(self.scan_library_signal.emit)
        self.library_view.favorite_toggled.connect(self.favorite_toggled_signal.emit)
        self.library_view.bulk_add_tag_requested.connect(self.bulk_add_tag_signal.emit)
        self.library_view.bulk_remove_tag_requested.connect(self.bulk_remove_tag_signal.emit)
        self.library_view.bulk_favorite_requested.connect(self.bulk_favorite_signal.emit)
        self.library_view.bulk_delete_requested.connect(self.bulk_delete_signal.emit)

        self.note_editor = NoteEditor()
        self.note_editor.save_requested.connect(self.save_note_signal.emit)

        self.notes_view = NotesView()
        self.notes_view.note_clicked.connect(self.note_clicked_signal.emit)
        self.notes_view.note_favorite_toggled.connect(self.note_favorite_toggled_signal.emit)
        self.notes_view.new_note_requested.connect(self.sidebar.new_note_requested.emit)
        self.notes_view.scope_changed.connect(self.notes_scope_changed_signal.emit)

        self.workflow_view = WorkflowView()
        self.workflow_view.workflow_clicked.connect(self.workflow_clicked_signal.emit)
        self.workflow_view.add_workflow_requested.connect(self.add_workflow_signal.emit)
        self.workflow_view.workflow_favorite_toggled.connect(self.workflow_favorite_toggled_signal.emit)

        self.agenda_view = AgendaView()
        self.notebooks_view = NotebooksView()

        self.center_stack.addWidget(self.welcome_screen)  # index 0
        self.center_stack.addWidget(self.library_view)    # index 1
        self.center_stack.addWidget(self.note_editor)     # index 2
        self.center_stack.addWidget(self.notes_view)     # index 3
        self.center_stack.addWidget(self.workflow_view)  # index 4
        self.center_stack.addWidget(self.agenda_view)    # index 5
        self.center_stack.addWidget(self.notebooks_view) # index 6
        
        self.splitter.addWidget(self.center_stack)

        # Connect Sidebar Notebook signals
        self.sidebar.notebook_selected.connect(self.notebook_selected_signal.emit)
        self.sidebar.all_notebooks_requested.connect(self.all_notebooks_requested_signal.emit)
        self.sidebar.new_notebook_requested.connect(self.new_notebook_signal.emit)
        self.sidebar.rename_notebook_requested.connect(self.rename_notebook_signal.emit)
        self.sidebar.delete_notebook_requested.connect(self.delete_notebook_signal.emit)

        # Connect NotebooksView signals
        self.notebooks_view.notebook_opened.connect(self.notebook_selected_signal.emit)
        self.notebooks_view.create_notebook_requested.connect(self.new_notebook_signal.emit)
        self.notebooks_view.rename_notebook_requested.connect(self.rename_notebook_signal.emit)
        self.notebooks_view.delete_notebook_requested.connect(self.delete_notebook_signal.emit)
        self.notebooks_view.bulk_delete_notebooks_requested.connect(self.bulk_delete_notebooks_signal.emit)
        self.notes_view.back_to_notebooks_requested.connect(self.all_notebooks_requested_signal.emit)

        # Install Global Mouse & Keyboard Navigation Event Filter
        app = QApplication.instance()
        if app:
            self._nav_filter = NavigationEventFilter(self)
            app.installEventFilter(self._nav_filter)

        # Set stretch factors (Sidebar: 0, Center Stack: 1)
        self.splitter.setStretchFactor(0, 0) # Sidebar
        self.splitter.setStretchFactor(1, 1) # Center Stack
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        self.setCentralWidget(self.splitter)
        if self.sidebar.is_collapsed:
            self.splitter.setSizes([64, 1136])
        else:
            self.splitter.setSizes([260, 940])

        # Detail Panel wrapped inside native QDockWidget (Floatable / Detachable / Closable)
        self.detail_panel = DetailPanel()
        self.detail_panel.close_requested.connect(self.hide_detail_panel)
        self.detail_panel.save_model_data_requested.connect(self.save_model_data_signal.emit)
        self.detail_panel.add_trigger_requested.connect(self.add_trigger_signal.emit)
        self.detail_panel.delete_trigger_requested.connect(self.delete_trigger_signal.emit)
        self.detail_panel.set_triggers_requested.connect(self.set_triggers_signal.emit)
        self.detail_panel.add_tag_requested.connect(self.add_tag_signal.emit)
        self.detail_panel.delete_tag_requested.connect(self.delete_tag_signal.emit)
        self.detail_panel.set_tags_requested.connect(self.set_tags_signal.emit)
        self.detail_panel.delete_model_requested.connect(self.delete_model_signal.emit)
        self.detail_panel.image_changed.connect(self.image_changed_signal.emit)
        self.detail_panel.save_note_requested.connect(self.save_note_new_signal.emit)
        self.detail_panel.save_workflow_data_requested.connect(self.save_workflow_data_signal.emit)
        self.detail_panel.delete_workflow_requested.connect(self.delete_workflow_signal.emit)
        self.detail_panel.workflow_image_changed.connect(self.workflow_image_changed_signal.emit)
        self.detail_panel.associate_model_requested.connect(self.note_associate_model_signal.emit)
        self.detail_panel.dissociate_model_requested.connect(self.note_dissociate_model_signal.emit)
        self.detail_panel.add_note_tag_requested.connect(self.add_note_tag_signal.emit)
        self.detail_panel.delete_note_tag_requested.connect(self.delete_note_tag_signal.emit)
        self.detail_panel.clear_note_tags_requested.connect(self.clear_note_tags_signal.emit)
        self.detail_panel.set_note_notebook_requested.connect(self.set_note_notebook_signal.emit)

        self.setObjectName("MainWindow")

        # Setup Dock Widget in RightDockWidgetArea
        dock_title = t("detail_dock_title")
        self.detail_dock = ResettableDockWidget(dock_title, self)
        self.detail_dock.setObjectName("DetailDockWidget")
        self.detail_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.detail_dock.setFeatures(
            QDockWidget.DockWidgetMovable | 
            QDockWidget.DockWidgetFloatable | 
            QDockWidget.DockWidgetClosable
        )
        self.detail_dock.setWidget(self.detail_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.detail_dock)

        # Save pristine docked layout state so we can restore docked position with 100% precision
        self._pristine_docked_state = self.saveState()

        # Initially hidden
        self.detail_dock.hide()
        self.detail_dock.visibilityChanged.connect(self._on_dock_visibility_changed)

        # Connect context menu hide/unhide signals
        self.library_view.model_hide_requested.connect(self.model_hide_signal.emit)
        self.library_view.model_unhide_requested.connect(self.model_unhide_signal.emit)
        
        self.workflow_view.workflow_hide_requested.connect(self.workflow_hide_signal.emit)
        self.workflow_view.workflow_unhide_requested.connect(self.workflow_unhide_signal.emit)

        self.notes_view.note_hide_requested.connect(self.note_hide_signal.emit)
        self.notes_view.note_unhide_requested.connect(self.note_unhide_signal.emit)

        # Connect sidebar events
        self.sidebar.new_note_requested.connect(self.create_new_note)
        self.sidebar.settings_requested.connect(self.settings_requested_signal.emit)
        self.sidebar.home_requested.connect(self.show_welcome)
        self.sidebar.agenda_requested.connect(self.show_agenda)
        self.sidebar.collapsed_toggled.connect(self._on_sidebar_collapsed_toggled)

    def _on_sidebar_collapsed_toggled(self, collapsed: bool):
        target_w = 64 if collapsed else 260
        self.sidebar.setFixedWidth(target_w)
        sizes = self.splitter.sizes()
        if sizes and len(sizes) >= 2:
            total_w = sum(sizes)
            self.splitter.setSizes([target_w, max(100, total_w - target_w)])

    def set_comfyui_enabled(self, enabled: bool):
        self.sidebar.set_comfyui_visible(enabled)
        if not enabled:
            curr_idx = self.center_stack.currentIndex()
            if curr_idx in (1, 4):  # 1 is library_view, 4 is workflow_view
                self.show_welcome()
            if hasattr(self, 'detail_panel') and getattr(self.detail_panel, 'mode', None) in ("MODEL", "WORKFLOW"):
                self.hide_detail_panel()

    def _record_nav_state(self, state: tuple):
        if getattr(self, '_nav_navigating', False):
            return
        if not self._nav_history or self._nav_history[-1] != state:
            self._nav_history.append(state)
            self._nav_forward.clear()

    def navigate_back(self):
        # 1. If currently inside a notebook's notes view, return to notebooks overview
        if self.center_stack.currentIndex() == 3 and self.notes_view.current_notebook_id is not None:
            self.all_notebooks_requested_signal.emit()
            return True
        # 2. General history back
        if len(self._nav_history) > 1:
            curr = self._nav_history.pop()
            self._nav_forward.append(curr)
            prev = self._nav_history[-1]
            self._restore_nav_state(prev)
            return True
        return False

    def navigate_forward(self):
        if self._nav_forward:
            nxt = self._nav_forward.pop()
            self._nav_history.append(nxt)
            self._restore_nav_state(nxt)
            return True
        return False

    def _restore_nav_state(self, state: tuple):
        self._nav_navigating = True
        try:
            kind = state[0]
            if kind == 'home':
                self.sidebar.home_requested.emit()
            elif kind == 'agenda':
                self.sidebar.agenda_requested.emit()
            elif kind == 'all_notebooks':
                self.all_notebooks_requested_signal.emit()
            elif kind == 'notebook':
                self.notebook_selected_signal.emit(state[1], state[2])
            elif kind == 'notes':
                if len(state) > 1 and state[1]:
                    self.sidebar.trash_requested.emit()
                else:
                    self.sidebar.all_notes_requested.emit()
            elif kind == 'library':
                self.sidebar.library_selected.emit(state[1])
            elif kind == 'workflow_lib':
                self.sidebar.workflow_library_selected.emit(state[2])
        finally:
            self._nav_navigating = False

    def show_welcome(self):
        self._record_nav_state(('home',))
        self.sidebar.set_active_item('home')
        self.center_stack.setCurrentIndex(0)
        self.hide_detail_panel()
        if getattr(self.welcome_screen, '_corkboard_dirty', False):
            import database
            cork_notes = database.get_corkboard_notes(show_hidden=getattr(self, 'incognito_active', False))
            self.welcome_screen.set_corkboard_notes(cork_notes)
            self.welcome_screen._corkboard_dirty = False

    def show_agenda(self):
        self._record_nav_state(('agenda',))
        self.sidebar.set_active_item('agenda')
        self.center_stack.setCurrentIndex(5)
        self.hide_detail_panel()

    def create_new_note(self):
        self.note_editor.clear_note()
        self.center_stack.setCurrentIndex(2)
        self.hide_detail_panel()

    def show_note(self, note_id, title, content):
        self.note_editor.load_note(note_id, title, content)
        self.center_stack.setCurrentIndex(2)
        self.hide_detail_panel()

    def show_library(self, name, models):
        self._record_nav_state(('library', name))
        self.hide_detail_panel()
        self.sidebar.set_active_item('model', name)
        self.center_stack.setCurrentIndex(1)
        if self.center_stack.width() > 100:
            self.library_view.resize(self.center_stack.size())
        self.library_view.set_library(name, models)

    def show_workflow_library(self, lib_id, name, workflows):
        self._record_nav_state(('workflow_lib', lib_id, name))
        self.hide_detail_panel()
        self.sidebar.set_active_item('workflow', name)
        self.center_stack.setCurrentIndex(4)
        if self.center_stack.width() > 100:
            self.workflow_view.resize(self.center_stack.size())
        self.workflow_view.set_workflows(lib_id, name, workflows)

    def show_notes_panel(self, notes, is_trash=False, notebook_id=None, notebook_name=None):
        if is_trash:
            self._record_nav_state(('notes', True))
        elif notebook_id is not None:
            self._record_nav_state(('notebook', notebook_id, notebook_name))
        else:
            self._record_nav_state(('notes', False))
        self.hide_detail_panel()
        if is_trash:
            self.sidebar.set_active_item('trash')
        elif notebook_id is not None:
            self.sidebar.set_active_item('notebook', notebook_name)
        else:
            self.sidebar.set_active_item('all_notes')
        self.center_stack.setCurrentIndex(3)
        if self.center_stack.width() > 100:
            self.notes_view.resize(self.center_stack.size())
        self.notes_view.set_notebook_context(notebook_id=notebook_id, notebook_name=notebook_name)
        if notes is not None:
            self.notes_view.set_notes(notes, is_trash=is_trash)

    def show_notebook_panel(self, notebook_id, notebook_name, notes):
        self.show_notes_panel(notes, is_trash=False, notebook_id=notebook_id, notebook_name=notebook_name)

    def show_notebooks_overview(self, notebooks):
        self._record_nav_state(('all_notebooks',))
        self.hide_detail_panel()
        self.sidebar.set_active_item('all_notebooks')
        self.center_stack.setCurrentIndex(6)
        if self.center_stack.width() > 100:
            self.notebooks_view.resize(self.center_stack.size())
        self.notebooks_view.set_notebooks(notebooks)

    def on_model_clicked(self, model_data):
        pass

    def reset_detail_dock(self):
        """Resets the detail dock widget back to its pristine right dock area position."""
        if hasattr(self, '_pristine_docked_state') and self._pristine_docked_state:
            if hasattr(self, 'detail_dock') and self.detail_dock:
                self.addDockWidget(Qt.RightDockWidgetArea, self.detail_dock)
            self.restoreState(self._pristine_docked_state)

    def show_detail_panel(self, model_data=None):
        """Shows the detail panel, guaranteeing it is docked in Qt.RightDockWidgetArea."""
        if not hasattr(self, 'detail_dock') or not self.detail_dock:
            return

        # If floating or hidden, restore pristine docked position
        if self.detail_dock.isFloating() or not self.detail_dock.isVisible():
            self.reset_detail_dock()

        self.detail_dock.show()
        self.detail_dock.raise_()

    def _on_dock_visibility_changed(self, visible: bool):
        if not visible:
            self.hide_detail_panel()

    def hide_detail_panel(self):
        """Hide detail panel dock widget."""
        if hasattr(self, 'detail_dock') and self.detail_dock and self.detail_dock.isVisible():
            self.detail_dock.hide()

    def show_toast(self, message: str, toast_type: str = "info", duration_ms: int = 2800):
        """Displays a non-blocking floating toast notification in the bottom-right corner."""
        from ui.widgets.toast import show_toast
        return show_toast(self, message, toast_type, duration_ms)

    def on_quick_note_saved(self, title, content):
        self.save_note_signal.emit(None, title, content)

    def change_theme(self, theme_name, custom_colors=None):
        from ui.styles import get_stylesheet, get_calendar_theme_config, get_palette
        from utils.icon_manager import clear_cache
        clear_cache()
        
        stylesheet = get_stylesheet(theme_name, custom_colors)
        palette = get_palette(theme_name, custom_colors)

        # Freeze widget updates during style & theme cascade to avoid multiple redundant layout & paint passes
        self.setUpdatesEnabled(False)
        try:
            self.setStyleSheet(stylesheet)
            if hasattr(self, 'sidebar') and self.sidebar:
                self.sidebar.apply_theme(palette)
            if hasattr(self, 'notebooks_view') and self.notebooks_view:
                self.notebooks_view.apply_theme(palette)
            if hasattr(self, 'notes_view') and self.notes_view:
                self.notes_view.apply_theme(palette)
            if hasattr(self, 'agenda_view') and self.agenda_view:
                cal_theme = get_calendar_theme_config(theme_name, custom_colors)
                self.agenda_view.set_calendar_theme(cal_theme)
            if hasattr(self, 'detail_panel') and self.detail_panel and hasattr(self.detail_panel, 'apply_theme'):
                self.detail_panel.apply_theme(palette)
            if hasattr(self, 'welcome_screen') and self.welcome_screen and hasattr(self.welcome_screen, 'apply_theme'):
                self.welcome_screen.apply_theme(palette)
            if hasattr(self, 'workflow_view') and self.workflow_view and hasattr(self.workflow_view, 'apply_theme'):
                self.workflow_view.apply_theme(palette)
            if hasattr(self, 'detail_dock') and self.detail_dock and self.detail_dock.isFloating():
                self.detail_dock.setStyleSheet(stylesheet)
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def retranslate_ui(self):
        self.setWindowTitle(t("app_title"))
        self.sidebar.retranslate_ui()
        self.note_editor.retranslate_ui()
        self.notes_view.retranslate_ui()
        self.welcome_screen.retranslate_ui()
        self.library_view.retranslate_ui()
        self.workflow_view.retranslate_ui()
        self.agenda_view.retranslate_ui()
        self.notebooks_view.retranslate_ui()
        self.detail_panel.retranslate_ui()
        if hasattr(self, 'detail_dock') and self.detail_dock and hasattr(self.detail_dock, 'setWindowTitle'):
            self.detail_dock.setWindowTitle(t("detail_dock_title"))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fn = url.toLocalFile().lower()
                if fn.endswith('.png') or fn.endswith('.json'):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fn = url.toLocalFile().lower()
                if fn.endswith('.png') or fn.endswith('.json'):
                    event.acceptProposedAction()
                    return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.png') or file_path.lower().endswith('.json'):
                    event.acceptProposedAction()
                    self.file_dropped_signal.emit(file_path)
                    return
        super().dropEvent(event)

    def closeEvent(self, event):
        if hasattr(self, 'agenda_view') and self.agenda_view:
            self.agenda_view.flush_pending_saves()
        super().closeEvent(event)
