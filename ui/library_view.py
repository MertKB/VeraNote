# ui/library_view.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QRunnable, QThreadPool, QObject, Slot
from PySide6.QtGui import QPixmap, QFontMetrics, QPainter, QPainterPath, QImage
from utils.i18n import t, get_lang

from utils.cache import THUMBNAIL_CACHE

def cache_thumbnail(path, pixmap, max_size=150):
    if not path or not pixmap or pixmap.isNull():
        return
    THUMBNAIL_CACHE[path] = pixmap

class ImageLoadSignals(QObject):
    image_loaded = Signal(str, object, int, int) # image_path, QImage, target_w, target_h

class ImageLoadWorker(QRunnable):
    def __init__(self, image_path, target_w=184, target_h=160):
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

def get_rounded_pixmap(pixmap, radius=11):
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

    def __init__(self, model_data, parent=None):
        super().__init__(parent)
        self.model_data = model_data
        self.setObjectName("ModelCard")
        
        # Set fixed card size so it never squashes or deforms under grid layout resizing
        self.setFixedSize(200, 240)
        
        filepath = self.model_data.get('file_path', '')
        self.original_filename = os.path.basename(filepath) if filepath else t("unknown_file")
        
        # Check if file exists on disk
        self.file_exists = os.path.exists(filepath) if filepath else False
        
        self.is_fav = bool(self.model_data.get('is_favorite', 0))
        
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Image Container (Thumbnail) - Fixed size inside fixed card
        self.image_label = QLabel()
        self.image_label.setObjectName("CardImageLabel")
        self.image_label.setFixedSize(184, 160)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Overlay Title layout inside the image label at the bottom
        self.image_layout = QVBoxLayout(self.image_label)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        self.image_layout.setSpacing(0)
        self.image_layout.addStretch()

        self.title_label = QLabel()
        self.title_label.setObjectName("CardTitleOverlay")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel#CardTitleOverlay {
                background-color: rgba(0, 0, 0, 0.65);
                color: #F3F3F3;
                padding: 6px;
                font-size: 12px;
                font-weight: bold;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        self.image_layout.addWidget(self.title_label)
        layout.addWidget(self.image_label)

        # Filename Label - Placed outside/below the thumbnail container, single-line elided
        self.filename_label = QLabel()
        self.filename_label.setObjectName("CardFilename")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setWordWrap(False)
        self.filename_label.setFixedHeight(20) # Fixed height prevents vertical displacement
        layout.addWidget(self.filename_label)

        # Render elided texts & cached image
        self.set_card_image(self.model_data.get('image_path'))
        self.update_texts()

        # If file does not exist on disk, render a dark yellow warning badge overlay on top-right of card
        if not self.file_exists:
            self.warning_badge = QLabel(t("not_on_disk"), self.image_label)
            self.warning_badge.setStyleSheet("""
                background-color: rgba(249, 168, 37, 0.9);
                color: #131314;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
            """)
            self.warning_badge.setGeometry(108, 8, 68, 20)
            self.warning_badge.setAlignment(Qt.AlignCenter)

        # Star / Favorite Button Overlay on top-left of card
        self.fav_btn = QPushButton(self.image_label)
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setGeometry(8, 8, 28, 28)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(self.on_fav_clicked)
        self.update_fav_btn_style()

    def update_texts(self):
        metrics = QFontMetrics(self.font())
        
        # Elide name overlay (Max 172px width)
        name = self.model_data.get('name', '')
        if self.model_data.get('is_hidden', 0) == 1:
            name = "🔒 " + name
        elided_title = metrics.elidedText(name, Qt.ElideRight, 172)
        self.title_label.setText(elided_title)

        # Elide filename (Max 180px width)
        elided_filename = metrics.elidedText(self.original_filename, Qt.ElideRight, 180)
        self.filename_label.setText(elided_filename)

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
        if image_path and os.path.exists(image_path):
            # Check module-level cache
            if image_path in THUMBNAIL_CACHE:
                self.image_label.setPixmap(THUMBNAIL_CACHE[image_path])
                self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                return
            
            # Non-blocking async background loading via QThreadPool
            worker = ImageLoadWorker(image_path, target_w=184, target_h=160)
            worker.signals.image_loaded.connect(self._on_async_image_loaded)
            QThreadPool.globalInstance().start(worker)
            return
        
        self.image_label.setText("Görsel Yok")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setStyleSheet("color: #5F6368; font-size: 14px; font-weight: bold; background-color: #2D2F31; border-radius: 8px;")

    @Slot(str, object, int, int)
    def _on_async_image_loaded(self, path, qimage, w, h):
        if getattr(self, 'current_image_path', '') != path:
            return
        if qimage and not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage)
            rounded = get_rounded_pixmap(pixmap, radius=11)
            cache_thumbnail(path, rounded)
            self.image_label.setPixmap(rounded)
            self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
        else:
            self.image_label.setText("Görsel Yok")
            self.image_label.setPixmap(QPixmap())
            self.image_label.setStyleSheet("color: #5F6368; font-size: 14px; font-weight: bold; background-color: #2D2F31; border-radius: 8px;")

    def prepare_for_deletion(self):
        """Immediately clear QPixmap references to release RAM memory before Qt deletes the widget."""
        self.image_label.setPixmap(QPixmap())
        if hasattr(self, 'warning_badge'):
            self.warning_badge.deleteLater()
        if hasattr(self, 'fav_btn'):
            self.fav_btn.deleteLater()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.model_data)
        super().mouseReleaseEvent(event)

    def on_fav_clicked(self):
        self.is_fav = not self.is_fav
        self.model_data['is_favorite'] = 1 if self.is_fav else 0
        self.update_fav_btn_style()
        self.favorite_toggled.emit(self.model_data.get('id', 0), self.is_fav)

    def update_fav_btn_style(self):
        if self.is_fav:
            text = "⭐"
            bg = "rgba(255, 215, 0, 0.25)"
            border = "rgba(255, 215, 0, 0.8)"
            color = "#FFD700"
        else:
            text = "☆"
            bg = "rgba(255, 255, 255, 0.1)"
            border = "rgba(255, 255, 255, 0.25)"
            color = "#888888"
        self.fav_btn.setText(text)
        self.fav_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
                color: {color};
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 215, 0, 0.4);
                border-color: #FFD700;
                color: #FFD700;
            }}
        """)


class LibraryView(QWidget):
    model_clicked = Signal(dict)
    scan_requested = Signal(str) # library_name
    favorite_toggled = Signal(int, bool)
    model_hide_requested = Signal(dict)
    model_unhide_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LibraryViewWidget")
        self.library_name = ""
        self.models_data = []
        self.filtered_models_data = []
        self.cards = []
        
        # Incremental loader state variables
        self.pending_cards_data = []
        self.current_loading_index = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.load_next_batch)

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self.apply_filters)

        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Header: Name, Search input, Scan Button
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Kütüphane")
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        # Local search input
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText("Bu kitaplık içinde filtrele...")
        self.local_search.setMinimumWidth(120)
        self.local_search.setMaximumWidth(400)
        self.local_search.textChanged.connect(self.on_local_search_changed)
        header_layout.addWidget(self.local_search)

        # ⭐ Favoriler Toggle Button
        self.fav_toggle_btn = QPushButton("⭐ Favoriler")
        self.fav_toggle_btn.setCheckable(True)
        self.fav_toggle_btn.setObjectName("FavToggleBtn")
        self.fav_toggle_btn.clicked.connect(self.on_fav_toggle_clicked)
        header_layout.addWidget(self.fav_toggle_btn)

        header_layout.addStretch()

        self.scan_btn = QPushButton("🔄 Kitaplığı Tara")
        self.scan_btn.setObjectName("HeaderAddBtn")
        self.scan_btn.setFixedHeight(36)
        self.scan_btn.setStyleSheet("QPushButton { border-radius: 18px !important; padding: 6px 14px !important; font-weight: bold !important; }")
        self.scan_btn.clicked.connect(self.on_scan_clicked)
        header_layout.addWidget(self.scan_btn)

        self.main_layout.addLayout(header_layout)

        # Scroll Area for Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("GridScrollArea")
        self.scroll_area.setWidgetResizable(True)
        
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background-color: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_container)
        self.main_layout.addWidget(self.scroll_area)

    def set_library(self, name, models):
        self.library_name = name
        self.models_data = models
        self.filtered_models_data = models
        
        # Reset filters with blocked signals to avoid duplicate rendering
        self.fav_toggle_btn.blockSignals(True)
        self.fav_toggle_btn.setChecked(False)
        self.fav_toggle_btn.blockSignals(False)
        
        self.local_search.blockSignals(True)
        self.local_search.clear()
        self.local_search.blockSignals(False)
        
        if name == "Favoriler":
            self.scan_btn.setVisible(False)
        else:
            self.scan_btn.setVisible(True)
            
        self.retranslate_ui()

    def populate_grid(self, use_filtered=False):
        # Stop any active loading timer before clearing
        if self.loading_timer.isActive():
            self.loading_timer.stop()

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
            return

        self.update_grid_layout(display_data)

    def update_grid_layout(self, display_data=None):
        # REARRANGE INSTEAD OF RE-CREATING: If cards are already instantiated, 
        # simply shift grid columns rather than re-creating widgets. Smooth as silk!
        if self.cards and not isinstance(self.cards[0], QLabel):
            width = self.scroll_area.viewport().width()
            card_width = 200
            spacing = 16
            columns = max(1, (width + spacing) // (card_width + spacing))
            
            for i, card in enumerate(self.cards):
                self.grid_layout.removeWidget(card)
                row = i // columns
                col = i % columns
                self.grid_layout.addWidget(card, row, col)
            return

        if display_data is None:
            display_data = self.filtered_models_data
            
        if not display_data:
            return

        # Prepare for incremental QTimer-driven loading
        self.pending_cards_data = list(display_data)
        self.current_loading_index = 0
        self.loading_timer.start(10) # Render batch every 10ms to keep GUI completely lag-free

    def load_next_batch(self):
        if not self.pending_cards_data or self.current_loading_index >= len(self.pending_cards_data):
            self.loading_timer.stop()
            return

        width = self.scroll_area.viewport().width()
        card_width = 200
        spacing = 16
        columns = max(1, (width + spacing) // (card_width + spacing))

        batch_size = 20 # Render 20 cards per batch
        end_index = min(self.current_loading_index + batch_size, len(self.pending_cards_data))

        for i in range(self.current_loading_index, end_index):
            model = self.pending_cards_data[i]
            card = ModelCardWidget(model, parent=self)
            card.clicked.connect(self.model_clicked.emit)
            card.favorite_toggled.connect(self.favorite_toggled.emit)
            card.hide_requested.connect(self.model_hide_requested.emit)
            card.unhide_requested.connect(self.model_unhide_requested.emit)
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(card, row, col)
            self.cards.append(card)

        self.current_loading_index = end_index
        
        # Stop timer if finished
        if self.current_loading_index >= len(self.pending_cards_data):
            self.loading_timer.stop()

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
        # Invalidate module cache key to force reload
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
                
        # If the favorite toggle filter is active, re-apply it so the unfavorited card disappears immediately
        if self.fav_toggle_btn.isChecked():
            self.apply_filters()
        else:
            # Otherwise, just update the individual card's visual state
            for card in self.cards:
                if isinstance(card, ModelCardWidget) and card.model_data.get('id') == model_id:
                    card.model_data['is_favorite'] = 1 if is_favorite else 0
                    card.is_fav = is_favorite
                    card.update_fav_btn_style()
                    break

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_grid_layout()

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
        self.populate_grid(use_filtered=True)
