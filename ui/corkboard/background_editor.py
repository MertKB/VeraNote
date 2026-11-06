"""
Background Editor (Arka Plan Düzenleyici) for VeraNote Welcome Screen.
Provides a modern visual interface matching the user-designed mockup:
- "Dosyalarım (resim veya video)" with "+ Yeni ekle"
- Thumbnail gallery with active selection highlight
- Action buttons: "🔍 Görünüm", "🔗 Seçenekler", "➖ Kaldır"
- Sliders: "Dikey", "Yatay", "Boyut", "Parlaklık", "Bulanıklık"
"""
import os
import shutil
import time
import json
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSlider, QMenu, QFileDialog,
    QFrame, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QPoint, QObject
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QCursor
from PIL import Image, ImageEnhance, ImageFilter
from utils.i18n import t


class AutoSaveOnOutsideClickFilter(QObject):
    """Event filter that automatically accepts and closes the dialog when clicking outside."""
    def __init__(self, dialog):
        super().__init__(dialog)
        self.dialog = dialog

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if getattr(self.dialog, '_child_dialog_open', False):
                return False
            active_modal = QApplication.activeModalWidget()
            if active_modal and active_modal != self.dialog:
                return False
            active_popup = QApplication.activePopupWidget()
            pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
            if active_popup:
                if active_popup.frameGeometry().contains(pos) or self.dialog.frameGeometry().contains(pos):
                    return False
            if not self.dialog.frameGeometry().contains(pos):
                self.dialog.accept()
                return True
        return False


class CustomPillSlider(QSlider):
    """
    Sleek custom slider matching the provided screenshot design:
    - Pill/capsule white handle
    - Bright blue active track
    - Dark gray inactive track
    """
    def __init__(self, orientation=Qt.Horizontal, parent=None, accent_color="#1A73E8"):
        super().__init__(orientation, parent)
        self.accent_color = accent_color
        self.update_style()

    def wheelEvent(self, event):
        event.ignore()

    def update_style(self, accent_color=None):
        if accent_color:
            self.accent_color = accent_color
        self.setStyleSheet(f"""
            QSlider {{
                min-height: 26px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: #383A3D;
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.accent_color};
                border-radius: 2px;
            }}
            QSlider::add-page:horizontal {{
                background: #383A3D;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #FFFFFF;
                border: none;
                width: 28px;
                height: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #F0F4F9;
            }}
        """)


class WallpaperThumbnailCard(QFrame):
    """
    Thumbnail card for wallpaper files.
    Renders rounded preview and blue highlight border when selected.
    """
    clicked = Signal(str)

    def __init__(self, file_path: str, is_selected: bool = False, parent=None, accent_color="#1A73E8"):
        super().__init__(parent)
        self.file_path = file_path.replace("\\", "/")
        self.is_selected = is_selected
        self.accent_color = accent_color
        self.setFixedSize(126, 76)
        self.setCursor(Qt.PointingHandCursor)
        self._pixmap = None
        self.load_thumbnail()

    def set_selected(self, selected: bool):
        if self.is_selected != selected:
            self.is_selected = selected
            self.update()

    def load_thumbnail(self):
        if not self.file_path or not os.path.exists(self.file_path):
            return
        ext = os.path.splitext(self.file_path)[1].lower()
        try:
            if ext in ('.mp4', '.webm', '.mov', '.avi', '.mkv'):
                # Video file placeholder
                self.is_video = True
            else:
                self.is_video = False
                with Image.open(self.file_path) as raw_img:
                    img = raw_img.convert('RGB')
                    img.thumbnail((240, 144), Image.Resampling.BILINEAR)
                    data = img.tobytes("raw", "RGB")
                    qimg = QImage(data, img.width, img.height, img.width * 3, QImage.Format_RGB888)
                    self._pixmap = QPixmap.fromImage(qimg.copy())
        except Exception:
            self._pixmap = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_path)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background base
        rect = self.rect().adjusted(1, 1, -1, -1)
        bg_color = QColor("#18191B")
        painter.setBrush(bg_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 8, 8)

        # Draw Pixmap if available
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (scaled.width() - self.width()) // 2
            sy = (scaled.height() - self.height()) // 2
            cropped = scaled.copy(sx, sy, self.width(), self.height())
            
            # Clip with rounded rect
            from PySide6.QtGui import QPainterPath
            path = QPainterPath()
            path.addRoundedRect(rect, 7, 7)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.setClipping(False)
        elif getattr(self, 'is_video', False):
            # Draw video badge
            painter.setPen(QColor("#8AB4F8"))
            painter.drawText(rect, Qt.AlignCenter, "▶ VIDEO")

        # Selection Border
        if self.is_selected:
            pen = QPen(QColor(self.accent_color), 2.5)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)
        else:
            pen = QPen(QColor("#383A3D"), 1.0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, 8, 8)

        painter.end()


