# ui/workflow_view.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit, QDialog, QFormLayout, QTextEdit, QFileDialog, QMessageBox, QComboBox)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QUrl, QMimeData, QThreadPool, Slot, QPoint, QRect
from PySide6.QtGui import QPixmap, QFontMetrics, QPainter, QPainterPath, QDrag, QGuiApplication, QImage
from utils.i18n import t, get_lang
from ui.library_view import THUMBNAIL_CACHE, ImageLoadWorker

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

class WorkflowMetadataDialog(QDialog):
    def __init__(self, default_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("workflow_dialog_title"))
        self.setFixedSize(450, 300)
        self.init_ui(default_name)

    def init_ui(self, default_name):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        self.name_edit = QLineEdit(default_name)
        form_layout.addRow(t("workflow_dialog_name"), self.name_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText(t("workflow_dialog_desc_placeholder"))
        self.desc_edit.setFixedHeight(80)
        form_layout.addRow(t("workflow_dialog_desc"), self.desc_edit)

        # Preview image selection
        img_layout = QHBoxLayout()
        self.img_edit = QLineEdit()
        self.img_edit.setPlaceholderText(t("workflow_dialog_preview_placeholder"))
        self.img_browse_btn = QPushButton(t("settings_browse"))
        self.img_browse_btn.clicked.connect(self.browse_image)
        img_layout.addWidget(self.img_edit)
        img_layout.addWidget(self.img_browse_btn)
        form_layout.addRow(t("workflow_dialog_preview"), img_layout)

        layout.addLayout(form_layout)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.cancel_btn = QPushButton(t("workflow_dialog_cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn = QPushButton(t("workflow_dialog_save"))
        self.ok_btn.setObjectName("SaveBtn") # Blue styled
        self.ok_btn.clicked.connect(self.accept)
        btn_box.addWidget(self.cancel_btn)
        btn_box.addWidget(self.ok_btn)
        layout.addLayout(btn_box)

    def browse_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("workflow_dialog_preview").replace(":", ""), "", t("dialog_image_filter")
        )
        if file_path:
            self.img_edit.setText(file_path)

    def get_metadata(self):
        return {
            'name': self.name_edit.text().strip(),
            'description': self.desc_edit.toPlainText().strip(),
            'image_path': self.img_edit.text().strip()
        }

class WorkflowCardWidget(QFrame):
    clicked = Signal(dict)
    hide_requested = Signal(dict)
    unhide_requested = Signal(dict)
    favorite_toggled = Signal(int, bool)

    def __init__(self, workflow_data, parent=None):
        super().__init__(parent)
        self.workflow_data = workflow_data
        self.setObjectName("ModelCard") # Reuse ModelCard styles (border-radius, hover, etc.)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(200, 240)
        self.setCursor(Qt.PointingHandCursor)
        self.image_loaded = False
        self.image_loading = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image Container
        self.image_label = QLabel(self)
        self.image_label.setObjectName("CardImageLabel")
        self.image_label.setFixedSize(200, 135)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Star / Favorite Button Overlay on top-left of image
        self.fav_btn = QPushButton(self.image_label)
        self.fav_btn.setObjectName("CardFavBtn")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setGeometry(8, 8, 28, 28)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.clicked.connect(self.on_fav_clicked)

        # Bottom Info Panel
        self.info_panel = QFrame(self)
        self.info_panel.setObjectName("CardInfoPanel")
        self.info_panel.setAttribute(Qt.WA_StyledBackground, True)
        self.info_panel.setFixedHeight(105)
        
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(10, 6, 10, 6)
        info_layout.setSpacing(2)

        # Name label
        self.title_label = QLabel(self.info_panel)
        self.title_label.setObjectName("CardTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.title_label)

        # Filename label
        self.filename_label = QLabel(self.info_panel)
        self.filename_label.setObjectName("CardFilename")
        self.filename_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.filename_label)

        # Description/snippet label
        self.desc_label = QLabel(self.info_panel)
        self.desc_label.setObjectName("CardFilename") # smaller grey text
        self.desc_label.setWordWrap(True)
        self.desc_label.setFixedHeight(34)
        self.desc_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.desc_label)

        layout.addWidget(self.info_panel)

        # Set values
        self.update_content()

    def update_fav_btn_style(self):
        is_fav = self.workflow_data.get('is_favorite', 0) == 1
        self.fav_btn.setText("⭐" if is_fav else "☆")
        self.fav_btn.setProperty("favorite", is_fav)
        self.fav_btn.style().unpolish(self.fav_btn)
        self.fav_btn.style().polish(self.fav_btn)

    def on_fav_clicked(self):
        is_fav = self.workflow_data.get('is_favorite', 0) == 1
        new_fav = not is_fav
        self.workflow_data['is_favorite'] = 1 if new_fav else 0
        self.update_fav_btn_style()
        self.favorite_toggled.emit(self.workflow_data.get('id', 0), new_fav)

    def update_content(self):
        metrics = QFontMetrics(self.font())
        name = self.workflow_data.get('name', t("unknown_workflow"))
        if self.workflow_data.get('is_hidden', 0) == 1:
            name = "🔒 " + name
        file_path = self.workflow_data.get('file_path', '')
        filename = os.path.basename(file_path) if file_path else 'workflow.json'
        description = self.workflow_data.get('description', '') or t("no_description")
        image_path = self.workflow_data.get('image_path', '')

        # Set texts elided
        self.title_label.setText(metrics.elidedText(name, Qt.ElideRight, 180))
        self.filename_label.setText(metrics.elidedText(filename, Qt.ElideRight, 180))
        self.desc_label.setText(metrics.elidedText(description, Qt.ElideRight, 180 * 2))

        # Update fav button style
        self.update_fav_btn_style()

        # Set image
        if image_path and os.path.exists(image_path):
            self.current_image_path = image_path
            if image_path in THUMBNAIL_CACHE:
                self.image_label.setPixmap(THUMBNAIL_CACHE[image_path])
                self.image_label.setText("")
                self.image_label.setStyleSheet("background-color: transparent;")
                self.image_loaded = True
                return
            else:
                self.image_label.setText("")
                self.image_label.setPixmap(QPixmap())
                self.image_label.setStyleSheet("background-color: #242527; border-radius: 8px;")
                self.image_loaded = False
                self.ensure_image_loaded()
                return

        self.show_default_placeholder()
        self.image_loaded = True

    def ensure_image_loaded(self):
        if getattr(self, 'image_loaded', False) or getattr(self, 'image_loading', False):
            return
        image_path = self.workflow_data.get('image_path', '')
        if not image_path or not os.path.exists(image_path):
            self.image_loaded = True
            return
        if image_path in THUMBNAIL_CACHE:
            self.image_label.setPixmap(THUMBNAIL_CACHE[image_path])
            self.image_label.setText("")
            self.image_label.setStyleSheet("background-color: transparent;")
            self.image_loaded = True
            return
        self.image_loading = True
        self.current_image_path = image_path
        worker = ImageLoadWorker(image_path, target_w=200, target_h=135)
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
            THUMBNAIL_CACHE[path] = rounded
            self.image_label.setPixmap(rounded)
            self.image_label.setText("")
            self.image_label.setStyleSheet("background-color: transparent;")
            self.image_loaded = True
        else:
            self.show_default_placeholder()
            self.image_loaded = True

    def prepare_for_deletion(self):
        """Immediately clear QPixmap references to release RAM memory before Qt deletes the widget."""
        self.image_label.setPixmap(QPixmap())
        self.image_loaded = False
        self.image_loading = False

    def show_default_placeholder(self):
        # Default Flow placeholder (emoji / styling)
        self.image_label.setText("🧩")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setStyleSheet("""
            color: #8ab4f8; 
            font-size: 48px; 
            font-weight: bold; 
            background-color: #2D2F31; 
            border-radius: 8px;
        """)

    def contextMenuEvent(self, event):
        main_win = self.window()
        if not (main_win and getattr(main_win, 'incognito_active', False)):
            event.ignore()
            return

        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        menu = QMenu(self)
        
        is_hidden = self.workflow_data.get('is_hidden', 0) == 1
        
        if not is_hidden:
            hide_action = menu.addAction(t("menu_hide"))
            action = menu.exec(QCursor.pos())
            if action == hide_action:
                self.hide_requested.emit(self.workflow_data)
        else:
            unhide_action = menu.addAction(t("menu_unhide"))
            action = menu.exec(QCursor.pos())
            if action == unhide_action:
                self.unhide_requested.emit(self.workflow_data)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self, 'drag_start_position') and self.drag_start_position is not None:
                dist = (event.position().toPoint() - self.drag_start_position).manhattanLength()
                if dist < QGuiApplication.styleHints().startDragDistance():
                    self.clicked.emit(self.workflow_data)
            else:
                self.clicked.emit(self.workflow_data)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, 'drag_start_position') or self.drag_start_position is None:
            return
        if (event.position().toPoint() - self.drag_start_position).manhattanLength() < QGuiApplication.styleHints().startDragDistance():
            return
            
        file_path = self.workflow_data.get('file_path', '')
        if not file_path or not os.path.exists(file_path):
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(file_path)])
        mime_data.setText(file_path)
        drag.setMimeData(mime_data)
        
        # Grab card visual representation to show a thumbnail under cursor
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_position)
        
        drag.exec(Qt.CopyAction)

