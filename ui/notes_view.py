# ui/notes_view.py
import os
import re
import html
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit, QComboBox, QMessageBox, QMenu)
from PySide6.QtCore import Signal, Qt, QSize, QTimer, QThreadPool, Slot, QPoint, QRect
from PySide6.QtGui import QPixmap, QFontMetrics, QGuiApplication, QImage, QKeyEvent, QCursor
from utils.i18n import t
from utils.icon_manager import get_icon
from ui.library_view import get_rounded_pixmap, THUMBNAIL_CACHE, cache_thumbnail, ImageLoadWorker
from database import resolve_image_path

_STYLE_RE = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
_HEAD_RE = re.compile(r'<head[^>]*>.*?</head>', re.DOTALL | re.IGNORECASE)
_SCRIPT_RE = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r'</?(?:p|div|br|h[1-6]|li|blockquote)[^>]*>', re.IGNORECASE)
_ANY_TAG_RE = re.compile(r'<[^>]+>')

def html_to_plain(html_str: str) -> str:
    """Ultra-fast regex and entity decoder to extract plain text without QTextDocument allocation."""
    if not html_str:
        return ""
    # Strip style, head and script blocks along with their inner css/scripts
    text = _STYLE_RE.sub('', html_str)
    text = _HEAD_RE.sub('', text)
    text = _SCRIPT_RE.sub('', text)
    # Block level tags become spaces / line breaks
    text = _TAG_RE.sub(' ', text)
    # Inline formatting tags like <b>, <i>, <span> are stripped without adding whitespace
    text = _ANY_TAG_RE.sub('', text)
    return html.unescape(' '.join(text.split()))

