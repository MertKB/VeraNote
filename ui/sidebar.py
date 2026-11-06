# ui/sidebar.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QListWidget, QListWidgetItem, QLabel, QFrame, QScrollArea, QSizePolicy)
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
    notebook_selected = Signal(int, str) # notebook_id, notebook_name
    all_notebooks_requested = Signal()
    new_notebook_requested = Signal()
    rename_notebook_requested = Signal(int, str) # notebook_id, notebook_name
    delete_notebook_requested = Signal(int, str) # notebook_id, notebook_name
    new_library_requested = Signal()
    note_selected = Signal(int) # note_id
    library_selected = Signal(str) # model_library_name
    workflow_library_selected = Signal(str) # workflow_library_name
    delete_workflow_library_requested = Signal(str) # workflow_library_name
    workflow_builder_requested = Signal()
    settings_requested = Signal()
    collapsed_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.incognito_active_state = False
        self.comfyui_visible = True
        self.current_palette = {}
        self.notebooks_data = []
        self.last_selected_notebook = None
        self.model_lib_names = []
        self.last_selected_model_lib = None
        self.workflow_lib_names = []
        self.last_selected_workflow_lib = None
        self.init_palette()

        self.is_collapsed = False
        try:
            import database
            self.is_collapsed = (database.get_setting("sidebar_collapsed", "0") == "1")
        except Exception:
            self.is_collapsed = False

        self.setFixedWidth(64 if self.is_collapsed else 230)
        self.init_ui()

    def init_palette(self):
        try:
            import database
            from ui.styles import get_palette
            theme_name = database.get_setting("theme", "Koyu Gece")
            custom_colors = database.get_setting("custom_theme_colors", "{}")
            self.current_palette = get_palette(theme_name, custom_colors)
        except Exception:
            self.current_palette = {}

    def get_active_color(self):
        return "#FFFFFF"

    def get_unified_color(self):
        try:
            from ui.styles import is_light
            bg = self.current_palette.get('bg_sidebar', self.current_palette.get('bg_card', '#17121C'))
            if is_light(bg):
                return "#1A1A1A"
        except Exception:
            pass
        return "#FFFFFF"

    def get_inactive_color(self):
        return self.get_unified_color()

    def apply_theme(self, palette: dict):
        self.current_palette = palette or {}
        if hasattr(self, 'active_item_type'):
            self.set_active_item(self.active_item_type)
        else:
            self.set_active_item('all_notes')

    def init_ui(self):
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
        self.main_layout.setContentsMargins(8, 10, 8, 12)
        self.main_layout.setSpacing(4)

        # --- HEADER (Brand + Lock + Collapse Button) ---
        self.header_widget = QFrame()
        self.header_widget.setObjectName("SidebarHeader")
        self.header_widget.setFixedSize(224, 40)
        self.header_widget.setStyleSheet("QFrame#SidebarHeader { background-color: transparent; border: none; }")
        
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(4, 2, 4, 2)
        self.header_layout.setSpacing(8)

        # Brand application vector logo (nav_concept.png)
        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("SidebarBrandLogo")
        self.brand_logo.setFixedSize(28, 28)
        self.brand_logo.setScaledContents(True)
        self.brand_logo.setCursor(Qt.PointingHandCursor)
        self.brand_logo.setPixmap(get_pixmap("brand", self.get_unified_color(), 28))
        self.brand_logo.mousePressEvent = lambda e: (self.set_active_item('home'), self.home_requested.emit())

        # Brand label ("Vera Note")
        self.brand_label = QLabel("Vera Note")
        self.brand_label.setObjectName("SidebarTitle")
        self.brand_label.setCursor(Qt.PointingHandCursor)
        self.brand_label.mousePressEvent = lambda e: (self.set_active_item('home'), self.home_requested.emit())
        
        # Incognito detective badge
        self.lock_badge = QLabel()
        self.lock_badge.setObjectName("SidebarLockBadge")
        self.lock_badge.setFixedSize(20, 20)
        self.lock_badge.setScaledContents(True)
        self.lock_badge.setPixmap(get_pixmap("incognito", "#D7AEF5", 20))
        self.lock_badge.setToolTip(t("status_incognito_on"))
        self.lock_badge.setVisible(False)

        self.header_stretch = QWidget()
        self.header_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Collapse / Expand Rail Toggle Button (uses btn_sidebar.png)
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("SidebarCollapseBtn")
        self.collapse_btn.setFixedSize(28, 28)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setIcon(get_icon("sidebar", self.get_unified_color(), 18))
        self.collapse_btn.setIconSize(QSize(18, 18))
        self.collapse_btn.setToolTip(t("sidebar_collapse"))
        self.collapse_btn.clicked.connect(self.toggle_collapsed)

        self.header_layout.addWidget(self.brand_logo)
        self.header_layout.addWidget(self.brand_label)
        self.header_layout.addWidget(self.lock_badge)
        self.header_layout.addWidget(self.header_stretch)
        self.header_layout.addWidget(self.collapse_btn)
        self.main_layout.addWidget(self.header_widget, 0, Qt.AlignCenter)

        # Header Separator Line
        self.sep_header = QFrame()
        self.sep_header.setProperty("class", "SidebarDivider")
        self.sep_header.setFixedSize(224, 1)
        self.main_layout.addWidget(self.sep_header, 0, Qt.AlignCenter)

        # --- ANA SAYFA (HOME BUTTON) ---
        self.home_btn = QPushButton()
        self.home_btn.setObjectName("HomeBtn")
        self.home_btn.setFixedSize(224, 38)
        self.home_btn.setCursor(Qt.PointingHandCursor)
        self.home_btn.clicked.connect(lambda: (self.set_active_item('home'), self.home_requested.emit()))
        
        self.home_layout = QHBoxLayout(self.home_btn)
        self.home_layout.setContentsMargins(10, 0, 10, 0)
        self.home_layout.setSpacing(10)
        
        self.home_icon = QLabel()
        self.home_icon.setFixedSize(20, 20)
        self.home_icon.setScaledContents(True)
        self.home_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.home_icon.setPixmap(get_pixmap("home", self.get_unified_color(), 20))
        
        self.home_label = QLabel(t("home"))
        self.home_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.home_stretch = QWidget()
        self.home_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.home_layout.addWidget(self.home_icon, 0, Qt.AlignCenter)
        self.home_layout.addWidget(self.home_label)
        self.home_layout.addWidget(self.home_stretch)
        self.main_layout.addWidget(self.home_btn, 0, Qt.AlignCenter)

        # ==========================================
        # SECTION 1: NOTLAR
        # ==========================================
        self.notes_section_label = QLabel(t("sidebar_section_notes"))
        self.notes_section_label.setProperty("class", "SidebarSectionHeader")
        self.main_layout.addWidget(self.notes_section_label)

        # 1. Ajanda Button
        self.agenda_btn = QPushButton()
        self.agenda_btn.setObjectName("AgendaBtn")
        self.agenda_btn.setFixedSize(224, 38)
        self.agenda_btn.setCursor(Qt.PointingHandCursor)
        self.agenda_btn.clicked.connect(lambda: (self.set_active_item('agenda'), self.agenda_requested.emit()))
        
        self.agenda_layout = QHBoxLayout(self.agenda_btn)
        self.agenda_layout.setContentsMargins(10, 0, 10, 0)
        self.agenda_layout.setSpacing(10)
        
        self.agenda_icon = QLabel()
        self.agenda_icon.setFixedSize(20, 20)
        self.agenda_icon.setScaledContents(True)
        self.agenda_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.agenda_icon.setPixmap(get_pixmap("calendar", self.get_unified_color(), 20))
        
        self.agenda_label = QLabel(t("nav_agenda"))
        self.agenda_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.agenda_stretch = QWidget()
        self.agenda_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.agenda_layout.addWidget(self.agenda_icon, 0, Qt.AlignCenter)
        self.agenda_layout.addWidget(self.agenda_label)
        self.agenda_layout.addWidget(self.agenda_stretch)
        self.main_layout.addWidget(self.agenda_btn, 0, Qt.AlignCenter)

        # 2. Notlar Button (with Capsule Counter + 32x32 '+' button)
        self.all_notes_btn = QPushButton()
        self.all_notes_btn.setObjectName("AllNotesBtn")
        self.all_notes_btn.setFixedSize(224, 40)
        self.all_notes_btn.setCursor(Qt.PointingHandCursor)
        self.all_notes_btn.clicked.connect(lambda: (self.set_active_item('all_notes'), self.all_notes_requested.emit()))
        
        self.all_notes_layout = QHBoxLayout(self.all_notes_btn)
        self.all_notes_layout.setContentsMargins(10, 0, 4, 0)
        self.all_notes_layout.setSpacing(8)
        
        self.all_notes_icon = QLabel()
        self.all_notes_icon.setFixedSize(20, 20)
        self.all_notes_icon.setScaledContents(True)
        self.all_notes_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.all_notes_icon.setPixmap(get_pixmap("notes", self.get_unified_color(), 20))
        
        self.all_notes_label = QLabel(t("notes"))
        self.all_notes_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.all_notes_stretch = QWidget()
        self.all_notes_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.all_notes_badge = QLabel("0")
        self.all_notes_badge.setObjectName("AllNotesBadge")
        self.all_notes_badge.setAlignment(Qt.AlignCenter)
        self.all_notes_badge.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 32x32 '+' button to create new note directly from Notlar row
        self.new_note_mini_btn = QPushButton("+")
        self.new_note_mini_btn.setProperty("class", "SidebarMiniAddBtn")
        self.new_note_mini_btn.setFixedSize(32, 32)
        self.new_note_mini_btn.setCursor(Qt.PointingHandCursor)
        self.new_note_mini_btn.setToolTip(t("new_note"))
        self.new_note_mini_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_note_requested.emit()))

        # Backward compatibility alias
        self.new_note_btn = self.new_note_mini_btn
        self.new_note_icon = QLabel()
        self.new_note_label = QLabel()
        self.new_note_stretch = QWidget()
        
        self.all_notes_layout.addWidget(self.all_notes_icon, 0, Qt.AlignCenter)
        self.all_notes_layout.addWidget(self.all_notes_label)
        self.all_notes_layout.addWidget(self.all_notes_stretch)
        self.all_notes_layout.addWidget(self.all_notes_badge)
        self.all_notes_layout.addWidget(self.new_note_mini_btn)
        self.main_layout.addWidget(self.all_notes_btn, 0, Qt.AlignCenter)

        # 3. Not Defterleri (Notebooks) Header (with Capsule Counter + 32x32 '+' button)
        self.notebooks_header = QPushButton()
        self.notebooks_header.setObjectName("NotebooksHeaderBtn")
        self.notebooks_header.setFixedSize(224, 40)
        self.notebooks_header.setCursor(Qt.PointingHandCursor)
        self.notebooks_header.clicked.connect(self.on_notebooks_header_clicked)

        self.notebooks_h_layout = QHBoxLayout(self.notebooks_header)
        self.notebooks_h_layout.setContentsMargins(10, 0, 4, 0)
        self.notebooks_h_layout.setSpacing(8)

        self.notebooks_icon = QLabel()
        self.notebooks_icon.setFixedSize(20, 20)
        self.notebooks_icon.setScaledContents(True)
        self.notebooks_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.notebooks_icon.setPixmap(get_pixmap("notebooks", self.get_unified_color(), 20))

        self.notebooks_label = QLabel(t("notebooks_title"))
        self.notebooks_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.notebooks_stretch = QWidget()
        self.notebooks_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.notebooks_badge = QLabel("0")
        self.notebooks_badge.setObjectName("NotebooksBadge")
        self.notebooks_badge.setAlignment(Qt.AlignCenter)
        self.notebooks_badge.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 32x32 '+' button to create new notebook directly from Not Defterleri row
        self.new_notebook_mini_btn = QPushButton("+")
        self.new_notebook_mini_btn.setProperty("class", "SidebarMiniAddBtn")
        self.new_notebook_mini_btn.setFixedSize(32, 32)
        self.new_notebook_mini_btn.setCursor(Qt.PointingHandCursor)
        self.new_notebook_mini_btn.setToolTip(t("new_notebook"))
        self.new_notebook_mini_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_notebook_requested.emit()))

        # Backward compatibility aliases
        self.new_notebook_btn = self.new_notebook_mini_btn
        self.new_notebook_icon = QLabel()
        self.new_notebook_label = QLabel()

        self.notebooks_h_layout.addWidget(self.notebooks_icon, 0, Qt.AlignCenter)
        self.notebooks_h_layout.addWidget(self.notebooks_label)
        self.notebooks_h_layout.addWidget(self.notebooks_stretch)
        self.notebooks_h_layout.addWidget(self.notebooks_badge)
        self.notebooks_h_layout.addWidget(self.new_notebook_mini_btn)
        self.main_layout.addWidget(self.notebooks_header, 0, Qt.AlignCenter)

        # Tree Container for Notebooks (if user configures sidebar notebooks limit > 0)
        self.notebooks_tree_widget = QWidget()
        self.notebooks_tree_layout = QHBoxLayout(self.notebooks_tree_widget)
        self.notebooks_tree_layout.setContentsMargins(22, 0, 4, 0)
        self.notebooks_tree_layout.setSpacing(10)

        self.notebooks_tree_line = QFrame()
        self.notebooks_tree_line.setFixedWidth(2)
        self.notebooks_tree_line.setStyleSheet("background-color: #38383A; border: none; border-radius: 1px;")

        self.notebooks_list = StaticListWidget()
        self.notebooks_list.setObjectName("NotebooksList")
        self.notebooks_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notebooks_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.notebooks_list.setFocusPolicy(Qt.NoFocus)
        self.notebooks_list.itemClicked.connect(self.on_notebook_clicked)
        self.notebooks_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.notebooks_list.customContextMenuRequested.connect(self.on_notebook_context_menu)

        self.notebooks_tree_layout.addWidget(self.notebooks_tree_line)
        self.notebooks_tree_layout.addWidget(self.notebooks_list)
        self.notebooks_tree_widget.setVisible(False)
        self.main_layout.addWidget(self.notebooks_tree_widget)

        # 4. Çöp Kutusu Button (with Capsule Counter aligned with above rows)
        self.trash_btn = QPushButton()
        self.trash_btn.setObjectName("TrashBtn")
        self.trash_btn.setFixedSize(224, 40)
        self.trash_btn.setCursor(Qt.PointingHandCursor)
        self.trash_btn.clicked.connect(lambda: (self.set_active_item('trash'), self.trash_requested.emit()))
        
        self.trash_layout = QHBoxLayout(self.trash_btn)
        self.trash_layout.setContentsMargins(10, 0, 4, 0)
        self.trash_layout.setSpacing(8)
        
        self.trash_icon = QLabel()
        self.trash_icon.setFixedSize(20, 20)
        self.trash_icon.setScaledContents(True)
        self.trash_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.trash_icon.setPixmap(get_pixmap("trash", self.get_unified_color(), 20))
        
        self.trash_label = QLabel(t("trash"))
        self.trash_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.trash_stretch = QWidget()
        self.trash_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.trash_badge = QLabel("0")
        self.trash_badge.setObjectName("TrashBadge")
        self.trash_badge.setAlignment(Qt.AlignCenter)
        self.trash_badge.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 32px invisible spacer so counter aligns identically with rows with a 32x32 '+' button
        self.trash_spacer = QWidget()
        self.trash_spacer.setFixedSize(32, 32)
        
        self.trash_layout.addWidget(self.trash_icon, 0, Qt.AlignCenter)
        self.trash_layout.addWidget(self.trash_label)
        self.trash_layout.addWidget(self.trash_stretch)
        self.trash_layout.addWidget(self.trash_badge)
        self.trash_layout.addWidget(self.trash_spacer)
        self.main_layout.addWidget(self.trash_btn, 0, Qt.AlignCenter)

        # Separator Line 1 (between NOTLAR and AI & ÜRETİM)
        self.sep_line_1 = QFrame()
        self.sep_line_1.setProperty("class", "SidebarDivider")
        self.sep_line_1.setFixedSize(224, 1)
        self.main_layout.addWidget(self.sep_line_1, 0, Qt.AlignCenter)

        # ==========================================
        # SECTION 2: AI & ÜRETİM
        # ==========================================
        self.ai_section_label = QLabel(t("sidebar_section_ai"))
        self.ai_section_label.setProperty("class", "SidebarSectionHeader")
        self.main_layout.addWidget(self.ai_section_label)

        # 5. İş Akışı Oluşturucu (Special Outlined Card Button)
        self.workflow_builder_btn = QPushButton()
        self.workflow_builder_btn.setObjectName("WorkflowBuilderBtn")
        self.workflow_builder_btn.setFixedSize(224, 42)
        self.workflow_builder_btn.setCursor(Qt.PointingHandCursor)
        self.workflow_builder_btn.clicked.connect(lambda: (self.clear_list_selections(), self.set_active_item('workflow_builder'), self.workflow_builder_requested.emit()))

        self.wf_builder_layout = QHBoxLayout(self.workflow_builder_btn)
        self.wf_builder_layout.setContentsMargins(10, 0, 10, 0)
        self.wf_builder_layout.setSpacing(10)

        self.wf_builder_icon = QLabel()
        self.wf_builder_icon.setFixedSize(20, 20)
        self.wf_builder_icon.setScaledContents(True)
        self.wf_builder_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.wf_builder_icon.setPixmap(get_pixmap("builder", self.get_unified_color(), 20))

        self.wf_builder_label = QLabel(t("workflow_builder"))
        self.wf_builder_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.wf_builder_stretch = QWidget()
        self.wf_builder_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.wf_builder_layout.addWidget(self.wf_builder_icon, 0, Qt.AlignCenter)
        self.wf_builder_layout.addWidget(self.wf_builder_label)
        self.wf_builder_layout.addWidget(self.wf_builder_stretch)
        self.main_layout.addWidget(self.workflow_builder_btn, 0, Qt.AlignCenter)

        # 6. İş Akışları Header (with Capsule Counter + 32x32 '+' button)
        self.lib_header = QPushButton()
        self.lib_header.setObjectName("LibHeaderBtn")
        self.lib_header.setFixedSize(224, 40)
        self.lib_header.setCursor(Qt.PointingHandCursor)
        self.lib_header.clicked.connect(self.on_lib_header_clicked)
        
        self.lib_h_layout = QHBoxLayout(self.lib_header)
        self.lib_h_layout.setContentsMargins(10, 0, 4, 0)
        self.lib_h_layout.setSpacing(8)
        
        self.lib_icon = QLabel()
        self.lib_icon.setFixedSize(20, 20)
        self.lib_icon.setScaledContents(True)
        self.lib_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lib_icon.setPixmap(get_pixmap("workflows", self.get_unified_color(), 20))

        self.lib_label = QLabel(t("workflows_title"))
        self.lib_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lib_stretch = QWidget()
        self.lib_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.workflows_badge = QLabel("0")
        self.workflows_badge.setObjectName("WorkflowsBadge")
        self.workflows_badge.setAlignment(Qt.AlignCenter)
        self.workflows_badge.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 32x32 '+' button to create new workflow library directly from İş Akışları row
        self.new_lib_mini_btn = QPushButton("+")
        self.new_lib_mini_btn.setProperty("class", "SidebarMiniAddBtn")
        self.new_lib_mini_btn.setFixedSize(32, 32)
        self.new_lib_mini_btn.setCursor(Qt.PointingHandCursor)
        self.new_lib_mini_btn.setToolTip(t("new_lib"))
        self.new_lib_mini_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_library_requested.emit()))

        # Backward compatibility alias
        self.new_lib_btn = self.new_lib_mini_btn

        self.lib_h_layout.addWidget(self.lib_icon, 0, Qt.AlignCenter)
        self.lib_h_layout.addWidget(self.lib_label)
        self.lib_h_layout.addWidget(self.lib_stretch)
        self.lib_h_layout.addWidget(self.workflows_badge)
        self.lib_h_layout.addWidget(self.new_lib_mini_btn)
        self.main_layout.addWidget(self.lib_header, 0, Qt.AlignCenter)

        # Workflow Libraries Tree Container (hidden if only 1 general library, or displayed with tree line)
        self.workflows_tree_widget = QWidget()
        self.workflows_tree_layout = QHBoxLayout(self.workflows_tree_widget)
        self.workflows_tree_layout.setContentsMargins(22, 0, 4, 0)
        self.workflows_tree_layout.setSpacing(10)

        self.workflows_tree_line = QFrame()
        self.workflows_tree_line.setFixedWidth(2)
        self.workflows_tree_line.setStyleSheet("background-color: #38383A; border: none; border-radius: 1px;")

        self.libraries_list = StaticListWidget()
        self.libraries_list.setObjectName("LibrariesList")
        self.libraries_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.libraries_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.libraries_list.setFocusPolicy(Qt.NoFocus)
        self.libraries_list.itemClicked.connect(self.on_library_clicked)
        self.libraries_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.libraries_list.customContextMenuRequested.connect(self.on_workflow_lib_context_menu)

        self.workflows_tree_layout.addWidget(self.workflows_tree_line)
        self.workflows_tree_layout.addWidget(self.libraries_list)
        self.workflows_tree_widget.setVisible(False)
        self.main_layout.addWidget(self.workflows_tree_widget)

        # 7. Modeller Category Header
        self.models_header = QPushButton()
        self.models_header.setObjectName("ModelsHeaderBtn")
        self.models_header.setFixedSize(224, 38)
        self.models_header.setCursor(Qt.PointingHandCursor)
        self.models_header.clicked.connect(self.on_models_header_clicked)
        
        self.models_h_layout = QHBoxLayout(self.models_header)
        self.models_h_layout.setContentsMargins(10, 0, 10, 0)
        self.models_h_layout.setSpacing(10)
        
        self.models_icon = QLabel()
        self.models_icon.setFixedSize(20, 20)
        self.models_icon.setScaledContents(True)
        self.models_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.models_icon.setPixmap(get_pixmap("models", self.get_unified_color(), 20))
        
        self.models_label = QLabel(t("models_title"))
        self.models_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.models_stretch = QWidget()
        self.models_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.models_h_layout.addWidget(self.models_icon, 0, Qt.AlignCenter)
        self.models_h_layout.addWidget(self.models_label)
        self.models_h_layout.addWidget(self.models_stretch)
        self.main_layout.addWidget(self.models_header, 0, Qt.AlignCenter)

        # Tree Container for Model Libraries with Vertical Guide Line
        self.models_tree_widget = QWidget()
        self.models_tree_layout = QHBoxLayout(self.models_tree_widget)
        self.models_tree_layout.setContentsMargins(22, 0, 4, 0)
        self.models_tree_layout.setSpacing(10)

        self.models_tree_line = QFrame()
        self.models_tree_line.setFixedWidth(2)
        self.models_tree_line.setStyleSheet("background-color: #38383A; border: none; border-radius: 1px;")

        self.models_list = StaticListWidget()
        self.models_list.setObjectName("ModelsList")
        self.models_list.setWordWrap(True)
        self.models_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.models_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.models_list.setFocusPolicy(Qt.NoFocus)
        self.models_list.itemClicked.connect(self.on_model_clicked)

        self.models_tree_layout.addWidget(self.models_tree_line)
        self.models_tree_layout.addWidget(self.models_list)
        self.main_layout.addWidget(self.models_tree_widget)

        # Stretch to push settings all the way to the very bottom
        self.main_layout.addStretch()

        # ==========================================
        # SECTION 3: AYARLAR (At the bottom)
        # ==========================================
        self.settings_section_label = QLabel(t("sidebar_section_settings"))
        self.settings_section_label.setProperty("class", "SidebarSectionHeader")
        self.main_layout.addWidget(self.settings_section_label)

        # 8. Ayarlar Button
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setFixedSize(224, 38)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.clicked.connect(lambda: (self.set_active_item('settings'), self.settings_requested.emit()))
        
        self.settings_layout = QHBoxLayout(self.settings_btn)
        self.settings_layout.setContentsMargins(10, 0, 10, 0)
        self.settings_layout.setSpacing(10)
        
        self.settings_icon = QLabel()
        self.settings_icon.setFixedSize(20, 20)
        self.settings_icon.setScaledContents(True)
        self.settings_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.settings_icon.setPixmap(get_pixmap("settings", self.get_unified_color(), 20))
        
        self.settings_label = QLabel(t("settings"))
        self.settings_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.settings_stretch = QWidget()
        self.settings_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.settings_layout.addWidget(self.settings_icon, 0, Qt.AlignCenter)
        self.settings_layout.addWidget(self.settings_label)
        self.settings_layout.addWidget(self.settings_stretch)
        self.main_layout.addWidget(self.settings_btn, 0, Qt.AlignCenter)

        self.scroll_area.setWidget(self.container)
        outer_layout.addWidget(self.scroll_area)

        # Apply initial collapsed rail state
        self.set_collapsed(self.is_collapsed)
        # Default active state: all_notes
        self.set_active_item('all_notes')

    def toggle_collapsed(self):
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        
        try:
            import database
            database.set_setting("sidebar_collapsed", "1" if collapsed else "0")
        except Exception:
            pass

        target_w = 64 if collapsed else 240
        self.setFixedWidth(target_w)

        # Toggle inner stretch widgets
        for st in [self.header_stretch, self.home_stretch, self.agenda_stretch, self.all_notes_stretch,
                   self.notebooks_stretch, self.trash_stretch, self.wf_builder_stretch,
                   self.lib_stretch, self.models_stretch, self.settings_stretch]:
            if st:
                st.setVisible(not collapsed)

        # Toggle section labels and mini '+' buttons
        for lbl in [self.notes_section_label, self.ai_section_label, self.settings_section_label]:
            if lbl:
                lbl.setVisible(not collapsed and (not (lbl == self.ai_section_label and not self.comfyui_visible)))

        for mini in [self.new_note_mini_btn, self.new_notebook_mini_btn, self.new_lib_mini_btn]:
            if mini:
                mini.setVisible(not collapsed)

        if hasattr(self, 'trash_spacer'):
            self.trash_spacer.setVisible(not collapsed)

        if collapsed:
            # Compact Navigation Rail
            self.main_layout.setContentsMargins(10, 10, 10, 10)
            self.main_layout.setSpacing(6)
            
            # Header
            self.header_widget.setFixedSize(44, 38)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setSpacing(0)
            self.brand_logo.setVisible(False)
            self.brand_label.setVisible(False)
            self.lock_badge.setVisible(False)
            self.collapse_btn.setFixedSize(44, 38)
            self.collapse_btn.setToolTip(f"{t('sidebar_expand')} • {t('status_incognito_on')}" if self.incognito_active_state else t("sidebar_expand"))
            
            # Small centered separators
            self.sep_header.setFixedWidth(36)
            self.sep_line_1.setFixedWidth(36)

            btn_w, btn_h = 44, 38

            # Home
            self.home_btn.setFixedSize(btn_w, btn_h)
            self.home_label.setVisible(False)
            self.home_layout.setContentsMargins(0, 0, 0, 0)
            self.home_btn.setToolTip(t("home"))

            # Agenda
            self.agenda_btn.setFixedSize(btn_w, btn_h)
            self.agenda_label.setVisible(False)
            self.agenda_layout.setContentsMargins(0, 0, 0, 0)
            self.agenda_btn.setToolTip(t("nav_agenda"))

            # All notes
            self.all_notes_btn.setFixedSize(btn_w, btn_h)
            self.all_notes_label.setVisible(False)
            self.all_notes_badge.setVisible(False)
            self.all_notes_layout.setContentsMargins(0, 0, 0, 0)
            self.all_notes_btn.setToolTip(f"{t('notes')} ({self.all_notes_badge.text()})")

            # Notebooks
            self.notebooks_header.setFixedSize(btn_w, btn_h)
            self.notebooks_label.setVisible(False)
            self.notebooks_badge.setVisible(False)
            self.notebooks_h_layout.setContentsMargins(0, 0, 0, 0)
            self.notebooks_header.setToolTip(f"{t('notebooks_title')} ({self.notebooks_badge.text()})")
            self.notebooks_tree_widget.setVisible(False)

            # Trash
            self.trash_btn.setFixedSize(btn_w, btn_h)
            self.trash_label.setVisible(False)
            self.trash_badge.setVisible(False)
            self.trash_layout.setContentsMargins(0, 0, 0, 0)
            self.trash_btn.setToolTip(f"{t('trash')} ({self.trash_badge.text()})")

            # Workflow Builder
            self.workflow_builder_btn.setFixedSize(btn_w, btn_h)
            self.wf_builder_label.setVisible(False)
            self.wf_builder_layout.setContentsMargins(0, 0, 0, 0)
            self.workflow_builder_btn.setToolTip(t("workflow_builder"))

            # Workflows
            self.lib_header.setFixedSize(btn_w, btn_h)
            self.lib_label.setVisible(False)
            self.workflows_badge.setVisible(False)
            self.lib_h_layout.setContentsMargins(0, 0, 0, 0)
            self.lib_header.setToolTip(f"{t('workflows_title')} ({self.workflows_badge.text()})")
            self.workflows_tree_widget.setVisible(False)

            # Models
            self.models_header.setFixedSize(btn_w, btn_h)
            self.models_label.setVisible(False)
            self.models_h_layout.setContentsMargins(0, 0, 0, 0)
            curr_model = getattr(self, 'last_selected_model_lib', None) or (self.model_lib_names[0] if getattr(self, 'model_lib_names', None) else "")
            self.models_header.setToolTip(f"{t('models_title')}: {self.tr_lib_name(curr_model)}" if curr_model else t("models_title"))
            self.models_tree_widget.setVisible(False)

            # Settings
            self.settings_btn.setFixedSize(btn_w, btn_h)
            self.settings_label.setVisible(False)
            self.settings_layout.setContentsMargins(0, 0, 0, 0)
            self.settings_btn.setToolTip(t("settings"))
        else:
            # Expanded Sidebar
            self.main_layout.setContentsMargins(8, 10, 8, 12)
            self.main_layout.setSpacing(4)
            
            # Header
            self.header_widget.setFixedSize(224, 40)
            self.header_layout.setContentsMargins(4, 2, 4, 2)
            self.header_layout.setSpacing(8)
            self.brand_logo.setVisible(True)
            self.brand_label.setVisible(True)
            self.lock_badge.setVisible(self.incognito_active_state)
            self.collapse_btn.setFixedSize(28, 28)
            self.collapse_btn.setToolTip(t("sidebar_collapse"))
            
            # Separators
            self.sep_header.setFixedWidth(224)
            self.sep_line_1.setFixedWidth(224)

            btn_w = 224

            # Home
            self.home_btn.setFixedSize(btn_w, 38)
            self.home_label.setVisible(True)
            self.home_layout.setContentsMargins(10, 0, 10, 0)
            self.home_btn.setToolTip("")

            # Agenda
            self.agenda_btn.setFixedSize(btn_w, 38)
            self.agenda_label.setVisible(True)
            self.agenda_layout.setContentsMargins(10, 0, 10, 0)
            self.agenda_btn.setToolTip("")

            # All notes
            self.all_notes_btn.setFixedSize(btn_w, 40)
            self.all_notes_label.setVisible(True)
            self.all_notes_badge.setVisible(True)
            self.all_notes_layout.setContentsMargins(10, 0, 4, 0)
            self.all_notes_btn.setToolTip("")

            # Notebooks
            self.notebooks_header.setFixedSize(btn_w, 40)
            self.notebooks_label.setVisible(True)
            self.notebooks_badge.setVisible(True)
            self.notebooks_h_layout.setContentsMargins(10, 0, 4, 0)
            self.notebooks_header.setToolTip("")
            self.notebooks_tree_widget.setVisible(bool(self.notebooks_data) and self.notebooks_list.count() > 0)

            # Trash
            self.trash_btn.setFixedSize(btn_w, 40)
            self.trash_label.setVisible(True)
            self.trash_badge.setVisible(True)
            self.trash_layout.setContentsMargins(10, 0, 4, 0)
            self.trash_btn.setToolTip("")

            # Workflow Builder
            self.workflow_builder_btn.setFixedSize(btn_w, 42)
            self.wf_builder_label.setVisible(True)
            self.wf_builder_layout.setContentsMargins(10, 0, 10, 0)
            self.workflow_builder_btn.setToolTip("")
            self.workflow_builder_btn.setVisible(self.comfyui_visible)

            # Workflows
            self.lib_header.setFixedSize(btn_w, 40)
            self.lib_label.setVisible(True)
            self.workflows_badge.setVisible(True)
            self.lib_h_layout.setContentsMargins(10, 0, 4, 0)
            self.lib_header.setToolTip("")
            self.lib_header.setVisible(self.comfyui_visible)
            self.workflows_tree_widget.setVisible(self.comfyui_visible and len(self.workflow_lib_names) > 1)

            # Models
            self.models_header.setFixedSize(btn_w, 38)
            self.models_label.setVisible(True)
            self.models_h_layout.setContentsMargins(10, 0, 10, 0)
            self.models_header.setToolTip("")
            self.models_header.setVisible(self.comfyui_visible)
            self.models_tree_widget.setVisible(self.comfyui_visible and self.models_list.count() > 0)

            # Settings
            self.settings_btn.setFixedSize(btn_w, 38)
            self.settings_label.setVisible(True)
            self.settings_layout.setContentsMargins(10, 0, 10, 0)
            self.settings_btn.setToolTip("")

        self.collapsed_toggled.emit(collapsed)

    def on_models_header_clicked(self):
        if not hasattr(self, 'model_lib_names') or not self.model_lib_names:
            return

        if self.is_collapsed:
            if self.active_item_type == 'model' and getattr(self, 'last_selected_model_lib', None) in self.model_lib_names:
                current_idx = self.model_lib_names.index(self.last_selected_model_lib)
                next_idx = (current_idx + 1) % len(self.model_lib_names)
            else:
                next_idx = 0
            
            target = self.model_lib_names[next_idx]
            self.last_selected_model_lib = target
            self.set_active_item('model', target)
            self.models_header.setToolTip(f"{t('models_title')}: {self.tr_lib_name(target)}")
            self.library_selected.emit(target)
        else:
            if self.active_item_type == 'model' and getattr(self, 'last_selected_model_lib', None) in self.model_lib_names and len(self.model_lib_names) > 1:
                current_idx = self.model_lib_names.index(self.last_selected_model_lib)
                next_idx = (current_idx + 1) % len(self.model_lib_names)
            elif getattr(self, 'last_selected_model_lib', None) in self.model_lib_names:
                next_idx = self.model_lib_names.index(self.last_selected_model_lib)
            else:
                next_idx = 0

            target = self.model_lib_names[next_idx]
            self.last_selected_model_lib = target
            self.set_active_item('model', target)
            self.library_selected.emit(target)

    def on_lib_header_clicked(self):
        if not hasattr(self, 'workflow_lib_names') or not self.workflow_lib_names:
            self.workflow_lib_names = ["Genel"]

        if self.is_collapsed:
            if self.active_item_type == 'workflow' and getattr(self, 'last_selected_workflow_lib', None) in self.workflow_lib_names:
                current_idx = self.workflow_lib_names.index(self.last_selected_workflow_lib)
                next_idx = (current_idx + 1) % len(self.workflow_lib_names)
            else:
                next_idx = 0
            
            target = self.workflow_lib_names[next_idx]
            self.last_selected_workflow_lib = target
            self.set_active_item('workflow', target)
            self.lib_header.setToolTip(f"{t('workflows_title')}: {self.tr_lib_name(target)}")
            self.workflow_library_selected.emit(target)
        else:
            target = self.last_selected_workflow_lib if (getattr(self, 'last_selected_workflow_lib', None) in self.workflow_lib_names) else self.workflow_lib_names[0]
            self.set_active_item('workflow', target)
            self.workflow_library_selected.emit(target)

    def set_active_item(self, item_type, name=None):
        self.active_item_type = item_type
        active_map = {
            self.home_btn: (item_type == 'home'),
            self.agenda_btn: (item_type == 'agenda'),
            self.all_notes_btn: (item_type == 'all_notes'),
            self.notebooks_header: (item_type in ('all_notebooks', 'notebook')),
            self.trash_btn: (item_type == 'trash'),
            self.settings_btn: (item_type == 'settings'),
            self.models_header: (item_type == 'model'),
            self.lib_header: (item_type == 'workflow'),
            self.workflow_builder_btn: (item_type == 'workflow_builder'),
        }
        for btn, is_active in active_map.items():
            if not btn:
                continue
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        # Update mini '+' button parent-active states
        self.new_note_mini_btn.setProperty("parent_active", item_type == 'all_notes')
        self.new_note_mini_btn.style().unpolish(self.new_note_mini_btn)
        self.new_note_mini_btn.style().polish(self.new_note_mini_btn)

        self.new_notebook_mini_btn.setProperty("parent_active", item_type in ('all_notebooks', 'notebook'))
        self.new_notebook_mini_btn.style().unpolish(self.new_notebook_mini_btn)
        self.new_notebook_mini_btn.style().polish(self.new_notebook_mini_btn)

        self.new_lib_mini_btn.setProperty("parent_active", item_type == 'workflow')
        self.new_lib_mini_btn.style().unpolish(self.new_lib_mini_btn)
        self.new_lib_mini_btn.style().polish(self.new_lib_mini_btn)

        # Update icon pixmaps
        active_color = self.get_active_color()
        unified_color = self.get_unified_color()

        self.brand_logo.setPixmap(get_pixmap("brand", unified_color, 28))
        self.collapse_btn.setIcon(get_icon("sidebar", active_color if self.is_collapsed else unified_color, 18))
        self.home_icon.setPixmap(get_pixmap("home", active_color if item_type == 'home' else unified_color, 20))
        self.agenda_icon.setPixmap(get_pixmap("calendar", active_color if item_type == 'agenda' else unified_color, 20))
        self.all_notes_icon.setPixmap(get_pixmap("notes", active_color if item_type == 'all_notes' else unified_color, 20))
        self.notebooks_icon.setPixmap(get_pixmap("notebooks", active_color if item_type in ('all_notebooks', 'notebook') else unified_color, 20))
        self.trash_icon.setPixmap(get_pixmap("trash", active_color if item_type == 'trash' else unified_color, 20))
        self.wf_builder_icon.setPixmap(get_pixmap("builder", active_color if item_type == 'workflow_builder' else unified_color, 20))
        self.lib_icon.setPixmap(get_pixmap("workflows", active_color if item_type == 'workflow' else unified_color, 20))
        self.models_icon.setPixmap(get_pixmap("models", active_color if item_type == 'model' else unified_color, 20))
        self.settings_icon.setPixmap(get_pixmap("settings", active_color if item_type == 'settings' else unified_color, 20))

        if item_type == 'notebook':
            if name is not None and hasattr(self, 'notebooks_list'):
                for r in range(self.notebooks_list.count()):
                    it = self.notebooks_list.item(r)
                    if it and it.data(Qt.UserRole) == name:
                        self.notebooks_list.setCurrentRow(r)
                        break
        else:
            if hasattr(self, 'notebooks_list'):
                self.notebooks_list.clearSelection()

        if item_type == 'model':
            if name:
                self.last_selected_model_lib = name
                if hasattr(self, 'model_lib_names') and name in self.model_lib_names:
                    idx = self.model_lib_names.index(name)
                    self.models_list.setCurrentRow(idx)
            if self.is_collapsed and getattr(self, 'last_selected_model_lib', None):
                self.models_header.setToolTip(f"{t('models_title')}: {self.tr_lib_name(self.last_selected_model_lib)}")
        else:
            self.models_list.clearSelection()

        if item_type == 'workflow':
            if name:
                self.last_selected_workflow_lib = name
                if hasattr(self, 'workflow_lib_names') and name in self.workflow_lib_names:
                    idx = self.workflow_lib_names.index(name)
                    self.libraries_list.setCurrentRow(idx)
            if self.is_collapsed and getattr(self, 'last_selected_workflow_lib', None):
                self.lib_header.setToolTip(f"{t('workflows_title')}: {self.tr_lib_name(self.last_selected_workflow_lib)}")
        else:
            self.libraries_list.clearSelection()

    def retranslate_ui(self):
        self.home_label.setText(t("home"))
        self.notes_section_label.setText(t("sidebar_section_notes"))
        self.ai_section_label.setText(t("sidebar_section_ai"))
        self.settings_section_label.setText(t("sidebar_section_settings"))

        self.agenda_label.setText(t("nav_agenda"))
        self.all_notes_label.setText(t("notes"))
        self.notebooks_label.setText(t("notebooks_title"))
        self.trash_label.setText(t("trash"))
        self.wf_builder_label.setText(t("workflow_builder"))
        self.lib_label.setText(t("workflows_title"))
        self.models_label.setText(t("models_title"))
        self.settings_label.setText(t("settings"))

        self.new_note_mini_btn.setToolTip(t("new_note"))
        self.new_notebook_mini_btn.setToolTip(t("new_notebook"))
        self.new_lib_mini_btn.setToolTip(t("new_lib"))

        self.collapse_btn.setToolTip(t("sidebar_expand") if self.is_collapsed else t("sidebar_collapse"))
        self.set_incognito_active(self.incognito_active_state)

        if hasattr(self, 'active_item_type'):
            self.set_active_item(self.active_item_type)
        if hasattr(self, 'comfyui_visible'):
            self.set_comfyui_visible(self.comfyui_visible)
        if hasattr(self, 'last_models_data') and self.last_models_data:
            self.update_models_list(self.last_models_data, getattr(self, 'last_selected_model_lib', None))
        if hasattr(self, 'last_workflow_libs_data') and self.last_workflow_libs_data:
            self.update_workflow_libraries_list(self.last_workflow_libs_data, getattr(self, 'last_selected_workflow_lib', None))
        if hasattr(self, 'notebooks_data'):
            selected_id = self.last_selected_notebook['id'] if getattr(self, 'last_selected_notebook', None) else None
            self.update_notebooks_list(self.notebooks_data, selected_id)

    def set_comfyui_visible(self, visible: bool):
        self.comfyui_visible = visible
        self.ai_section_label.setVisible(visible and not self.is_collapsed)
        self.sep_line_1.setVisible(visible and not self.is_collapsed)
        self.workflow_builder_btn.setVisible(visible)
        self.lib_header.setVisible(visible)
        self.workflows_tree_widget.setVisible(visible and not self.is_collapsed and len(self.workflow_lib_names) > 1)
        self.models_header.setVisible(visible)
        self.models_tree_widget.setVisible(visible and not self.is_collapsed and self.models_list.count() > 0)

    def tr_lib_name(self, name):
        if name == "Lora Modelleri":
            return "Lora Models" if get_lang() == "en" else "Lora Modelleri"
        elif name == "Checkpoint Modelleri":
            return "Checkpoint Models" if get_lang() == "en" else "Checkpoint Modelleri"
        elif name == "Favoriler":
            return "Favorites" if get_lang() == "en" else "Favoriler"
        elif name == "Genel":
            return "General" if get_lang() == "en" else "Genel"
        return name

    def update_notes_count(self, count):
        self.all_notes_badge.setText(str(count))
        if self.is_collapsed:
            self.all_notes_btn.setToolTip(f"{t('notes')} ({count})")

    def update_trash_count(self, count):
        self.trash_badge.setText(str(count))
        if self.is_collapsed:
            self.trash_btn.setToolTip(f"{t('trash')} ({count})")

    def update_models_list(self, models_with_counts, selected_model_lib=None):
        self.last_models_data = models_with_counts
        self.last_selected_model_lib = selected_model_lib or (models_with_counts[0][0] if models_with_counts else None)
        self.models_list.clear()
        self.model_lib_names = []
        for lib_name, count in models_with_counts:
            # Format as: Checkpoint Modelleri\n(19) or inline based on width
            item = QListWidgetItem(f"{self.tr_lib_name(lib_name)}\n({count})" if len(lib_name) > 14 else f"{self.tr_lib_name(lib_name)} ({count})")
            self.models_list.addItem(item)
            self.model_lib_names.append(lib_name)
            if self.last_selected_model_lib and lib_name == self.last_selected_model_lib:
                self.models_list.setCurrentRow(self.models_list.count() - 1)
        
        count = max(1, len(models_with_counts))
        self.models_list.setFixedHeight(count * 46 + 6)
        if self.is_collapsed or (hasattr(self, 'comfyui_visible') and not self.comfyui_visible):
            self.models_tree_widget.setVisible(False)
        else:
            self.models_tree_widget.setVisible(True)

    def update_workflow_libraries_list(self, workflow_libs_with_counts, selected_workflow_lib=None):
        self.last_workflow_libs_data = workflow_libs_with_counts
        self.last_selected_workflow_lib = selected_workflow_lib or (workflow_libs_with_counts[0][0] if workflow_libs_with_counts else None)
        
        # Total workflows count
        total_count = sum(c for _, c in workflow_libs_with_counts)
        self.workflows_badge.setText(str(total_count))
        if self.is_collapsed:
            self.lib_header.setToolTip(f"{t('workflows_title')} ({total_count})")

        self.libraries_list.clear()
        self.workflow_lib_names = []
        for lib_name, count in workflow_libs_with_counts:
            item = QListWidgetItem(f"{self.tr_lib_name(lib_name)} ({count})")
            self.libraries_list.addItem(item)
            self.workflow_lib_names.append(lib_name)
            if self.last_selected_workflow_lib and lib_name == self.last_selected_workflow_lib:
                self.libraries_list.setCurrentRow(self.libraries_list.count() - 1)

        count = max(1, len(workflow_libs_with_counts))
        self.libraries_list.setFixedHeight(count * 34 + 4)
        show_tree = len(workflow_libs_with_counts) > 1 and not self.is_collapsed and (not hasattr(self, 'comfyui_visible') or self.comfyui_visible)
        self.workflows_tree_widget.setVisible(show_tree)

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

    def on_notebooks_header_clicked(self):
        self.set_active_item('all_notebooks')
        self.all_notebooks_requested.emit()

    def on_notebook_clicked(self, item):
        nb_id = item.data(Qt.UserRole)
        if nb_id == -1:
            self.set_active_item('all_notebooks')
            self.all_notebooks_requested.emit()
            return

        nb = next((n for n in self.notebooks_data if n['id'] == nb_id), None)
        if nb:
            self.last_selected_notebook = nb
            self.set_active_item('notebook', nb['id'])
            self.notebook_selected.emit(nb['id'], nb['name'])

    def on_notebook_context_menu(self, pos):
        item = self.notebooks_list.itemAt(pos)
        if not item:
            return
        nb_id = item.data(Qt.UserRole)
        if not nb_id or nb_id == -1:
            return
        nb = next((n for n in self.notebooks_data if n['id'] == nb_id), None)
        if not nb:
            return
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        rename_act = menu.addAction(t("notebook_rename"))
        del_act = menu.addAction(t("notebook_delete"))
        chosen = menu.exec(QCursor.pos())
        if chosen == rename_act:
            self.rename_notebook_requested.emit(nb_id, nb['name'])
        elif chosen == del_act:
            self.delete_notebook_requested.emit(nb_id, nb['name'])

    def update_notebooks_list(self, notebooks, active_id=None, selected_notebook_id=None, limit=None):
        target_active_id = active_id if active_id is not None else selected_notebook_id
        self.notebooks_data = notebooks or []
        self.notebooks_list.clear()

        self.notebooks_badge.setText(str(len(self.notebooks_data)))
        if self.is_collapsed:
            self.notebooks_header.setToolTip(f"{t('notebooks_title')} ({len(self.notebooks_data)})")

        if limit is None:
            try:
                import database
                limit = int(database.get_setting("sidebar_notebooks_limit", "0"))
            except Exception:
                limit = 0
        else:
            try:
                limit = int(limit)
            except Exception:
                limit = 0

        if limit <= 0:
            self.notebooks_list.clear()
            self.notebooks_list.setFixedHeight(0)
            self.notebooks_tree_widget.setVisible(False)
            return

        display_items = self.notebooks_data[:limit]
        for nb in display_items:
            count = nb.get('note_count', 0)
            item = QListWidgetItem(f"{nb['name']} ({count})")
            item.setData(Qt.UserRole, nb['id'])
            self.notebooks_list.addItem(item)
            if target_active_id and nb['id'] == target_active_id:
                self.last_selected_notebook = nb
                self.notebooks_list.setCurrentRow(self.notebooks_list.count() - 1)

        count = self.notebooks_list.count()
        if count == 0 or self.is_collapsed or not self.notebooks_data:
            self.notebooks_list.setFixedHeight(0)
            self.notebooks_tree_widget.setVisible(False)
        else:
            self.notebooks_list.setFixedHeight(count * 34 + 4)
            self.notebooks_tree_widget.setVisible(True)

    def clear_list_selections(self):
        self.models_list.clearSelection()
        self.libraries_list.clearSelection()
        if hasattr(self, 'notebooks_list'):
            self.notebooks_list.clearSelection()

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
            self.brand_label.setStyleSheet("color: #D7AEF5; font-weight: bold;")
            self.lock_badge.setVisible(not self.is_collapsed)
            if self.is_collapsed:
                self.collapse_btn.setToolTip(f"{t('sidebar_expand')} • {t('status_incognito_on')}")
        else:
            self.header_widget.setStyleSheet("""
                QFrame#SidebarHeader {
                    background-color: transparent;
                    border: none;
                }
            """)
            self.brand_label.setStyleSheet("")
            self.lock_badge.setVisible(False)
            if self.is_collapsed:
                self.collapse_btn.setToolTip(t("sidebar_expand"))