class WorkflowView(QWidget):
    workflow_clicked = Signal(dict)
    add_workflow_requested = Signal(int, str, str, str, str) # library_id, name, file_path, description, image_path
    workflow_hide_requested = Signal(dict)
    workflow_unhide_requested = Signal(dict)
    workflow_favorite_toggled = Signal(int, bool)
    delete_library_requested = Signal(str) # library_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("LibraryViewWidget")
        self.library_id = None
        self.library_name = ""
        self.workflows_data = []
        self.filtered_workflows_data = []
        self.cards = []
        self.current_columns = -1
        
        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self.populate_grid)

        self.resize_debounce_timer = QTimer(self)
        self.resize_debounce_timer.setSingleShot(True)
        self.resize_debounce_timer.timeout.connect(self._on_debounced_resize)

        self.scroll_check_timer = QTimer(self)
        self.scroll_check_timer.setSingleShot(True)
        self.scroll_check_timer.timeout.connect(self.check_visible_cards)
        
        self.setAcceptDrops(True)
        self.init_ui()

    def minimumSizeHint(self):
        return QSize(300, 144)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel(t("workflow_library_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        # Search field
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("view_search_workflows_placeholder"))
        self.search_edit.setMinimumWidth(120)
        self.search_edit.setMaximumWidth(400)
        self.search_edit.textChanged.connect(lambda: self.search_debounce_timer.start(150))
        header_layout.addWidget(self.search_edit)

        # Favorites Filter Toggle
        self.fav_toggle_btn = QPushButton()
        self.fav_toggle_btn.setCheckable(True)
        self.fav_toggle_btn.setObjectName("FavToggleBtn")
        self.fav_toggle_btn.clicked.connect(self.on_filter_changed)
        header_layout.addWidget(self.fav_toggle_btn)

        # Sorting ComboBox
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([t("view_sort_newest"), t("view_last_edited"), t("view_sort_oldest"), t("view_sort_az"), t("view_sort_za")])
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

        self.delete_lib_btn = QPushButton(t("workflow_delete_library"))
        self.delete_lib_btn.setObjectName("DeleteLibHeaderBtn")
        self.delete_lib_btn.setFixedHeight(36)
        self.delete_lib_btn.setStyleSheet("""
            QPushButton#DeleteLibHeaderBtn {
                background-color: transparent;
                border: 1px solid #7F1D1D;
                color: #F87171;
                border-radius: 18px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton#DeleteLibHeaderBtn:hover {
                background-color: #7F1D1D;
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        self.delete_lib_btn.clicked.connect(self.on_delete_library_clicked)
        header_layout.addWidget(self.delete_lib_btn)

        self.add_btn = QPushButton(t("view_add_workflow"))
        self.add_btn.setObjectName("HeaderAddBtn") # Oval style
        self.add_btn.setFixedHeight(36)
        self.add_btn.setStyleSheet("QPushButton { border-radius: 18px !important; padding: 6px 14px !important; font-weight: bold !important; }")
        self.add_btn.clicked.connect(self.browse_workflow_file)
        header_layout.addWidget(self.add_btn)

        self.main_layout.addLayout(header_layout)

        # Drop Zone instruction
        self.drop_label = QLabel(t("workflow_drop_zone_hint"))
        self.drop_label.setStyleSheet("""
            QLabel {
                background-color: #1E1F20;
                border: 2px dashed #444746;
                border-radius: 12px;
                color: #9AA0A6;
                padding: 16px;
                font-size: 13px;
                font-weight: 500;
            }
        """)
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.drop_label)

        # Scroll Area for Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("GridScrollArea")
        self.scroll_area.setWidgetResizable(True)
        
        self.grid_container = QWidget()
        self.grid_container.setObjectName("WorkflowGridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_container)
        self.scroll_area.verticalScrollBar().valueChanged.connect(lambda: self.scroll_check_timer.start(40))
        self.main_layout.addWidget(self.scroll_area)

    def set_workflows(self, library_id, library_name, workflows):
        existing_card_ids = [c.workflow_data['id'] for c in self.cards if isinstance(c, WorkflowCardWidget)]
        new_workflow_ids = [w['id'] for w in workflows] if workflows else []
        same_lib = (self.library_id == library_id and self.library_name == library_name)
        same_workflows = (existing_card_ids == new_workflow_ids and len(new_workflow_ids) > 0)

        self.library_id = library_id
        self.library_name = library_name
        self.workflows_data = workflows or []
        self.filtered_workflows_data = self.workflows_data

        if same_lib and same_workflows:
            self.title_label.setText(self.tr_lib_name(self.library_name) if self.library_name else t("workflows_title"))
            self.update_grid_layout()
            return
        
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        
        self.fav_toggle_btn.blockSignals(True)
        self.fav_toggle_btn.setChecked(False)
        self.fav_toggle_btn.blockSignals(False)
        
        self.retranslate_ui()

    def _create_card(self, workflow):
        card = WorkflowCardWidget(workflow, parent=self.grid_container)
        card.clicked.connect(self.workflow_clicked.emit)
        card.hide_requested.connect(self.workflow_hide_requested.emit)
        card.unhide_requested.connect(self.workflow_unhide_requested.emit)
        card.favorite_toggled.connect(self.on_card_favorite_toggled)
        return card

    def on_filter_changed(self, text=None):
        self.populate_grid()

    def on_sort_changed(self, text):
        self.populate_grid()

    def on_card_favorite_toggled(self, workflow_id, is_fav):
        for w in self.workflows_data:
            if w.get('id') == workflow_id:
                w['is_favorite'] = 1 if is_fav else 0
                break
        self.workflow_favorite_toggled.emit(workflow_id, is_fav)
        if self.fav_toggle_btn.isChecked():
            self.populate_grid()

    def populate_grid(self):
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

            query = self.search_edit.text().strip().lower()
            show_only_favs = self.fav_toggle_btn.isChecked()
            
            self.filtered_workflows_data = []
            for w in self.workflows_data:
                if show_only_favs and w.get('is_favorite', 0) != 1:
                    continue
                if query:
                    name_match = query in w.get('name', '').lower()
                    desc_match = query in (w.get('description', '') or '').lower()
                    json_match = False
                    workflow_json = w.get('workflow_json')
                    if workflow_json:
                        json_match = query in workflow_json.lower()
                    
                    if not (name_match or desc_match or json_match):
                        continue
                self.filtered_workflows_data.append(w)

            sort_idx = self.sort_combo.currentIndex()
            if sort_idx == 1: # Son Düzenlenen / Last Edited
                self.filtered_workflows_data.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
            elif sort_idx == 3: # A-Z
                self.filtered_workflows_data.sort(key=lambda x: x.get('name', '').lower())
            elif sort_idx == 4: # Z-A
                self.filtered_workflows_data.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
            elif sort_idx == 2: # En Eski / Oldest
                self.filtered_workflows_data.sort(key=lambda x: x.get('created_at', ''))
            else: # En Yeni / Newest
                self.filtered_workflows_data.sort(key=lambda x: x.get('created_at', ''), reverse=True)

            if not self.filtered_workflows_data:
                empty_label = QLabel(t("view_empty_workflow"))
                empty_label.setObjectName("CardFilename")
                empty_label.setAlignment(Qt.AlignCenter)
                empty_label.setStyleSheet("font-size: 13px; color: #9AA0A6; padding: 40px;")
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
            scrollbar_w = 16 if len(self.filtered_workflows_data) > 16 else 0
            avail_w = max(100, width - scrollbar_w)
            columns = max(1, (avail_w + spacing) // (card_width + spacing))
            self.current_columns = columns

            total_rows = (len(self.filtered_workflows_data) + columns - 1) // columns
            row_height = 240 + spacing
            # Responsive Phase 1: fill entire visible screen (FHD: ~24, 2K/4K: ~40-60 workflows)
            viewport_h = max(600, self.scroll_area.viewport().height())
            visible_rows = (viewport_h // row_height) + 2
            needed_cards = max(24, columns * visible_rows)
            initial_count = min(needed_cards, len(self.filtered_workflows_data))
            for i in range(initial_count):
                card = self._create_card(self.filtered_workflows_data[i])
                self.grid_layout.addWidget(card, i // columns, i % columns)
                self.cards.append(card)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

        if len(self.filtered_workflows_data) > initial_count:
            self._pending_workflows_data = self.filtered_workflows_data
            self._pending_load_index = initial_count
            if not hasattr(self, '_chunk_timer'):
                self._chunk_timer = QTimer(self)
                self._chunk_timer.setSingleShot(True)
                self._chunk_timer.timeout.connect(self._load_remaining_cards)
            self._chunk_timer.start(0)

        self.scroll_check_timer.start(10)

    def _load_remaining_cards(self):
        if not hasattr(self, '_pending_workflows_data') or self._pending_load_index >= len(self._pending_workflows_data):
            return

        display_data = self._pending_workflows_data
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

    def update_grid_layout(self):
        if not self.cards or isinstance(self.cards[0], QLabel):
            return

        width = self.scroll_area.viewport().width()
        card_width = 200
        spacing = 16
        total_items = len(self.filtered_workflows_data) if getattr(self, 'filtered_workflows_data', None) else len(self.cards)
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

        self.scroll_check_timer.start(20)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.oldSize().width() <= 0 or event.oldSize().width() == event.size().width():
            return
        width = self.scroll_area.viewport().width()
        card_width = 200
        spacing = 16
        total_items = len(self.filtered_workflows_data) if getattr(self, 'filtered_workflows_data', None) else len(self.cards)
        scrollbar_w = 16 if total_items > 16 else 0
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
            if isinstance(card, WorkflowCardWidget):
                if not (getattr(card, 'image_loaded', False) or getattr(card, 'image_loading', False)):
                    card.ensure_image_loaded()

    # --- DRAG AND DROP HANDLERS ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                local_file = url.toLocalFile().lower()
                if local_file.endswith('.json') or local_file.endswith('.png'):
                    event.acceptProposedAction()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.json'):
                    self.on_add_workflow_file(file_path)
                    event.acceptProposedAction()
                    return
                elif file_path.lower().endswith('.png'):
                    self.on_add_png_workflow(file_path)
                    event.acceptProposedAction()
                    return
        super().dropEvent(event)

    def on_add_png_workflow(self, file_path):
        if not self.library_id:
            return
        from utils.png_parser import extract_comfyui_metadata_from_png
        
        meta = extract_comfyui_metadata_from_png(file_path)
        if meta.get('workflow'):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            desc = meta.get('formatted_summary', '')
            self.add_workflow_requested.emit(self.library_id, base_name, file_path, desc, file_path)
        else:
            QMessageBox.warning(
                self,
                t("warning_title"),
                t("msg_png_no_workflow")
            )

    def browse_workflow_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("workflow_dialog_title") + " JSON", "", t("dialog_workflow_filter")
        )
        if file_path:
            self.on_add_workflow_file(file_path)

    def on_add_workflow_file(self, file_path):
        if not self.library_id:
            return
        default_name = os.path.splitext(os.path.basename(file_path))[0]
        dialog = WorkflowMetadataDialog(default_name, self)
        if dialog.exec():
            meta = dialog.get_metadata()
            name = meta['name'] or default_name
            description = meta['description']
            image_path = meta['image_path']
            self.add_workflow_requested.emit(self.library_id, name, file_path, description, image_path)

    def on_delete_library_clicked(self):
        if self.library_name:
            self.delete_library_requested.emit(self.library_name)

    def tr_lib_name(self, name):
        if name == "Lora Modelleri":
            return "Lora Models" if get_lang() == "en" else "Lora Modelleri"
        elif name == "Checkpoint Modelleri":
            return "Checkpoint Models" if get_lang() == "en" else "Checkpoint Modelleri"
        elif name == "Favoriler":
            return "Favorites" if get_lang() == "en" else "Favoriler"
        return name

    def retranslate_ui(self):
        self.title_label.setText(self.tr_lib_name(self.library_name) if self.library_name else t("workflows_title"))
        self.add_btn.setText(t("view_add_workflow"))
        if hasattr(self, 'delete_lib_btn'):
            self.delete_lib_btn.setText(t("workflow_delete_library"))
        self.search_edit.setPlaceholderText(t("view_search_workflows_placeholder"))
        self.fav_toggle_btn.setText(t("view_favorites"))
        self.drop_label.setText(t("workflow_drop_zone_hint"))
        
        # update sorting combo items in current language without triggering sorting
        self.sort_combo.blockSignals(True)
        current_idx = self.sort_combo.currentIndex()
        self.sort_combo.clear()
        self.sort_combo.addItems([t("view_sort_newest"), t("view_last_edited"), t("view_sort_oldest"), t("view_sort_az"), t("view_sort_za")])
        if current_idx >= 0:
            self.sort_combo.setCurrentIndex(current_idx)
        self.sort_combo.blockSignals(False)
        
        self.populate_grid()
