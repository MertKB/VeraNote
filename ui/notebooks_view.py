# ui/notebooks_view.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QGridLayout, QFrame, 
                             QSizePolicy, QLineEdit, QComboBox, QMessageBox, QApplication)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QKeySequence, QShortcut, QKeyEvent
from utils.i18n import t
from utils.icon_manager import get_icon, get_pixmap

class NotebookCardWidget(QFrame):
    clicked = Signal(int, str) # id, name
    rename_requested = Signal(int, str) # id, name
    delete_requested = Signal(int, str) # id, name
    selection_toggled = Signal(dict, bool)

    def __init__(self, notebook_data: dict, highlight_color: str = "#8AB4F8", parent=None):
        super().__init__(parent)
        self.notebook_data = notebook_data
        self.highlight_color = highlight_color
        self.nb_id = notebook_data['id']
        self.nb_name = notebook_data['name']
        self.note_count = notebook_data.get('note_count', 0)
        self.is_selected = False
        
        self.setObjectName("NotebookCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(260, 150)
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Top bar: Notebook icon + Actions (Rename, Delete)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(28, 28)
        self.icon_label.setScaledContents(True)
        self.icon_label.setPixmap(get_pixmap("notebooks", self.highlight_color, 28))
        self.icon_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        top_layout.addWidget(self.icon_label)

        top_layout.addStretch()

        # Rename button
        self.rename_btn = QPushButton()
        self.rename_btn.setObjectName("CardActionBtn")
        self.rename_btn.setFixedSize(28, 28)
        self.rename_btn.setIcon(get_icon("settings", "#C4C7C5", 14))
        self.rename_btn.setIconSize(QSize(14, 14))
        self.rename_btn.setToolTip(t("notebook_rename"))
        self.rename_btn.setCursor(Qt.PointingHandCursor)
        self.rename_btn.clicked.connect(self.on_rename_clicked)
        top_layout.addWidget(self.rename_btn)

        # Delete button
        self.delete_btn = QPushButton()
        self.delete_btn.setObjectName("CardDeleteBtn")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setIcon(get_icon("trash", "#F28B82", 14))
        self.delete_btn.setIconSize(QSize(14, 14))
        self.delete_btn.setToolTip(t("notebook_delete"))
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self.on_delete_clicked)
        top_layout.addWidget(self.delete_btn)

        layout.addLayout(top_layout)

        # Middle: Notebook Name
        self.name_label = QLabel(self.nb_name)
        self.name_label.setObjectName("NotebookCardTitle")
        self.name_label.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: bold;")
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.name_label)

        layout.addStretch()

        # Bottom bar: Note count chip + Open prompt
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(8)

        self.count_badge = QLabel(f" {t('notebook_card_notes_count').format(count=self.note_count)}")
        self.count_badge.setObjectName("NotebookCardBadge")
        self.count_badge.setStyleSheet("""
            background-color: #2F3336;
            color: #C4C7C5;
            font-size: 11px;
            font-weight: 600;
            border-radius: 6px;
            padding: 3px 8px;
        """)
        self.count_badge.setAttribute(Qt.WA_TransparentForMouseEvents)
        bottom_layout.addWidget(self.count_badge)

        bottom_layout.addStretch()

        self.open_label = QLabel(f"{t('notebook_open')} →")
        self.open_label.setStyleSheet(f"color: {self.highlight_color}; font-size: 12px; font-weight: bold;")
        self.open_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        bottom_layout.addWidget(self.open_label)

        layout.addLayout(bottom_layout)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_card_style()

    def toggle_selection(self):
        self.set_selected(not self.is_selected)
        self.selection_toggled.emit(self.notebook_data, self.is_selected)

    def update_card_style(self):
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame#NotebookCard {{
                    background-color: #263238;
                    border: 2px solid {self.highlight_color};
                    border-radius: 12px;
                }}
            """)
        else:
            self.setStyleSheet("")

    def update_theme(self, highlight_color: str):
        self.highlight_color = highlight_color
        self.icon_label.setPixmap(get_pixmap("notebooks", self.highlight_color, 28))
        self.open_label.setStyleSheet(f"color: {self.highlight_color}; font-size: 12px; font-weight: bold;")
        self.update_card_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            from PySide6.QtGui import QGuiApplication
            if QGuiApplication.keyboardModifiers() & Qt.ControlModifier:
                self.toggle_selection()
                return
            self.clicked.emit(self.nb_id, self.nb_name)
        super().mousePressEvent(event)

    def on_rename_clicked(self):
        self.rename_requested.emit(self.nb_id, self.nb_name)

    def on_delete_clicked(self):
        self.delete_requested.emit(self.nb_id, self.nb_name)


class NotebooksView(QWidget):
    notebook_opened = Signal(int, str) # id, name
    create_notebook_requested = Signal()
    rename_notebook_requested = Signal(int, str) # id, name
    delete_notebook_requested = Signal(int, str) # id, name
    bulk_delete_notebooks_requested = Signal(list) # list of notebook ids

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NotebooksView")
        self.notebooks_data = []
        self.filtered_notebooks = []
        self.cards = []
        self.selected_notebook_ids = set()
        self.highlight_color = "#8AB4F8"
        
        self.select_all_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        self.select_all_shortcut.activated.connect(self.select_all_notebooks)

        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)

        # Header Bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.title_icon = QLabel()
        self.title_icon.setFixedSize(28, 28)
        self.title_icon.setScaledContents(True)
        self.title_icon.setPixmap(get_pixmap("notebooks", self.highlight_color, 28))
        header_layout.addWidget(self.title_icon)

        self.title_label = QLabel(t("notebooks_title"))
        self.title_label.setStyleSheet("color: #E3E3E3; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(self.title_label)

        self.count_badge = QLabel("0")
        self.count_badge.setObjectName("NotebooksBadge")
        self.count_badge.setAlignment(Qt.AlignCenter)
        self.count_badge.setFixedSize(28, 22)
        header_layout.addWidget(self.count_badge)

        # Search field
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(t("notebooks_search_placeholder"))
        self.search_edit.setMinimumWidth(160)
        self.search_edit.setMaximumWidth(320)
        self.search_edit.textChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.search_edit)

        # Sort combo
        self.sort_combo = QComboBox()
        self.populate_sort_combo()
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
        self.sort_combo.currentIndexChanged.connect(self.on_filter_changed)
        header_layout.addWidget(self.sort_combo)

        header_layout.addStretch()

        # New Notebook button
        self.new_notebook_btn = QPushButton(f"  {t('new_notebook')}")
        self.new_notebook_btn.setObjectName("HeaderAddBtn")
        self.new_notebook_btn.setIcon(get_icon("add", "#FFFFFF", 16))
        self.new_notebook_btn.setIconSize(QSize(16, 16))
        self.new_notebook_btn.setFixedHeight(36)
        self.new_notebook_btn.setCursor(Qt.PointingHandCursor)
        self.new_notebook_btn.clicked.connect(self.create_notebook_requested.emit)
        header_layout.addWidget(self.new_notebook_btn)

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

        self.bulk_count_label = QLabel(t("notebooks_bulk_selected_count").format(count=0), self.bulk_bar)
        self.bulk_count_label.setStyleSheet(f"color: {self.highlight_color}; font-weight: bold; font-size: 14px;")
        bulk_layout.addWidget(self.bulk_count_label)

        bulk_layout.addStretch()

        self.select_all_btn = QPushButton(t("bulk_select_all"), self.bulk_bar)
        self.select_all_btn.setStyleSheet("background-color: #334155; color: #F1F5F9; border-radius: 6px; padding: 5px 10px; font-weight: 500;")
        self.select_all_btn.setCursor(Qt.PointingHandCursor)
        self.select_all_btn.clicked.connect(self.select_all_notebooks)
        bulk_layout.addWidget(self.select_all_btn)

        self.clear_select_btn = QPushButton(t("bulk_clear_selection"), self.bulk_bar)
        self.clear_select_btn.setStyleSheet("background-color: #334155; color: #94A3B8; border-radius: 6px; padding: 5px 10px; font-weight: 500;")
        self.clear_select_btn.setCursor(Qt.PointingHandCursor)
        self.clear_select_btn.clicked.connect(self.clear_selection)
        bulk_layout.addWidget(self.clear_select_btn)

        self.bulk_delete_btn = QPushButton(t("bulk_delete"), self.bulk_bar)
        self.bulk_delete_btn.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; border-radius: 6px; padding: 5px 12px;")
        self.bulk_delete_btn.setCursor(Qt.PointingHandCursor)
        self.bulk_delete_btn.clicked.connect(self.on_bulk_delete_clicked)
        bulk_layout.addWidget(self.bulk_delete_btn)

        self.bulk_bar.setVisible(False)
        self.main_layout.addWidget(self.bulk_bar)

        # Scroll Area for Cards Grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 10, 0, 10)
        self.cards_layout.setSpacing(16)
        self.cards_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.scroll_area.setWidget(self.cards_container)
        self.main_layout.addWidget(self.scroll_area)

        # Empty State Container (shown when no notebooks)
        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(12)

        self.empty_icon = QLabel()
        self.empty_icon.setFixedSize(64, 64)
        self.empty_icon.setScaledContents(True)
        self.empty_icon.setPixmap(get_pixmap("notebooks", "#5F6368", 64))
        empty_layout.addWidget(self.empty_icon, 0, Qt.AlignCenter)

        self.empty_title = QLabel(t("notebooks_empty_title"))
        self.empty_title.setStyleSheet("color: #E3E3E3; font-size: 18px; font-weight: bold;")
        empty_layout.addWidget(self.empty_title, 0, Qt.AlignCenter)

        self.empty_desc = QLabel(t("notebooks_empty_subtitle"))
        self.empty_desc.setStyleSheet("color: #9AA0A6; font-size: 13px;")
        empty_layout.addWidget(self.empty_desc, 0, Qt.AlignCenter)

        self.empty_btn = QPushButton(f"  {t('notebooks_create_first_btn')}")
        self.empty_btn.setObjectName("HeaderAddBtn")
        self.empty_btn.setIcon(get_icon("add", "#FFFFFF", 16))
        self.empty_btn.setIconSize(QSize(16, 16))
        self.empty_btn.setFixedHeight(38)
        self.empty_btn.setCursor(Qt.PointingHandCursor)
        self.empty_btn.clicked.connect(self.create_notebook_requested.emit)
        empty_layout.addWidget(self.empty_btn, 0, Qt.AlignCenter)

        self.empty_widget.setVisible(False)
        self.main_layout.addWidget(self.empty_widget)

    def populate_sort_combo(self):
        self.sort_combo.clear()
        self.sort_combo.addItem(t("notebooks_sort_recent"), "recent")
        self.sort_combo.addItem(t("notebooks_sort_name_asc"), "name_asc")
        self.sort_combo.addItem(t("notebooks_sort_name_desc"), "name_desc")
        self.sort_combo.addItem(t("notebooks_sort_count_desc"), "count_desc")

    def set_notebooks(self, notebooks: list):
        self.notebooks_data = notebooks or []
        self.count_badge.setText(str(len(self.notebooks_data)))
        # Prune deleted notebooks from selection
        valid_ids = {nb['id'] for nb in self.notebooks_data}
        self.selected_notebook_ids = self.selected_notebook_ids.intersection(valid_ids)
        self.update_bulk_bar()
        self.apply_filters()

    def on_filter_changed(self):
        self.apply_filters()

    def apply_filters(self):
        query = self.search_edit.text().strip().lower()
        items = list(self.notebooks_data)

        if query:
            items = [nb for nb in items if query in nb.get('name', '').lower()]

        sort_mode = self.sort_combo.currentData()
        if sort_mode == "name_asc":
            items.sort(key=lambda x: x.get('name', '').lower())
        elif sort_mode == "name_desc":
            items.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
        elif sort_mode == "count_desc":
            items.sort(key=lambda x: x.get('note_count', 0), reverse=True)
        else: # "recent"
            items.sort(key=lambda x: x.get('updated_at') or '', reverse=True)

        self.filtered_notebooks = items
        self.render_cards()

    def render_cards(self):
        # Clear existing cards in layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.cards.clear()

        if not self.filtered_notebooks:
            self.scroll_area.setVisible(False)
            self.empty_widget.setVisible(True)
            return

        self.empty_widget.setVisible(False)
        self.scroll_area.setVisible(True)

        # Responsive columns based on available container width
        viewport_w = self.scroll_area.viewport().width()
        card_w = 260
        spacing = 16
        columns = max(1, (viewport_w + spacing) // (card_w + spacing)) if viewport_w > 100 else 3

        for idx, nb in enumerate(self.filtered_notebooks):
            row = idx // columns
            col = idx % columns
            card = NotebookCardWidget(nb, highlight_color=self.highlight_color, parent=self)
            if nb['id'] in self.selected_notebook_ids:
                card.set_selected(True)
            card.clicked.connect(self.notebook_opened.emit)
            card.rename_requested.connect(self.rename_notebook_requested.emit)
            card.delete_requested.connect(self.delete_notebook_requested.emit)
            card.selection_toggled.connect(self.on_card_selection_toggled)
            self.cards_layout.addWidget(card, row, col)
            self.cards.append(card)

    def on_card_selection_toggled(self, notebook_data: dict, is_selected: bool):
        nb_id = notebook_data.get('id')
        if nb_id is None:
            return
        if is_selected:
            self.selected_notebook_ids.add(nb_id)
        else:
            self.selected_notebook_ids.discard(nb_id)
        self.update_bulk_bar()

    def select_all_notebooks(self):
        for nb in self.filtered_notebooks:
            self.selected_notebook_ids.add(nb['id'])
        for card in self.cards:
            card.set_selected(True)
        self.update_bulk_bar()

    def clear_selection(self):
        self.selected_notebook_ids.clear()
        for card in self.cards:
            card.set_selected(False)
        self.update_bulk_bar()

    def update_bulk_bar(self):
        count = len(self.selected_notebook_ids)
        if count > 0:
            self.bulk_count_label.setText(t("notebooks_bulk_selected_count").format(count=count))
            self.bulk_bar.setVisible(True)
        else:
            self.bulk_bar.setVisible(False)

    def on_bulk_delete_clicked(self):
        count = len(self.selected_notebook_ids)
        if count == 0:
            return

        msg = t("notebooks_bulk_delete_confirm").format(count=count)
        reply = QMessageBox.question(
            self,
            t("notebook_delete"),
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            ids_to_delete = list(self.selected_notebook_ids)
            self.clear_selection()
            self.bulk_delete_notebooks_requested.emit(ids_to_delete)

    def keyPressEvent(self, event: QKeyEvent):
        if event.matches(QKeySequence.SelectAll):
            self.select_all_notebooks()
            event.accept()
            return
        super().keyPressEvent(event)

    def apply_theme(self, palette: dict):
        if not palette:
            return
        self.highlight_color = palette.get("highlight_color", palette.get("border_focus", "#8AB4F8"))
        self.title_icon.setPixmap(get_pixmap("notebooks", self.highlight_color, 28))
        self.bulk_count_label.setStyleSheet(f"color: {self.highlight_color}; font-weight: bold; font-size: 14px;")
        for card in self.cards:
            card.update_theme(self.highlight_color)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.filtered_notebooks:
            self.render_cards()

    def retranslate_ui(self):
        self.title_label.setText(t("notebooks_title"))
        self.search_edit.setPlaceholderText(t("notebooks_search_placeholder"))
        self.new_notebook_btn.setText(f"  {t('new_notebook')}")
        self.empty_title.setText(t("notebooks_empty_title"))
        self.empty_desc.setText(t("notebooks_empty_subtitle"))
        self.empty_btn.setText(f"  {t('notebooks_create_first_btn')}")
        self.select_all_btn.setText(t("bulk_select_all"))
        self.clear_select_btn.setText(t("bulk_clear_selection"))
        self.bulk_delete_btn.setText(t("bulk_delete"))
        self.update_bulk_bar()
        
        curr_data = self.sort_combo.currentData()
        self.populate_sort_combo()
        idx = self.sort_combo.findData(curr_data)
        if idx >= 0:
            self.sort_combo.setCurrentIndex(idx)
        self.render_cards()