class BackgroundEditorDialog(QDialog):
    """
    Dedicated Background Editor matching the user's mockup.
    Live updates the WelcomeScreen background with sliders and options.
    """
    def __init__(self, welcome_screen, parent=None):
        super().__init__(parent or welcome_screen)
        self.welcome_screen = welcome_screen
        self.accent_color = getattr(welcome_screen, 'accent_color', '#1A73E8')
        self.highlight_color = getattr(welcome_screen, 'highlight_color', '#8AB4F8')
        self._child_dialog_open = False
        self._outside_filter = AutoSaveOnOutsideClickFilter(self)

        self.setWindowTitle(t("home_bg_editor_title"))
        self.setFixedWidth(460)
        self.setMinimumHeight(440)
        self.setObjectName("BackgroundEditorDialog")

        self.setStyleSheet(f"""
            QDialog#BackgroundEditorDialog {{
                background-color: #1A1B1E;
                border: 1px solid #333538;
                border-radius: 16px;
            }}
            QLabel {{
                color: #E3E3E3;
                font-size: 13px;
            }}
            QPushButton {{
                background-color: #26282B;
                color: #8AB4F8;
                border: 1px solid #3C4043;
                border-radius: 14px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #313438;
                color: #FFFFFF;
                border-color: {self.highlight_color};
            }}
            QPushButton#PrimaryBtn {{
                background-color: rgba(26, 115, 232, 0.15);
                color: {self.highlight_color};
                border: 1px solid {self.accent_color};
            }}
            QPushButton#PrimaryBtn:hover {{
                background-color: {self.accent_color};
                color: #FFFFFF;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header Row: "Dosyalarım (resim veya video)" and "+ Yeni ekle"
        header_layout = QHBoxLayout()
        header_lbl = QLabel(t("home_bg_files_title"), self)
        header_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()

        self.add_btn = QPushButton(t("home_bg_add_new"), self)
        self.add_btn.setObjectName("PrimaryBtn")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_new_file)
        header_layout.addWidget(self.add_btn)
        layout.addLayout(header_layout)

        # Thumbnails Gallery Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setFixedHeight(92)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                height: 4px;
                background: transparent;
            }
            QScrollBar::handle:horizontal {
                background: #444746;
                border-radius: 2px;
            }
        """)

        self.thumb_container = QWidget()
        self.thumb_container.setStyleSheet("background: transparent;")
        self.thumb_layout = QHBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(0, 0, 0, 0)
        self.thumb_layout.setSpacing(10)
        self.thumb_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.scroll_area.setWidget(self.thumb_container)
        layout.addWidget(self.scroll_area)

        # Action Buttons Row: "Görünüm", "Seçenekler", "Kaldır"
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.view_btn = QPushButton(t("home_bg_view"), self)
        self.view_btn.setCursor(Qt.PointingHandCursor)
        self.view_btn.clicked.connect(self.show_view_menu)
        actions_layout.addWidget(self.view_btn)

        self.options_btn = QPushButton(t("home_bg_options"), self)
        self.options_btn.setCursor(Qt.PointingHandCursor)
        self.options_btn.clicked.connect(self.show_options_menu)
        actions_layout.addWidget(self.options_btn)

        self.remove_btn = QPushButton(t("home_bg_remove"), self)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.clicked.connect(self.remove_active_wallpaper)
        actions_layout.addWidget(self.remove_btn)

        layout.addLayout(actions_layout)

        # Sliders Section: Dikey, Yatay, Boyut, Parlaklık, Bulanıklık
        sliders_box = QVBoxLayout()
        sliders_box.setSpacing(12)

        # 1. Dikey (Vertical Offset: -100 to 100)
        self.v_slider = self.create_slider_row(
            t("home_bg_vertical"), -100, 100,
            getattr(self.welcome_screen, 'wallpaper_vertical', 0),
            self.on_v_changed, sliders_box
        )

        # 2. Yatay (Horizontal Offset: -100 to 100)
        self.h_slider = self.create_slider_row(
            t("home_bg_horizontal"), -100, 100,
            getattr(self.welcome_screen, 'wallpaper_horizontal', 0),
            self.on_h_changed, sliders_box
        )

        # 3. Boyut (Scale: 50% to 250%)
        self.scale_slider = self.create_slider_row(
            t("home_bg_scale"), 50, 250,
            getattr(self.welcome_screen, 'wallpaper_scale', 100),
            self.on_scale_changed, sliders_box
        )

        # 4. Parlaklık (Brightness: 10% to 200%)
        self.brightness_slider = self.create_slider_row(
            t("home_bg_brightness"), 10, 200,
            getattr(self.welcome_screen, 'wallpaper_brightness', 100),
            self.on_brightness_changed, sliders_box
        )

        # 5. Bulanıklık (Blur: 0 to 30px)
        self.blur_slider = self.create_slider_row(
            t("home_bg_blur"), 0, 30,
            getattr(self.welcome_screen, 'wallpaper_blur', 0),
            self.on_blur_changed, sliders_box
        )

        layout.addLayout(sliders_box)

        # Populate thumbnails
        self.refresh_thumbnails()

    def create_slider_row(self, label_text, min_val, max_val, curr_val, callback, parent_layout):
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text, self)
        lbl.setFixedWidth(75)
        lbl.setStyleSheet("color: #E3E3E3; font-size: 13px; font-weight: 500;")
        row.addWidget(lbl)

        slider = CustomPillSlider(Qt.Horizontal, self, accent_color=self.accent_color)
        slider.setRange(min_val, max_val)
        slider.setValue(curr_val)
        slider.valueChanged.connect(callback)
        row.addWidget(slider, 1)

        parent_layout.addLayout(row)
        return slider

    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowModality(Qt.NonModal)
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._outside_filter)

    def hideEvent(self, event):
        super().hideEvent(event)
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._outside_filter)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow():
                if not getattr(self, '_child_dialog_open', False):
                    active_modal = QApplication.activeModalWidget()
                    if not active_modal or active_modal == self:
                        self.accept()

    def refresh_thumbnails(self):
        # Clear existing
        while self.thumb_layout.count():
            item = self.thumb_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        wallpapers = self.welcome_screen.get_wallpapers_list()
        active_wp = self.welcome_screen.wallpaper_path

        for wp_path in wallpapers:
            card = WallpaperThumbnailCard(
                wp_path,
                is_selected=(wp_path == active_wp),
                parent=self.thumb_container,
                accent_color=self.accent_color
            )
            card.clicked.connect(self.on_thumbnail_clicked)
            self.thumb_layout.addWidget(card)

    def on_thumbnail_clicked(self, file_path):
        self.welcome_screen.set_wallpaper(file_path)
        self.welcome_screen.setting_changed.emit("welcome_wallpaper", file_path)
        # Update cards selection
        for i in range(self.thumb_layout.count()):
            card = self.thumb_layout.itemAt(i).widget()
            if isinstance(card, WallpaperThumbnailCard):
                card.set_selected(card.file_path == file_path)

    def add_new_file(self):
        self._child_dialog_open = True
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                t("welcome_wallpaper_dialog"),
                "",
                t("dialog_media_filter")
            )
            if not files:
                return

            dest_dir = self.welcome_screen.get_wallpapers_storage_dir()
            os.makedirs(dest_dir, exist_ok=True)

            last_added = None
            current_list = self.welcome_screen.get_wallpapers_list()

            for f in files:
                f_norm = f.replace("\\", "/")
                # Copy to local veranote wallpapers directory
                filename = os.path.basename(f)
                timestamp = int(time.time() * 1000)
                name, ext = os.path.splitext(filename)
                target_path = os.path.join(dest_dir, f"wp_{timestamp}_{name}{ext}").replace("\\", "/")
                
                try:
                    shutil.copy2(f, target_path)
                    saved_path = target_path
                except Exception:
                    saved_path = f_norm

                if saved_path not in current_list:
                    current_list.append(saved_path)
                last_added = saved_path

            self.welcome_screen.set_wallpapers_list(current_list)
            if last_added:
                self.welcome_screen.set_wallpaper(last_added)
                self.welcome_screen.setting_changed.emit("welcome_wallpaper", last_added)

            self.refresh_thumbnails()
        finally:
            self._child_dialog_open = False

    def remove_active_wallpaper(self):
        active_wp = self.welcome_screen.wallpaper_path
        if not active_wp:
            return

        current_list = self.welcome_screen.get_wallpapers_list()
        if active_wp in current_list:
            current_list.remove(active_wp)

        new_active = current_list[0] if current_list else ""
        self.welcome_screen.set_wallpapers_list(current_list)
        self.welcome_screen.set_wallpaper(new_active)
        self.welcome_screen.setting_changed.emit("welcome_wallpaper", new_active)
        self.refresh_thumbnails()

    def show_view_menu(self):
        self._child_dialog_open = True
        try:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2D2F31;
                    border: 1px solid #444746;
                    border-radius: 8px;
                    color: #E3E3E3;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 16px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #1A73E8;
                    color: #FFFFFF;
                }
            """)
            modes = [
                ("cover", t("home_bg_view_cover")),
                ("contain", t("home_bg_view_contain")),
                ("center", t("home_bg_view_center")),
                ("stretch", t("home_bg_view_stretch")),
            ]
            curr_mode = getattr(self.welcome_screen, 'wallpaper_mode', 'cover')
            for mode_key, mode_title in modes:
                act = menu.addAction(f"✓  {mode_title}" if mode_key == curr_mode else f"    {mode_title}")
                act.triggered.connect(lambda checked=False, m=mode_key: self.set_wallpaper_mode(m))

            pos = self.view_btn.mapToGlobal(QPoint(0, self.view_btn.height() + 4))
            menu.exec(pos)
        finally:
            self._child_dialog_open = False

    def set_wallpaper_mode(self, mode):
        self.welcome_screen.set_wallpaper_mode(mode)

    def show_options_menu(self):
        self._child_dialog_open = True
        try:
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2D2F31;
                    border: 1px solid #444746;
                    border-radius: 8px;
                    color: #E3E3E3;
                    padding: 4px;
                }
                QMenu::item {
                    padding: 6px 16px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #1A73E8;
                    color: #FFFFFF;
                }
            """)
            reset_act = menu.addAction(t("home_bg_reset_defaults"))
            reset_act.triggered.connect(self.reset_all_sliders)

            pos = self.options_btn.mapToGlobal(QPoint(0, self.options_btn.height() + 4))
            menu.exec(pos)
        finally:
            self._child_dialog_open = False

    def reset_all_sliders(self):
        self.v_slider.setValue(0)
        self.h_slider.setValue(0)
        self.scale_slider.setValue(100)
        self.brightness_slider.setValue(100)
        self.blur_slider.setValue(0)
        self.welcome_screen.set_wallpaper_adjustments(0, 0, 100, 100, 0)

    def on_v_changed(self, val):
        self.welcome_screen.set_wallpaper_vertical(val)

    def on_h_changed(self, val):
        self.welcome_screen.set_wallpaper_horizontal(val)

    def on_scale_changed(self, val):
        self.welcome_screen.set_wallpaper_scale(val)

    def on_brightness_changed(self, val):
        self.welcome_screen.set_wallpaper_brightness(val)

    def on_blur_changed(self, val):
        self.welcome_screen.set_wallpaper_blur(val)
