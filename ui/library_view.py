# ui/library_view.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QRunnable, QThreadPool, QObject, Slot, QPoint, QRect, QMimeData, QUrl
from PySide6.QtGui import QPixmap, QFontMetrics, QPainter, QPainterPath, QImage, QDrag, QGuiApplication
from utils.i18n import t, get_lang

from utils.cache import THUMBNAIL_CACHE

def cache_thumbnail(path, pixmap, max_size=150):
    if not path or not pixmap or pixmap.isNull():
        return
    THUMBNAIL_CACHE[path] = pixmap

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

    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self.setObjectName("ModelCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # Set fixed card size so it never squashes or deforms under grid layout resizing
        self.setFixedSize(200, 240)
        
        filepath = self.model_data.get('file_path', '')
        self.original_filename = os.path.basename(filepath) if filepath else t("unknown_file")
        
        # Fast initialization without blocking disk stat
        self.file_exists = True
        self.is_fav = bool(self.model_data.get('is_favorite', 0))
        self.is_selected = False
        self.drag_start_pos = None
        
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

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

        # Multi-select Checkbox Button Overlay on top-right of image
        self.select_btn = QPushButton(self.image_label)
        self.select_btn.setObjectName("CardSelectBtn")
        self.select_btn.setFixedSize(24, 24)
        self.select_btn.setGeometry(166, 8, 24, 24)
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self.on_select_clicked)
        self.update_selection_style()

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

    def contextMenuEvent(self, event):
        main_win = self.window()
        if not (main_win and getattr(main_win, 'incognito_active', False)):
            event.ignore()
            return

        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        
        is_hidden = self.model_data.get('is_hidden', 0) == 1
        
        if not is_hidden:
            hide_action = menu.addAction(t("menu_hide"))
            action = menu.exec(QCursor.pos())
            if action == hide_action:
                self.hide_requested.emit(self.model_data)
        else:
            unhide_action = menu.addAction(t("menu_unhide"))
            action = menu.exec(QCursor.pos())
            if action == unhide_action:
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
        if hasattr(self, 'warning_badge'):
            self.warning_badge.deleteLater()
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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LibraryViewWidget")
        self.library_name = ""
        self.models_data = []
        self.filtered_models_data = []
        self.cards = []
        self.selected_model_ids = set()
        self.current_columns = -1
        

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
        self.local_search.setMaximumWidth(320)
        self.local_search.textChanged.connect(self.on_local_search_changed)
        header_layout.addWidget(self.local_search)

        # ⭐ Favoriler Toggle Button
        self.fav_toggle_btn = QPushButton(t("view_favorites"))
        self.fav_toggle_btn.setCheckable(True)
        self.fav_toggle_btn.setObjectName("FavToggleBtn")
        self.fav_toggle_btn.clicked.connect(self.on_fav_toggle_clicked)
        header_layout.addWidget(self.fav_toggle_btn)

        header_layout.addStretch()

        self.scan_btn = QPushButton(t("view_scan_library"))
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

        self.bulk_clear_btn = QPushButton(t("bulk_clear_selection"))
        self.bulk_clear_btn.setProperty("class", "bulk_btn")
        self.bulk_clear_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_clear_btn.clicked.connect(self.clear_selection)
        bulk_layout.addWidget(self.bulk_clear_btn)

        self.bulk_fav_btn = QPushButton("⭐ " + t("bulk_set_fav"))
        self.bulk_fav_btn.setProperty("class", "bulk_btn")
        self.bulk_fav_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_fav_btn.clicked.connect(lambda: self.on_bulk_fav_clicked(True))
        bulk_layout.addWidget(self.bulk_fav_btn)

        self.bulk_add_tag_btn = QPushButton("🏷️ " + t("bulk_add_tag"))
        self.bulk_add_tag_btn.setProperty("class", "bulk_primary_btn")
        self.bulk_add_tag_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_add_tag_btn.clicked.connect(self.on_bulk_add_tag_clicked)
        bulk_layout.addWidget(self.bulk_add_tag_btn)

        self.bulk_remove_tag_btn = QPushButton("✕ " + t("bulk_remove_tag"))
        self.bulk_remove_tag_btn.setProperty("class", "bulk_btn")
        self.bulk_remove_tag_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_remove_tag_btn.clicked.connect(self.on_bulk_remove_tag_clicked)
        bulk_layout.addWidget(self.bulk_remove_tag_btn)

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

        self.retranslate_ui()

    def _create_card(self, model):
        card = ModelCardWidget(model, parent=self.grid_container)
        card.clicked.connect(self.model_clicked.emit)
        card.favorite_toggled.connect(self.favorite_toggled.emit)
        card.hide_requested.connect(self.model_hide_requested.emit)
        card.unhide_requested.connect(self.model_unhide_requested.emit)
        card.selection_toggled.connect(self.on_card_selection_toggled)
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

    def apply_filters(self):
        query = self.local_search.text().strip().lower()
        show_only_favs = self.fav_toggle_btn.isChecked()
        
        filtered = []
        for m in self.models_data:
            # 1. Favorite condition
            if show_only_favs and not m.get('is_favorite', 0):
                continue
            # 2. Search query condition
            if query:
                name_match = query in m.get('name', '').lower()
                file_match = query in os.path.basename(m.get('file_path', '')).lower()
                tag_match = any(query in tag.lower() for tag in m.get('tags', []))
                if not (name_match or file_match or tag_match):
                    continue
            filtered.append(m)
            
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
        for m in self.models_data:
            if m.get('id') == model_id:
                m['name'] = name
        for m in self.filtered_models_data:
            if m.get('id') == model_id:
                m['name'] = name

        for card in self.cards:
            if isinstance(card, ModelCardWidget) and card.model_data.get('id') == model_id:
                card.model_data['name'] = name
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
        if is_selected:
            self.selected_model_ids.add(m_id)
        else:
            self.selected_model_ids.discard(m_id)
        self.update_bulk_bar()

    def update_bulk_bar(self):
        count = len(self.selected_model_ids)
        if count > 0:
            self.bulk_count_label.setText(t("bulk_models_selected_count").format(count=count))
            self.bulk_bar.setVisible(True)
        else:
            self.bulk_bar.setVisible(False)

    def select_all_cards(self):
        for card in self.cards:
            if isinstance(card, ModelCardWidget):
                card.set_selected(True)
                self.selected_model_ids.add(card.model_data.get('id'))
        self.update_bulk_bar()

    def clear_selection(self):
        for card in self.cards:
            if isinstance(card, ModelCardWidget) and card.is_selected:
                card.set_selected(False)
        self.selected_model_ids.clear()
        self.update_bulk_bar()

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
        self.scan_btn.setText(t("view_scan_library"))
        self.bulk_select_all_btn.setText(t("bulk_select_all"))
        self.bulk_clear_btn.setText(t("bulk_clear_selection"))
        self.bulk_fav_btn.setText("⭐ " + t("bulk_set_fav"))
        self.bulk_add_tag_btn.setText("🏷️ " + t("bulk_add_tag"))
        self.bulk_remove_tag_btn.setText("✕ " + t("bulk_remove_tag"))
        if len(self.selected_model_ids) > 0:
            self.bulk_count_label.setText(t("bulk_models_selected_count").format(count=len(self.selected_model_ids)))
        self.populate_grid(use_filtered=True)