class NoteCardWidget(QFrame):
    clicked = Signal(dict)
    favorite_toggled = Signal(int, bool)
    restore_requested = Signal(int)
    perm_delete_requested = Signal(int)
    hide_requested = Signal(dict)
    unhide_requested = Signal(dict)
    corkboard_pin_toggled = Signal(int, bool)
    color_changed = Signal(int, str)
    selection_toggled = Signal(dict, bool)

    def __init__(self, note_data, is_trash=False, parent=None):
        super().__init__(parent)
        self.note_data = note_data
        self.is_trash = is_trash
        self.setObjectName("NoteCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(240, 260)
        self.setCursor(Qt.PointingHandCursor)
        
        self.is_fav = bool(self.note_data.get('is_favorite', 0))
        self.is_pinned = bool(self.note_data.get('is_pinned_corkboard', 0))
        self.is_selected = False
        self.display_mode = self.note_data.get('display_mode', 'WITH_IMAGE')
        self.image_path = resolve_image_path(self.note_data.get('image_path') or '')
        self.image_loaded = False
        self.image_loading = False
        
        self.init_ui()
        self.update_card_style()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Image label / container
        self.image_label = QLabel(self)
        self.image_label.setObjectName("NoteCardImageLabel")
        self.image_label.setFixedSize(216, 130)
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # Absolute overlays layout container
        self.top_overlay_container = QWidget(self)
        self.top_overlay_container.setGeometry(12, 12, 216, 28)
        self.top_overlay_container.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.top_overlay_container.setStyleSheet("background: transparent;")
        
        top_overlay_layout = QHBoxLayout(self.top_overlay_container)
        top_overlay_layout.setContentsMargins(0, 0, 0, 0)
        top_overlay_layout.setSpacing(4)
        
        if self.is_trash:
            # Restore button
            self.restore_btn = QPushButton("🔄", self)
            self.restore_btn.setFixedSize(26, 26)
            self.restore_btn.setCursor(Qt.PointingHandCursor)
            self.restore_btn.setToolTip(t("menu_restore"))
            self.restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 47, 49, 0.7);
                    border: 1px solid rgba(68, 71, 70, 0.7);
                    border-radius: 13px;
                    color: #E3E3E3;
                    font-size: 11px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(0, 74, 119, 0.9);
                    border-color: #8AB4F8;
                }
            """)
            self.restore_btn.clicked.connect(self.on_restore_clicked)
            top_overlay_layout.addWidget(self.restore_btn)
            
            top_overlay_layout.addStretch()
            
            # Permanently delete button
            self.perm_delete_btn = QPushButton("❌", self)
            self.perm_delete_btn.setFixedSize(26, 26)
            self.perm_delete_btn.setCursor(Qt.PointingHandCursor)
            self.perm_delete_btn.setToolTip(t("menu_delete_forever"))
            self.perm_delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 47, 49, 0.7);
                    border: 1px solid rgba(68, 71, 70, 0.7);
                    border-radius: 13px;
                    color: #F28B82;
                    font-size: 11px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(168, 32, 26, 0.9);
                    border-color: #F28B82;
                }
            """)
            self.perm_delete_btn.clicked.connect(self.on_perm_delete_clicked)
            top_overlay_layout.addWidget(self.perm_delete_btn)
        else:
            # Star button
            self.fav_btn = QPushButton("☆", self)
            self.fav_btn.setFixedSize(26, 26)
            self.fav_btn.setCursor(Qt.PointingHandCursor)
            self.fav_btn.clicked.connect(self.on_fav_clicked)
            self.update_fav_btn_style()
            top_overlay_layout.addWidget(self.fav_btn)
            
            top_overlay_layout.addStretch()

            # Copy button
            self.copy_btn = QPushButton("📋", self)
            self.copy_btn.setFixedSize(26, 26)
            self.copy_btn.setCursor(Qt.PointingHandCursor)
            self.copy_btn.setToolTip(t("copy_text"))
            self.copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(45, 47, 49, 0.7);
                    border: 1px solid rgba(68, 71, 70, 0.7);
                    border-radius: 13px;
                    color: #C4C7C5;
                    font-size: 11px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(60, 64, 67, 0.9);
                    border-color: #8AB4F8;
                    color: #E3E3E3;
                }
            """)
            self.copy_btn.clicked.connect(self.on_copy_clicked)
            top_overlay_layout.addWidget(self.copy_btn)

        # Add image, title and content labels to layout
        layout.addWidget(self.image_label)
        
        # Title Label
        self.title_label = QLabel(self)
        self.title_label.setObjectName("NoteCardTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Content Label
        self.content_label = QLabel(self)
        self.content_label.setObjectName("NoteCardContent")
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.content_label)

        # Date Label
        self.date_label = QLabel(self)
        self.date_label.setObjectName("NoteCardDate")
        self.date_label.setStyleSheet("color: #71717A; font-size: 10px; font-weight: 500;")
        self.date_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.date_label)

        # Render layout according to display mode and path
        self.update_layout()

        # Crucial Z-order fix: Raise the overlay container so it is clickable
        self.top_overlay_container.raise_()

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_card_style()

    def toggle_selection(self):
        self.set_selected(not self.is_selected)
        self.selection_toggled.emit(self.note_data, self.is_selected)

    def update_card_style(self):
        if self.is_selected:
            self.setStyleSheet("""
                QFrame#NoteCard {
                    background-color: #263238;
                    border: 2px solid #8AB4F8;
                    border-radius: 12px;
                }
            """)
        elif self.note_data.get('color_hex') and self.note_data.get('color_hex') != "default":
            color_hex = self.note_data['color_hex']
            from ui.welcome_screen import get_palette_colors
            bg, border, text_col = get_palette_colors(color_hex)
            if bg:
                self.setStyleSheet(f"""
                    QFrame#NoteCard {{
                        background-color: {bg};
                        border: 1px solid {border};
                        border-radius: 12px;
                    }}
                    QLabel {{
                        color: {text_col};
                    }}
                """)
            else:
                self.setStyleSheet("")
        else:
            self.setStyleSheet("") # default QSS from theme

    def open_color_menu(self):
        from ui.welcome_screen import PASTEL_PALETTE
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E1F20;
                color: #E3E3E3;
                border: 1px solid #444746;
                padding: 4px;
                border-radius: 8px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2D2F31;
                color: #8AB4F8;
            }
        """)
        for bg, border, text_col, name in PASTEL_PALETTE:
            action = menu.addAction(f"{name}")
            action.triggered.connect(lambda checked=False, c=bg: self.on_select_color(c))
        menu.exec(QCursor.pos())

    def on_select_color(self, color_hex):
        self.note_data['color_hex'] = color_hex
        self.update_card_style()
        self.color_changed.emit(self.note_data.get('id', 0), color_hex)

    def update_pin_btn_style(self):
        if not hasattr(self, 'pin_btn'):
            return
        if self.is_pinned:
            bg = "rgba(255, 152, 0, 0.3)"
            border = "rgba(255, 152, 0, 0.8)"
            color = "#FFB74D"
        else:
            bg = "rgba(45, 47, 49, 0.7)"
            border = "rgba(68, 71, 70, 0.7)"
            color = "#888888"
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 13px;
                color: {color};
                font-size: 11px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 152, 0, 0.5);
                border-color: #FFB74D;
                color: #FFFFFF;
            }}
        """)

    def on_pin_clicked(self):
        self.is_pinned = not self.is_pinned
        self.note_data['is_pinned_corkboard'] = 1 if self.is_pinned else 0
        self.update_pin_btn_style()
        self.corkboard_pin_toggled.emit(self.note_data.get('id', 0), self.is_pinned)

    def update_layout(self):
        self.image_path = resolve_image_path(self.image_path or self.note_data.get('image_path') or '')
        show_img = (self.display_mode == 'WITH_IMAGE') and self.image_path and os.path.exists(self.image_path)
        layout = self.layout()
        if not layout:
            return
            
        if show_img:
            self.image_label.setVisible(True)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(8)
            
            if self.image_path in THUMBNAIL_CACHE:
                self.image_label.setPixmap(THUMBNAIL_CACHE[self.image_path])
                self.image_label.setText("")
                self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
                self.image_loaded = True
            else:
                self.image_label.setText("")
                self.image_label.setPixmap(QPixmap())
                self.image_label.setStyleSheet("background-color: #242527; border-radius: 8px;")
                self.image_loaded = False
                self.ensure_image_loaded()
                
            self.content_label.setFixedHeight(50)
            self.content_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        else:
            self.image_label.setVisible(False)
            layout.setContentsMargins(12, 44, 12, 12)
            layout.setSpacing(12)
            self.content_label.setFixedHeight(120)
            self.content_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.image_loaded = True
            
        self.update_texts()

    def ensure_image_loaded(self):
        if getattr(self, 'image_loaded', False) or getattr(self, 'image_loading', False):
            return
        self.image_path = resolve_image_path(self.image_path or self.note_data.get('image_path') or '')
        show_img = (self.display_mode == 'WITH_IMAGE') and self.image_path and os.path.exists(self.image_path)
        if not show_img:
            self.image_loaded = True
            return
        if self.image_path in THUMBNAIL_CACHE:
            self.image_label.setPixmap(THUMBNAIL_CACHE[self.image_path])
            self.image_label.setText("")
            self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
            self.image_loaded = True
            return
        self.image_loading = True
        worker = ImageLoadWorker(self.image_path, target_w=216, target_h=130)
        worker.signals.image_loaded.connect(self._on_async_image_loaded)
        QThreadPool.globalInstance().start(worker)

    @Slot(str, object, int, int)
    def _on_async_image_loaded(self, path, qimage, w, h):
        self.image_loading = False
        if getattr(self, 'image_path', '') != path:
            return
        if qimage and not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage)
            rounded = get_rounded_pixmap(pixmap, radius=11)
            cache_thumbnail(path, rounded)
            self.image_label.setPixmap(rounded)
            self.image_label.setText("")
            self.image_label.setStyleSheet("background-color: transparent; border-radius: 8px;")
            self.image_loaded = True
        else:
            self.show_no_image_style()
            self.image_loaded = True

    def prepare_for_deletion(self):
        """Immediately clear QPixmap references to release RAM memory before Qt deletes the widget."""
        self.image_label.setPixmap(QPixmap())
        self.image_loaded = False
        self.image_loading = False

    def show_no_image_style(self):
        self.image_label.setText(t("msg_image_load_failed"))
        self.image_label.setStyleSheet("color: #5F6368; font-size: 12px; background-color: #2D2F31; border-radius: 8px;")

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
                border-radius: 13px;
                color: {color};
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 215, 0, 0.4);
                border-color: #FFD700;
                color: #FFD700;
            }}
        """)

    def update_texts(self):
        metrics = QFontMetrics(self.font())
        title_text = self.note_data.get('title', '')
        if self.note_data.get('is_hidden', 0) == 1:
            title_text = "🔒 " + title_text
        elided_title = metrics.elidedText(title_text, Qt.ElideRight, 210)
        self.title_label.setText(elided_title)

        html_content = self.note_data.get('content', '')
        plain_text = html_to_plain(html_content)
        
        show_img = (self.display_mode == 'WITH_IMAGE') and self.image_path and os.path.exists(self.image_path)
        if show_img:
            display_text = plain_text
            if len(display_text) > 80:
                display_text = display_text[:80] + "..."
            self.content_label.setText(display_text)
        else:
            display_text = plain_text
            if len(display_text) > 250:
                display_text = display_text[:250] + "..."
            self.content_label.setText(display_text)

        if hasattr(self, 'date_label'):
            dt_raw = self.note_data.get('updated_at') or self.note_data.get('created_at') or ''
            date_display = ""
            if dt_raw:
                try:
                    s = str(dt_raw).replace('T', ' ')
                    parts = s.split(' ')
                    d_parts = parts[0].split('-')
                    if len(d_parts) == 3:
                        date_display = f"{d_parts[2]}.{d_parts[1]}.{d_parts[0]}"
                except Exception:
                    date_display = str(dt_raw)[:10]
            self.date_label.setText(date_display)

    def contextMenuEvent(self, event):
        if self.is_trash:
            super().contextMenuEvent(event)
            return
            
        main_win = self.window()
        if not (main_win and getattr(main_win, 'incognito_active', False)):
            event.ignore()
            return

        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        
        is_hidden = self.note_data.get('is_hidden', 0) == 1
        
        if not is_hidden:
            hide_action = menu.addAction(t("menu_hide"))
            action = menu.exec(event.globalPos())
            if action == hide_action:
                self.hide_requested.emit(self.note_data)
        else:
            unhide_action = menu.addAction(t("menu_unhide"))
            action = menu.exec(event.globalPos())
            if action == unhide_action:
                self.unhide_requested.emit(self.note_data)

    def on_fav_clicked(self):
        self.is_fav = not self.is_fav
        self.note_data['is_favorite'] = 1 if self.is_fav else 0
        self.update_fav_btn_style()
        self.favorite_toggled.emit(self.note_data.get('id', 0), self.is_fav)

    def on_copy_clicked(self):
        html_content = self.note_data.get('content', '')
        doc = QTextDocument()
        doc.setHtml(html_content)
        plain_text = doc.toPlainText().strip()
        
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(plain_text)
        
        win = self.window()
        if win and hasattr(win, 'show_toast'):
            win.show_toast(t("toast_copied"), "success")

    def on_restore_clicked(self):
        self.restore_requested.emit(self.note_data.get('id', 0))

    def on_perm_delete_clicked(self):
        self.perm_delete_requested.emit(self.note_data.get('id', 0))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if hasattr(self, 'top_overlay_container') and self.top_overlay_container:
            self.top_overlay_container.setGeometry(12, 12, max(100, w - 24), 28)

    def contextMenuEvent(self, event):
        if self.is_trash:
            super().contextMenuEvent(event)
            return

        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QCursor
        menu = QMenu(self)

        main_win = self.window()
        is_incognito = main_win and getattr(main_win, 'incognito_active', False)

        if is_incognito:
            is_hidden = self.note_data.get('is_hidden', 0) == 1
            if not is_hidden:
                hide_action = menu.addAction(t("menu_hide"))
                hide_action.triggered.connect(lambda: self.hide_requested.emit(self.note_data))
            else:
                unhide_action = menu.addAction(t("menu_unhide"))
                unhide_action.triggered.connect(lambda: self.unhide_requested.emit(self.note_data))
            menu.addSeparator()

        color_menu = menu.addMenu(t("menu_select_color"))
        from ui.welcome_screen import get_pastel_palette
        for bg, border, text_col, name in get_pastel_palette():
            act = color_menu.addAction(name)
            act.triggered.connect(lambda checked=False, c=bg: self.on_select_color(c))

        menu.exec(QCursor.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if QGuiApplication.keyboardModifiers() & Qt.ControlModifier:
                self.toggle_selection()
                return
            elif not self.is_trash:
                self.clicked.emit(self.note_data)
        super().mouseReleaseEvent(event)


class NotesView(QWidget):
    note_clicked = Signal(dict)
    note_favorite_toggled = Signal(int, bool)
    new_note_requested = Signal()
    note_restore_requested = Signal(int)
    note_perm_delete_requested = Signal(int)
    empty_trash_requested = Signal()
    note_hide_requested = Signal(dict)
    note_unhide_requested = Signal(dict)
    bulk_delete_requested = Signal(list, bool) # ids, is_trash
    bulk_restore_requested = Signal(list) # ids
    corkboard_pin_toggled = Signal(int, bool)
    note_color_changed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotesViewWidget")
        self.notes_data = []
        self.filtered_notes_data = []
        self.cards = []
        self.selected_note_ids = set()
        self.is_trash = False
        self.current_columns = -1
        

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

        header_layout = QHBoxLayout()
        self.title_label = QLabel(t("trash") if self.is_trash else t("notes"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        # Search field
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("view_search_notes_placeholder"))
        self.search_edit.setMinimumWidth(120)
        self.search_edit.setMaximumWidth(300)
        self.search_edit.textChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.search_edit)

        # Favorites Filter Toggle
        self.fav_toggle_btn = QPushButton(f"  {t('view_favorites')}")
        self.fav_toggle_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.fav_toggle_btn.setIconSize(QSize(16, 16))
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

        self.empty_trash_btn = QPushButton(f"  {t('trash_empty_title')}")
        self.empty_trash_btn.setObjectName("EmptyTrashBtn")
        self.empty_trash_btn.setIcon(get_icon("trash", "#FFFFFF", 16))
        self.empty_trash_btn.setIconSize(QSize(16, 16))
        self.empty_trash_btn.setFixedHeight(36)
        self.empty_trash_btn.setStyleSheet("QPushButton { border-radius: 18px !important; padding: 6px 14px !important; font-weight: bold !important; }")
        self.empty_trash_btn.clicked.connect(self.on_empty_trash_clicked)
        self.empty_trash_btn.setVisible(False)
        header_layout.addWidget(self.empty_trash_btn)

        self.new_note_btn = QPushButton(f"  {t('new_note')}")
        self.new_note_btn.setObjectName("HeaderAddBtn")
        self.new_note_btn.setIcon(get_icon("add", "#FFFFFF", 16))
        self.new_note_btn.setIconSize(QSize(16, 16))
        self.new_note_btn.setFixedHeight(36)
        self.new_note_btn.setStyleSheet("QPushButton { border-radius: 18px !important; padding: 6px 14px !important; font-weight: bold !important; }")
        self.new_note_btn.clicked.connect(self.new_note_requested.emit)
        header_layout.addWidget(self.new_note_btn)

        self.main_layout.addLayout(header_layout)

        # --- MULTI-SELECTION BULK ACTION BAR ---
        self.bulk_bar = QFrame(self)
        self.bulk_bar.setObjectName("BulkActionBar")
        self.bulk_bar.setStyleSheet("""
            QFrame#BulkActionBar {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 4px 12px;
            }
        """)
        bulk_layout = QHBoxLayout(self.bulk_bar)
        bulk_layout.setContentsMargins(8, 6, 8, 6)
        bulk_layout.setSpacing(12)

        self.bulk_count_label = QLabel(t("bulk_selected_count").format(count=0), self.bulk_bar)
        self.bulk_count_label.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 14px;")
        bulk_layout.addWidget(self.bulk_count_label)

        bulk_layout.addStretch()

        self.select_all_btn = QPushButton(t("bulk_select_all"), self.bulk_bar)
        self.select_all_btn.setStyleSheet("background-color: #334155; color: #F1F5F9; border-radius: 6px; padding: 5px 10px;")
        self.select_all_btn.clicked.connect(self.select_all_notes)
        bulk_layout.addWidget(self.select_all_btn)

        self.clear_select_btn = QPushButton(t("bulk_clear_selection"), self.bulk_bar)
        self.clear_select_btn.setStyleSheet("background-color: #334155; color: #94A3B8; border-radius: 6px; padding: 5px 10px;")
        self.clear_select_btn.clicked.connect(self.clear_selection)
        bulk_layout.addWidget(self.clear_select_btn)

        self.bulk_pin_btn = QPushButton(t("bulk_pin_corkboard"), self.bulk_bar)
        self.bulk_pin_btn.setStyleSheet("background-color: #D97706; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        self.bulk_pin_btn.clicked.connect(self.on_bulk_pin_clicked)
        bulk_layout.addWidget(self.bulk_pin_btn)

        self.bulk_restore_btn = QPushButton(t("bulk_restore"), self.bulk_bar)
        self.bulk_restore_btn.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        self.bulk_restore_btn.clicked.connect(self.on_bulk_restore_clicked)
        self.bulk_restore_btn.setVisible(False)
        bulk_layout.addWidget(self.bulk_restore_btn)

        self.bulk_delete_btn = QPushButton(t("bulk_delete"), self.bulk_bar)
        self.bulk_delete_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        self.bulk_delete_btn.clicked.connect(self.on_bulk_delete_clicked)
        bulk_layout.addWidget(self.bulk_delete_btn)

        self.bulk_bar.setVisible(False)
        self.main_layout.addWidget(self.bulk_bar)

        # Scroll Area for Cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("GridScrollArea")
        self.scroll_area.setWidgetResizable(True)
        
        self.grid_container = QWidget()
        self.grid_container.setObjectName("NotesGridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll_area.setWidget(self.grid_container)
        self.scroll_area.verticalScrollBar().valueChanged.connect(lambda: self.scroll_check_timer.start(40))
        self.main_layout.addWidget(self.scroll_area)

    def set_notes(self, notes, is_trash=False):
        existing_card_ids = [c.note_data['id'] for c in self.cards if isinstance(c, NoteCardWidget)]
        new_note_ids = [n['id'] for n in notes] if notes else []
        same_trash = (self.is_trash == is_trash)
        same_notes = (existing_card_ids == new_note_ids and len(new_note_ids) > 0)

        self.is_trash = is_trash
        self.notes_data = notes or []
        self.filtered_notes_data = self.notes_data
        self.clear_selection()
        
        self.empty_trash_btn.setVisible(is_trash)
        self.new_note_btn.setVisible(not is_trash)
        self.fav_toggle_btn.setVisible(not is_trash)
        self.bulk_pin_btn.setVisible(not is_trash)
        self.bulk_restore_btn.setVisible(is_trash)

        if same_trash and same_notes:
            self.title_label.setText(t("trash_title") if self.is_trash else t("view_all_notes"))
            self.update_grid_layout()
            return

        # Reset local filters silently
        self.fav_toggle_btn.blockSignals(True)
        self.fav_toggle_btn.setChecked(False)
        self.fav_toggle_btn.blockSignals(False)
        
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        
        self.retranslate_ui()

    def _create_card(self, note):
        card = NoteCardWidget(note, is_trash=self.is_trash, parent=self.grid_container)
        card.selection_toggled.connect(self.on_card_selection_toggled)
        card.corkboard_pin_toggled.connect(self.corkboard_pin_toggled.emit)
        card.color_changed.connect(self.note_color_changed.emit)
        
        if card.note_data.get('id') in self.selected_note_ids:
            card.set_selected(True)
            
        if self.is_trash:
            card.restore_requested.connect(self.note_restore_requested.emit)
            card.perm_delete_requested.connect(self.note_perm_delete_requested.emit)
        else:
            card.clicked.connect(self.note_clicked.emit)
            card.favorite_toggled.connect(self.note_favorite_toggled.emit)
            card.hide_requested.connect(self.note_hide_requested.emit)
            card.unhide_requested.connect(self.note_unhide_requested.emit)
        return card

    def on_card_selection_toggled(self, note_data, is_selected):
        note_id = note_data.get('id')
        if not note_id:
            return
        if is_selected:
            self.selected_note_ids.add(note_id)
        else:
            self.selected_note_ids.discard(note_id)
        self.update_bulk_bar()

    def update_bulk_bar(self):
        count = len(self.selected_note_ids)
        if count > 0:
            self.bulk_count_label.setText(t("bulk_selected_count").format(count=count))
            self.bulk_bar.setVisible(True)
        else:
            self.bulk_bar.setVisible(False)

    def select_all_notes(self):
        for card in self.cards:
            if isinstance(card, NoteCardWidget):
                card.set_selected(True)
                note_id = card.note_data.get('id')
                if note_id:
                    self.selected_note_ids.add(note_id)
        self.update_bulk_bar()

    def clear_selection(self):
        self.selected_note_ids.clear()
        for card in self.cards:
            if isinstance(card, NoteCardWidget):
                card.set_selected(False)
        self.update_bulk_bar()

    def on_bulk_delete_clicked(self):
        if not self.selected_note_ids:
            return
        count = len(self.selected_note_ids)
        msg_text = (t("bulk_delete_confirm_perm") if self.is_trash else t("bulk_delete_confirm_trash")).format(count=count)
        reply = QMessageBox.question(
            self, t("bulk_delete_title"), msg_text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ids = list(self.selected_note_ids)
            self.bulk_delete_requested.emit(ids, self.is_trash)
            self.clear_selection()

    def on_bulk_restore_clicked(self):
        if not self.selected_note_ids:
            return
        ids = list(self.selected_note_ids)
        self.bulk_restore_requested.emit(ids)
        self.clear_selection()

    def on_bulk_pin_clicked(self):
        if not self.selected_note_ids:
            return
        for note_id in list(self.selected_note_ids):
            self.corkboard_pin_toggled.emit(note_id, True)
        self.clear_selection()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Delete and self.selected_note_ids:
            self.on_bulk_delete_clicked()
        elif event.key() == Qt.Key_Escape:
            self.clear_selection()
        else:
            super().keyPressEvent(event)

    def apply_filters_and_sorting(self):
        query = self.search_edit.text().strip().lower()
        show_only_favs = self.fav_toggle_btn.isChecked()
        sort_idx = self.sort_combo.currentIndex()

        filtered = []
        for n in self.notes_data:
            if show_only_favs and not n.get('is_favorite', 0):
                continue
            if query:
                title_match = query in n.get('title', '').lower()
                plain_content = html_to_plain(n.get('content', '')).lower()
                content_match = query in plain_content
                if not (title_match or content_match):
                    continue
            filtered.append(n)

        if sort_idx == 1: # Son Düzenlenen / Last Edited
            filtered.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        elif sort_idx == 3: # A-Z
            filtered.sort(key=lambda x: x.get('title', '').lower())
        elif sort_idx == 4: # Z-A
            filtered.sort(key=lambda x: x.get('title', '').lower(), reverse=True)
        elif sort_idx == 2: # En Eski / Oldest
            filtered.sort(key=lambda x: x.get('created_at', ''))
        else: # En Yeni / Newest
            filtered.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        self.filtered_notes_data = filtered
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

            if not self.filtered_notes_data:
                empty_label = QLabel(t("view_empty_notes"))
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

            card_width = 240
            spacing = 16
            scrollbar_w = 16 if len(self.filtered_notes_data) > 12 else 0
            avail_w = max(100, width - scrollbar_w)
            columns = max(1, (avail_w + spacing) // (card_width + spacing))
            self.current_columns = columns

            total_rows = (len(self.filtered_notes_data) + columns - 1) // columns
            row_height = 260 + spacing
            self.grid_container.setMinimumHeight(total_rows * row_height)

            # Responsive Phase 1: fill entire visible screen (FHD: ~24, 2K/4K: ~40-60 notes)
            viewport_h = max(600, self.scroll_area.viewport().height())
            visible_rows = (viewport_h // row_height) + 2
            needed_cards = max(24, columns * visible_rows)
            initial_count = min(needed_cards, len(self.filtered_notes_data))
            for i in range(initial_count):
                card = self._create_card(self.filtered_notes_data[i])
                self.grid_layout.addWidget(card, i // columns, i % columns)
                self.cards.append(card)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

        if len(self.filtered_notes_data) > initial_count:
            self._pending_load_index = initial_count
            if not hasattr(self, '_chunk_timer'):
                self._chunk_timer = QTimer(self)
                self._chunk_timer.setSingleShot(True)
                self._chunk_timer.timeout.connect(self._load_remaining_notes)
            self._chunk_timer.start(0)

        self.scroll_check_timer.start(10)

    def _load_remaining_notes(self):
        if not hasattr(self, '_pending_load_index') or self._pending_load_index >= len(self.filtered_notes_data):
            return

        columns = self.current_columns if self.current_columns > 0 else 1
        chunk_size = 40
        end_idx = min(self._pending_load_index + chunk_size, len(self.filtered_notes_data))

        self.scroll_area.setUpdatesEnabled(False)
        self.grid_container.setUpdatesEnabled(False)
        try:
            for i in range(self._pending_load_index, end_idx):
                card = self._create_card(self.filtered_notes_data[i])
                self.grid_layout.addWidget(card, i // columns, i % columns)
                self.cards.append(card)
        finally:
            self.grid_container.setUpdatesEnabled(True)
            self.scroll_area.setUpdatesEnabled(True)

        self._pending_load_index = end_idx
        if self._pending_load_index < len(self.filtered_notes_data):
            self._chunk_timer.start(0)

    def update_grid_layout(self):
        if not self.cards or isinstance(self.cards[0], QLabel):
            return

        width = self.scroll_area.viewport().width()
        card_width = 240
        spacing = 16
        total_items = len(self.filtered_notes_data) if getattr(self, 'filtered_notes_data', None) else len(self.cards)
        scrollbar_w = 16 if total_items > 12 else 0
        avail_w = max(100, width - scrollbar_w)
        columns = max(1, (avail_w + spacing) // (card_width + spacing))

        if columns == self.current_columns:
            return

        self.current_columns = columns
        total_rows = (total_items + columns - 1) // columns
        row_height = 260 + spacing
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

    def on_filter_changed(self):
        self.apply_filters_and_sorting()

    def on_sort_changed(self, text):
        self.apply_filters_and_sorting()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.oldSize().width() <= 0 or event.oldSize().width() == event.size().width():
            return

        width = self.scroll_area.viewport().width()
        card_width = 240
        spacing = 16
        scrollbar_w = 16 if len(self.cards) > 12 else 0
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
        row_h = 260 + 16 # card height + spacing
        first_row = max(0, (scroll_y - 300) // row_h)
        last_row = (scroll_y + viewport_h + 350) // row_h
        first_idx = int(first_row * columns)
        last_idx = min(len(self.cards), int((last_row + 1) * columns))

        for i in range(first_idx, last_idx):
            card = self.cards[i]
            if isinstance(card, NoteCardWidget):
                if not (getattr(card, 'image_loaded', False) or getattr(card, 'image_loading', False)):
                    card.ensure_image_loaded()

    def update_card_favorite(self, note_id, is_favorite):
        for n in self.notes_data:
            if n.get('id') == note_id:
                n['is_favorite'] = 1 if is_favorite else 0
                
        if self.fav_toggle_btn.isChecked():
            self.apply_filters_and_sorting()
        else:
            for card in self.cards:
                if isinstance(card, NoteCardWidget) and card.note_data.get('id') == note_id:
                    card.note_data['is_favorite'] = 1 if is_favorite else 0
                    card.is_fav = is_favorite
                    card.update_fav_btn_style()
                    break

    def on_empty_trash_clicked(self):
        reply = QMessageBox.question(
            self, t("trash_empty_title"), t("trash_empty_confirm"),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.empty_trash_requested.emit()

    def retranslate_ui(self):
        self.title_label.setText(t("trash") if self.is_trash else t("notes"))
        self.search_edit.setPlaceholderText(t("view_search_notes_placeholder"))
        self.fav_toggle_btn.setText(f"  {t('view_favorites')}")
        self.fav_toggle_btn.setIcon(get_icon("star", "#8AB4F8", 16))
        self.empty_trash_btn.setText(f"  {t('trash_empty_title')}")
        self.empty_trash_btn.setIcon(get_icon("trash", "#FFFFFF", 16))
        self.new_note_btn.setText(f"  {t('new_note')}")
        self.new_note_btn.setIcon(get_icon("add", "#FFFFFF", 16))
        
        self.select_all_btn.setText(t("bulk_select_all"))
        self.clear_select_btn.setText(t("bulk_clear_selection"))
        self.bulk_pin_btn.setText(t("bulk_pin_corkboard"))
        self.bulk_restore_btn.setText(t("bulk_restore"))
        self.bulk_delete_btn.setText(t("bulk_delete"))
        self.update_bulk_bar()

        self.sort_combo.blockSignals(True)
        current_idx = self.sort_combo.currentIndex()
        self.sort_combo.clear()
        self.sort_combo.addItems([t("view_sort_newest"), t("view_last_edited"), t("view_sort_oldest"), t("view_sort_az"), t("view_sort_za")])
        if current_idx >= 0:
            self.sort_combo.setCurrentIndex(current_idx)
        self.sort_combo.blockSignals(False)
        
        self.apply_filters_and_sorting()
