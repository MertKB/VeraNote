# ui/sidebar.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QLabel, QFrame, QScrollArea)
from PySide6.QtCore import Signal, QSize, Qt
from PySide6.QtGui import QPixmap, QIcon
from utils.i18n import t, get_lang
from utils.icon_manager import get_icon, get_pixmap

class StaticListWidget(QListWidget):
    """QListWidget that ignores wheel events so it never scrolls internally."""
    def wheelEvent(self, event):
        event.ignore()

class Sidebar(QWidget):
    # Signals
    home_requested = Signal()
    agenda_requested = Signal()
    all_notes_requested = Signal()
    new_note_requested = Signal()
    trash_requested = Signal()
    new_library_requested = Signal()
    note_selected = Signal(int) # note_id
    library_selected = Signal(str) # model_library_name
    workflow_library_selected = Signal(str) # workflow_library_name
    delete_workflow_library_requested = Signal(str) # workflow_library_name
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.setFixedWidth(260) # Fixed static width
        self.incognito_active_state = False
        self.comfyui_visible = True
        self.current_palette = {}
        self.init_palette()
        
        self.init_ui()

    def init_palette(self):
        try:
            import database
            from ui.styles import get_palette
            theme_name = database.get_setting("theme", "Koyu Gece")
            custom_colors = database.get_setting("custom_colors", None)
            self.current_palette = get_palette(theme_name, custom_colors)
        except Exception:
            self.current_palette = {}

    def get_active_color(self):
        if not hasattr(self, 'current_palette') or not self.current_palette:
            self.init_palette()
        return self.current_palette.get('border_focus', '#8AB4F8')

    def get_inactive_color(self):
        if not hasattr(self, 'current_palette') or not self.current_palette:
            self.init_palette()
        return self.current_palette.get('text_muted', '#9AA0A6')

    def apply_theme(self, palette: dict):
        self.current_palette = palette or {}
        if hasattr(self, 'active_item_type'):
            self.set_active_item(self.active_item_type)
        else:
            self.set_active_item('home')

    def init_ui(self):
        # Outer layout for Sidebar widget
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Unified Outer Scroll Area for small display heights
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        self.container = QWidget()
        self.container.setObjectName("SidebarContainer")
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(12, 16, 12, 16)
        self.main_layout.setSpacing(12)

        # Header with Brand wrapped in a QFrame
        self.header_widget = QFrame()
        self.header_widget.setObjectName("SidebarHeader")
        self.header_widget.setStyleSheet("QFrame#SidebarHeader { background-color: transparent; border: none; }")
        
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(10)

        # Brand application vector logo matching theme and line design
        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("SidebarBrandLogo")
        self.brand_logo.setFixedSize(26, 26)
        self.brand_logo.setScaledContents(True)
        self.brand_logo.setPixmap(get_pixmap("brand", self.get_active_color(), 26))

        self.brand_label = QLabel("Vera Note")
        self.brand_label.setObjectName("SidebarTitle")
        
        header_layout.addWidget(self.brand_logo)
        header_layout.addWidget(self.brand_label)
        header_layout.addStretch()
        
        self.main_layout.addWidget(self.header_widget)

        # Separator
        self.sep_line = QFrame()
        self.sep_line.setFrameShape(QFrame.HLine)
        self.sep_line.setFrameShadow(QFrame.Sunken)
        self.sep_line.setStyleSheet("background-color: #2F2F2F; margin: 4px 0px;")
        self.main_layout.addWidget(self.sep_line)

        # --- HOME BUTTON ---
        self.home_btn = QPushButton()
        self.home_btn.setObjectName("HomeBtn")
        self.home_btn.setFixedSize(236, 40)
        self.home_btn.clicked.connect(lambda: (self.set_active_item('home'), self.home_requested.emit()))
        
        home_layout = QHBoxLayout(self.home_btn)
        home_layout.setContentsMargins(16, 0, 16, 0)
        home_layout.setSpacing(12)
        
        self.home_icon = QLabel()
        self.home_icon.setFixedSize(20, 20)
        self.home_icon.setScaledContents(True)
        self.home_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.home_icon.setPixmap(get_pixmap("home", "#8AB4F8", 20))
        
        self.home_label = QLabel(t("home"))
        self.home_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        home_layout.addWidget(self.home_icon)
        home_layout.addWidget(self.home_label)
        home_layout.addStretch()
        self.main_layout.addWidget(self.home_btn, 0, Qt.AlignCenter)

        # --- AGENDA BUTTON ---
        self.agenda_btn = QPushButton()
        self.agenda_btn.setObjectName("AgendaBtn")
        self.agenda_btn.setFixedSize(236, 40)
        self.agenda_btn.clicked.connect(lambda: (self.set_active_item('agenda'), self.agenda_requested.emit()))
        
        agenda_layout = QHBoxLayout(self.agenda_btn)
        agenda_layout.setContentsMargins(16, 0, 16, 0)
        agenda_layout.setSpacing(12)
        
        self.agenda_icon = QLabel()
        self.agenda_icon.setFixedSize(20, 20)
        self.agenda_icon.setScaledContents(True)
        self.agenda_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.agenda_icon.setPixmap(get_pixmap("calendar", "#E3E3E3", 20))
        
        self.agenda_label = QLabel(t("nav_agenda"))
        self.agenda_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        agenda_layout.addWidget(self.agenda_icon)
        agenda_layout.addWidget(self.agenda_label)
        agenda_layout.addStretch()
        self.main_layout.addWidget(self.agenda_btn, 0, Qt.AlignCenter)

        # --- SECTION: NOTES ---
        self.new_note_btn = QPushButton(f"  {t('new_note')}")
        self.new_note_btn.setObjectName("NewNoteBtn")
        self.new_note_btn.setIcon(get_icon("add", "#FFFFFF", 18))
        self.new_note_btn.setIconSize(QSize(18, 18))
        self.new_note_btn.setFixedSize(236, 40)
        self.new_note_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_note_requested.emit()))
        self.main_layout.addWidget(self.new_note_btn, 0, Qt.AlignCenter)

        # --- ALL NOTES BUTTON ---
        self.all_notes_btn = QPushButton()
        self.all_notes_btn.setObjectName("AllNotesBtn")
        self.all_notes_btn.setFixedSize(236, 40)
        self.all_notes_btn.clicked.connect(lambda: (self.set_active_item('all_notes'), self.all_notes_requested.emit()))
        
        all_notes_layout = QHBoxLayout(self.all_notes_btn)
        all_notes_layout.setContentsMargins(16, 0, 16, 0)
        all_notes_layout.setSpacing(12)
        
        self.all_notes_icon = QLabel()
        self.all_notes_icon.setFixedSize(20, 20)
        self.all_notes_icon.setScaledContents(True)
        self.all_notes_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.all_notes_icon.setPixmap(get_pixmap("notes", "#E3E3E3", 20))
        
        self.all_notes_label = QLabel(t("notes"))
        self.all_notes_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.all_notes_badge = QLabel("0")
        self.all_notes_badge.setObjectName("AllNotesBadge")
        self.all_notes_badge.setAlignment(Qt.AlignCenter)
        self.all_notes_badge.setFixedSize(24, 20)
        self.all_notes_badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        all_notes_layout.addWidget(self.all_notes_icon)
        all_notes_layout.addWidget(self.all_notes_label)
        all_notes_layout.addStretch()
        all_notes_layout.addWidget(self.all_notes_badge)
        self.main_layout.addWidget(self.all_notes_btn, 0, Qt.AlignCenter)

        # --- TRASH BUTTON ---
        self.trash_btn = QPushButton()
        self.trash_btn.setObjectName("TrashBtn")
        self.trash_btn.setFixedSize(236, 40)
        self.trash_btn.clicked.connect(lambda: (self.set_active_item('trash'), self.trash_requested.emit()))
        
        trash_layout = QHBoxLayout(self.trash_btn)
        trash_layout.setContentsMargins(16, 0, 16, 0)
        trash_layout.setSpacing(12)
        
        self.trash_icon = QLabel()
        self.trash_icon.setFixedSize(20, 20)
        self.trash_icon.setScaledContents(True)
        self.trash_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.trash_icon.setPixmap(get_pixmap("trash", "#E3E3E3", 20))
        
        self.trash_label = QLabel(t("trash"))
        self.trash_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.trash_badge = QLabel("0")
        self.trash_badge.setObjectName("TrashBadge")
        self.trash_badge.setAlignment(Qt.AlignCenter)
        self.trash_badge.setFixedSize(24, 20)
        self.trash_badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        trash_layout.addWidget(self.trash_icon)
        trash_layout.addWidget(self.trash_label)
        trash_layout.addStretch()
        trash_layout.addWidget(self.trash_badge)
        self.main_layout.addWidget(self.trash_btn, 0, Qt.AlignCenter)

        # --- SECTION: MODELS (MODELLER) ---
        self.models_header = QWidget()
        models_h_layout = QHBoxLayout(self.models_header)
        models_h_layout.setContentsMargins(8, 12, 8, 2)
        models_h_layout.setSpacing(8)
        
        self.models_icon = QLabel()
        self.models_icon.setFixedSize(16, 16)
        self.models_icon.setScaledContents(True)
        self.models_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.models_icon.setPixmap(get_pixmap("models", "#B5A9BC", 16))
        
        self.models_label = QLabel(t("models_title"))
        self.models_label.setStyleSheet("color: #B5A9BC; font-size: 11px; font-weight: bold;")
        
        models_h_layout.addWidget(self.models_icon)
        models_h_layout.addWidget(self.models_label)
        models_h_layout.addStretch()
        self.main_layout.addWidget(self.models_header)

        self.models_list = StaticListWidget()
        self.models_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.models_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.models_list.setFocusPolicy(Qt.NoFocus)
        self.models_list.itemClicked.connect(self.on_model_clicked)
        self.main_layout.addWidget(self.models_list)

        # --- SECTION: WORKFLOW LIBRARIES (KİTAPLIKLAR) ---
        self.new_lib_btn = QPushButton(f"  {t('new_lib')}")
        self.new_lib_btn.setObjectName("NewLibBtn")
        self.new_lib_btn.setIcon(get_icon("add", "#FFFFFF", 18))
        self.new_lib_btn.setIconSize(QSize(18, 18))
        self.new_lib_btn.setFixedSize(236, 40)
        self.new_lib_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_library_requested.emit()))
        self.main_layout.addWidget(self.new_lib_btn, 0, Qt.AlignCenter)

        self.lib_header = QWidget()
        lib_h_layout = QHBoxLayout(self.lib_header)
        lib_h_layout.setContentsMargins(8, 12, 8, 2)
        lib_h_layout.setSpacing(8)
        
        self.lib_icon = QLabel()
        self.lib_icon.setFixedSize(16, 16)
        self.lib_icon.setScaledContents(True)
        self.lib_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lib_icon.setPixmap(get_pixmap("workflows", "#B5A9BC", 16))

        self.lib_label = QLabel(t("workflows_title"))
        self.lib_label.setStyleSheet("color: #B5A9BC; font-size: 11px; font-weight: bold;")

        lib_h_layout.addWidget(self.lib_icon)
        lib_h_layout.addWidget(self.lib_label)
        lib_h_layout.addStretch()
        self.main_layout.addWidget(self.lib_header)

        self.libraries_list = StaticListWidget()
        self.libraries_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.libraries_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.libraries_list.setFocusPolicy(Qt.NoFocus)
        self.libraries_list.itemClicked.connect(self.on_library_clicked)
        self.libraries_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.libraries_list.customContextMenuRequested.connect(self.on_workflow_lib_context_menu)
        self.main_layout.addWidget(self.libraries_list)

        self.main_layout.addStretch()

        # Settings Button at bottom
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setFixedSize(236, 40)
        self.settings_btn.clicked.connect(lambda: (self.set_active_item('settings'), self.settings_requested.emit()))
        
        settings_layout = QHBoxLayout(self.settings_btn)
        settings_layout.setContentsMargins(16, 0, 16, 0)
        settings_layout.setSpacing(12)
        
        self.settings_icon = QLabel()
        self.settings_icon.setFixedSize(20, 20)
        self.settings_icon.setScaledContents(True)
        self.settings_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.settings_icon.setPixmap(get_pixmap("settings", "#E3E3E3", 20))
        
        self.settings_label = QLabel(t("settings"))
        self.settings_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        settings_layout.addWidget(self.settings_icon)
        settings_layout.addWidget(self.settings_label)
        settings_layout.addStretch()
        self.main_layout.addWidget(self.settings_btn, 0, Qt.AlignCenter)

        self.scroll_area.setWidget(self.container)
        outer_layout.addWidget(self.scroll_area)

        # Default active state: home
        self.set_active_item('home')

    def set_active_item(self, item_type, name=None):
        self.active_item_type = item_type
        buttons = {
            'home': self.home_btn,
            'agenda': self.agenda_btn,
            'all_notes': self.all_notes_btn,
            'trash': self.trash_btn,
            'settings': self.settings_btn,
        }
        for k, btn in buttons.items():
            is_active = (k == item_type)
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        # Update dynamic icon colors for active vs inactive state based on theme
        active_color = self.get_active_color()
        inactive_color = "#E3E3E3"
        self.brand_logo.setPixmap(get_pixmap("brand", active_color, 26))
        self.home_icon.setPixmap(get_pixmap("home", active_color if item_type == 'home' else inactive_color, 20))
        self.agenda_icon.setPixmap(get_pixmap("calendar", active_color if item_type == 'agenda' else inactive_color, 20))
        self.all_notes_icon.setPixmap(get_pixmap("notes", active_color if item_type == 'all_notes' else inactive_color, 20))
        self.trash_icon.setPixmap(get_pixmap("trash", active_color if item_type == 'trash' else inactive_color, 20))
        self.settings_icon.setPixmap(get_pixmap("settings", active_color if item_type == 'settings' else inactive_color, 20))

        if item_type != 'model':
            self.models_list.clearSelection()
        else:
            if name and hasattr(self, 'model_lib_names') and name in self.model_lib_names:
                idx = self.model_lib_names.index(name)
                self.models_list.setCurrentRow(idx)

        if item_type != 'workflow':
            self.libraries_list.clearSelection()
        else:
            if name and hasattr(self, 'workflow_lib_names') and name in self.workflow_lib_names:
                idx = self.workflow_lib_names.index(name)
                self.libraries_list.setCurrentRow(idx)

    def retranslate_ui(self):
        self.home_label.setText(t("home"))
        self.agenda_label.setText(t("nav_agenda"))
        self.new_note_btn.setText(f"  {t('new_note')}")
        self.all_notes_label.setText(t("notes"))
        self.trash_label.setText(t("trash"))
        self.models_label.setText(t("models_title"))
        self.new_lib_btn.setText(f"  {t('new_lib')}")
        self.lib_label.setText(t("workflows_title"))
        self.settings_label.setText(t("settings"))
        self.set_incognito_active(self.incognito_active_state)
        if hasattr(self, 'active_item_type'):
            self.set_active_item(self.active_item_type)
        if hasattr(self, 'comfyui_visible'):
            self.set_comfyui_visible(self.comfyui_visible)
        if hasattr(self, 'last_models_data') and self.last_models_data:
            self.update_models_list(self.last_models_data, getattr(self, 'last_selected_model_lib', None))
        if hasattr(self, 'last_workflow_libs_data') and self.last_workflow_libs_data:
            self.update_workflow_libraries_list(self.last_workflow_libs_data, getattr(self, 'last_selected_workflow_lib', None))

    def set_comfyui_visible(self, visible: bool):
        self.comfyui_visible = visible
        if hasattr(self, 'models_header'):
            self.models_header.setVisible(visible)
        self.models_list.setVisible(visible)
        self.new_lib_btn.setVisible(visible)
        if hasattr(self, 'lib_header'):
            self.lib_header.setVisible(visible)
        self.libraries_list.setVisible(visible)

    def tr_lib_name(self, name):
        if name == "Lora Modelleri":
            return "Lora Models" if get_lang() == "en" else "Lora Modelleri"
        elif name == "Checkpoint Modelleri":
            return "Checkpoint Models" if get_lang() == "en" else "Checkpoint Modelleri"
        elif name == "Favoriler":
            return "Favorites" if get_lang() == "en" else "Favoriler"
        return name

    def update_notes_count(self, count):
        self.all_notes_badge.setText(str(count))

    def update_trash_count(self, count):
        self.trash_badge.setText(str(count))

    def update_models_list(self, models_with_counts, selected_model_lib=None):
        self.last_models_data = models_with_counts
        self.last_selected_model_lib = selected_model_lib
        self.models_list.clear()
        self.model_lib_names = []
        for lib_name, count in models_with_counts:
            # Sub-items indented without icon per user request
            item = QListWidgetItem(f"   {self.tr_lib_name(lib_name)} ({count})")
            self.models_list.addItem(item)
            self.model_lib_names.append(lib_name)
            if selected_model_lib and lib_name == selected_model_lib:
                self.models_list.setCurrentRow(self.models_list.count() - 1)
        
        # Calculate height so all items fit statically without inner scrollbar
        count = max(1, len(models_with_counts))
        self.models_list.setFixedHeight(count * 44 + 8)
        if hasattr(self, 'comfyui_visible') and not self.comfyui_visible:
            self.models_list.setVisible(False)

    def update_workflow_libraries_list(self, workflow_libs_with_counts, selected_workflow_lib=None):
        self.last_workflow_libs_data = workflow_libs_with_counts
        self.last_selected_workflow_lib = selected_workflow_lib
        self.libraries_list.clear()
        self.workflow_lib_names = []
        for lib_name, count in workflow_libs_with_counts:
            # Sub-items indented without icon per user request
            item = QListWidgetItem(f"   {self.tr_lib_name(lib_name)} ({count})")
            self.libraries_list.addItem(item)
            self.workflow_lib_names.append(lib_name)
            if selected_workflow_lib and lib_name == selected_workflow_lib:
                self.libraries_list.setCurrentRow(self.libraries_list.count() - 1)

        count = max(1, len(workflow_libs_with_counts))
        self.libraries_list.setFixedHeight(count * 44 + 8)
        if hasattr(self, 'comfyui_visible') and not self.comfyui_visible:
            self.libraries_list.setVisible(False)

    def on_model_clicked(self, item):
        row = self.models_list.row(item)
        if 0 <= row < len(self.model_lib_names):
            self.set_active_item('model', self.model_lib_names[row])
            self.library_selected.emit(self.model_lib_names[row])

    def on_library_clicked(self, item):
        row = self.libraries_list.row(item)
        if 0 <= row < len(self.workflow_lib_names):
            self.set_active_item('workflow', self.workflow_lib_names[row])
            self.workflow_library_selected.emit(self.workflow_lib_names[row])

    def on_workflow_lib_context_menu(self, pos):
        item = self.libraries_list.itemAt(pos)
        if not item:
            return
        row = self.libraries_list.row(item)
        if 0 <= row < len(self.workflow_lib_names):
            lib_name = self.workflow_lib_names[row]
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QCursor
            menu = QMenu(self)
            del_action = menu.addAction(t("workflow_delete_library_menu"))
            action = menu.exec(QCursor.pos())
            if action == del_action:
                self.delete_workflow_library_requested.emit(lib_name)

    def clear_list_selections(self):
        self.models_list.clearSelection()
        self.libraries_list.clearSelection()

    def set_incognito_active(self, active):
        self.incognito_active_state = active
        if active:
            self.header_widget.setStyleSheet("""
                QFrame#SidebarHeader {
                    background-color: #2D1E2F;
                    border: 1px solid #4B3254;
                    border-radius: 8px;
                }
            """)
            self.brand_label.setText("Vera Note (Incognito)")
            self.brand_label.setStyleSheet("color: #D7AEF5; font-size: 20px; font-weight: 800; padding: 8px 4px;")
        else:
            self.header_widget.setStyleSheet("""
                QFrame#SidebarHeader {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.brand_label.setText("Vera Note")
            self.brand_label.setStyleSheet("")
