# ui/detail_panel.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QScrollArea, QLayout,
                             QSizePolicy, QMessageBox, QFileDialog, QLineEdit, QComboBox)
from PySide6.QtCore import Signal, Qt, QPoint, QRect, QSize, QTimer
from PySide6.QtGui import QPixmap, QGuiApplication, QFontMetrics, QTextCursor
from utils.i18n import t, get_lang

class ZoomableTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1 if delta > 0 else -1
            self.adjust_font_size(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def adjust_font_size(self, factor):
        cursor = self.textCursor()
        anchor = cursor.anchor()
        pos = cursor.position()
        
        self.blockSignals(True)
        self.selectAll()
        
        current_size = self.fontPointSize()
        if current_size <= 0:
            current_size = self.font().pointSize()
            if current_size <= 0:
                current_size = 13
                
        new_size = max(8, min(72, current_size + factor))
        self.setFontPointSize(new_size)
        
        # Restore selection
        cursor = self.textCursor()
        try:
            cursor.setPosition(anchor)
            cursor.setPosition(pos, QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        except Exception:
            pass
        self.blockSignals(False)
        
        fmt = self.currentCharFormat()
        fmt.setFontPointSize(new_size)
        self.setCurrentCharFormat(fmt)

class FlowLayout(QLayout):
    """Custom FlowLayout to display trigger words in wrapping pill style."""
    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        while self.count():
            self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(left, top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            widget = item.widget()
            spaceX = self.spacing()
            spaceY = self.spacing()
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class TriggerPillButton(QPushButton):
    """Pill button that copies text on click and requests deletion on right-click."""
    delete_requested = Signal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("TriggerPill")
        self.setToolTip("Kopyalamak için Tıkla, Silmek için Sağ Tıkla")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.delete_requested.emit(self.text())
        else:
            super().mousePressEvent(event)


class TagPillWidget(QWidget):
    """Pill widget displaying tag name and a close ✕ button to delete it."""
    delete_requested = Signal(str)

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.setObjectName("TagPill")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        self.setStyleSheet("""
            QWidget#TagPill {
                background-color: #323639;
                border: 1px solid #444746;
                border-radius: 12px;
            }
        """)
        
        self.label = QLabel(self.text)
        self.label.setStyleSheet("color: #E3E3E3; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(self.label)
        
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(14, 14)
        self.del_btn.setCursor(Qt.PointingHandCursor)
        self.del_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #9AA0A6;
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 7px;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                background-color: #444746;
                color: #F28B82;
            }
        """)
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.text))
        layout.addWidget(self.del_btn)


class DetailPanel(QWidget):
    close_requested = Signal()
    save_model_data_requested = Signal(int, str, str) # model_id, name, notes
    image_changed = Signal(int, str) # model_id, new_image_path
    add_trigger_requested = Signal(int, str) # model_id, word
    delete_trigger_requested = Signal(int, str) # model_id, word
    add_tag_requested = Signal(int, str) # model_id, tag_name
    delete_tag_requested = Signal(int, str) # model_id, tag_name
    save_note_requested = Signal(int, str, str, str, str, int, bool) # id, title, content, image_path, display_mode, is_fav, is_auto_save
    delete_note_requested = Signal(int) # note_id
    save_workflow_data_requested = Signal(int, str, str, str) # workflow_id, name, description, notes
    delete_workflow_requested = Signal(int) # workflow_id
    workflow_image_changed = Signal(int, str) # workflow_id, new_image_path
    corkboard_pin_toggled = Signal(int, bool)
    note_color_changed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailPanelWidget")
        self.setMinimumWidth(360) # Only general minimum width limit
        
        self.mode = "MODEL" # "MODEL", "NOTE", or "WORKFLOW"
        self.model_data = None
        self.note_data = None
        self.workflow_data = None
        self.trigger_words = []
        self.all_models_list = []
        self.initial_name = ""
        self.initial_notes = ""
        self.current_image_path = ""
        
        self.initial_note_title = ""
        self.initial_note_content = ""
        self.initial_note_display_mode = ""

        self.initial_workflow_name = ""
        self.initial_workflow_description = ""
        self.initial_workflow_notes = ""
        
        # Auto-Save Debounce Timer
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.trigger_auto_save)
        
        self.auto_save_enabled = 1
        self.auto_save_interval = 1.5
        
        self.init_ui()

    def minimumSizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(360, 200)

    def sizeHint(self):
        from PySide6.QtCore import QSize
        return QSize(360, 800)

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10) # 10px margins
        self.main_layout.setSpacing(10)

        # Header: Close button
        header_layout = QHBoxLayout()
        self.header_label = QLabel("Model Detayı")
        self.header_label.setObjectName("DetailTitle")
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")

        self.close_btn.clicked.connect(self.close_requested.emit)
        header_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        self.scroll_area = scroll_area
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        
        # CRITICAL FIX: Set horizontal size policy to QSizePolicy.Ignored.
        # This forces the content widget to fit exactly inside the viewport width without overflowing.
        scroll_content.setMinimumWidth(0)
        scroll_content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(10)

        # Model Image Label (Responsive Width scaling, Fixed Height)
        self.image_label = QLabel()
        self.image_label.setFixedHeight(180)
        self.image_label.setMinimumWidth(0)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.image_label.setStyleSheet("background-color: #131314; border-radius: 8px;")
        self.image_label.setCursor(Qt.PointingHandCursor)
        self.image_label.mousePressEvent = self.on_image_clicked
        self.scroll_layout.addWidget(self.image_label)

        # --- COMPACT NOTE HEADER WIDGET (Visible only in NOTE mode) ---
        self.note_header_widget = QWidget()
        note_hdr_layout = QVBoxLayout(self.note_header_widget)
        note_hdr_layout.setContentsMargins(0, 0, 0, 0)
        note_hdr_layout.setSpacing(8)

        # Note Title row (Row 1)
        self.note_title_edit = QLineEdit()
        self.note_title_edit.setPlaceholderText("Not Başlığı...")
        self.note_title_edit.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 8px 10px;
            }
            QLineEdit:focus {
                border-color: #8AB4F8;
            }
        """)
        self.note_title_edit.textChanged.connect(self.check_changes)
        note_hdr_layout.addWidget(self.note_title_edit)

        # Thumbnail and display actions row (Row 2)
        note_row2 = QWidget()
        note_row2_layout = QHBoxLayout(note_row2)
        note_row2_layout.setContentsMargins(0, 0, 0, 0)
        note_row2_layout.setSpacing(6)

        # Small 60x36 preview image label
        self.note_thumb_preview = QLabel()
        self.note_thumb_preview.setFixedSize(60, 36)
        self.note_thumb_preview.setAlignment(Qt.AlignCenter)
        self.note_thumb_preview.setStyleSheet("background-color: #131314; border-radius: 6px; border: 1px solid #444746;")
        self.note_thumb_preview.setCursor(Qt.PointingHandCursor)
        self.note_thumb_preview.mousePressEvent = lambda e: self.on_select_note_image()
        note_row2_layout.addWidget(self.note_thumb_preview)

        self.select_note_img_btn = QPushButton("Görsel Seç")
        self.select_note_img_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 500;")
        self.select_note_img_btn.clicked.connect(self.on_select_note_image)
        note_row2_layout.addWidget(self.select_note_img_btn)

        self.remove_note_img_btn = QPushButton("Kaldır")
        self.remove_note_img_btn.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: 500; color: #F28B82;")
        self.remove_note_img_btn.clicked.connect(self.on_remove_note_image)
        note_row2_layout.addWidget(self.remove_note_img_btn)

        note_row2_layout.addStretch()

        # Display Mode selection combobox
        self.display_mode_combo = QComboBox()
        self.display_mode_combo.addItems(["Görsel + Başlık", "Sadece Metin"])
        self.display_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #2D2F31;
                border: 1px solid #444746;
                border-radius: 8px;
                color: #E3E3E3;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.display_mode_combo.currentTextChanged.connect(self.on_display_mode_changed)
        note_row2_layout.addWidget(self.display_mode_combo)
        note_hdr_layout.addWidget(note_row2)

        # Pin Button (Row 3)
        note_row3 = QWidget()
        note_row3_layout = QHBoxLayout(note_row3)
        note_row3_layout.setContentsMargins(0, 4, 0, 4)
        note_row3_layout.setSpacing(6)
        note_row3_layout.addStretch()

        self.pin_corkboard_btn = QPushButton("📌 Mantar Panoya Sabitle")
        self.pin_corkboard_btn.setCursor(Qt.PointingHandCursor)
        self.pin_corkboard_btn.clicked.connect(self.on_toggle_pin_corkboard)
        note_row3_layout.addWidget(self.pin_corkboard_btn)

        note_hdr_layout.addWidget(note_row3)

        self.scroll_layout.addWidget(self.note_header_widget)

        # Editable Model Name (Visible only in MODEL mode)
        self.name_title = QLabel("Kart Adı")
        self.name_title.setObjectName("DetailWordLabel")
        self.scroll_layout.addWidget(self.name_title)

        self.name_edit = QLineEdit()
        self.name_edit.setMinimumWidth(0) # Explicitly clear minimum width constraint
        self.name_edit.setPlaceholderText("Başlığı düzenleyin...")
        self.name_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.name_edit.textChanged.connect(self.check_changes)
        self.scroll_layout.addWidget(self.name_edit)

        # File Path Info (Word wrap checked)
        self.path_label = QLabel("Dosya Yolu:")
        self.path_label.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        self.path_label.setWordWrap(True)
        self.scroll_layout.addWidget(self.path_label)

        # Copy to Clipboard Button for Workflows (Visible only in WORKFLOW mode)
        self.copy_clip_btn = QPushButton("📋 Panoya Kopyala")
        self.copy_clip_btn.setObjectName("CopyClipBtn")

        self.copy_clip_btn.clicked.connect(self.copy_workflow_to_clipboard)
        self.scroll_layout.addWidget(self.copy_clip_btn)

        # Workflow Description (Visible only in WORKFLOW mode)
        self.workflow_desc_title = QLabel("Workflow Açıklaması")
        self.workflow_desc_title.setObjectName("DetailWordLabel")
        self.scroll_layout.addWidget(self.workflow_desc_title)

        self.workflow_desc_edit = QTextEdit()
        self.workflow_desc_edit.setFixedHeight(60)
        self.workflow_desc_edit.setPlaceholderText("Workflow açıklamasını düzenleyin...")
        self.workflow_desc_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.workflow_desc_edit.textChanged.connect(self.check_changes)
        self.scroll_layout.addWidget(self.workflow_desc_edit)

        # Notes Section
        self.notes_title = QLabel("Model Notları")
        self.notes_title.setObjectName("DetailWordLabel")
        self.scroll_layout.addWidget(self.notes_title)

        self.notes_edit = ZoomableTextEdit()
        self.notes_edit.setMinimumWidth(0) # Explicitly clear minimum width constraint
        self.notes_edit.setPlaceholderText("Not içeriğini yazın...")
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(200)
        self.notes_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.notes_edit.textChanged.connect(self.check_changes)
        self.scroll_layout.addWidget(self.notes_edit)

        # Character Counter Layout
        self.char_count_container = QWidget()
        char_layout = QHBoxLayout(self.char_count_container)
        char_layout.setContentsMargins(0, 0, 4, 0)
        char_layout.addStretch()
        self.char_count_label = QLabel("0 karakter")
        self.char_count_label.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: 500;")
        char_layout.addWidget(self.char_count_label)
        self.scroll_layout.addWidget(self.char_count_container)

        # Save & Delete Buttons Container
        self.buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        self.save_btn = QPushButton("Kart Bilgilerini Kaydet")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_clicked)
        buttons_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("Notu Sil")
        self.delete_btn.setObjectName("DeleteNoteBtn")

        self.delete_btn.clicked.connect(self.on_delete_note_clicked)
        buttons_layout.addWidget(self.delete_btn)
        
        self.scroll_layout.addWidget(self.buttons_container)

        # --- MODEL TAGS SECTION ---
        self.tags_title = QLabel("Model Etiketleri")
        self.tags_title.setObjectName("DetailWordLabel")
        self.scroll_layout.addWidget(self.tags_title)

        # Tags Flow Layout Container
        self.tags_container = QWidget()
        self.tags_layout = FlowLayout(self.tags_container, spacing=6)
        self.scroll_layout.addWidget(self.tags_container)

        # Add Tag Input
        self.new_tag_edit = QLineEdit()
        self.new_tag_edit.setMinimumWidth(0)
        self.new_tag_edit.setPlaceholderText("Yeni etiket yazıp Enter'a basın...")
        self.new_tag_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.new_tag_edit.returnPressed.connect(self.on_add_tag)
        self.scroll_layout.addWidget(self.new_tag_edit)

        # Trigger Words Section
        self.tw_title = QLabel("Tetikleyici Kelimeler")
        self.tw_title.setObjectName("DetailWordLabel")
        self.scroll_layout.addWidget(self.tw_title)

        # Add Trigger Word Container
        self.add_tw_container = QWidget()
        add_tw_layout = QHBoxLayout(self.add_tw_container)
        add_tw_layout.setContentsMargins(0, 0, 0, 0)
        self.new_tw_edit = QLineEdit()
        self.new_tw_edit.setMinimumWidth(0) # Explicitly clear minimum width constraint
        self.new_tw_edit.setPlaceholderText("Yeni kelime ekle...")
        self.new_tw_edit.setStyleSheet("background-color: #2D2F31; border: 1px solid #444746; border-radius: 8px; color: #E3E3E3; padding: 6px;")
        self.new_tw_edit.returnPressed.connect(self.on_add_trigger)
        self.add_tw_btn = QPushButton("+ Ekle")
        self.add_tw_btn.setStyleSheet("padding: 6px 12px;")
        self.add_tw_btn.clicked.connect(self.on_add_trigger)
        add_tw_layout.addWidget(self.new_tw_edit)
        add_tw_layout.addWidget(self.add_tw_btn)
        self.scroll_layout.addWidget(self.add_tw_container)

        # Pills Container for Trigger Words
        self.pills_container = QWidget()
        self.pills_layout = FlowLayout(self.pills_container, spacing=6)
        self.scroll_layout.addWidget(self.pills_container)

        # Copy All Words Button
        self.copy_all_btn = QPushButton("📋 Tüm Kelimeleri Kopyala")
        self.copy_all_btn.clicked.connect(self.on_copy_all_clicked)
        self.scroll_layout.addWidget(self.copy_all_btn)

        self.scroll_area.setWidget(scroll_content)
        self.main_layout.addWidget(self.scroll_area)

    def set_model(self, model_data, trigger_words):
        self.mode = "MODEL"
        self.model_data = model_data
        self.note_data = None
        self.trigger_words = trigger_words
        
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

        self.initial_name = model_data.get('name', '')
        self.initial_notes = model_data.get('notes', '')

        # Set labels and values
        self.header_label.setText("Model Detayı")
        self.name_title.setText("Kart Adı")
        self.name_edit.blockSignals(True)
        self.notes_edit.blockSignals(True)
        self.name_edit.setText(self.initial_name)
        self.notes_edit.setPlainText(self.initial_notes)
        self.name_edit.blockSignals(False)
        self.notes_edit.blockSignals(False)

        self.path_label.setVisible(True)
        self.path_label.setText(f"Dosya Yolu: {model_data.get('file_path', '')}")

        # Show model-specific elements
        self.save_btn.setText("Kart Bilgilerini Kaydet")
        self.save_btn.setEnabled(False)
        
        self.delete_btn.setVisible(False)
        self.char_count_container.setVisible(False)
        self.copy_clip_btn.setVisible(False)
        
        self.note_header_widget.setVisible(False)
        self.workflow_desc_title.setVisible(False)
        self.workflow_desc_edit.setVisible(False)
        
        self.image_label.setVisible(True)
        self.name_title.setVisible(True)
        self.name_edit.setVisible(True)
        self.notes_title.setVisible(True)
        self.tags_title.setVisible(True)
        self.tags_container.setVisible(True)
        self.new_tag_edit.setVisible(True)
        
        self.tw_title.setVisible(True)
        self.add_tw_container.setVisible(True)
        self.pills_container.setVisible(True)
        self.copy_all_btn.setVisible(True)

        # Set standard height for model notes
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(200)

        # Explicitly set current_image_path and trigger update_image to prevent leaking images from previous views
        self.current_image_path = model_data.get('image_path') or ""
        self.update_image()
        self.reload_tags()
        self.reload_pills()

    def set_note(self, note_data, all_models):
        self.mode = "NOTE"
        self.note_data = note_data
        self.model_data = None
        self.all_models_list = all_models
        
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

        self.initial_note_title = note_data.get('title', '')
        self.initial_note_content = note_data.get('content', '')
        self.initial_note_display_mode = note_data.get('display_mode', 'WITH_IMAGE')
        self.current_image_path = note_data.get('image_path') or ''

        # Load fresh auto-save settings from settings table
        import database
        try:
            self.auto_save_enabled = int(database.get_setting("auto_save_enabled", "1"))
            self.auto_save_interval = float(database.get_setting("auto_save_interval", "1.5"))
        except Exception:
            pass

        # Set labels and values
        self.header_label.setText("Not Düzenleyici")
        
        self.note_title_edit.blockSignals(True)
        if self.note_title_edit.text() != self.initial_note_title:
            pos = self.note_title_edit.cursorPosition()
            self.note_title_edit.setText(self.initial_note_title)
            
            def restore_title_pos(p=pos):
                if not self.note_title_edit:
                    return
                val_len = len(self.note_title_edit.text())
                if p <= val_len:
                    self.note_title_edit.setCursorPosition(p)
            QTimer.singleShot(10, restore_title_pos)
        self.note_title_edit.blockSignals(False)

        self.notes_edit.blockSignals(True)
        if self.notes_edit.toHtml().strip() != self.initial_note_content.strip():
            cursor = self.notes_edit.textCursor()
            anchor = cursor.anchor()
            pos = cursor.position()
            
            self.notes_edit.setHtml(self.initial_note_content)
            
            def restore_pos(a=anchor, p=pos):
                if not self.notes_edit:
                    return
                doc_len = self.notes_edit.document().characterCount()
                if a <= doc_len and p <= doc_len:
                    cursor = self.notes_edit.textCursor()
                    try:
                        cursor.setPosition(a)
                        cursor.setPosition(p, QTextCursor.KeepAnchor)
                        self.notes_edit.setTextCursor(cursor)
                    except Exception:
                        pass
            QTimer.singleShot(10, restore_pos)
        self.notes_edit.blockSignals(False)

        # Combo display mode
        self.display_mode_combo.blockSignals(True)
        if self.initial_note_display_mode == 'TEXT_ONLY':
            self.display_mode_combo.setCurrentText("Sadece Metin")
        else:
            self.display_mode_combo.setCurrentText("Görsel + Başlık")
        self.display_mode_combo.blockSignals(False)

        # Show note-specific elements
        self.save_btn.setText("Notu Kaydet")
        self.save_btn.setEnabled(False)
        
        self.delete_btn.setText("Notu Sil")
        self.delete_btn.setVisible(True)
        self.char_count_container.setVisible(True)
        self.update_char_count()
        
        self.note_header_widget.setVisible(True)
        self.update_pin_corkboard_btn_text()
        
        # Hide model-specific elements
        self.image_label.setVisible(False)
        self.name_title.setVisible(False)
        self.name_edit.setVisible(False)
        self.workflow_desc_title.setVisible(False)
        self.workflow_desc_edit.setVisible(False)
        self.path_label.setVisible(False)
        self.notes_title.setVisible(False)
        self.tags_title.setVisible(False)
        self.tags_container.setVisible(False)
        self.new_tag_edit.setVisible(False)
        
        self.tw_title.setVisible(False)
        self.add_tw_container.setVisible(False)
        self.pills_container.setVisible(False)
        self.copy_all_btn.setVisible(False)
        self.copy_clip_btn.setVisible(False)

        # Increase editor vertical height to maximize writing area
        self.notes_edit.setMinimumHeight(450)
        self.notes_edit.setMaximumHeight(1500)

        self.update_image()

    def set_workflow(self, workflow_data):
        self.mode = "WORKFLOW"
        self.workflow_data = workflow_data
        self.model_data = None
        self.note_data = None
        
        if hasattr(self, 'scroll_area'):
            self.scroll_area.verticalScrollBar().setValue(0)
        self.setFocus()

        self.initial_workflow_name = workflow_data.get('name', '')
        self.initial_workflow_description = workflow_data.get('description', '')
        self.initial_workflow_notes = workflow_data.get('notes', '')
        self.current_image_path = workflow_data.get('image_path') or ""

        # Set labels and values
        self.header_label.setText("Workflow Detayı")
        self.name_title.setText("Workflow Adı")
        self.notes_title.setText("Workflow Notları")
        self.save_btn.setText("Workflow Bilgilerini Kaydet")
        self.delete_btn.setText("Workflow'u Sil")

        self.name_edit.blockSignals(True)
        self.name_edit.setText(self.initial_workflow_name)
        self.name_edit.blockSignals(False)

        self.workflow_desc_edit.blockSignals(True)
        self.workflow_desc_edit.setPlainText(self.initial_workflow_description)
        self.workflow_desc_edit.blockSignals(False)

        self.notes_edit.blockSignals(True)
        self.notes_edit.setPlainText(self.initial_workflow_notes)
        self.notes_edit.blockSignals(False)

        self.path_label.setVisible(True)
        self.path_label.setText(f"Dosya Yolu: {workflow_data.get('file_path', '')}")

        # Show workflow-specific elements
        self.save_btn.setEnabled(False)
        self.delete_btn.setVisible(True)
        self.char_count_container.setVisible(False)
        self.note_header_widget.setVisible(False)
        
        self.image_label.setVisible(True)
        self.copy_clip_btn.setVisible(True)
        self.name_title.setVisible(True)
        self.name_edit.setVisible(True)
        self.workflow_desc_title.setVisible(True)
        self.workflow_desc_edit.setVisible(True)
        self.notes_title.setVisible(True)
        self.notes_edit.setVisible(True)
        self.buttons_container.setVisible(True)

        # Hide model-specific elements
        self.tags_title.setVisible(False)
        self.tags_container.setVisible(False)
        self.new_tag_edit.setVisible(False)
        self.tw_title.setVisible(False)
        self.add_tw_container.setVisible(False)
        self.pills_container.setVisible(False)
        self.copy_all_btn.setVisible(False)

        # Set standard height
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.setMaximumHeight(200)

        self.update_image()

    def check_changes(self):
        if self.mode == "MODEL":
            if not self.model_data:
                return
            current_name = self.name_edit.text().strip()
            current_notes = self.notes_edit.toPlainText().strip()
            has_changed = (current_name != self.initial_name) or (current_notes != self.initial_notes)
            self.save_btn.setEnabled(has_changed)
        elif self.mode == "WORKFLOW":
            if not self.workflow_data:
                return
            current_name = self.name_edit.text().strip()
            current_desc = self.workflow_desc_edit.toPlainText().strip()
            current_notes = self.notes_edit.toPlainText().strip()
            has_changed = (
                current_name != self.initial_workflow_name or
                current_desc != self.initial_workflow_description or
                current_notes != self.initial_workflow_notes or
                self.current_image_path != (self.workflow_data.get('image_path') or '')
            )
            self.save_btn.setEnabled(has_changed)
        else: # NOTE mode
            if not self.note_data:
                return
            self.update_char_count()
            current_title = self.note_title_edit.text().strip()
            current_content = self.notes_edit.toHtml().strip()
            current_disp = 'TEXT_ONLY' if self.display_mode_combo.currentText() == "Sadece Metin" else 'WITH_IMAGE'
            has_changed = (
                current_title != self.initial_note_title or 
                current_content != self.initial_note_content or 
                current_disp != self.initial_note_display_mode or 
                self.current_image_path != (self.note_data.get('image_path') or '')
            )
            self.save_btn.setEnabled(has_changed)

            # Auto-save triggers
            if has_changed and self.auto_save_enabled:
                self.auto_save_timer.start(int(self.auto_save_interval * 1000))
            else:
                self.auto_save_timer.stop()

    def sync_auto_save_settings(self, enabled, interval):
        self.auto_save_enabled = int(enabled)
        self.auto_save_interval = float(interval)
        if not self.auto_save_enabled:
            self.auto_save_timer.stop()

    def trigger_auto_save(self):
        if self.mode == "NOTE" and self.note_data and self.auto_save_enabled:
            title = self.note_title_edit.text().strip()
            content = self.notes_edit.toHtml().strip()
            if not title:
                return
            disp_mode = 'TEXT_ONLY' if self.display_mode_combo.currentText() == "Sadece Metin" else 'WITH_IMAGE'
            self.save_note_requested.emit(
                self.note_data['id'], 
                title, 
                content, 
                self.current_image_path, 
                disp_mode,
                self.note_data.get('is_favorite', 0),
                True
            )
            self.initial_note_title = title
            self.initial_note_content = content
            self.initial_note_display_mode = disp_mode
            self.save_btn.setEnabled(False)

    def on_swatch_color_selected(self, color_hex):
        if self.note_data:
            self.note_data['color_hex'] = color_hex
            import database
            database.update_note_color(self.note_data['id'], color_hex)
            self.note_color_changed.emit(self.note_data['id'], color_hex)
            if hasattr(self, 'save_note_requested'):
                title = self.note_title_edit.text().strip()
                content = self.notes_edit.toHtml().strip()
                disp_mode = 'TEXT_ONLY' if self.display_mode_combo.currentText() == "Sadece Metin" else 'WITH_IMAGE'
                self.save_note_requested.emit(
                    self.note_data['id'],
                    title,
                    content,
                    self.current_image_path,
                    disp_mode,
                    self.note_data.get('is_favorite', 0),
                    True
                )

    def update_pin_corkboard_btn_text(self):
        if not self.note_data or not hasattr(self, 'pin_corkboard_btn'):
            return
        is_pinned = self.note_data.get('is_corkboard', 0) == 1
        if is_pinned:
            self.pin_corkboard_btn.setText("📌 Panodan Çıkar")
            self.pin_corkboard_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4B5563;
                    color: #E5E7EB;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #6B7280;
                }
            """)
        else:
            self.pin_corkboard_btn.setText("📌 Mantar Panoya Sabitle")
            self.pin_corkboard_btn.setStyleSheet("""
                QPushButton {
                    background-color: #D97706;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 6px;
                    padding: 4px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F59E0B;
                }
            """)

    def on_toggle_pin_corkboard(self):
        if not self.note_data:
            return
        note_id = self.note_data.get('id', 0)
        current_pinned = self.note_data.get('is_corkboard', 0) == 1
        new_pinned = not current_pinned
        self.note_data['is_corkboard'] = 1 if new_pinned else 0
        import database
        database.toggle_corkboard_pin(note_id, is_pinned=new_pinned)
        self.update_pin_corkboard_btn_text()
        self.corkboard_pin_toggled.emit(note_id, new_pinned)

    def reload_pills(self):
        while self.pills_layout.count():
            item = self.pills_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for word in self.trigger_words:
            pill = TriggerPillButton(word, parent=self)
            pill.clicked.connect(lambda checked=False, w=word: self.on_word_clicked(w))
            pill.delete_requested.connect(self.on_delete_trigger)
            self.pills_layout.addWidget(pill)

        if not self.trigger_words:
            no_word = QLabel("Tetikleyici kelime bulunamadı.\nYukarıdan kelime yazıp ekleyebilirsiniz.")
            no_word.setStyleSheet("color: #9AA0A6; font-style: italic; font-size: 11px;")
            self.pills_layout.addWidget(no_word)
            self.copy_all_btn.setEnabled(False)
        else:
            self.copy_all_btn.setEnabled(True)

    def reload_tags(self):
        while self.tags_layout.count():
            item = self.tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        tags = self.model_data.get('tags', [])
        for tag in tags:
            tag_pill = TagPillWidget(tag, parent=self)
            tag_pill.delete_requested.connect(self.on_delete_tag)
            self.tags_layout.addWidget(tag_pill)

        if not tags:
            no_tags = QLabel("Etiket bulunamadı.\nAşağıdan etiket yazıp ekleyebilirsiniz.")
            no_tags.setStyleSheet("color: #9AA0A6; font-style: italic; font-size: 11px;")
            self.tags_layout.addWidget(no_tags)

    def on_add_tag(self):
        if not self.model_data:
            return
        tag = self.new_tag_edit.text().strip()
        if tag:
            tags = self.model_data.get('tags', [])
            if tag in tags:
                QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_tag_exists"), QMessageBox.Ok)
                return
            self.add_tag_requested.emit(self.model_data['id'], tag)
            self.new_tag_edit.clear()

    def on_delete_tag(self, tag):
        if not self.model_data:
            return
        reply = QMessageBox.question(
            self, t("msg_confirm_remove_tag_title"), t("msg_confirm_remove_tag_text").format(tag=tag),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_tag_requested.emit(self.model_data['id'], tag)

    def update_image(self, image_path=None):
        if image_path is not None:
            self.current_image_path = image_path
            
        path = self.current_image_path
        
        # NOTE mode: update self.note_thumb_preview
        if self.mode == "NOTE":
            if self.display_mode_combo.currentText() == "Sadece Metin":
                self.note_thumb_preview.setText("Metin")
                self.note_thumb_preview.setPixmap(QPixmap())
                self.note_thumb_preview.setStyleSheet("color: #9AA0A6; font-size: 10px; background-color: #1E1F20; border-radius: 6px; border: 1px solid #2F2F2F; qproperty-alignment: AlignCenter;")
                return

            if path and os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(60, 36, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    cropped = scaled.copy(0, 0, 60, 36)
                    self.note_thumb_preview.setPixmap(cropped)
                    self.note_thumb_preview.setStyleSheet("border-radius: 6px; background-color: transparent; border: 1px solid #444746; qproperty-alignment: AlignCenter;")
                    return
            self.note_thumb_preview.setText("+Resim")
            self.note_thumb_preview.setPixmap(QPixmap())
            self.note_thumb_preview.setStyleSheet("color: #8AB4F8; font-size: 10px; font-weight: bold; background-color: #131314; border-radius: 6px; border: 1px dashed #444746; qproperty-alignment: AlignCenter;")
            return
            
        # MODEL/WORKFLOW mode: update self.image_label
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                w = max(200, self.image_label.width())
                h = 180
                scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                return
        
        if self.mode == "WORKFLOW":
            self.image_label.setText("🧩\nÖnizleme Görseli Seçmek İçin Tıklayın")
        else:
            self.image_label.setText("Görsel Yüklemek İçin Tıklayın")
        self.image_label.setPixmap(QPixmap())
        self.image_label.setStyleSheet("color: #8AB4F8; font-size: 12px; background-color: #131314; border-radius: 8px; border: 2px dashed #444746; qproperty-alignment: AlignCenter;")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image_path:
            self.update_image()

    def on_image_clicked(self, event):
        if not self.model_data and not self.note_data and not self.workflow_data:
            return
        
        if self.mode == "NOTE":
            self.on_select_note_image()
        elif self.mode == "MODEL" and self.model_data:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Model Resmi Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.webp)"
            )
            if file_path:
                self.image_changed.emit(self.model_data['id'], file_path)
        elif self.mode == "WORKFLOW" and self.workflow_data:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Workflow Önizleme Resmi Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.webp)"
            )
            if file_path:
                self.current_image_path = file_path
                self.update_image()
                self.workflow_image_changed.emit(self.workflow_data['id'], file_path)
                self.check_changes()

    def on_word_clicked(self, word):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(word)
        QMessageBox.information(self, t("msg_copied_title"), t("msg_trigger_copied_text").format(word=word), QMessageBox.Ok)

    def on_copy_all_clicked(self):
        if self.trigger_words:
            all_words = ", ".join(self.trigger_words)
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(all_words)
            QMessageBox.information(self, t("msg_copied_title"), t("msg_all_triggers_copied_text"), QMessageBox.Ok)

    def copy_workflow_to_clipboard(self):
        if not self.workflow_data:
            return
        
        # 1. Try to get workflow_json directly from data dictionary (database column)
        workflow_json = self.workflow_data.get('workflow_json')
        if workflow_json:
            try:
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(workflow_json)
                self.copy_clip_btn.setText(t("msg_copied_title") + "! ✓")
                self.copy_clip_btn.setEnabled(False)
                QTimer.singleShot(1500, lambda: [self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard")), self.copy_clip_btn.setEnabled(True)] if hasattr(self, 'copy_clip_btn') and self.copy_clip_btn else None)
                return
            except Exception as e:
                QMessageBox.critical(self, t("msg_copy_error_title"), t("msg_file_read_error").format(error=e))
                return

        # 2. Fallback to reading file_path
        file_path = self.workflow_data.get('file_path', '')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_file_not_found").format(path=file_path))
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(content)
            self.copy_clip_btn.setText(t("msg_copied_title") + "! ✓")
            self.copy_clip_btn.setEnabled(False)
            QTimer.singleShot(1500, lambda: [self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard")), self.copy_clip_btn.setEnabled(True)] if hasattr(self, 'copy_clip_btn') and self.copy_clip_btn else None)
        except Exception as e:
            QMessageBox.critical(self, t("msg_copy_error_title"), t("msg_file_read_error").format(error=e))

    def on_save_clicked(self):
        if self.mode == "MODEL":
            if self.model_data:
                name = self.name_edit.text().strip()
                notes = self.notes_edit.toPlainText().strip()
                if not name:
                    QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_model_name_empty"), QMessageBox.Ok)
                    return
                self.save_model_data_requested.emit(self.model_data['id'], name, notes)
                self.initial_name = name
                self.initial_notes = notes
                self.save_btn.setEnabled(False)
        elif self.mode == "WORKFLOW":
            if self.workflow_data:
                name = self.name_edit.text().strip()
                desc = self.workflow_desc_edit.toPlainText().strip()
                notes = self.notes_edit.toPlainText().strip()
                if not name:
                    QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_workflow_name_empty"), QMessageBox.Ok)
                    return
                self.save_workflow_data_requested.emit(self.workflow_data['id'], name, desc, notes)
                self.initial_workflow_name = name
                self.initial_workflow_description = desc
                self.initial_workflow_notes = notes
                self.save_btn.setEnabled(False)
        else: # NOTE mode
            if self.note_data:
                title = self.note_title_edit.text().strip()
                content = self.notes_edit.toHtml().strip()
                if not title:
                    QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_empty_title_error"), QMessageBox.Ok)
                    return
                disp_mode = 'TEXT_ONLY' if self.display_mode_combo.currentText() == "Sadece Metin" else 'WITH_IMAGE'
                self.save_note_requested.emit(
                    self.note_data['id'], 
                    title, 
                    content, 
                    self.current_image_path, 
                    disp_mode,
                    self.note_data.get('is_favorite', 0),
                    False
                )
                self.initial_note_title = title
                self.initial_note_content = content
                self.initial_note_display_mode = disp_mode
                self.save_btn.setEnabled(False)

    def on_add_trigger(self):
        if not self.model_data:
            return
        word = self.new_tw_edit.text().strip()
        if word:
            if word in self.trigger_words:
                QMessageBox.warning(self, t("msg_copy_error_title"), t("msg_trigger_exists"), QMessageBox.Ok)
                return
            self.add_trigger_requested.emit(self.model_data['id'], word)
            self.new_tw_edit.clear()

    def on_delete_trigger(self, word):
        if not self.model_data:
            return
        reply = QMessageBox.question(
            self, t("msg_confirm_delete_trigger_title"), t("msg_confirm_delete_trigger_text").format(word=word),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.delete_trigger_requested.emit(self.model_data['id'], word)

    def on_select_note_image(self):
        if not self.note_data:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, t("msg_select_note_image"), "", "Resim Dosyaları (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.current_image_path = file_path
            self.update_image()
            self.check_changes()

    def on_remove_note_image(self):
        if not self.note_data:
            return
        self.current_image_path = ""
        self.update_image()
        self.check_changes()

    def on_delete_note_clicked(self):
        if self.mode == "NOTE" and self.note_data:
            reply = QMessageBox.question(
                self, t("detail_delete_note"), t("detail_delete_note_confirm"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.delete_note_requested.emit(self.note_data['id'])
        elif self.mode == "WORKFLOW" and self.workflow_data:
            reply = QMessageBox.question(
                self, t("detail_delete_workflow"), t("detail_delete_workflow_confirm"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.delete_workflow_requested.emit(self.workflow_data['id'])

    def update_char_count(self):
        text_len = len(self.notes_edit.toPlainText())
        self.char_count_label.setText(f"{text_len} {t('detail_char_count')}")

    def on_display_mode_changed(self):
        self.update_image()
        self.check_changes()

    def retranslate_ui(self):
        self.name_title.setText(t("detail_card_title"))
        self.name_edit.setPlaceholderText(t("detail_card_title_placeholder"))
        self.path_label.setText(t("detail_card_path"))
        self.copy_clip_btn.setText("📋 " + t("detail_copy_clipboard"))
        self.workflow_desc_title.setText(t("detail_workflow_desc"))
        self.workflow_desc_edit.setPlaceholderText(t("detail_workflow_desc_placeholder"))
        
        if self.mode == "NOTE":
            self.notes_title.setText(t("view_all_notes"))
            self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_note"))
        else:
            self.notes_title.setText(t("detail_notes_title"))
            self.notes_edit.setPlaceholderText(t("detail_notes_placeholder_model"))
            
        self.save_btn.setText(t("detail_save_changes") if self.mode != "NOTE" else t("save_note"))
        self.delete_btn.setText(t("detail_delete_note"))
        self.tags_title.setText(t("detail_tags_title"))
        self.new_tag_edit.setPlaceholderText(t("detail_new_tag_placeholder"))
        self.tw_title.setText(t("detail_triggers_title"))
        self.new_tw_edit.setPlaceholderText(t("detail_new_trigger_placeholder"))
        self.add_tw_btn.setText("+ " + (t("new_note").split()[-1] if get_lang() == "tr" else "Add"))
        
        self.update_char_count()
