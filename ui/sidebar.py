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
    new_library_requested = Signal()
    note_selected = Signal(int) # note_id
    library_selected = Signal(str) # model_library_name
    workflow_library_selected = Signal(str) # workflow_library_name
    delete_workflow_library_requested = Signal(str) # workflow_library_name
    settings_requested = Signal()
    collapsed_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SidebarWidget")
        self.incognito_active_state = False
        self.comfyui_visible = True
        self.current_palette = {}
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

        self.setFixedWidth(64 if self.is_collapsed else 260)
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
        self.main_layout.setContentsMargins(10, 12, 10, 12)
        self.main_layout.setSpacing(8)

        # --- HEADER (Brand + Lock + Collapse Button) ---
        self.header_widget = QFrame()
        self.header_widget.setObjectName("SidebarHeader")
        self.header_widget.setStyleSheet("QFrame#SidebarHeader { background-color: transparent; border: none; }")
        
        self.header_layout = QHBoxLayout(self.header_widget)
        self.header_layout.setContentsMargins(4, 4, 4, 4)
        self.header_layout.setSpacing(6)

        # Brand application vector logo
        self.brand_logo = QLabel()
        self.brand_logo.setObjectName("SidebarBrandLogo")
        self.brand_logo.setFixedSize(32, 32)
        self.brand_logo.setScaledContents(True)
        self.brand_logo.setPixmap(get_pixmap("brand", self.get_active_color(), 32))

        # Brand label
        self.brand_label = QLabel("Vera Note")
        self.brand_label.setObjectName("SidebarTitle")
        
        # Lock badge (shown only when Incognito mode is active)
        self.lock_badge = QLabel()
        self.lock_badge.setObjectName("SidebarLockBadge")
        self.lock_badge.setFixedSize(18, 18)
        self.lock_badge.setScaledContents(True)
        self.lock_badge.setPixmap(get_pixmap("lock", "#D7AEF5", 18))
        self.lock_badge.setToolTip(t("status_incognito_on"))
        self.lock_badge.setVisible(False)

        self.header_stretch = QWidget()
        self.header_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # Collapse / Expand Rail Toggle Button (uses btn_sidebar.png)
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("SidebarCollapseBtn")
        self.collapse_btn.setFixedSize(32, 32)
        self.collapse_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_btn.setIcon(get_icon("sidebar", self.get_inactive_color(), 20))
        self.collapse_btn.setIconSize(QSize(20, 20))
        self.collapse_btn.setToolTip(t("sidebar_collapse"))
        self.collapse_btn.clicked.connect(self.toggle_collapsed)

        self.header_layout.addWidget(self.brand_logo)
        self.header_layout.addWidget(self.brand_label)
        self.header_layout.addWidget(self.lock_badge)
        self.header_layout.addWidget(self.header_stretch)
        self.header_layout.addWidget(self.collapse_btn)
        
        self.main_layout.addWidget(self.header_widget, 0, Qt.AlignCenter)

        # Separator Line (centered divider)
        self.sep_line = QFrame()
        self.sep_line.setFrameShape(QFrame.HLine)
        self.sep_line.setFrameShadow(QFrame.Sunken)
        self.sep_line.setStyleSheet("background-color: #2F2F2F; margin: 4px 0px;")
        self.main_layout.addWidget(self.sep_line, 0, Qt.AlignCenter)

        # --- HOME BUTTON ---
        self.home_btn = QPushButton()
        self.home_btn.setObjectName("HomeBtn")
        self.home_btn.setFixedSize(236, 40)
        self.home_btn.clicked.connect(lambda: (self.set_active_item('home'), self.home_requested.emit()))
        
        self.home_layout = QHBoxLayout(self.home_btn)
        self.home_layout.setContentsMargins(16, 0, 16, 0)
        self.home_layout.setSpacing(12)
        
        self.home_icon = QLabel()
        self.home_icon.setFixedSize(20, 20)
        self.home_icon.setScaledContents(True)
        self.home_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.home_icon.setPixmap(get_pixmap("home", self.get_active_color(), 20))
        
        self.home_label = QLabel(t("home"))
        self.home_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.home_stretch = QWidget()
        self.home_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.home_layout.addWidget(self.home_icon, 0, Qt.AlignCenter)
        self.home_layout.addWidget(self.home_label)
        self.home_layout.addWidget(self.home_stretch)
        self.main_layout.addWidget(self.home_btn, 0, Qt.AlignCenter)

        # --- AGENDA BUTTON ---
        self.agenda_btn = QPushButton()
        self.agenda_btn.setObjectName("AgendaBtn")
        self.agenda_btn.setFixedSize(236, 40)
        self.agenda_btn.clicked.connect(lambda: (self.set_active_item('agenda'), self.agenda_requested.emit()))
        
        self.agenda_layout = QHBoxLayout(self.agenda_btn)
        self.agenda_layout.setContentsMargins(16, 0, 16, 0)
        self.agenda_layout.setSpacing(12)
        
        self.agenda_icon = QLabel()
        self.agenda_icon.setFixedSize(20, 20)
        self.agenda_icon.setScaledContents(True)
        self.agenda_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.agenda_icon.setPixmap(get_pixmap("calendar", "#E3E3E3", 20))
        
        self.agenda_label = QLabel(t("nav_agenda"))
        self.agenda_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.agenda_stretch = QWidget()
        self.agenda_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.agenda_layout.addWidget(self.agenda_icon, 0, Qt.AlignCenter)
        self.agenda_layout.addWidget(self.agenda_label)
        self.agenda_layout.addWidget(self.agenda_stretch)
        self.main_layout.addWidget(self.agenda_btn, 0, Qt.AlignCenter)

        # --- SECTION: NEW NOTE BUTTON ---
        self.new_note_btn = QPushButton()
        self.new_note_btn.setObjectName("NewNoteBtn")
        self.new_note_btn.setFixedSize(236, 40)
        self.new_note_btn.clicked.connect(lambda: (self.clear_list_selections(), self.new_note_requested.emit()))
        
        self.new_note_layout = QHBoxLayout(self.new_note_btn)
        self.new_note_layout.setContentsMargins(16, 0, 16, 0)
        self.new_note_layout.setSpacing(12)
        
        self.new_note_icon = QLabel()
        self.new_note_icon.setFixedSize(20, 20)
        self.new_note_icon.setScaledContents(True)
        self.new_note_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.new_note_icon.setPixmap(get_pixmap("add", "#FFFFFF", 20))
        
        self.new_note_label = QLabel(t("new_note"))
        self.new_note_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.new_note_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        
        self.new_note_stretch = QWidget()
        self.new_note_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.new_note_layout.addWidget(self.new_note_icon, 0, Qt.AlignCenter)
        self.new_note_layout.addWidget(self.new_note_label)
        self.new_note_layout.addWidget(self.new_note_stretch)
        self.main_layout.addWidget(self.new_note_btn, 0, Qt.AlignCenter)

        # --- ALL NOTES BUTTON ---
        self.all_notes_btn = QPushButton()
        self.all_notes_btn.setObjectName("AllNotesBtn")
        self.all_notes_btn.setFixedSize(236, 40)
        self.all_notes_btn.clicked.connect(lambda: (self.set_active_item('all_notes'), self.all_notes_requested.emit()))
        
        self.all_notes_layout = QHBoxLayout(self.all_notes_btn)
        self.all_notes_layout.setContentsMargins(16, 0, 16, 0)
        self.all_notes_layout.setSpacing(12)
        
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
        
        self.all_notes_stretch = QWidget()
        self.all_notes_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.all_notes_layout.addWidget(self.all_notes_icon, 0, Qt.AlignCenter)
        self.all_notes_layout.addWidget(self.all_notes_label)
        self.all_notes_layout.addWidget(self.all_notes_stretch)
        self.all_notes_layout.addWidget(self.all_notes_badge)
        self.main_layout.addWidget(self.all_notes_btn, 0, Qt.AlignCenter)

        # --- TRASH BUTTON ---
        self.trash_btn = QPushButton()
        self.trash_btn.setObjectName("TrashBtn")
        self.trash_btn.setFixedSize(236, 40)
        self.trash_btn.clicked.connect(lambda: (self.set_active_item('trash'), self.trash_requested.emit()))
        
        self.trash_layout = QHBoxLayout(self.trash_btn)
        self.trash_layout.setContentsMargins(16, 0, 16, 0)
        self.trash_layout.setSpacing(12)
        
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
        
        self.trash_stretch = QWidget()
        self.trash_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.trash_layout.addWidget(self.trash_icon, 0, Qt.AlignCenter)
        self.trash_layout.addWidget(self.trash_label)
        self.trash_layout.addWidget(self.trash_stretch)
        self.trash_layout.addWidget(self.trash_badge)
        self.main_layout.addWidget(self.trash_btn, 0, Qt.AlignCenter)

        # --- SECTION: MODELS (MODELLER) ---
        self.models_header = QPushButton()
        self.models_header.setObjectName("ModelsHeaderBtn")
        self.models_header.setCursor(Qt.PointingHandCursor)
        self.models_header.clicked.connect(self.on_models_header_clicked)
        
        self.models_h_layout = QHBoxLayout(self.models_header)
        self.models_h_layout.setContentsMargins(16, 0, 16, 0)
        self.models_h_layout.setSpacing(12)
        
        self.models_icon = QLabel()
        self.models_icon.setFixedSize(20, 20)
        self.models_icon.setScaledContents(True)
        self.models_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.models_icon.setPixmap(get_pixmap("models", "#B5A9BC", 20))
        
        self.models_label = QLabel(t("models_title"))
        self.models_label.setStyleSheet("color: #B5A9BC; font-size: 11px; font-weight: bold;")
        self.models_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.models_stretch = QWidget()
        self.models_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.models_h_layout.addWidget(self.models_icon, 0, Qt.AlignCenter)
        self.models_h_layout.addWidget(self.models_label)
        self.models_h_layout.addWidget(self.models_stretch)
        self.main_layout.addWidget(self.models_header, 0, Qt.AlignCenter)

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

        self.lib_header = QPushButton()
        self.lib_header.setObjectName("LibHeaderBtn")
        self.lib_header.setCursor(Qt.PointingHandCursor)
        self.lib_header.clicked.connect(self.on_lib_header_clicked)
        
        self.lib_h_layout = QHBoxLayout(self.lib_header)
        self.lib_h_layout.setContentsMargins(16, 0, 16, 0)
        self.lib_h_layout.setSpacing(12)
        
        self.lib_icon = QLabel()
        self.lib_icon.setFixedSize(20, 20)
        self.lib_icon.setScaledContents(True)
        self.lib_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.lib_icon.setPixmap(get_pixmap("workflows", "#B5A9BC", 20))

        self.lib_label = QLabel(t("workflows_title"))
        self.lib_label.setStyleSheet("color: #B5A9BC; font-size: 11px; font-weight: bold;")
        self.lib_label.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.lib_stretch = QWidget()
        self.lib_stretch.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.lib_h_layout.addWidget(self.lib_icon, 0, Qt.AlignCenter)
        self.lib_h_layout.addWidget(self.lib_label)
        self.lib_h_layout.addWidget(self.lib_stretch)
        self.main_layout.addWidget(self.lib_header, 0, Qt.AlignCenter)

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
        
        self.settings_layout = QHBoxLayout(self.settings_btn)
        self.settings_layout.setContentsMargins(16, 0, 16, 0)
        self.settings_layout.setSpacing(12)
        
        self.settings_icon = QLabel()
        self.settings_icon.setFixedSize(20, 20)
        self.settings_icon.setScaledContents(True)
        self.settings_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.settings_icon.setPixmap(get_pixmap("settings", "#E3E3E3", 20))
        
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
        # Default active state: home
        self.set_active_item('home')

    def toggle_collapsed(self):
        self.set_collapsed(not self.is_collapsed)

    def set_collapsed(self, collapsed: bool):
        self.is_collapsed = collapsed
        
        # Persist setting
        try:
            import database
            database.set_setting("sidebar_collapsed", "1" if collapsed else "0")
        except Exception:
            pass

        target_w = 64 if collapsed else 260
        self.setFixedWidth(target_w)

        # Toggle inner stretch widgets (when hidden in collapsed mode, icons are 100% dead-centered)
        for st in [self.header_stretch, self.home_stretch, self.agenda_stretch,
                   self.new_note_stretch, self.all_notes_stretch, self.trash_stretch,
                   self.models_stretch, self.lib_stretch, self.settings_stretch]:
            st.setVisible(not collapsed)

        if collapsed:
            # Compact Navigation Rail margins
            self.main_layout.setContentsMargins(10, 12, 10, 12)
            self.main_layout.setSpacing(8)
            
            # Header - Center collapse button perfectly in 44x40 footprint
            self.header_widget.setFixedSize(44, 40)
            self.header_layout.setContentsMargins(0, 0, 0, 0)
            self.header_layout.setSpacing(0)
            self.brand_logo.setVisible(False)
            self.brand_label.setVisible(False)
            self.lock_badge.setVisible(False)
            self.collapse_btn.setFixedSize(44, 40)
            self.collapse_btn.setToolTip(f"{t('sidebar_expand')} • {t('status_incognito_on')}" if self.incognito_active_state else t("sidebar_expand"))
            
            # Centered 36px separator divider
            self.sep_line.setFixedWidth(36)

            # Uniform 44x40 centered square-ish rail buttons
            btn_w, btn_h = 44, 40
            
            # Home
            self.home_btn.setFixedSize(btn_w, btn_h)
            self.home_label.setVisible(False)
            self.home_layout.setContentsMargins(0, 0, 0, 0)
            self.home_layout.setSpacing(0)
            self.home_btn.setToolTip(t("home"))
            
            # Agenda
            self.agenda_btn.setFixedSize(btn_w, btn_h)
            self.agenda_label.setVisible(False)
            self.agenda_layout.setContentsMargins(0, 0, 0, 0)
            self.agenda_layout.setSpacing(0)
            self.agenda_btn.setToolTip(t("nav_agenda"))
            
            # New note (dead-centered, same 44x40 size and 10px radius as all other buttons)
            self.new_note_btn.setFixedSize(btn_w, btn_h)
            self.new_note_label.setVisible(False)
            self.new_note_layout.setContentsMargins(0, 0, 0, 0)
            self.new_note_layout.setSpacing(0)
            self.new_note_btn.setToolTip(t("new_note"))
            
            # All notes
            self.all_notes_btn.setFixedSize(btn_w, btn_h)
            self.all_notes_label.setVisible(False)
            self.all_notes_badge.setVisible(False)
            self.all_notes_layout.setContentsMargins(0, 0, 0, 0)
            self.all_notes_layout.setSpacing(0)
            self.all_notes_btn.setToolTip(f"{t('notes')} ({self.all_notes_badge.text()})")
            
            # Trash
            self.trash_btn.setFixedSize(btn_w, btn_h)
            self.trash_label.setVisible(False)
            self.trash_badge.setVisible(False)
            self.trash_layout.setContentsMargins(0, 0, 0, 0)
            self.trash_layout.setSpacing(0)
            self.trash_btn.setToolTip(f"{t('trash')} ({self.trash_badge.text()})")
            
            # Models
            self.models_header.setFixedSize(btn_w, btn_h)
            self.models_label.setVisible(False)
            self.models_h_layout.setContentsMargins(0, 0, 0, 0)
            self.models_h_layout.setSpacing(0)
            curr_model = getattr(self, 'last_selected_model_lib', None) or (self.model_lib_names[0] if getattr(self, 'model_lib_names', None) else "")
            self.models_header.setToolTip(f"{t('models_title')}: {self.tr_lib_name(curr_model)}" if curr_model else t("models_title"))
            self.models_list.setVisible(False)
            
            # Hide redundant '+' button in rail mode for pristine uncluttered layout
            self.new_lib_btn.setVisible(False)
            
            # Workflows
            self.lib_header.setFixedSize(btn_w, btn_h)
            self.lib_label.setVisible(False)
            self.lib_h_layout.setContentsMargins(0, 0, 0, 0)
            self.lib_h_layout.setSpacing(0)
            curr_wf = getattr(self, 'last_selected_workflow_lib', None) or (self.workflow_lib_names[0] if getattr(self, 'workflow_lib_names', None) else "")
            self.lib_header.setToolTip(f"{t('workflows_title')}: {self.tr_lib_name(curr_wf)}" if curr_wf else t("workflows_title"))
            self.libraries_list.setVisible(False)
            
            # Settings
            self.settings_btn.setFixedSize(btn_w, btn_h)
            self.settings_label.setVisible(False)
            self.settings_layout.setContentsMargins(0, 0, 0, 0)
            self.settings_layout.setSpacing(0)
            self.settings_btn.setToolTip(t("settings"))
        else:
            # Full Sidebar margins
            self.main_layout.setContentsMargins(12, 16, 12, 16)
            self.main_layout.setSpacing(12)
            
            # Header
            self.header_widget.setFixedSize(236, 40)
            self.header_layout.setContentsMargins(4, 4, 4, 4)
            self.header_layout.setSpacing(6)
            self.brand_logo.setVisible(True)
            self.brand_label.setVisible(True)
            self.lock_badge.setVisible(self.incognito_active_state)
            self.collapse_btn.setFixedSize(32, 32)
            self.collapse_btn.setToolTip(t("sidebar_collapse"))
            
            # Separator line
            self.sep_line.setFixedWidth(236)
            
            # Buttons
            btn_w, btn_h = 236, 40
            
            # Home
            self.home_btn.setFixedSize(btn_w, btn_h)
            self.home_label.setVisible(True)
            self.home_layout.setContentsMargins(16, 0, 16, 0)
            self.home_layout.setSpacing(12)
            self.home_btn.setToolTip("")
            
            # Agenda
            self.agenda_btn.setFixedSize(btn_w, btn_h)
            self.agenda_label.setVisible(True)
            self.agenda_layout.setContentsMargins(16, 0, 16, 0)
            self.agenda_layout.setSpacing(12)
            self.agenda_btn.setToolTip("")
            
            # New note
            self.new_note_btn.setFixedSize(btn_w, btn_h)
            self.new_note_label.setVisible(True)
            self.new_note_layout.setContentsMargins(16, 0, 16, 0)
            self.new_note_layout.setSpacing(12)
            self.new_note_btn.setToolTip("")
            
            # All notes
            self.all_notes_btn.setFixedSize(btn_w, btn_h)
            self.all_notes_label.setVisible(True)
            self.all_notes_badge.setVisible(True)
            self.all_notes_layout.setContentsMargins(16, 0, 16, 0)
            self.all_notes_layout.setSpacing(12)
            self.all_notes_btn.setToolTip("")
            
            # Trash
            self.trash_btn.setFixedSize(btn_w, btn_h)
            self.trash_label.setVisible(True)
            self.trash_badge.setVisible(True)
            self.trash_layout.setContentsMargins(16, 0, 16, 0)
            self.trash_layout.setSpacing(12)
            self.trash_btn.setToolTip("")
            
            # Models
            self.models_header.setFixedSize(btn_w, 32)
            self.models_label.setVisible(True)
            self.models_h_layout.setContentsMargins(16, 0, 16, 0)
            self.models_h_layout.setSpacing(12)
            self.models_header.setToolTip("")
            if hasattr(self, 'comfyui_visible'):
                self.models_list.setVisible(self.comfyui_visible)
            else:
                self.models_list.setVisible(True)
            
            # New lib
            self.new_lib_btn.setFixedSize(btn_w, btn_h)
            self.new_lib_btn.setText(f"  {t('new_lib')}")
            self.new_lib_btn.setToolTip("")
            if hasattr(self, 'comfyui_visible'):
                self.new_lib_btn.setVisible(self.comfyui_visible)
            else:
                self.new_lib_btn.setVisible(True)
            
            # Workflows
            self.lib_header.setFixedSize(btn_w, 32)
            self.lib_label.setVisible(True)
            self.lib_h_layout.setContentsMargins(16, 0, 16, 0)
            self.lib_h_layout.setSpacing(12)
            self.lib_header.setToolTip("")
            if hasattr(self, 'comfyui_visible'):
                self.libraries_list.setVisible(self.comfyui_visible)
            else:
                self.libraries_list.setVisible(True)
            
            # Settings
            self.settings_btn.setFixedSize(btn_w, btn_h)
            self.settings_label.setVisible(True)
            self.settings_layout.setContentsMargins(16, 0, 16, 0)
            self.settings_layout.setSpacing(12)
            self.settings_btn.setToolTip("")

        self.collapsed_toggled.emit(collapsed)

    def on_models_header_clicked(self):
        if not hasattr(self, 'model_lib_names') or not self.model_lib_names:
            return

        if self.is_collapsed:
            # Cycle through model libraries when rail mode is active
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
            target = self.last_selected_model_lib if (getattr(self, 'last_selected_model_lib', None) in self.model_lib_names) else self.model_lib_names[0]
            self.set_active_item('model', target)
            self.library_selected.emit(target)

    def on_lib_header_clicked(self):
        if not hasattr(self, 'workflow_lib_names') or not self.workflow_lib_names:
            self.workflow_lib_names = ["Genel"]

        if self.is_collapsed:
            # Cycle through workflow libraries when rail mode is active
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
        buttons = {
            'home': self.home_btn,
            'agenda': self.agenda_btn,
            'all_notes': self.all_notes_btn,
            'trash': self.trash_btn,
            'settings': self.settings_btn,
            'model': self.models_header,
            'workflow': self.lib_header,
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
        self.brand_logo.setPixmap(get_pixmap("brand", active_color, 32))
        self.collapse_btn.setIcon(get_icon("sidebar", active_color if self.is_collapsed else self.get_inactive_color(), 20))
        self.home_icon.setPixmap(get_pixmap("home", active_color if item_type == 'home' else inactive_color, 20))
        self.agenda_icon.setPixmap(get_pixmap("calendar", active_color if item_type == 'agenda' else inactive_color, 20))
        self.new_note_icon.setPixmap(get_pixmap("add", "#FFFFFF", 20))
        self.all_notes_icon.setPixmap(get_pixmap("notes", active_color if item_type == 'all_notes' else inactive_color, 20))
        self.trash_icon.setPixmap(get_pixmap("trash", active_color if item_type == 'trash' else inactive_color, 20))
        self.settings_icon.setPixmap(get_pixmap("settings", active_color if item_type == 'settings' else inactive_color, 20))
        self.models_icon.setPixmap(get_pixmap("models", active_color if item_type == 'model' else "#B5A9BC", 20))
        self.lib_icon.setPixmap(get_pixmap("workflows", active_color if item_type == 'workflow' else "#B5A9BC", 20))

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
        self.agenda_label.setText(t("nav_agenda"))
        self.new_note_label.setText(t("new_note"))
        self.new_lib_btn.setText(f"  {t('new_lib')}")
        self.all_notes_label.setText(t("notes"))
        self.trash_label.setText(t("trash"))
        self.models_label.setText(t("models_title"))
        self.lib_label.setText(t("workflows_title"))
        self.settings_label.setText(t("settings"))
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

    def set_comfyui_visible(self, visible: bool):
        self.comfyui_visible = visible
        if hasattr(self, 'models_header'):
            self.models_header.setVisible(visible)
        if hasattr(self, 'models_list'):
            self.models_list.setVisible(visible and not self.is_collapsed)
        if hasattr(self, 'new_lib_btn'):
            self.new_lib_btn.setVisible(visible and not self.is_collapsed)
        if hasattr(self, 'lib_header'):
            self.lib_header.setVisible(visible)
        if hasattr(self, 'libraries_list'):
            self.libraries_list.setVisible(visible and not self.is_collapsed)

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
            item = QListWidgetItem(f"   {self.tr_lib_name(lib_name)} ({count})")
            self.models_list.addItem(item)
            self.model_lib_names.append(lib_name)
            if self.last_selected_model_lib and lib_name == self.last_selected_model_lib:
                self.models_list.setCurrentRow(self.models_list.count() - 1)
        
        count = max(1, len(models_with_counts))
        self.models_list.setFixedHeight(count * 44 + 8)
        if self.is_collapsed or (hasattr(self, 'comfyui_visible') and not self.comfyui_visible):
            self.models_list.setVisible(False)
        else:
            self.models_list.setVisible(True)

    def update_workflow_libraries_list(self, workflow_libs_with_counts, selected_workflow_lib=None):
        self.last_workflow_libs_data = workflow_libs_with_counts
        self.last_selected_workflow_lib = selected_workflow_lib or (workflow_libs_with_counts[0][0] if workflow_libs_with_counts else None)
        self.libraries_list.clear()
        self.workflow_lib_names = []
        for lib_name, count in workflow_libs_with_counts:
            item = QListWidgetItem(f"   {self.tr_lib_name(lib_name)} ({count})")
            self.libraries_list.addItem(item)
            self.workflow_lib_names.append(lib_name)
            if self.last_selected_workflow_lib and lib_name == self.last_selected_workflow_lib:
                self.libraries_list.setCurrentRow(self.libraries_list.count() - 1)

        count = max(1, len(workflow_libs_with_counts))
        self.libraries_list.setFixedHeight(count * 44 + 8)
        if self.is_collapsed or (hasattr(self, 'comfyui_visible') and not self.comfyui_visible):
            self.libraries_list.setVisible(False)
        else:
            self.libraries_list.setVisible(True)

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
