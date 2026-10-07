# ui/library_view.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit, QComboBox)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QRunnable, QThreadPool, QObject, Slot, QPoint, QRect, QMimeData, QUrl
from PySide6.QtGui import QPixmap, QFontMetrics, QPainter, QPainterPath, QImage, QDrag, QGuiApplication
from utils.i18n import t, get_lang
from utils.icon_manager import get_icon, get_pixmap

from utils.cache import THUMBNAIL_CACHE

def cache_thumbnail(path, pixmap, max_size=150):
    if not path or not pixmap or pixmap.isNull():
        return
    THUMBNAIL_CACHE[path] = pixmap

class FileCheckSignals(QObject):
    checked = Signal(str, bool) # file_path, exists

class FileCheckWorker(QRunnable):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.signals = FileCheckSignals()

    def run(self):
        exists = False
        try:
            exists = bool(self.file_path and os.path.exists(self.file_path))
        except Exception:
            exists = False
        try:
            self.signals.checked.emit(self.file_path, exists)
        except RuntimeError:
            pass

class ImageLoadSignals(QObject):
    image_loaded = Signal(str, object, int, int) # image_path, QImage, target_w, target_h

class ImageLoadWorker(QRunnable):
    def __init__(self, image_path, target_w=200, target_h=176):
        super().__init__()
        self.image_path = image_path
        self.target_w = target_w
        self.target_h = target_h
        self.signals = ImageLoadSignals()

    def run(self):
        try:
            image = QImage(self.image_path)
            if not image.isNull():
                scaled = image.scaled(
                    self.target_w, self.target_h,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                cropped = scaled.copy(0, 0, self.target_w, self.target_h)
                try:
                    self.signals.image_loaded.emit(self.image_path, cropped, self.target_w, self.target_h)
                except RuntimeError:
                    pass
            else:
                try:
                    self.signals.image_loaded.emit(self.image_path, None, self.target_w, self.target_h)
                except RuntimeError:
                    pass
        except Exception:
            try:
                self.signals.image_loaded.emit(self.image_path, None, self.target_w, self.target_h)
            except RuntimeError:
                pass

def get_rounded_pixmap(pixmap, radius=13):
    if pixmap.isNull():
        return pixmap
    
    size = pixmap.size()
    rounded = QPixmap(size)
    rounded.fill(Qt.transparent)
    
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    path = QPainterPath()
    path.moveTo(0, radius)
    path.arcTo(0, 0, radius * 2, radius * 2, 180, -90) # top-left
    path.lineTo(size.width() - radius, 0)
    path.arcTo(size.width() - radius * 2, 0, radius * 2, radius * 2, 90, -90) # top-right
    path.lineTo(size.width(), size.height())
    path.lineTo(0, size.height())
    path.lineTo(0, radius)
    path.closeSubpath()
    
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return rounded

class ModelCardWidget(QFrame):
    clicked = Signal(dict)
    favorite_toggled = Signal(int, bool)
    hide_requested = Signal(dict)
    unhide_requested = Signal(dict)
    selection_toggled = Signal(dict, bool)
    delete_requested = Signal(dict)

    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self.setObjectName("ModelCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # Set fixed card size so it never squashes or deforms under grid layout resizing
        self.setFixedSize(200, 240)
        
        filepath = self.model_data.get('file_path', '')
        self.original_filename = os.path.basename(filepath) if filepath else t("unknown_file")
        
        self.file_exists = True
        self.warning_badge = None
        self.is_fav = bool(self.model_data.get('is_favorite', 0))
        self.is_selected = False
        self.drag_start_pos = None
        
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()
        self.check_file_existence()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image Container (Thumbnail) - Top section of fixed card
        self.image_label = QLabel(self)
        self.image_label.setObjectName("CardImageLabel")
        self.image_label.setFixedSize(200, 176)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Star / Favorite Button Overlay on top-left of image
        self.fav_btn = QPushButton(self.image_label)
        self.fav_btn.setObjectName("CardFavBtn")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setGeometry(8, 8, 28, 28)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(self.on_fav_clicked)
        self.update_fav_btn_style()

        # Multi-select Checkbox Button Overlay on top-right of image (hidden by default)
        self.select_btn = QPushButton(self.image_label)
        self.select_btn.setObjectName("CardSelectBtn")
        self.select_btn.setFixedSize(24, 24)
        self.select_btn.setGeometry(166, 8, 24, 24)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self.on_select_clicked)
        self.select_btn.setVisible(False)
        self.update_selection_style()

        # Quick Copy Triggers Button Overlay on bottom-right of image
        self.copy_triggers_btn = QPushButton("📋", self.image_label)
        self.copy_triggers_btn.setObjectName("CardCopyTriggersBtn")
        self.copy_triggers_btn.setFixedSize(26, 26)
        self.copy_triggers_btn.setGeometry(166, 142, 26, 26)
        self.copy_triggers_btn.setCursor(Qt.PointingHandCursor)
        self.copy_triggers_btn.setToolTip(t("lib_copy_triggers"))
        self.copy_triggers_btn.setStyleSheet("""
            QPushButton#CardCopyTriggersBtn {
                background-color: rgba(30, 31, 34, 0.75);
                border: 1px solid rgba(68, 71, 70, 0.8);
                border-radius: 13px;
                color: #C2E7FF;
                font-size: 11px;
                padding: 0px;
            }
            QPushButton#CardCopyTriggersBtn:hover {
                background-color: rgba(26, 115, 232, 0.9);
                border-color: #8AB4F8;
                color: #FFFFFF;
            }
        """)
        self.copy_triggers_btn.clicked.connect(self.on_copy_triggers_clicked)

        # Architecture Badge Overlay on bottom-left of image
        self.arch_badge = QLabel(self.image_label)
        self.arch_badge.setObjectName("CardArchBadge")
        self.arch_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.arch_badge.setStyleSheet("""
            QLabel#CardArchBadge {
                background-color: rgba(20, 21, 24, 0.85);
                border: 1px solid rgba(138, 180, 248, 0.5);
                border-radius: 4px;
                color: #8AB4F8;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 5px;
            }
        """)
        self.arch_badge.setVisible(False)

        # Bottom Info Panel - Dedicated container for title & filename
        self.info_panel = QFrame(self)
        self.info_panel.setObjectName("CardInfoPanel")
        self.info_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.info_panel.setFixedHeight(64)
        
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(2)

        # Model Title (Row 1)
        self.title_label = QLabel(self.info_panel)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.title_label)

        # Filename Label (Row 2)
        self.filename_label = QLabel(self.info_panel)
        self.filename_label.setObjectName("CardFilename")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setWordWrap(False)
        info_layout.addWidget(self.filename_label)

        layout.addWidget(self.info_panel)

        # Render elided texts & cached image
        self.set_card_image(self.model_data.get('image_path'))
        self.update_texts()

    def check_file_existence(self):
        filepath = self.model_data.get('file_path', '')
        if not filepath:
            self.set_file_exists(False)
            return
        worker = FileCheckWorker(filepath)
        worker.signals.checked.connect(self._on_file_check_result)
        QThreadPool.globalInstance().start(worker)

    @Slot(str, bool)
    def _on_file_check_result(self, path, exists):
        if self.model_data.get('file_path', '') == path:
            self.set_file_exists(exists)

    def set_file_exists(self, exists: bool):
        self.file_exists = exists
        if not exists:
            if not getattr(self, 'warning_badge', None):
                self.warning_badge = QLabel(t("not_on_disk"), self.image_label)
                self.warning_badge.setObjectName("WarningBadge")
                self.warning_badge.setGeometry(88, 8, 72, 20)
                self.warning_badge.setAlignment(Qt.AlignCenter)
                self.warning_badge.setToolTip(t("not_on_disk_tooltip"))
                self.warning_badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.warning_badge.show()
        else:
            if getattr(self, 'warning_badge', None):
                self.warning_badge.hide()

    def set_checkbox_visible(self, visible: bool):
        if hasattr(self, 'select_btn'):
            self.select_btn.setVisible(visible)

    def update_texts(self):
        metrics = QFontMetrics(self.font())
        
        # Elide name (Max 178px width)
        name = self.model_data.get('name', '')
        if self.model_data.get('is_hidden', 0) == 1:
            name = "🔒 " + name
        elided_title = metrics.elidedText(name, Qt.ElideRight, 178)
        self.title_label.setText(elided_title)
        self.title_label.setToolTip(name)

        # Elide filename (Max 178px width)
        elided_filename = metrics.elidedText(self.original_filename, Qt.ElideRight, 178)
        self.filename_label.setText(elided_filename)
        self.filename_label.setToolTip(self.original_filename)

        if getattr(self, 'warning_badge', None):
            self.warning_badge.setText(t("not_on_disk"))
            self.warning_badge.setToolTip(t("not_on_disk_tooltip"))

        # Base architecture badge
        if hasattr(self, 'arch_badge'):
            arch = self.model_data.get('base_architecture') or ""
            if not arch:
                from utils.png_parser import detect_base_architecture
                arch = detect_base_architecture([self.model_data.get('name', ''), self.model_data.get('file_path', '')])
            if arch:
                self.arch_badge.setText(f"⚡ {arch}")
                self.arch_badge.adjustSize()
                self.arch_badge.move(8, 148)
                self.arch_badge.setVisible(True)
            else:
                self.arch_badge.setVisible(False)

    def on_copy_triggers_clicked(self):
        words = self.model_data.get('trigger_words') or []
        if words:
            clip_text = ", ".join(words)
        else:
            clip_text = self.model_data.get('name', '')
            
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(clip_text)
        
        self.copy_triggers_btn.setText("✓")
        self.copy_triggers_btn.setEnabled(False)
        win = self.window()
        if win and hasattr(win, 'show_toast'):
            win.show_toast(t("toast_copied_triggers"), "success")
        QTimer.singleShot(1500, lambda: [self.copy_triggers_btn.setText("📋"), self.copy_triggers_btn.setEnabled(True)] if hasattr(self, 'copy_triggers_btn') and self.copy_triggers_btn else None)

    def contextMenuEvent(self, event):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        
        main_win = self.window()
        incognito_active = bool(main_win and getattr(main_win, 'incognito_active', False))
        
        menu = QMenu(self)
        
        # Check parent library view for bulk selection state
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'selected_model_ids'):
            parent_widget = parent_widget.parent()
            
        selected_ids = getattr(parent_widget, 'selected_model_ids', set())
        
        # Delete action
        if self.is_selected and len(selected_ids) > 1:
            del_text = t("menu_delete_selected_models").format(count=len(selected_ids))
            del_action = menu.addAction(del_text)
            del_bulk = True
        else:
            del_text = t("menu_delete_model")
            del_action = menu.addAction(del_text)
            del_bulk = False
            
        hide_action = None
        unhide_action = None
        if incognito_active:
            menu.addSeparator()
            is_hidden = self.model_data.get('is_hidden', 0) == 1
            if not is_hidden:
                hide_action = menu.addAction(t("menu_hide"))
            else:
                unhide_action = menu.addAction(t("menu_unhide"))
                
        action = menu.exec(QCursor.pos())
        if action == del_action:
            if del_bulk and parent_widget and hasattr(parent_widget, 'on_bulk_delete_clicked'):
                parent_widget.on_bulk_delete_clicked()
            else:
                self.delete_requested.emit(self.model_data)
        elif hide_action and action == hide_action:
            self.hide_requested.emit(self.model_data)
        elif unhide_action and action == unhide_action:
            self.unhide_requested.emit(self.model_data)

    def set_card_image(self, image_path):
        self.current_image_path = image_path
        self.image_loaded = False
        self.image_loading = False
        if image_path:
            # Check module-level cache
            if image_path in THUMBNAIL_CACHE:
                self.image_label.setPixmap(THUMBNAIL_CACHE[image_path])
                self.image_label.setText("")
                self.image_loaded = True
                return
            
            # Placeholder while background thread loads
            self.image_label.setText("")
            self.image_label.setPixmap(QPixmap())
            self.ensure_image_loaded()
            return
        
        self.image_label.setText("")
        self.image_label.setPixmap(QPixmap())
        self.image_loaded = True

    def ensure_image_loaded(self):
        if getattr(self, 'image_loaded', False) or getattr(self, 'image_loading', False):
            return
        image_path = getattr(self, 'current_image_path', '')
        if not image_path:
            self.image_loaded = True
            return
        if image_path in THUMBNAIL_CACHE:
            self.image_label.setPixmap(THUMBNAIL_CACHE[image_path])
            self.image_label.setText("")
            self.image_loaded = True
            return

        self.image_loading = True
        worker = ImageLoadWorker(image_path, target_w=200, target_h=176)
        worker.signals.image_loaded.connect(self._on_async_image_loaded)
        QThreadPool.globalInstance().start(worker)

    @Slot(str, object, int, int)
    def _on_async_image_loaded(self, path, qimage, w, h):
        self.image_loading = False
        if getattr(self, 'current_image_path', '') != path:
            return
        if qimage and not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage)
            rounded = get_rounded_pixmap(pixmap, radius=13)
            cache_thumbnail(path, rounded)
            self.image_label.setPixmap(rounded)
            self.image_label.setText("")
            self.image_loaded = True
        else:
            self.image_label.setText("")
            self.image_label.setPixmap(QPixmap())
            self.image_loaded = True

    def prepare_for_deletion(self):
        """Immediately clear QPixmap references to release RAM memory before Qt deletes the widget."""
        self.image_label.setPixmap(QPixmap())
        self.image_loaded = False
        self.image_loading = False
        if getattr(self, 'warning_badge', None):
            self.warning_badge.deleteLater()
            self.warning_badge = None
        if hasattr(self, 'fav_btn'):
            self.fav_btn.deleteLater()
        if hasattr(self, 'select_btn'):
            self.select_btn.deleteLater()

    def on_select_clicked(self):
        self.set_selected(not self.is_selected)
        self.selection_toggled.emit(self.model_data, self.is_selected)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_selection_style()

    def update_selection_style(self):
        self.setProperty("selected", self.is_selected)
        self.style().unpolish(self)
        self.style().polish(self)
        if hasattr(self, 'select_btn'):
            self.select_btn.setText("✓" if self.is_selected else "")
            self.select_btn.setProperty("selected", self.is_selected)
            self.select_btn.style().unpolish(self.select_btn)
            self.select_btn.style().polish(self.select_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.drag_start_pos is not None:
            dist = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
            if dist >= QGuiApplication.styleHints().startDragDistance():
                self.start_drag()
                self.drag_start_pos = None
                return
        super().mouseMoveEvent(event)

    def start_drag(self):
        filepath = self.model_data.get('file_path', '')
        mime_data = QMimeData()
        if filepath:
            mime_data.setUrls([QUrl.fromLocalFile(filepath)])
            mime_data.setText(filepath)
        else:
            mime_data.setText(self.model_data.get('name', ''))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pix = self.image_label.pixmap()
        if pix and not pix.isNull():
            preview = pix.scaled(90, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        else:
            preview = self.grab().scaled(90, 108, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        drag.setPixmap(preview)
        drag.setHotSpot(QPoint(preview.width() // 2, preview.height() // 2))
        drag.exec(Qt.CopyAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            is_click = True
            if self.drag_start_pos is not None:
                dist = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
                if dist >= QGuiApplication.styleHints().startDragDistance():
                    is_click = False
            self.drag_start_pos = None
            if is_click:
                if event.modifiers() & Qt.ControlModifier:
                    self.on_select_clicked()
                else:
                    self.clicked.emit(self.model_data)
        super().mouseReleaseEvent(event)

    def on_fav_clicked(self):
        self.is_fav = not self.is_fav
        self.model_data['is_favorite'] = 1 if self.is_fav else 0
        self.update_fav_btn_style()
        self.favorite_toggled.emit(self.model_data.get('id', 0), self.is_fav)

    def update_fav_btn_style(self):
        if hasattr(self, 'fav_btn'):
            self.fav_btn.setText("⭐" if self.is_fav else "☆")
            self.fav_btn.setProperty("favorite", self.is_fav)
            self.fav_btn.style().unpolish(self.fav_btn)
            self.fav_btn.style().polish(self.fav_btn)


class LibraryView(QWidget):
    model_clicked = Signal(dict)
    scan_requested = Signal(str) # library_name
    favorite_toggled = Signal(int, bool)
    model_hide_requested = Signal(dict)
    model_unhide_requested = Signal(dict)
    bulk_add_tag_requested = Signal(list)
    bulk_remove_tag_requested = Signal(list)
    bulk_favorite_requested = Signal(list, bool)
    bulk_delete_requested = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LibraryViewWidget")
        self.library_name = ""
        self.models_data = []
        self.filtered_models_data = []
        self.cards = []
        self.selected_model_ids = set()
        self.current_columns = -1
        self.selected_tag = None
        self.tag_buttons = {}

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self.apply_filters)

        self.resize_debounce_timer = QTimer(self)
        self.resize_debounce_timer.setSingleShot(True)
        self.resize_debounce_timer.timeout.connect(self._on_debounced_resize)

        self.scroll_check_timer = QTimer(self)
        self.scroll_check_timer.setSingleShot(True)
        self.scroll_check_timer.timeout.connect(self.check_visible_cards)

        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Header: Name, Search input, Scan Button
        header_layout = QHBoxLayout()
        self.title_label = QLabel(t("models_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        self.title_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.title_label.setMinimumWidth(150)
        header_layout.addWidget(self.title_label)

        # Local search input
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText(t("search_placeholder"))
        self.local_search.setMinimumWidth(100)
        self.local_search.setMaximumWidth(280)
        self.local_search.textChanged.connect(self.on_local_search_changed)
        header_layout.addWidget(self.local_search)

        # Favoriler Toggle Button with vector star icon
        self.fav_toggle_btn = QPushButton(f"  {t('view_favorites')}")
        self.fav_toggle_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.fav_toggle_btn.setIconSize(QSize(16, 16))
        self.fav_toggle_btn.setCheckable(True)
        self.fav_toggle_btn.setObjectName("FavToggleBtn")
        self.fav_toggle_btn.clicked.connect(self.on_fav_toggle_clicked)
        header_layout.addWidget(self.fav_toggle_btn)

        # Tag Filter ComboBox
        self.tag_combo = QComboBox()
        self.tag_combo.setObjectName("TagFilterCombo")
        self.tag_combo.addItem(get_icon("tag", "#8AB4F8", 14), t("lib_tag_all"), userData=None)
        self.tag_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.tag_combo.currentIndexChanged.connect(self.on_tag_combo_changed)
        header_layout.addWidget(self.tag_combo)
        self.tag_combo.setVisible(False)

        # Architecture Filter ComboBox with vector lightning icon
        self.arch_combo = QComboBox()
        self.arch_combo.setObjectName("ArchFilterCombo")
        self.arch_combo.addItem(get_icon("lightning", "#8AB4F8", 14), t("lib_arch_all"), userData=None)
        for arch in ["Flux", "SDXL", "SD 1.5", "Pony", "SD3", "Illustrious", "SD 2.1"]:
            self.arch_combo.addItem(get_icon("lightning", "#E3E3E3", 14), arch, userData=arch)
        self.arch_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.arch_combo.currentIndexChanged.connect(self.on_arch_combo_changed)
        header_layout.addWidget(self.arch_combo)

        # Sorting ComboBox with clock icon for newest
        self.sort_combo = QComboBox()
        self.sort_combo.addItem(get_icon("clock", "#8AB4F8", 14), t("lib_sort_newest"))
        self.sort_combo.addItem(t("lib_sort_az"))
        self.sort_combo.addItem(t("lib_sort_za"))
        self.sort_combo.addItem(get_icon("star", "#8AB4F8", 14), t("lib_sort_fav_first"))
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.sort_combo.currentTextChanged.connect(self.on_sort_changed)
        header_layout.addWidget(self.sort_combo)

        header_layout.addStretch()

        self.scan_btn = QPushButton(f"  {t('view_scan_library')}")
        self.scan_btn.setIcon(get_icon("refresh", "#FFFFFF", 16))
        self.scan_btn.setIconSize(QSize(16, 16))
        self.scan_btn.setObjectName("HeaderAddBtn")
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setStyleSheet("QPushButton { border-radius: 18px !important; padding: 6px 14px !important; font-weight: bold !important; }")
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        header_layout.addWidget(self.scan_btn)

        self.main_layout.addLayout(header_layout)

        # Bulk Action Bar (Visible only when 1 or more models are selected)
        self.bulk_bar = QFrame()
        self.bulk_bar.setObjectName("BulkActionBar")
        self.bulk_bar.setStyleSheet("""
            QFrame#BulkActionBar {
                background-color: #242936;
                border: 1px solid #3c4456;
                border-radius: 10px;
            }
            QLabel#BulkCountLabel {
                color: #8AB4F8;
                font-weight: bold;
                font-size: 13px;
                padding-left: 6px;
            }
            QPushButton.bulk_btn {
                background-color: #303644;
                color: #E8EAED;
                border: 1px solid #444c60;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton.bulk_btn:hover {
                background-color: #3c4456;
                border-color: #8AB4F8;
                color: #FFFFFF;
            }
            QPushButton.bulk_primary_btn {
                background-color: #8AB4F8;
                color: #1A1A1A;
                border: none;
                border-radius: 6px;
                padding: 5px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton.bulk_primary_btn:hover {
                background-color: #A8C7FA;
            }
            QPushButton.bulk_danger_btn {
                background-color: #3B1C22;
                color: #F87171;
                border: 1px solid #7F1D1D;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton.bulk_danger_btn:hover {
                background-color: #DC2626;
                border-color: #EF4444;
                color: #FFFFFF;
            }
            QPushButton.bulk_warning_btn {
                background-color: #382B12;
                color: #FBBF24;
                border: 1px solid #78350F;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton.bulk_warning_btn:hover {
                background-color: #D97706;
                border-color: #F59E0B;
                color: #FFFFFF;
            }
        """)
        bulk_layout = QHBoxLayout(self.bulk_bar)
        bulk_layout.setContentsMargins(12, 8, 12, 8)
        bulk_layout.setSpacing(10)

        self.bulk_count_label = QLabel()
        self.bulk_count_label.setObjectName("BulkCountLabel")
        bulk_layout.addWidget(self.bulk_count_label)

        bulk_layout.addStretch()

        self.bulk_select_all_btn = QPushButton(t("bulk_select_all"))
        self.bulk_select_all_btn.setProperty("class", "bulk_btn")
        self.bulk_select_all_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_select_all_btn.clicked.connect(self.select_all_cards)
        bulk_layout.addWidget(self.bulk_select_all_btn)

        self.bulk_select_missing_btn = QPushButton(t("bulk_select_missing"))
        self.bulk_select_missing_btn.setProperty("class", "bulk_warning_btn")
        self.bulk_select_missing_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_select_missing_btn.clicked.connect(self.select_missing_cards)
        self.bulk_select_missing_btn.setVisible(False)
        bulk_layout.addWidget(self.bulk_select_missing_btn)

        self.bulk_clear_btn = QPushButton(t("bulk_clear_selection"))
        self.bulk_clear_btn.setProperty("class", "bulk_btn")
        self.bulk_clear_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_clear_btn.clicked.connect(self.clear_selection)
        bulk_layout.addWidget(self.bulk_clear_btn)

        self.bulk_fav_btn = QPushButton(f"  {t('bulk_set_fav')}")
        self.bulk_fav_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.bulk_fav_btn.setIconSize(QSize(16, 16))
        self.bulk_fav_btn.setProperty("class", "bulk_btn")
        self.bulk_fav_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_fav_btn.clicked.connect(lambda: self.on_bulk_fav_clicked(True))
        bulk_layout.addWidget(self.bulk_fav_btn)

        self.bulk_add_tag_btn = QPushButton(f"  {t('bulk_add_tag')}")
        self.bulk_add_tag_btn.setIcon(get_icon("tag", "#FFFFFF", 16))
        self.bulk_add_tag_btn.setIconSize(QSize(16, 16))
        self.bulk_add_tag_btn.setProperty("class", "bulk_primary_btn")
        self.bulk_add_tag_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_add_tag_btn.clicked.connect(self.on_bulk_add_tag_clicked)
        bulk_layout.addWidget(self.bulk_add_tag_btn)

        self.bulk_remove_tag_btn = QPushButton(f"  {t('bulk_remove_tag')}")
        self.bulk_remove_tag_btn.setIcon(get_icon("tag", "#9AA0A6", 16))
        self.bulk_remove_tag_btn.setIconSize(QSize(16, 16))
        self.bulk_remove_tag_btn.setProperty("class", "bulk_btn")
        self.bulk_remove_tag_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_remove_tag_btn.clicked.connect(self.on_bulk_remove_tag_clicked)
        bulk_layout.addWidget(self.bulk_remove_tag_btn)

        self.bulk_delete_btn = QPushButton(f"  {t('bulk_delete_models')}")
        self.bulk_delete_btn.setIcon(get_icon("trash", "#FFFFFF", 16))
        self.bulk_delete_btn.setIconSize(QSize(16, 16))
        self.bulk_delete_btn.setProperty("class", "bulk_danger_btn")
        self.bulk_delete_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_delete_btn.clicked.connect(self.on_bulk_delete_clicked)
        bulk_layout.addWidget(self.bulk_delete_btn)

        self.bulk_bar.setVisible(False)
        self.main_layout.addWidget(self.bulk_bar)

        # Scroll Area for Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("GridScrollArea")
        self.scroll_area.setWidgetResizable(True)
        
        self.grid_container = QWidget()
        self.grid_container.setObjectName("LibraryGridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_container)
        self.main_layout.addWidget(self.scroll_area)

    def set_library(self, name, models):
        models = models or []
        existing_card_ids = [c.model_data['id'] for c in self.cards if isinstance(c, ModelCardWidget)]
        new_model_ids = [m['id'] for m in models]

        same_library = (self.library_name == name)
        same_models = (existing_card_ids == new_model_ids and len(new_model_ids) > 0)

        self.library_name = name
        self.models_data = models
        self.filtered_models_data = self.models_data

        if name == "Favoriler":
            self.scan_btn.setVisible(False)
        else:
            self.scan_btn.setVisible(True)

        self.title_label.setText(self.tr_lib_name(self.library_name) if self.library_name else t("app_title").split()[0])

        if same_library and same_models:
            # Cards are already in the grid! Re-align columns if viewport changed in 0.2ms
            self.update_grid_layout()
            return

        # Reset filters with blocked signals to avoid duplicate rendering
        self.fav_toggle_btn.blockSignals(True)
        self.fav_toggle_btn.setChecked(False)
        self.fav_toggle_btn.blockSignals(False)

        self.local_search.blockSignals(True)
        self.local_search.clear()
        self.local_search.blockSignals(False)

        self.selected_tag = None
        self.update_tag_bar(models)

        self.retranslate_ui()

    def _create_card(self, model):
        card = ModelCardWidget(model, parent=self.grid_container)
        card.clicked.connect(self.model_clicked.emit)
        card.favorite_toggled.connect(self.favorite_toggled.emit)
        card.hide_requested.connect(self.model_hide_requested.emit)
        card.unhide_requested.connect(self.model_unhide_requested.emit)
        card.selection_toggled.connect(self.on_card_selection_toggled)
        card.delete_requested.connect(self.on_single_card_delete_requested)
        
        is_sel_active = len(self.selected_model_ids) > 0
        card.set_checkbox_visible(is_sel_active)
        if card.model_data.get('id') in self.selected_model_ids:
            card.set_selected(True)
        return card

    def populate_grid(self, use_filtered=False):
        if hasattr(self, '_chunk_timer') and self._chunk_timer.isActive():
            self._chunk_timer.stop()

        self.scroll_area.setUpdatesEnabled(False)
        self.grid_container.setUpdatesEnabled(False)
        try:
            for card in self.cards:
                self.grid_layout.removeWidget(card)
                if hasattr(card, 'prepare_for_deletion'):
                    card.prepare_for_deletion()
                card.deleteLater()
            self.cards.clear()

            display_data = self.filtered_models_data if use_filtered else self.models_data

            if not display_data:
                empty_label = QLabel(t("view_empty_library"))
                empty_label.setObjectName("CardFilename")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet("font-size: 14px; color: #9AA0A6; padding: 40px;")
                self.grid_layout.addWidget(empty_label, 0, 0)
                self.cards.append(empty_label)
                self.current_columns = -1
                self.grid_container.setMinimumHeight(0)
                return

            width = self.scroll_area.viewport().width()
            if width <= 100:
                width = self.scroll_area.width() - 48
            if width <= 100:
                width = 860

            card_width = 200
            spacing = 16
            scrollbar_w = 16 if len(display_data) > 16 else 0
            avail_w = max(100, width - scrollbar_w)
            columns = max(1, (avail_w + spacing) // (card_width + spacing))
            self.current_columns = columns

            total_rows = (len(display_data) + columns - 1) // columns
            row_height = 240 + spacing
            self.grid_container.setMinimumHeight(total_rows * row_height)

            # Responsive Phase 1: fill entire visible screen (FHD: ~24, 2K/4K: ~40-60 cards)
            viewport_h = max(600, self.scroll_area.viewport().height())
            visible_rows = (viewport_h // row_height) + 2
            needed_cards = max(24, columns * visible_rows)
            initial_count = min(needed_cards, len(display_data))
            for i in range(initial_count):
                card = self._create_card(display_data[i])
                self.grid_layout.addWidget(card, i // columns, i % columns)
                self.cards.append(card)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

        # Background Phase 2: seamlessly load remaining cards on idle ticks
        if len(display_data) > initial_count:
            self._pending_display_data = display_data
            self._pending_load_index = initial_count
            if not hasattr(self, '_chunk_timer'):
                self._chunk_timer = QTimer(self)
                self._chunk_timer.setSingleShot(True)
                self._chunk_timer.timeout.connect(self._load_remaining_cards)
            self._chunk_timer.start(0)

    def _load_remaining_cards(self):
        if not hasattr(self, '_pending_display_data') or self._pending_load_index >= len(self._pending_display_data):
            return

        display_data = self._pending_display_data
        columns = self.current_columns if self.current_columns > 0 else 1
        chunk_size = 40
        end_idx = min(self._pending_load_index + chunk_size, len(display_data))

        self.scroll_area.setUpdatesEnabled(False)
        self.grid_container.setUpdatesEnabled(False)
        try:
            for i in range(self._pending_load_index, end_idx):
                card = self._create_card(display_data[i])
                self.grid_layout.addWidget(card, i // columns, i % columns)
                self.cards.append(card)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

        self._pending_load_index = end_idx
        if self._pending_load_index < len(display_data):
            self._chunk_timer.start(0)

    def update_grid_layout(self, display_data=None):
        if not self.cards or isinstance(self.cards[0], QLabel):
            return

        width = self.scroll_area.viewport().width()
        card_width = 200
        spacing = 16
        total_items = len(self.filtered_models_data) if getattr(self, 'filtered_models_data', None) else len(self.cards)
        scrollbar_w = 16 if total_items > 16 else 0
        avail_w = max(100, width - scrollbar_w)
        columns = max(1, (avail_w + spacing) // (card_width + spacing))

        if columns == self.current_columns:
            return

        self.current_columns = columns
        total_rows = (total_items + columns - 1) // columns
        row_height = 240 + spacing
        self.grid_container.setMinimumHeight(total_rows * row_height)

        self.scroll_area.setUpdatesEnabled(False)
        self.grid_container.setUpdatesEnabled(False)
        try:
            for i, card in enumerate(self.cards):
                self.grid_layout.addWidget(card, i // columns, i % columns)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

    def update_tag_bar(self, models):
        all_tags = set()
        for m in (models or []):
            for tg in m.get('tags', []):
                if tg and tg.strip():
                    all_tags.add(tg.strip())

        if not hasattr(self, 'tag_combo'):
            return

        self.tag_combo.blockSignals(True)
        prev_tag = self.selected_tag
        self.tag_combo.clear()
        self.tag_combo.addItem(t("lib_tag_all"), userData=None)

        if not all_tags:
            self.tag_combo.setVisible(False)
            self.selected_tag = None
        else:
            self.tag_combo.setVisible(True)
            for tag in sorted(all_tags, key=lambda s: s.lower()):
                self.tag_combo.addItem(f"🏷️ {tag}", userData=tag)

            # Restore previous selection if it still exists
            if prev_tag:
                found = False
                for i in range(self.tag_combo.count()):
                    if self.tag_combo.itemData(i) == prev_tag:
                        self.tag_combo.setCurrentIndex(i)
                        found = True
                        break
                if not found:
                    self.selected_tag = None
                    self.tag_combo.setCurrentIndex(0)
            else:
                self.tag_combo.setCurrentIndex(0)

        self.tag_combo.blockSignals(False)

    def on_tag_combo_changed(self, index):
        tag_val = self.tag_combo.itemData(index) if hasattr(self, 'tag_combo') else None
        self.selected_tag = tag_val
        self.apply_filters()

    def on_arch_combo_changed(self, index):
        self.apply_filters()

    def on_tag_filter_clicked(self, tag):
        self.selected_tag = tag
        self.apply_filters()

    def on_sort_changed(self, text=None):
        self.apply_filters()

    def apply_filters(self):
        query = self.local_search.text().strip().lower()
        show_only_favs = self.fav_toggle_btn.isChecked()
        selected_tag = getattr(self, 'selected_tag', None)
        selected_arch = self.arch_combo.itemData(self.arch_combo.currentIndex()) if hasattr(self, 'arch_combo') else None
        
        filtered = []
        for m in self.models_data:
            # 1. Favorite condition
            if show_only_favs and not m.get('is_favorite', 0):
                continue
            # 2. Tag filter condition
            if selected_tag and selected_tag not in m.get('tags', []):
                continue
            # 3. Architecture filter condition
            if selected_arch:
                m_arch = m.get('base_architecture') or ""
                if not m_arch:
                    from utils.png_parser import detect_base_architecture
                    m_arch = detect_base_architecture([m.get('name', ''), m.get('file_path', '')])
                if m_arch != selected_arch:
                    continue
            # 4. Search query condition
            if query:
                name_match = query in m.get('name', '').lower()
                file_match = query in os.path.basename(m.get('file_path', '')).lower()
                tag_match = any(query in tag.lower() for tag in m.get('tags', []))
                arch_match = query in (m.get('base_architecture', '') or '').lower()
                if not (name_match or file_match or tag_match or arch_match):
                    continue
            filtered.append(m)

        # 4. Sorting
        sort_mode = self.sort_combo.currentText() if hasattr(self, 'sort_combo') else ""
        if sort_mode == t("lib_sort_az"):
            filtered.sort(key=lambda x: x.get('name', '').lower())
        elif sort_mode == t("lib_sort_za"):
            filtered.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
        elif sort_mode == t("lib_sort_fav_first"):
            filtered.sort(key=lambda x: (not bool(x.get('is_favorite', 0)), x.get('name', '').lower()))
        elif sort_mode == t("lib_sort_newest"):
            filtered.sort(key=lambda x: x.get('id', 0), reverse=True)
            
        self.filtered_models_data = filtered
        self.populate_grid(use_filtered=True)

    def on_local_search_changed(self, text):
        self.search_debounce_timer.start(150)

    def on_fav_toggle_clicked(self):
        self.apply_filters()

    def update_card_image(self, model_id, image_path):
        if image_path in THUMBNAIL_CACHE:
            del THUMBNAIL_CACHE[image_path]

        for m in self.models_data:
            if m.get('id') == model_id:
                m['image_path'] = image_path
        for m in self.filtered_models_data:
            if m.get('id') == model_id:
                m['image_path'] = image_path
                
        for card in self.cards:
            if isinstance(card, ModelCardWidget) and card.model_data.get('id') == model_id:
                card.model_data['image_path'] = image_path
                card.set_card_image(image_path)
                break

    def update_card_name(self, model_id, name):
        self.update_card_model_data(model_id, name)

    def update_card_model_data(self, model_id, name, base_architecture=None):
        for m in self.models_data:
            if m.get('id') == model_id:
                m['name'] = name
                if base_architecture is not None:
                    m['base_architecture'] = base_architecture
        for m in self.filtered_models_data:
            if m.get('id') == model_id:
                m['name'] = name
                if base_architecture is not None:
                    m['base_architecture'] = base_architecture

        for card in self.cards:
            if isinstance(card, ModelCardWidget) and card.model_data.get('id') == model_id:
                card.model_data['name'] = name
                if base_architecture is not None:
                    card.model_data['base_architecture'] = base_architecture
                card.update_texts()
                break

    def update_card_favorite(self, model_id, is_favorite):
        for m in self.models_data:
            if m.get('id') == model_id:
                m['is_favorite'] = 1 if is_favorite else 0
                
        if self.fav_toggle_btn.isChecked():
            self.apply_filters()
        else:
            for card in self.cards:
                if isinstance(card, ModelCardWidget) and card.model_data.get('id') == model_id:
                    card.model_data['is_favorite'] = 1 if is_favorite else 0
                    card.is_fav = is_favorite
                    card.update_fav_btn_style()
                    break

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.oldSize().width() <= 0 or event.oldSize().width() == event.size().width():
            return

        width = self.scroll_area.viewport().width()
        card_width = 200
        spacing = 16
        scrollbar_w = 16 if len(self.cards) > 16 else 0
        avail_w = max(100, width - scrollbar_w)
        columns = max(1, (avail_w + spacing) // (card_width + spacing))

        if columns != self.current_columns:
            self.resize_debounce_timer.start(35)

    def _on_debounced_resize(self):
        self.update_grid_layout()

    def check_visible_cards(self):
        if not self.cards or isinstance(self.cards[0], QLabel):
            return
        viewport = self.scroll_area.viewport()
        if not viewport or not viewport.isVisible():
            return

        columns = self.current_columns if self.current_columns > 0 else 1
        scroll_y = self.scroll_area.verticalScrollBar().value()
        viewport_h = viewport.height()
        row_h = 240 + 16 # card height + spacing
        first_row = max(0, (scroll_y - 300) // row_h)
        last_row = (scroll_y + viewport_h + 350) // row_h
        first_idx = int(first_row * columns)
        last_idx = min(len(self.cards), int((last_row + 1) * columns))

        for i in range(first_idx, last_idx):
            card = self.cards[i]
            if isinstance(card, ModelCardWidget):
                if not (getattr(card, 'image_loaded', False) or getattr(card, 'image_loading', False)):
                    card.ensure_image_loaded()

    def on_card_selection_toggled(self, model_data, is_selected):
        m_id = model_data.get('id')
        was_active = len(self.selected_model_ids) > 0
        if is_selected:
            self.selected_model_ids.add(m_id)
        else:
            self.selected_model_ids.discard(m_id)
        is_active = len(self.selected_model_ids) > 0
        if is_active != was_active:
            for card in self.cards:
                if isinstance(card, ModelCardWidget):
                    card.set_checkbox_visible(is_active)
        self.update_bulk_bar()

    def update_bulk_bar(self):
        count = len(self.selected_model_ids)
        if count > 0:
            self.bulk_count_label.setText(t("bulk_models_selected_count").format(count=count))
            has_missing = any(isinstance(c, ModelCardWidget) and not getattr(c, 'file_exists', True) for c in self.cards)
            self.bulk_select_missing_btn.setVisible(has_missing)
            self.bulk_bar.setVisible(True)
        else:
            self.bulk_bar.setVisible(False)

    def select_all_cards(self):
        for card in self.cards:
            if isinstance(card, ModelCardWidget):
                card.set_checkbox_visible(True)
                card.set_selected(True)
                self.selected_model_ids.add(card.model_data.get('id'))
        self.update_bulk_bar()

    def select_missing_cards(self):
        for card in self.cards:
            if isinstance(card, ModelCardWidget) and not getattr(card, 'file_exists', True):
                card.set_selected(True)
                self.selected_model_ids.add(card.model_data.get('id'))
        is_active = len(self.selected_model_ids) > 0
        for card in self.cards:
            if isinstance(card, ModelCardWidget):
                card.set_checkbox_visible(is_active)
        self.update_bulk_bar()

    def clear_selection(self):
        for card in self.cards:
            if isinstance(card, ModelCardWidget):
                if card.is_selected:
                    card.set_selected(False)
                card.set_checkbox_visible(False)
        self.selected_model_ids.clear()
        self.update_bulk_bar()

    def on_bulk_delete_clicked(self):
        if not self.selected_model_ids:
            return
        from PySide6.QtWidgets import QMessageBox
        count = len(self.selected_model_ids)
        confirm = QMessageBox.question(
            self,
            t("confirm_delete_models_title"),
            t("confirm_delete_models_msg").format(count=count),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.bulk_delete_requested.emit(list(self.selected_model_ids))

    def on_single_card_delete_requested(self, model_data):
        from PySide6.QtWidgets import QMessageBox
        m_id = model_data.get('id')
        name = model_data.get('name', '')
        confirm = QMessageBox.question(
            self,
            t("confirm_delete_models_title"),
            t("detail_delete_model_confirm").format(name=name),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            self.bulk_delete_requested.emit([m_id])

    def on_bulk_fav_clicked(self, is_fav):
        if self.selected_model_ids:
            self.bulk_favorite_requested.emit(list(self.selected_model_ids), is_fav)

    def on_bulk_add_tag_clicked(self):
        if self.selected_model_ids:
            self.bulk_add_tag_requested.emit(list(self.selected_model_ids))

    def on_bulk_remove_tag_clicked(self):
        if self.selected_model_ids:
            self.bulk_remove_tag_requested.emit(list(self.selected_model_ids))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.selected_model_ids:
            self.clear_selection()
            return
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.selected_model_ids:
            self.on_bulk_delete_clicked()
            return
        super().keyPressEvent(event)

    def on_scan_clicked(self):
        self.scan_requested.emit(self.library_name)

    def tr_lib_name(self, name):
        if name == "Lora Modelleri":
            return "Lora Models" if get_lang() == "en" else "Lora Modelleri"
        elif name == "Checkpoint Modelleri":
            return "Checkpoint Models" if get_lang() == "en" else "Checkpoint Modelleri"
        elif name == "Favoriler":
            return "Favorites" if get_lang() == "en" else "Favoriler"
        return name

    def retranslate_ui(self):
        self.title_label.setText(self.tr_lib_name(self.library_name) if self.library_name else t("app_title").split()[0])
        self.local_search.setPlaceholderText(t("search_placeholder"))
        self.fav_toggle_btn.setText(t("view_favorites"))
        
        curr_sort_idx = self.sort_combo.currentIndex() if hasattr(self, 'sort_combo') else -1
        if hasattr(self, 'sort_combo'):
            self.sort_combo.blockSignals(True)
            self.sort_combo.clear()
            self.sort_combo.addItems([
                t("lib_sort_newest"),
                t("lib_sort_az"),
                t("lib_sort_za"),
                t("lib_sort_fav_first")
            ])
            if 0 <= curr_sort_idx < self.sort_combo.count():
                self.sort_combo.setCurrentIndex(curr_sort_idx)
            self.sort_combo.blockSignals(False)

        if hasattr(self, 'tag_combo') and self.tag_combo.count() > 0:
            self.tag_combo.blockSignals(True)
            self.tag_combo.setItemText(0, t("lib_tag_all"))
            self.tag_combo.blockSignals(False)

        if hasattr(self, 'arch_combo') and self.arch_combo.count() > 0:
            self.arch_combo.blockSignals(True)
            self.arch_combo.setItemText(0, t("lib_arch_all"))
            self.arch_combo.blockSignals(False)

        self.scan_btn.setText(f"  {t('view_scan_library')}")
        self.scan_btn.setIcon(get_icon("refresh", "#FFFFFF", 16))
        self.fav_toggle_btn.setText(f"  {t('view_favorites')}")
        self.fav_toggle_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.bulk_select_all_btn.setText(t("bulk_select_all"))
        self.bulk_select_missing_btn.setText(t("bulk_select_missing"))
        self.bulk_clear_btn.setText(t("bulk_clear_selection"))
        self.bulk_fav_btn.setText(f"  {t('bulk_set_fav')}")
        self.bulk_fav_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.bulk_add_tag_btn.setText(f"  {t('bulk_add_tag')}")
        self.bulk_add_tag_btn.setIcon(get_icon("tag", "#FFFFFF", 16))
        self.bulk_remove_tag_btn.setText(f"  {t('bulk_remove_tag')}")
        self.bulk_remove_tag_btn.setIcon(get_icon("tag", "#9AA0A6", 16))
        self.bulk_delete_btn.setText(f"  {t('bulk_delete_models')}")
        self.bulk_delete_btn.setIcon(get_icon("trash", "#FFFFFF", 16))
        if len(self.selected_model_ids) > 0:
            self.bulk_count_label.setText(t("bulk_models_selected_count").format(count=len(self.selected_model_ids)))
        self.populate_grid(use_filtered=True)
