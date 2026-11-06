# ui/workflow_builder_view.py
"""
Workflow Builder & Parameter Mapper for VeraNote.
Faithfully designed after the authentic ComfyUI node-graph interface:
  - Real ComfyUI nodes (Load Checkpoint, Load LoRA(s) chained, Load Image, VAE Encode,
    Empty Latent, CLIP Text Encode Positive/Negative, KSampler, VAE Decode, Save Image)
  - Curved antialiased cubic bezier wires in ComfyUI socket colors:
    * Purple: MODEL
    * Yellow: CLIP
    * Coral/Red: VAE
    * Orange: CONDITIONING (KOŞULLANDIRMA)
    * Magenta/Pink: LATENT (GİZLİ)
    * Sky Blue: IMAGE (GÖRÜNTÜ)
    * Green: MASK (MASKE)
  - ComfyUI stepper widgets [ ◄ label ... value ► ] without text clipping
  - Multi-LoRA visual and functional chaining with separate chained nodes
  - Mode-sensitive nodes: in Txt2Img, LoadImage/VAEEncode are cleanly hidden,
    EmptyLatentImage is connected to KSampler. In Img2Img, LoadImage/VAEEncode
    are connected to KSampler.
  - VAE Decode is connected to Save Image (Görüntüyü Kaydet)
  - Interactive nodes (draggable headers, reset layout)
  - Complete backwards compatibility with all unit tests and VeraNote features
"""

import os
import random
from PIL import Image

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QPlainTextEdit,
    QComboBox, QFileDialog, QFrame, QScrollArea,
    QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QRectF, QSize
from PySide6.QtGui import (
    QPixmap, QDragEnterEvent, QDropEvent, QPainter,
    QPainterPath, QPen, QColor, QBrush, QFont
)

from utils.i18n import t
from utils.icon_manager import get_icon, get_pixmap
from utils.png_parser import extract_comfyui_metadata_from_png
from services.workflow_generator import (
    generate_workflow,
    export_workflow_to_json,
    export_workflow_to_png
)
from ui.styles import get_palette, is_light, adjust_brightness


# ==============================================================================
# 1. COLOR DEFINITIONS & SOCKET SYSTEM
# ==============================================================================
COMFY_COLORS = {
    "MODEL": "#B388FF",          # Violet / Purple
    "CLIP": "#FFEB3B",           # Yellow
    "VAE": "#FF6B6B",            # Coral / Red
    "CONDITIONING": "#FFA726",   # Orange
    "LATENT": "#EC407A",         # Magenta / Pink
    "IMAGE": "#42A5F5",          # Cyan / Blue
    "MASK": "#66BB6A",           # Green
    "CANVAS_BG": "#181818",      # Canvas deep dark
    "CANVAS_DOT": "#262626",     # Dot grid
    "NODE_BG": "#242424",        # Node card background
    "NODE_BORDER": "#3A3A3A",    # Node outer border
    "NODE_HEADER": "#1E1E1E",    # Node header bar
    "NODE_HEADER_BG": "#1E1E1E", # Node header background
    "WIDGET_BG": "#161616",      # Parameter input pill
    "WIDGET_BORDER": "#333333",  # Input border
    "TEXT_LIGHT": "#DCDCDC",     # Standard light text
    "TEXT_MUTED": "#8E8E93",     # Muted pin/label text
}


class ComfyPin(QFrame):
    """Circular socket pin dot rendered on node boundaries."""
    def __init__(self, color_hex: str, is_output: bool = False, parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.is_output = is_output
        self.setFixedSize(10, 10)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        c = QColor(self.color_hex)
        painter.setBrush(QBrush(c))
        painter.setPen(QPen(QColor(0, 0, 0, 180), 1))
        painter.drawEllipse(1, 1, 8, 8)


_SOCKET_LABEL_KEYS = {
    "GÖRÜNTÜ": "socket_image",
    "MASKE": "socket_mask",
    "pikseller": "socket_pixels",
    "GİZLİ": "socket_latent",
    "KOŞULLANDIRMA": "socket_conditioning",
    "pozitif": "socket_positive",
    "negatif": "socket_negative",
    "gizli_görüntü": "socket_latent_image",
    "örnekler": "socket_samples",
    "görüntüler": "socket_images",
}


class ComfySocketRow(QWidget):
    """A row showing either an input (dot on left) or output (dot on right)."""
    def __init__(self, name: str, socket_type: str, is_output: bool = False, parent=None):
        super().__init__(parent)
        self.name = name
        self.socket_type = socket_type
        self.is_output = is_output
        self.color_hex = COMFY_COLORS.get(socket_type.upper(), "#9AA0A6")
        self.setFixedHeight(18)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(5)

        self.pin = ComfyPin(self.color_hex, is_output, self)
        display_text = t(_SOCKET_LABEL_KEYS[name]) if name in _SOCKET_LABEL_KEYS else name
        self.lbl = QLabel(display_text)
        self.lbl.setStyleSheet(f"color: {COMFY_COLORS['TEXT_MUTED']}; font-size: 10px; font-weight: 600;")

        if is_output:
            self.lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(self.lbl)
            layout.addWidget(self.pin)
        else:
            self.lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(self.pin)
            layout.addWidget(self.lbl)

    def retranslate_ui(self):
        if self.name in _SOCKET_LABEL_KEYS:
            self.lbl.setText(t(_SOCKET_LABEL_KEYS[self.name]))


# ==============================================================================
# 2. COMFYUI STEPPER WIDGET (ModernSpinBox)
# ==============================================================================
class ModernSpinBox(QFrame):
    """
    ComfyUI parameter capsule widget:
    [ label                      value   <  > ]
    - Left chevron (<) decrements value (btn_left / btn_down)
    - Right chevron (>) increments value (btn_right / btn_up)
    - Generous layout preventing any text clipping or label ellipsis
    - Fully compatible with unit tests expecting lineEdit(), btn_right, btn_left
    """
    valueChanged = Signal(float)

    def __init__(self, value: float = 20, vmin: float = 1, vmax: float = 4096,
                 step: float = 1, decimals: int = 0, label: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("ComfySpinBox")
        self._min = float(vmin)
        self._max = float(vmax)
        self._step = float(step)
        self._decimals = int(decimals)
        self._val = float(value)
        self._label_text = label

        self.setFixedHeight(28)
        self.setStyleSheet(f"""
            #ComfySpinBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
            }}
            #ComfySpinBox:hover {{
                border-color: #4A4A4A;
            }}
            #ComfySpinBox:focus-within {{
                border-color: #8AB4F8;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 1, 4, 1)
        layout.setSpacing(3)

        # Optional parameter label on the left
        self.lbl = QLabel(label)
        self.lbl.setStyleSheet("color: #9AA0A6; font-size: 11px; font-weight: 500;")
        if not label:
            self.lbl.setVisible(False)
        layout.addWidget(self.lbl)
        if label:
            layout.addStretch()

        # Value input line edit
        self.edit = QLineEdit()
        self.edit.setObjectName("ComfySpinEdit")
        self.edit.setAlignment(Qt.AlignRight if label else Qt.AlignCenter)
        self.edit.setMinimumWidth(45)
        self.edit.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #E3E3E3;
                font-size: 11px;
                font-weight: 600;
                padding: 0px 2px;
            }
        """)
        self.edit.editingFinished.connect(self._on_text_changed)
        layout.addWidget(self.edit)

        # < Decrement Button
        self.btn_left = QPushButton("<")
        self.btn_left.setObjectName("ComfyStepBtn")
        self.btn_left.setFixedSize(16, 20)
        self.btn_left.setCursor(Qt.PointingHandCursor)
        self.btn_left.setFocusPolicy(Qt.NoFocus)
        self.btn_left.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888888;
                font-family: Arial, "Segoe UI", sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }
        """)
        self.btn_left.clicked.connect(self.step_down)

        # > Increment Button
        self.btn_right = QPushButton(">")
        self.btn_right.setObjectName("ComfyStepBtn")
        self.btn_right.setFixedSize(16, 20)
        self.btn_right.setCursor(Qt.PointingHandCursor)
        self.btn_right.setFocusPolicy(Qt.NoFocus)
        self.btn_right.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #888888;
                font-family: Arial, "Segoe UI", sans-serif;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 2px;
            }
        """)
        self.btn_right.clicked.connect(self.step_up)

        # Backwards compatibility aliases
        self.btn_up = self.btn_right
        self.btn_down = self.btn_left

        layout.addWidget(self.btn_left)
        layout.addWidget(self.btn_right)

        self._update_text()

    def setLabel(self, text: str):
        self._label_text = text
        self.lbl.setText(text)
        self.lbl.setVisible(bool(text))
        self.edit.setAlignment(Qt.AlignRight if text else Qt.AlignCenter)

    def lineEdit(self):
        return self.edit

    def value(self):
        return int(round(self._val)) if self._decimals == 0 else float(round(self._val, self._decimals))

    def setValue(self, v):
        clamped = max(self._min, min(self._max, float(v)))
        if self._decimals == 0:
            clamped = round(clamped)
        else:
            clamped = round(clamped, self._decimals)
        if clamped != self._val:
            self._val = clamped
            self._update_text()
            self.valueChanged.emit(self.value())

    def setRange(self, vmin, vmax):
        self._min = float(vmin)
        self._max = float(vmax)
        self.setValue(self._val)

    def setSingleStep(self, step):
        self._step = float(step)

    def setDecimals(self, dec):
        self._decimals = int(dec)
        self._update_text()

    def step_up(self):
        self.setValue(self._val + self._step)

    def step_down(self):
        self.setValue(self._val - self._step)

    def _on_text_changed(self):
        try:
            val = float(self.edit.text().strip())
            self.setValue(val)
        except ValueError:
            self._update_text()

    def _update_text(self):
        txt = f"{int(round(self._val))}" if self._decimals == 0 else f"{self._val:.{self._decimals}f}"
        self.edit.setText(txt)


# ==============================================================================
# 3. COMFYUI DROP AREA WIDGET (ImageDropArea)
# ==============================================================================
class ImageDropArea(QFrame):
    """
    Load Image widget matching ComfyUI's 'Görüntü Yükle' node:
    - Browse file button
    - Thumbnail preview of the loaded image
    - Dimension label (e.g. 512 × 512)
    - Drag & drop support
    """
    image_loaded = Signal(str)
    metadata_detected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComfyDropArea")
        self.setAcceptDrops(True)
        self.image_path = None

        self.setStyleSheet(f"""
            #ComfyDropArea {{
                background-color: transparent;
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)

        # Browse action button
        self.browse_btn = QPushButton(t("drop_area_title"))
        self.browse_btn.setFixedHeight(26)
        self.browse_btn.setCursor(Qt.PointingHandCursor)
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #C0C0C0;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #262626;
                color: #FFFFFF;
                border-color: #8AB4F8;
            }}
        """)
        self.browse_btn.clicked.connect(self.browse_file)
        layout.addWidget(self.browse_btn)

        # Image preview container
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(f"""
            background-color: {COMFY_COLORS['WIDGET_BG']};
            border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
            border-radius: 4px;
        """)
        self.preview_frame.setMinimumHeight(150)
        p_layout = QVBoxLayout(self.preview_frame)
        p_layout.setContentsMargins(6, 6, 6, 6)
        p_layout.setSpacing(3)
        p_layout.setAlignment(Qt.AlignCenter)

        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setMinimumSize(140, 110)
        self.thumb_label.setStyleSheet("border: none; background: transparent;")

        # Default placeholder icon
        self.thumb_label.setPixmap(get_pixmap("image", "#555555", 38))

        self.file_dim_lbl = QLabel(t("drop_area_sub"))
        self.file_dim_lbl.setAlignment(Qt.AlignCenter)
        self.file_dim_lbl.setStyleSheet("color: #777777; font-size: 10px; font-weight: bold; border: none;")

        p_layout.addWidget(self.thumb_label, 1)
        p_layout.addWidget(self.file_dim_lbl)
        layout.addWidget(self.preview_frame)

        # Test compatibility and metadata pill
        self.meta_pill = QPushButton("Metadata")
        self.meta_pill.setVisible(False)
        self.title_lbl = QLabel()
        self.sub_lbl = QLabel()
        self.icon_label = QLabel()
        self.loaded_container = QWidget()
        self.file_name_lbl = QLabel()
        self.clear_btn = QPushButton()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_file()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                ext = os.path.splitext(url.toLocalFile())[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.webp'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.webp'):
                    self.set_image(file_path)
                    event.acceptProposedAction()
                    return

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("input_image"),
            "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if file_path:
            self.set_image(file_path)

    def set_image(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            return

        self.image_path = file_path
        filename = os.path.basename(file_path)

        try:
            pix = QPixmap(file_path)
            if not pix.isNull():
                scaled = pix.scaled(200, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumb_label.setPixmap(scaled)
                self.file_dim_lbl.setText(f"{pix.width()} × {pix.height()}")
                self.file_name_lbl.setText(filename)
                self.browse_btn.setText(f"◄ {filename[:22]}... ►" if len(filename) > 25 else f"◄ {filename} ►")
        except Exception as e:
            print(f"Error loading preview: {e}")

        self.image_loaded.emit(file_path)

        if file_path.lower().endswith('.png'):
            try:
                meta = extract_comfyui_metadata_from_png(file_path)
                if meta and (meta.get('positive_prompt') or meta.get('sampler_params')):
                    self.meta_pill.setVisible(True)
                    self.metadata_detected.emit(meta)
                else:
                    self.meta_pill.setVisible(False)
            except Exception:
                self.meta_pill.setVisible(False)
        else:
            self.meta_pill.setVisible(False)

    def clear_image(self):
        self.image_path = None
        self.thumb_label.setPixmap(get_pixmap("image", "#555555", 38))
        self.file_dim_lbl.setText(t("drop_area_sub"))
        self.browse_btn.setText(t("drop_area_title"))
        self.meta_pill.setVisible(False)
        self.image_loaded.emit("")


# ==============================================================================
# 4. MULTI-LORA ROW WIDGET (Clean Inner Controls)
# ==============================================================================
class LoraRowWidget(QFrame):
    """Inner controls for a LoRA entry with name selector and model/clip strengths."""
    removed = Signal(object)
    changed = Signal()

    def __init__(self, loras_list: list = None, parent=None):
        super().__init__(parent)
        self.loras_list = loras_list or []
        self.host_node = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setFixedHeight(26)
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.combo.setMinimumContentsLength(8)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 6px;
            }}
        """)
        self.combo.addItem("None")
        for item in self.loras_list:
            self.combo.addItem(item)
        self.combo.currentTextChanged.connect(lambda: self.changed.emit())

        self.remove_btn = QPushButton("✕")
        self.remove_btn.setObjectName("RemoveLoraBtn")
        self.remove_btn.setFixedSize(22, 22)
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #F87171;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(248, 113, 113, 0.2);
                border-radius: 3px;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self))

        top_row.addWidget(self.combo, 1)
        top_row.addWidget(self.remove_btn)
        layout.addLayout(top_row)

        self.m_strength_spin = ModernSpinBox(1.0, -5.0, 5.0, 0.05, 2, t("tag_model_strength"), self)
        self.m_strength_spin.valueChanged.connect(lambda: self.changed.emit())

        self.c_strength_spin = ModernSpinBox(1.0, -5.0, 5.0, 0.05, 2, t("tag_clip_strength"), self)
        self.c_strength_spin.valueChanged.connect(lambda: self.changed.emit())

        layout.addWidget(self.m_strength_spin)
        layout.addWidget(self.c_strength_spin)

    def set_lora(self, name: str, strength_model: float = 1.0, strength_clip: float = 1.0):
        idx = self.combo.findText(name)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)
        else:
            self.combo.setEditText(name)
        self.m_strength_spin.setValue(strength_model)
        self.c_strength_spin.setValue(strength_clip)

    def get_data(self) -> dict:
        return {
            "name": self.combo.currentText().strip(),
            "strength_model": self.m_strength_spin.value(),
            "strength_clip": self.c_strength_spin.value()
        }


# ==============================================================================
# 5. RESIZE HANDLE & COMFYUI NODE CARD
# ==============================================================================
class ComfyResizeHandle(QWidget):
    """Subtle diagonal resize grip handle placed at the bottom-right corner of a ComfyNode."""
    def __init__(self, target_node, parent=None):
        super().__init__(parent or target_node)
        self.target_node = target_node
        self.setFixedSize(14, 14)
        self.setCursor(Qt.SizeFDiagCursor)
        self._resizing = False
        self._start_pos = QPoint()
        self._start_size = QSize()
        self.setStyleSheet("background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resizing = True
            self._start_pos = event.globalPosition().toPoint()
            self._start_size = self.target_node.size()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._start_pos
            min_w = max(self.target_node.minimumWidth(), 240)
            min_h = max(self.target_node.minimumHeight(), 100)
            new_w = max(min_w, self._start_size.width() + delta.x())
            new_h = max(min_h, self._start_size.height() + delta.y())
            self.target_node.resize(new_w, new_h)
            self.target_node.layout().activate()
            if hasattr(self.target_node, "canvas") and self.target_node.canvas:
                self.target_node.canvas.update()
                view = getattr(self.target_node.canvas, "view_parent", None)
                if view and hasattr(view, "adjust_canvas_size"):
                    view.adjust_canvas_size()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resizing = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor("#777777"), 1.5, Qt.SolidLine, Qt.RoundCap))
        w, h = self.width(), self.height()
        painter.drawLine(w - 2, h - 8, w - 8, h - 2)
        painter.drawLine(w - 2, h - 4, w - 4, h - 2)


class ComfyNode(QFrame):
    """
    Authentic ComfyUI Node Widget:
    - Rounded dark container with subtle border
    - Header with gray dot indicator and node title
    - Left/Right socket pins (inputs/outputs)
    - Draggable across the canvas by dragging its header
    - Resizable via bottom-right resize grip
    - Reliable pin center calculation with geometric fallbacks
    """
    def __init__(self, title: str, canvas, parent=None):
        super().__init__(parent or canvas)
        self.title_text = title
        self.canvas = canvas
        self._dragging = False
        self._drag_start_pos = QPoint()

        self.setObjectName("ComfyNodeCard")
        self.setStyleSheet(f"""
            #ComfyNodeCard {{
                background-color: {COMFY_COLORS['NODE_BG']};
                border: 1.5px solid {COMFY_COLORS['NODE_BORDER']};
                border-radius: 8px;
            }}
            #ComfyNodeCard:hover {{
                border-color: #555555;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 4)
        self.main_layout.setSpacing(5)

        # ---------------- Node Header ----------------
        self.header_widget = QWidget()
        self.header_widget.setFixedHeight(24)
        h_layout = QHBoxLayout(self.header_widget)
        h_layout.setContentsMargins(2, 0, 2, 0)
        h_layout.setSpacing(6)

        self.indicator_dot = QFrame()
        self.indicator_dot.setFixedSize(8, 8)
        self.indicator_dot.setStyleSheet("background-color: #888888; border-radius: 4px;")

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"color: {COMFY_COLORS['TEXT_LIGHT']}; font-size: 11px; font-weight: bold;")

        h_layout.addWidget(self.indicator_dot)
        h_layout.addWidget(self.title_lbl)
        h_layout.addStretch()

        self.main_layout.addWidget(self.header_widget)

        # ---------------- Sockets Layout ----------------
        self.sockets_layout = QGridLayout()
        self.sockets_layout.setContentsMargins(0, 0, 0, 0)
        self.sockets_layout.setHorizontalSpacing(8)
        self.sockets_layout.setVerticalSpacing(2)
        self.sockets_layout.setColumnStretch(0, 1)
        self.sockets_layout.setColumnStretch(1, 1)
        self.main_layout.addLayout(self.sockets_layout)

        # ---------------- Content Layout ----------------
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 2, 0, 0)
        self.content_layout.setSpacing(5)
        self.main_layout.addLayout(self.content_layout, 1)

        # ---------------- Bottom Bar (Resize Handle) ----------------
        self.bottom_bar = QHBoxLayout()
        self.bottom_bar.setContentsMargins(0, 0, 0, 0)
        self.bottom_bar.addStretch()
        self.resize_handle = ComfyResizeHandle(self, self)
        self.bottom_bar.addWidget(self.resize_handle)
        self.main_layout.addLayout(self.bottom_bar)

        self.inputs = {}
        self.outputs = {}

    def set_title(self, title: str):
        self.title_text = title
        if hasattr(self, 'title_lbl') and self.title_lbl:
            self.title_lbl.setText(title)

    def add_input_socket(self, name: str, socket_type: str):
        row = ComfySocketRow(name, socket_type, is_output=False, parent=self)
        r = len(self.inputs)
        self.sockets_layout.addWidget(row, r, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.inputs[name] = row
        return row

    def add_output_socket(self, name: str, socket_type: str):
        row = ComfySocketRow(name, socket_type, is_output=True, parent=self)
        r = len(self.outputs)
        self.sockets_layout.addWidget(row, r, 1, Qt.AlignRight | Qt.AlignVCenter)
        self.outputs[name] = row
        return row

    def retranslate_sockets(self):
        for row in self.inputs.values():
            row.retranslate_ui()
        for row in self.outputs.values():
            row.retranslate_ui()

    def get_input_pin_center_in_canvas(self, name: str) -> QPointF:
        row = self.inputs.get(name)
        if row and row.pin and row.isVisible():
            try:
                pt = row.pin.mapTo(self.canvas, QPoint(5, 5))
                if self.x() <= pt.x() <= self.x() + 40 and pt.y() >= self.y() + 28:
                    return QPointF(pt.x(), pt.y())
            except Exception:
                pass
        idx = list(self.inputs.keys()).index(name) if name in self.inputs else 0
        return QPointF(self.x() + 15, self.y() + 46 + idx * 20)

    def get_output_pin_center_in_canvas(self, name: str) -> QPointF:
        row = self.outputs.get(name)
        if row and row.pin and row.isVisible():
            try:
                pt = row.pin.mapTo(self.canvas, QPoint(5, 5))
                if pt.x() >= self.x() + self.width() - 40 and pt.y() >= self.y() + 28:
                    return QPointF(pt.x(), pt.y())
            except Exception:
                pass
        idx = list(self.outputs.keys()).index(name) if name in self.outputs else 0
        return QPointF(self.x() + self.width() - 15, self.y() + 46 + idx * 20)

    # Dragging by header
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            header_rect = self.header_widget.geometry()
            if header_rect.contains(event.pos()):
                self._dragging = True
                self._drag_start_pos = event.globalPosition().toPoint()
                self._start_node_pos = self.pos()
                self.raise_()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            new_pos = self._start_node_pos + delta
            new_x = max(10, new_pos.x())
            new_y = max(10, new_pos.y())
            self.move(new_x, new_y)
            self.canvas.update()
            view = getattr(self.canvas, "view_parent", None)
            if view and hasattr(view, "adjust_canvas_size"):
                view.adjust_canvas_size()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.canvas.update()
        super().mouseReleaseEvent(event)


# ==============================================================================
# 6. COMFYUI NODE GRAPH CANVAS (ComfyGraphCanvas)
# ==============================================================================
class ComfyGraphCanvas(QWidget):
    """
    Interactive dark graph canvas matching ComfyUI:
    - Subtle dot grid background
    - Dynamic cubic bezier splines with shadow and anti-aliasing
    - Hosts interactive ComfyNodes
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ComfyGraphCanvas")
        self.setMinimumSize(1400, 750)
        self.wires = []
        self.setAcceptDrops(True)

    def set_wires(self, wire_defs: list):
        """
        wire_defs: list of tuples: (start_node, start_output_name, end_node, end_input_name, color_hex)
        """
        self.wires = wire_defs
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        # 1. Canvas background
        painter.fillRect(self.rect(), QColor(COMFY_COLORS["CANVAS_BG"]))

        # 2. Subtle dot grid
        grid_step = 20
        dot_color = QColor(COMFY_COLORS["CANVAS_DOT"])
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(dot_color))
        w = self.width()
        h = self.height()
        for x in range(10, w, grid_step):
            for y in range(10, h, grid_step):
                painter.drawRect(x, y, 1, 1)

        # 3. Draw Bezier Wires
        for start_node, out_name, end_node, in_name, color_hex in self.wires:
            if not start_node or not end_node or start_node.isHidden() or end_node.isHidden():
                continue
            try:
                p1 = start_node.get_output_pin_center_in_canvas(out_name)
                p2 = end_node.get_input_pin_center_in_canvas(in_name)
                self._draw_comfy_bezier(painter, p1, p2, QColor(color_hex), start_node, end_node)
            except Exception as e:
                pass

    def _draw_comfy_bezier(self, painter: QPainter, p1: QPointF, p2: QPointF, color: QColor, start_node=None, end_node=None):
        painter.setBrush(Qt.NoBrush)
        path = QPainterPath()
        path.moveTo(p1)

        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()

        if dx >= 0:
            # Forward connection: natural proportional curve
            h = max(40.0, dx * 0.45)
            c1 = QPointF(p1.x() + h, p1.y())
            c2 = QPointF(p2.x() - h, p2.y())
        else:
            # Backward connection (LiteGraph / ComfyUI style):
            # Soft, strictly clamped curve that prevents unsightly huge bulging loops
            h = max(35.0, min(90.0, max(abs(dx) * 0.35, abs(dy) * 0.35)))
            c1 = QPointF(p1.x() + h, p1.y())
            c2 = QPointF(p2.x() - h, p2.y())

        path.cubicTo(c1, c2, p2)

        # Soft shadow / glow
        shadow_pen = QPen(QColor(0, 0, 0, 160), 4.5)
        shadow_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(shadow_pen)
        painter.drawPath(path)

        # Main wire line
        wire_pen = QPen(color, 2.5)
        wire_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(wire_pen)
        painter.drawPath(path)


# ==============================================================================
# 7. WORKFLOW BUILDER VIEW (Main ComfyUI Canvas & Controller)
# ==============================================================================
class WorkflowBuilderView(QWidget):
    """
    Workflow Builder & Parameter Mapper matching ComfyUI interface:
      - 5-Column Node Flow (Checkpoint, LoRA/Image, Prompts, KSampler, VAE Decode & Save Image)
      - Interactive ComfyUI Node Cards with colored pins and bezier cables
      - Multi-LoRA visual and functional chaining
      - Mode-sensitive nodes: in Txt2Img, LoadImage/VAEEncode are cleanly hidden,
        EmptyLatentImage is connected to KSampler. In Img2Img, LoadImage/VAEEncode
        are connected to KSampler.
      - VAE Decode is connected to Save Image (Görüntüyü Kaydet)
      - Top Bar: Title, Txt2Img / Img2Img segmented toggle, Reset Layout button
      - Bottom Bar: Live summary status, JSON export and ComfyUI PNG export
      - Full backward compatibility with all test assertions and VeraNote features
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WorkflowBuilderViewWidget")
        self.installed_loras = []
        self.installed_ckpts = []
        self.lora_rows = []
        self.extra_lora_nodes = []
        self.mode = "txt2img"
        self.palette = {}

        self.init_palette()
        self.init_ui()
        self.load_models_from_db()
        self.reset_nodes_layout()
        self.update_status_summary()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ==========================================
        # 1. TOP HEADER BAR
        # ==========================================
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background-color: #1A1A1A; border-bottom: 1px solid #2B2B2B;")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(18, 6, 18, 6)
        top_bar_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)

        self.title_label = QLabel(t("workflow_builder_title"))
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #FFFFFF;")

        self.desc_label = QLabel(t("workflow_builder_desc"))
        self.desc_label.setStyleSheet("color: #888888; font-size: 11px;")

        title_col.addWidget(self.title_label)
        title_col.addWidget(self.desc_label)

        # Mode Selector Capsule (Txt2Img / Img2Img)
        self.mode_container = QFrame()
        self.mode_container.setObjectName("ModeToggleContainer")
        self.mode_container.setStyleSheet("""
            #ModeToggleContainer {
                background-color: #242424;
                border: 1px solid #383838;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        mode_layout = QHBoxLayout(self.mode_container)
        mode_layout.setContentsMargins(2, 2, 2, 2)
        mode_layout.setSpacing(2)

        self.txt2img_btn = QPushButton(t("builder_mode_txt2img"))
        self.txt2img_btn.setObjectName("ModeTxtBtn")
        self.txt2img_btn.setFixedHeight(26)
        self.txt2img_btn.setCursor(Qt.PointingHandCursor)
        self.txt2img_btn.setProperty("active", True)
        self.txt2img_btn.clicked.connect(lambda: self.set_mode("txt2img"))

        self.img2img_btn = QPushButton(t("builder_mode_img2img"))
        self.img2img_btn.setObjectName("ModeImgBtn")
        self.img2img_btn.setFixedHeight(26)
        self.img2img_btn.setCursor(Qt.PointingHandCursor)
        self.img2img_btn.setProperty("active", False)
        self.img2img_btn.clicked.connect(lambda: self.set_mode("img2img"))

        mode_layout.addWidget(self.txt2img_btn)
        mode_layout.addWidget(self.img2img_btn)

        # Reset Layout Button
        self.reset_layout_btn = QPushButton(t("builder_reset_layout"))
        self.reset_layout_btn.setFixedHeight(28)
        self.reset_layout_btn.setCursor(Qt.PointingHandCursor)
        self.reset_layout_btn.setStyleSheet("""
            QPushButton {
                background-color: #242424;
                color: #C0C0C0;
                border: 1px solid #383838;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2E2E2E;
                color: #FFFFFF;
                border-color: #8AB4F8;
            }
        """)
        self.reset_layout_btn.clicked.connect(self.reset_nodes_layout)

        top_bar_layout.addLayout(title_col)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.reset_layout_btn)
        top_bar_layout.addWidget(self.mode_container)

        root_layout.addWidget(top_bar)

        # ==========================================
        # 2. SCROLLABLE GRAPH CANVAS
        # ==========================================
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background-color: #181818; border: none;")

        self.canvas = ComfyGraphCanvas(self)
        self.canvas.view_parent = self
        self.scroll_area.setWidget(self.canvas)
        root_layout.addWidget(self.scroll_area, 1)

        # Build ComfyUI Nodes onto canvas
        self._build_nodes()

        # ==========================================
        # 3. BOTTOM FOOTER BAR
        # ==========================================
        self.footer_bar = QWidget()
        self.footer_bar.setObjectName("BuilderFooterBar")
        self.footer_bar.setFixedHeight(48)
        footer_layout = QHBoxLayout(self.footer_bar)
        footer_layout.setContentsMargins(18, 6, 18, 6)
        footer_layout.setSpacing(12)

        self.status_summary_lbl = QLabel()
        self.status_summary_lbl.setObjectName("BuilderStatusLabel")

        self.export_json_btn = QPushButton(f"  {t('export_json')}")
        self.export_json_btn.setObjectName("ExportJsonBtn")
        self.export_json_btn.setFixedHeight(34)
        self.export_json_btn.setCursor(Qt.PointingHandCursor)
        self.export_json_btn.clicked.connect(self.on_export_json_clicked)

        self.export_png_btn = QPushButton(f"  {t('export_png')}")
        self.export_png_btn.setObjectName("ExportPngBtn")
        self.export_png_btn.setFixedHeight(34)
        self.export_png_btn.setCursor(Qt.PointingHandCursor)
        self.export_png_btn.clicked.connect(self.on_export_png_clicked)

        footer_layout.addWidget(self.status_summary_lbl)
        footer_layout.addStretch()
        footer_layout.addWidget(self.export_json_btn)
        footer_layout.addWidget(self.export_png_btn)

        root_layout.addWidget(self.footer_bar)

        # Apply active user theme colors across all controls and footer
        self.apply_theme(self.palette)

        # Backward compatibility fallbacks
        self.lora_strength_spin = ModernSpinBox(1.0, 0.0, 2.0, 0.05, 2, parent=self)
        self.lora_strength_spin.setVisible(False)
        self.schema_layout = QHBoxLayout()

    # ==========================================================================
    # BUILD INDIVIDUAL COMFYUI NODES
    # ==========================================================================
    def _build_nodes(self):
        # ----------------------------------------------------
        # 1. NODE: Kontrol Noktası Yükle (Load Checkpoint)
        # ----------------------------------------------------
        self.node_ckpt = ComfyNode(t("node_load_checkpoint"), self.canvas)
        self.node_ckpt.setMinimumSize(280, 140)
        self.node_ckpt.add_output_socket("MODEL", "MODEL")
        self.node_ckpt.add_output_socket("CLIP", "CLIP")
        self.node_ckpt.add_output_socket("VAE", "VAE")

        self.ckpt_combo = QComboBox()
        self.ckpt_combo.setEditable(True)
        self.ckpt_combo.setFixedHeight(28)
        self.ckpt_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.ckpt_combo.setMinimumContentsLength(8)
        self.ckpt_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 8px;
            }}
        """)
        self.ckpt_combo.currentTextChanged.connect(self.update_status_summary)
        self.node_ckpt.content_layout.addWidget(self.ckpt_combo)

        # ----------------------------------------------------
        # 2. NODE: LoRA Yükle (Primary LoRA 1)
        # ----------------------------------------------------
        self.node_lora = ComfyNode(t("node_load_lora"), self.canvas)
        self.node_lora.setMinimumSize(280, 190)
        self.node_lora.add_input_socket("model", "MODEL")
        self.node_lora.add_input_socket("clip", "CLIP")
        self.node_lora.add_output_socket("MODEL", "MODEL")
        self.node_lora.add_output_socket("CLIP", "CLIP")

        # Header action to add more LoRAs
        self.add_lora_btn = QPushButton(t("add_lora_btn"))
        self.add_lora_btn.setFixedHeight(18)
        self.add_lora_btn.setCursor(Qt.PointingHandCursor)
        self.add_lora_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #4ADE80;
                color: #4ADE80;
                border-radius: 9px;
                padding: 1px 8px;
                font-size: 9px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(74, 222, 128, 0.2);
            }
        """)
        self.add_lora_btn.clicked.connect(lambda: self.add_lora_row())
        self.node_lora.header_widget.layout().addWidget(self.add_lora_btn)

        # Primary LoRA name selector
        self.lora_combo = QComboBox()
        self.lora_combo.setEditable(True)
        self.lora_combo.setFixedHeight(28)
        self.lora_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.lora_combo.setMinimumContentsLength(8)
        self.lora_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 8px;
            }}
        """)
        self.lora_combo.addItem(t("no_lora_model_only"))
        self.lora_combo.currentIndexChanged.connect(self.on_default_lora_changed)
        self.lora_combo.currentTextChanged.connect(lambda _: self.on_default_lora_changed(0))
        self.node_lora.content_layout.addWidget(self.lora_combo)

        # Primary LoRA strength spinners (matching ComfyUI screenshot)
        self.lora_model_spin = ModernSpinBox(1.0, -5.0, 5.0, 0.05, 2, t("tag_model_strength"), self.node_lora)
        self.lora_model_spin.valueChanged.connect(self.update_status_summary)
        self.lora_clip_spin = ModernSpinBox(1.0, -5.0, 5.0, 0.05, 2, t("tag_clip_strength"), self.node_lora)
        self.lora_clip_spin.valueChanged.connect(self.update_status_summary)

        self.node_lora.content_layout.addWidget(self.lora_model_spin)
        self.node_lora.content_layout.addWidget(self.lora_clip_spin)

        # ----------------------------------------------------
        # 3. NODE: Görüntü Yükle (Load Image - Img2Img)
        # ----------------------------------------------------
        self.node_image = ComfyNode(t("node_load_image"), self.canvas)
        self.node_image.setMinimumSize(280, 250)
        self.node_image.add_output_socket("GÖRÜNTÜ", "IMAGE")
        self.node_image.add_output_socket("MASKE", "MASK")

        self.drop_area = ImageDropArea(self.node_image)
        self.drop_area.image_loaded.connect(self.on_image_loaded)
        self.drop_area.metadata_detected.connect(self.on_metadata_detected)
        self.node_image.content_layout.addWidget(self.drop_area)

        # ----------------------------------------------------
        # 4. NODE: VAE Kodlama (VAE Encode - Img2Img)
        # ----------------------------------------------------
        self.node_vae_enc = ComfyNode(t("node_vae_encode"), self.canvas)
        self.node_vae_enc.setMinimumSize(260, 110)
        self.node_vae_enc.add_input_socket("pikseller", "IMAGE")
        self.node_vae_enc.add_input_socket("vae", "VAE")
        self.node_vae_enc.add_output_socket("GİZLİ", "LATENT")

        self.enc_info = QLabel(t("vae_encode_desc"))
        enc_info = self.enc_info
        enc_info.setStyleSheet("color: #888888; font-size: 10px; font-style: italic; padding: 4px;")
        enc_info.setAlignment(Qt.AlignCenter)
        self.node_vae_enc.content_layout.addWidget(enc_info)

        # ----------------------------------------------------
        # 5. NODE: Boş Gizli Görüntü (Empty Latent Image - Txt2Img)
        # ----------------------------------------------------
        self.node_empty_latent = ComfyNode(t("node_empty_latent"), self.canvas)
        self.node_empty_latent.setMinimumSize(280, 170)
        self.node_empty_latent.add_output_socket("GİZLİ", "LATENT")

        # Preset selector
        self.preset_combo = QComboBox()
        self.preset_combo.setFixedHeight(28)
        self.preset_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.preset_combo.setMinimumContentsLength(8)
        self.preset_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 8px;
            }}
        """)
        self._populate_presets()
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.node_empty_latent.content_layout.addWidget(self.preset_combo)

        self.width_spin = ModernSpinBox(1024, 64, 4096, 64, 0, t("tag_width"), self.node_empty_latent)
        self.width_spin.valueChanged.connect(self.on_dimension_changed)

        self.height_spin = ModernSpinBox(1024, 64, 4096, 64, 0, t("tag_height"), self.node_empty_latent)
        self.height_spin.valueChanged.connect(self.on_dimension_changed)

        self.node_empty_latent.content_layout.addWidget(self.width_spin)
        self.node_empty_latent.content_layout.addWidget(self.height_spin)

        # ----------------------------------------------------
        # 6. NODE: CLIP Text Encode (Positive)
        # ----------------------------------------------------
        self.node_pos = ComfyNode(t("node_clip_positive"), self.canvas)
        self.node_pos.setMinimumSize(320, 160)
        self.node_pos.add_input_socket("clip", "CLIP")
        self.node_pos.add_output_socket("KOŞULLANDIRMA", "CONDITIONING")

        self.pos_lbl = QLabel(t("positive_prompt"))
        self.pos_lbl.setStyleSheet("color: #4ADE80; font-size: 11px; font-weight: bold;")
        self.pos_edit = QPlainTextEdit()
        self.pos_edit.setObjectName("PositivePromptEdit")
        self.pos_edit.setPlaceholderText(t("pos_prompt_placeholder"))
        self.pos_edit.setMinimumHeight(80)
        self.pos_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pos_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 6px;
            }}
            QPlainTextEdit:focus {{
                border-color: #4ADE80;
            }}
        """)
        self.node_pos.content_layout.addWidget(self.pos_lbl)
        self.node_pos.content_layout.addWidget(self.pos_edit, 1)

        # ----------------------------------------------------
        # 7. NODE: CLIP Text Encode (Negative)
        # ----------------------------------------------------
        self.node_neg = ComfyNode(t("node_clip_negative"), self.canvas)
        self.node_neg.setMinimumSize(320, 140)
        self.node_neg.add_input_socket("clip", "CLIP")
        self.node_neg.add_output_socket("KOŞULLANDIRMA", "CONDITIONING")

        self.neg_lbl = QLabel(t("negative_prompt"))
        self.neg_lbl.setStyleSheet("color: #F87171; font-size: 11px; font-weight: bold;")
        self.neg_edit = QPlainTextEdit()
        self.neg_edit.setObjectName("NegativePromptEdit")
        self.neg_edit.setPlaceholderText(t("neg_prompt_placeholder"))
        self.neg_edit.setMinimumHeight(65)
        self.neg_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.neg_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #FFFFFF;
                font-size: 11px;
                padding: 6px;
            }}
            QPlainTextEdit:focus {{
                border-color: #F87171;
            }}
        """)
        self.node_neg.content_layout.addWidget(self.neg_lbl)
        self.node_neg.content_layout.addWidget(self.neg_edit, 1)

        # ----------------------------------------------------
        # 8. NODE: KSampler
        # ----------------------------------------------------
        self.node_ksampler = ComfyNode(t("node_ksampler"), self.canvas)
        self.node_ksampler.setMinimumSize(310, 370)
        self.node_ksampler.add_input_socket("model", "MODEL")
        self.node_ksampler.add_input_socket("pozitif", "CONDITIONING")
        self.node_ksampler.add_input_socket("negatif", "CONDITIONING")
        self.node_ksampler.add_input_socket("gizli_görüntü", "LATENT")
        self.node_ksampler.add_output_socket("GİZLİ", "LATENT")

        # Seed widget
        seed_frame = QFrame()
        seed_frame.setFixedHeight(28)
        seed_frame.setStyleSheet(f"""
            background-color: {COMFY_COLORS['WIDGET_BG']};
            border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
            border-radius: 4px;
        """)
        s_layout = QHBoxLayout(seed_frame)
        s_layout.setContentsMargins(6, 1, 4, 1)
        s_layout.setSpacing(6)

        self.seed_lbl = QLabel(t("tag_seed"))
        seed_lbl = self.seed_lbl
        seed_lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: 500;")

        self.seed_edit = QLineEdit()
        self.seed_edit.setText(str(random.randint(1000000000, 9999999999)))
        self.seed_edit.setAlignment(Qt.AlignRight)
        self.seed_edit.setStyleSheet("background: transparent; border: none; color: #E3E3E3; font-size: 11px; font-weight: bold;")

        self.rand_btn = QPushButton()
        self.rand_btn.setIcon(get_icon("refresh", "#DCDCDC", 13))
        self.rand_btn.setFixedSize(22, 22)
        self.rand_btn.setCursor(Qt.PointingHandCursor)
        self.rand_btn.setToolTip(t("tooltip_random_seed"))
        self.rand_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COMFY_COLORS['NODE_HEADER_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                padding: 1px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
                border-color: #8AB4F8;
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        self.rand_btn.clicked.connect(self.generate_random_seed)

        s_layout.addWidget(seed_lbl)
        s_layout.addWidget(self.seed_edit, 1)
        s_layout.addWidget(self.rand_btn)
        self.node_ksampler.content_layout.addWidget(seed_frame)

        # Steps, CFG, Denoise Steppers with generous room
        self.steps_spin = ModernSpinBox(20, 1, 150, 1, 0, t("tag_steps"), self.node_ksampler)
        self.cfg_spin = ModernSpinBox(4.0, 1.0, 30.0, 0.5, 1, t("tag_cfg"), self.node_ksampler)
        self.denoise_spin = ModernSpinBox(1.00, 0.0, 1.0, 0.05, 2, t("tag_denoise"), self.node_ksampler)

        # Sampler combo
        sampler_box = QHBoxLayout()
        sampler_box.setSpacing(6)
        self.s_lbl = QLabel(t("tag_sampler"))
        s_lbl = self.s_lbl
        s_lbl.setFixedWidth(82)
        s_lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: 500;")

        self.sampler_combo = QComboBox()
        self.sampler_combo.setFixedHeight(28)
        self.sampler_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.sampler_combo.setMinimumContentsLength(8)
        self.sampler_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 8px;
            }}
        """)
        self.sampler_combo.addItems([
            "dpmpp_2m", "euler", "euler_ancestral", "dpmpp_2m_sde",
            "dpmpp_sde", "dpm_2", "ddim", "uni_pc"
        ])
        sampler_box.addWidget(s_lbl)
        sampler_box.addWidget(self.sampler_combo, 1)

        # Scheduler combo
        sched_box = QHBoxLayout()
        sched_box.setSpacing(6)
        self.sc_lbl = QLabel(t("tag_scheduler"))
        sc_lbl = self.sc_lbl
        sc_lbl.setFixedWidth(82)
        sc_lbl.setStyleSheet("color: #888888; font-size: 11px; font-weight: 500;")

        self.sched_combo = QComboBox()
        self.sched_combo.setFixedHeight(28)
        self.sched_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.sched_combo.setMinimumContentsLength(8)
        self.sched_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COMFY_COLORS['WIDGET_BG']};
                border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
                border-radius: 4px;
                color: #DCDCDC;
                font-size: 11px;
                padding: 1px 8px;
            }}
        """)
        self.sched_combo.addItems([
            "normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform"
        ])
        sched_box.addWidget(sc_lbl)
        sched_box.addWidget(self.sched_combo, 1)

        self.node_ksampler.content_layout.addWidget(self.steps_spin)
        self.node_ksampler.content_layout.addWidget(self.cfg_spin)
        self.node_ksampler.content_layout.addLayout(sampler_box)
        self.node_ksampler.content_layout.addLayout(sched_box)
        self.node_ksampler.content_layout.addWidget(self.denoise_spin)

        # ----------------------------------------------------
        # 9. NODE: VAE Kod Çözme (VAE Decode)
        # ----------------------------------------------------
        self.node_vae_dec = ComfyNode(t("node_vae_decode"), self.canvas)
        self.node_vae_dec.setMinimumSize(260, 110)
        self.node_vae_dec.add_input_socket("örnekler", "LATENT")
        self.node_vae_dec.add_input_socket("vae", "VAE")
        self.node_vae_dec.add_output_socket("GÖRÜNTÜ", "IMAGE")

        self.dec_info = QLabel(t("vae_decode_desc"))
        dec_info = self.dec_info
        dec_info.setStyleSheet("color: #888888; font-size: 10px; font-style: italic; padding: 4px;")
        dec_info.setAlignment(Qt.AlignCenter)
        self.node_vae_dec.content_layout.addWidget(dec_info)

        # ----------------------------------------------------
        # 10. NODE: Görüntüyü Kaydet (Save Image)
        # ----------------------------------------------------
        self.node_save_img = ComfyNode(t("node_save_image"), self.canvas)
        self.node_save_img.setMinimumSize(260, 210)
        self.node_save_img.add_input_socket("görüntüler", "IMAGE")

        save_prefix_box = QHBoxLayout()
        save_prefix_box.setSpacing(6)
        self.prefix_lbl = QLabel(t("tag_prefix"))
        prefix_lbl = self.prefix_lbl
        prefix_lbl.setFixedWidth(85)
        prefix_lbl.setStyleSheet("color: #888888; font-size: 10px; font-weight: 500;")
        self.prefix_edit = QLineEdit("VeraNote")
        self.prefix_edit.setFixedHeight(24)
        self.prefix_edit.setStyleSheet(f"""
            background-color: {COMFY_COLORS['WIDGET_BG']};
            border: 1px solid {COMFY_COLORS['WIDGET_BORDER']};
            border-radius: 4px;
            color: #DCDCDC;
            font-size: 11px;
            padding: 1px 6px;
        """)
        save_prefix_box.addWidget(prefix_lbl)
        save_prefix_box.addWidget(self.prefix_edit, 1)
        self.node_save_img.content_layout.addLayout(save_prefix_box)

        # Result preview box
        self.save_preview_frame = QFrame()
        self.save_preview_frame.setStyleSheet(f"""
            background-color: {COMFY_COLORS['WIDGET_BG']};
            border: 1px dashed {COMFY_COLORS['WIDGET_BORDER']};
            border-radius: 4px;
        """)
        self.save_preview_frame.setMinimumHeight(100)
        sp_layout = QVBoxLayout(self.save_preview_frame)
        sp_layout.setContentsMargins(4, 4, 4, 4)
        sp_layout.setAlignment(Qt.AlignCenter)

        save_icon = QLabel()
        save_icon.setAlignment(Qt.AlignCenter)
        save_icon.setPixmap(get_pixmap("image", "#444444", 32))
        self.save_hint = QLabel(t("image_output_hint"))
        save_hint = self.save_hint
        save_hint.setAlignment(Qt.AlignCenter)
        save_hint.setStyleSheet("color: #666666; font-size: 10px; font-weight: bold;")
        sp_layout.addWidget(save_icon)
        sp_layout.addWidget(save_hint)
        self.node_save_img.content_layout.addWidget(self.save_preview_frame)

    # ==========================================================================
    # LAYOUT AND WIRE ROUTING
    # ==========================================================================
    def reset_nodes_layout(self):
        """Arranges nodes according to the authentic ComfyUI compact 5-column layout."""
        is_txt = (self.mode == "txt2img")

        # Col 1 (x = 20, w = 280): Checkpoint (top), Latent / Image (bottom)
        self.node_ckpt.setGeometry(20, 30, 280, 140)

        if is_txt:
            # In Txt2Img: EmptyLatent is in Column 1 below Checkpoint
            self.node_empty_latent.setGeometry(20, 190, 280, 170)
            self.node_image.setHidden(True)
            self.node_vae_enc.setHidden(True)
            self.node_empty_latent.setHidden(False)
        else:
            # In Img2Img: LoadImage is in Column 1 below Checkpoint
            self.node_image.setGeometry(20, 190, 280, 260)
            self.node_image.setHidden(False)
            self.node_empty_latent.setHidden(True)
            self.node_vae_enc.setHidden(False)

        # Col 2 (x = 320, w = 280): LoRA 1 (top), VAE Encode in img2img (bottom)
        self.node_lora.setGeometry(320, 30, 280, 190)

        if not is_txt:
            self.node_vae_enc.setGeometry(320, 240, 280, 115)

        # Extra chained LoRA nodes placement
        extra_start_y = 240 if is_txt else 375
        for i, extra_node in enumerate(self.extra_lora_nodes):
            y_offset = extra_start_y + (i * 205)
            extra_node.setGeometry(320, y_offset, 280, 190)

        # Col 3 (x = 620, w = 350): Positive Prompt (top), Negative Prompt (bottom)
        self.node_pos.setGeometry(620, 30, 350, 210)
        self.node_neg.setGeometry(620, 260, 350, 180)

        # Col 4 (x = 990, w = 310): KSampler
        self.node_ksampler.setGeometry(990, 30, 310, 370)

        # Col 5 (x = 1320, w = 270): VAE Decode (top), Save Image (bottom)
        self.node_vae_dec.setGeometry(1320, 30, 270, 120)
        self.node_save_img.setGeometry(1320, 170, 270, 230)

        # Dynamically ensure canvas expands to accommodate extra LoRAs
        max_y = max(450, extra_start_y + len(self.extra_lora_nodes) * 205 + 40)
        self.canvas.setMinimumSize(1650, max(750, max_y))

        self.update_schema_display()

    def adjust_canvas_size(self):
        """Dynamically expands canvas minimum size so dragged/resized nodes never clip."""
        max_r = 1500
        max_b = 750
        for child in self.canvas.findChildren(ComfyNode):
            if child and not child.isHidden():
                max_r = max(max_r, child.x() + child.width() + 60)
                max_b = max(max_b, child.y() + child.height() + 60)
        if max_r != self.canvas.minimumWidth() or max_b != self.canvas.minimumHeight():
            self.canvas.setMinimumSize(max_r, max_b)

    def update_schema_display(self):
        """Dynamically computes all connecting bezier wires matching the active state."""
        wires = []

        # 1. Model & Clip Wiring with Multi-LoRA Chaining (Primary LoRA + chained extra LoRAs)
        active_lora_nodes = [self.node_lora]
        for en in self.extra_lora_nodes:
            if not en.isHidden():
                active_lora_nodes.append(en)

        # Checkpoint -> first LoRA
        wires.append((self.node_ckpt, "MODEL", active_lora_nodes[0], "model", COMFY_COLORS["MODEL"]))
        wires.append((self.node_ckpt, "CLIP", active_lora_nodes[0], "clip", COMFY_COLORS["CLIP"]))
        # Chain intermediate LoRAs
        for i in range(len(active_lora_nodes) - 1):
            wires.append((active_lora_nodes[i], "MODEL", active_lora_nodes[i+1], "model", COMFY_COLORS["MODEL"]))
            wires.append((active_lora_nodes[i], "CLIP", active_lora_nodes[i+1], "clip", COMFY_COLORS["CLIP"]))
        # Last LoRA -> KSampler and Prompts
        last_lora = active_lora_nodes[-1]
        wires.append((last_lora, "MODEL", self.node_ksampler, "model", COMFY_COLORS["MODEL"]))
        wires.append((last_lora, "CLIP", self.node_pos, "clip", COMFY_COLORS["CLIP"]))
        wires.append((last_lora, "CLIP", self.node_neg, "clip", COMFY_COLORS["CLIP"]))

        # 2. Latent Image Wiring (Txt2Img vs Img2Img)
        if self.mode == "img2img":
            self.node_image.setHidden(False)
            self.node_vae_enc.setHidden(False)
            self.node_empty_latent.setHidden(True)
            wires.append((self.node_image, "GÖRÜNTÜ", self.node_vae_enc, "pikseller", COMFY_COLORS["IMAGE"]))
            wires.append((self.node_ckpt, "VAE", self.node_vae_enc, "vae", COMFY_COLORS["VAE"]))
            wires.append((self.node_vae_enc, "GİZLİ", self.node_ksampler, "gizli_görüntü", COMFY_COLORS["LATENT"]))
        else:
            self.node_image.setHidden(True)
            self.node_vae_enc.setHidden(True)
            self.node_empty_latent.setHidden(False)
            wires.append((self.node_empty_latent, "GİZLİ", self.node_ksampler, "gizli_görüntü", COMFY_COLORS["LATENT"]))

        # 3. Conditioning Wiring (Prompts -> KSampler)
        wires.append((self.node_pos, "KOŞULLANDIRMA", self.node_ksampler, "pozitif", COMFY_COLORS["CONDITIONING"]))
        wires.append((self.node_neg, "KOŞULLANDIRMA", self.node_ksampler, "negatif", COMFY_COLORS["CONDITIONING"]))

        # 4. VAE Decode Wiring
        wires.append((self.node_ksampler, "GİZLİ", self.node_vae_dec, "örnekler", COMFY_COLORS["LATENT"]))
        wires.append((self.node_ckpt, "VAE", self.node_vae_dec, "vae", COMFY_COLORS["VAE"]))

        # 5. Save Image Wiring (VAE Decode -> Save Image)
        wires.append((self.node_vae_dec, "GÖRÜNTÜ", self.node_save_img, "görüntüler", COMFY_COLORS["IMAGE"]))

        self.canvas.set_wires(wires)

    # ==========================================================================
    # MODE TOGGLING & IMAGE HANDLING
    # ==========================================================================
    def set_mode(self, mode: str):
        self.mode = mode
        is_txt = (mode == "txt2img")
        self.txt2img_btn.setProperty("active", is_txt)
        self.img2img_btn.setProperty("active", not is_txt)
        self.txt2img_btn.style().polish(self.txt2img_btn)
        self.img2img_btn.style().polish(self.img2img_btn)
        self._update_mode_buttons_style()

        if is_txt:
            self.denoise_spin.setValue(1.0)
        else:
            if self.denoise_spin.value() >= 1.0:
                self.denoise_spin.setValue(0.75)

        self.reset_nodes_layout()
        self.update_status_summary()

    def on_image_loaded(self, path: str):
        if path:
            self.set_mode("img2img")
            try:
                with Image.open(path) as img:
                    w, h = img.size
                    self.width_spin.setValue(w)
                    self.height_spin.setValue(h)
                    self.preset_combo.setCurrentIndex(self.preset_combo.count() - 1)
            except Exception:
                pass
        self.update_schema_display()
        self.update_status_summary()

    def _populate_presets(self):
        curr_idx = self.preset_combo.currentIndex()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItems([
            t("preset_square_sdxl"),
            t("preset_portrait_sdxl"),
            t("preset_landscape_sdxl"),
            t("preset_portrait_sdxl_2"),
            t("preset_landscape_sdxl_2"),
            t("preset_square_sd15"),
            t("preset_standard_sd15"),
            t("preset_custom")
        ])
        if 0 <= curr_idx < self.preset_combo.count():
            self.preset_combo.setCurrentIndex(curr_idx)
        else:
            self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    def on_preset_changed(self, index: int):
        presets = [
            (1024, 1024),
            (832, 1216),
            (1216, 832),
            (896, 1152),
            (1152, 896),
            (768, 768),
            (512, 512),
        ]
        if 0 <= index < len(presets):
            w, h = presets[index]
            self.width_spin.setValue(w)
            self.height_spin.setValue(h)
        self.update_status_summary()

    def on_dimension_changed(self):
        self.update_status_summary()

    # ==========================================================================
    # LORA MANAGEMENT & VISUAL CHAINING
    # ==========================================================================
    def on_default_lora_changed(self, index: int):
        self.update_schema_display()
        self.update_status_summary()

    def add_lora_row(self, name: str = "", strength_model: float = 1.0, strength_clip: float = 1.0):
        """Adds a new chained LoRA node on the canvas with dedicated sockets and controls."""
        idx = len(self.lora_rows) + 2
        extra_node = ComfyNode(t("node_load_lora_idx").format(idx=idx), self.canvas)
        extra_node.setMinimumSize(280, 190)
        extra_node.add_input_socket("model", "MODEL")
        extra_node.add_input_socket("clip", "CLIP")
        extra_node.add_output_socket("MODEL", "MODEL")
        extra_node.add_output_socket("CLIP", "CLIP")

        row = LoraRowWidget(self.installed_loras, extra_node)
        row.removed.connect(lambda r: self.remove_lora_row(r))
        row.changed.connect(self.on_lora_row_changed)
        if name:
            row.set_lora(name, strength_model, strength_clip)

        extra_node.content_layout.addWidget(row)
        extra_node.row_widget = row
        row.host_node = extra_node

        self.lora_rows.append(row)
        self.extra_lora_nodes.append(extra_node)
        extra_node.show()

        self.reset_nodes_layout()
        self.update_status_summary()
        return row

    def remove_lora_row(self, row_widget):
        """Removes a chained LoRA node from the canvas and reconnects the chain."""
        if row_widget in self.lora_rows:
            self.lora_rows.remove(row_widget)

        host_node = getattr(row_widget, "host_node", None)
        if host_node and host_node in self.extra_lora_nodes:
            self.extra_lora_nodes.remove(host_node)
            host_node.hide()
            host_node.deleteLater()

        self.reset_nodes_layout()
        self.update_status_summary()

    def on_lora_row_changed(self):
        self.update_schema_display()
        self.update_status_summary()

    def get_loras_data(self) -> list[dict]:
        results = []
        no_lora_placeholders = (
            "LoRA eklenmedi (yalnızca model)",
            "LoRA eklenmedi (yalnizca model)",
            "No LoRA added (model only)",
            "No LoRA added (only base model used)",
            t("no_lora_model_only"),
            t("no_lora_added"),
            "None",
            "",
        )
        # Primary LoRA
        val = self.lora_combo.currentText().strip()
        if val and val not in no_lora_placeholders:
            results.append({
                "name": val,
                "strength_model": self.lora_model_spin.value(),
                "strength_clip": self.lora_clip_spin.value()
            })

        # Extra chained LoRAs
        for row in self.lora_rows:
            data = row.get_data()
            if data["name"] and data["name"] not in no_lora_placeholders and data["name"].lower() not in ("none", "", "yok", "lora eklenmedi (yalnizca model)", "no lora added (model only)"):
                results.append(data)

        return results

    # ==========================================================================
    # DATA & STATUS SYNCHRONIZATION
    # ==========================================================================
    def update_status_summary(self):
        mode_text = "Txt2Img" if self.mode == "txt2img" else "Img2Img"
        w = self.width_spin.value()
        h = self.height_spin.value()
        loras = self.get_loras_data()
        lora_count = len(loras)
        ckpt_name = os.path.basename(self.ckpt_combo.currentText() or "Model")

        self.status_summary_lbl.setText(
            f"{mode_text} • {w}×{h} • {ckpt_name} • {lora_count} LoRA"
        )

    def load_models_from_db(self, show_hidden: bool = None):
        """Populates Checkpoint and LoRA lists from VeraNote SQLite database."""
        try:
            import database
            if show_hidden is None:
                win = self.window()
                show_hidden = bool(getattr(win, 'incognito_active', False))
                try:
                    import __main__
                    if hasattr(__main__, 'app_instance') and hasattr(__main__.app_instance, 'incognito_active'):
                        show_hidden = show_hidden or bool(__main__.app_instance.incognito_active)
                except Exception:
                    pass

            ckpts = []
            loras = []
            ckpt_set = set()
            lora_set = set()

            if hasattr(database, 'get_all_models_for_builder'):
                rows = database.get_all_models_for_builder(show_hidden=show_hidden)
                for m in rows:
                    name = os.path.basename(m.get('file_path') or m.get('name') or '')
                    if not name:
                        continue
                    lower = (m.get('lib_name') or '').lower()
                    if "checkpoint" in lower:
                        if name not in ckpt_set:
                            ckpt_set.add(name)
                            ckpts.append(name)
                    elif "lora" in lower:
                        if name not in lora_set:
                            lora_set.add(name)
                            loras.append(name)
                    else:
                        if "lora" in name.lower():
                            if name not in lora_set:
                                lora_set.add(name)
                                loras.append(name)
                        else:
                            if name not in ckpt_set:
                                ckpt_set.add(name)
                                ckpts.append(name)
            else:
                all_libs = database.get_libraries(lib_type='MODEL')
                for lib_name in all_libs:
                    lower = lib_name.lower()
                    models = database.get_models_in_library(lib_name, show_hidden=show_hidden)
                    for m in models:
                        name = os.path.basename(m.get('file_path') or m.get('name') or '')
                        if not name:
                            continue
                        if "checkpoint" in lower:
                            if name not in ckpt_set:
                                ckpt_set.add(name)
                                ckpts.append(name)
                        elif "lora" in lower:
                            if name not in lora_set:
                                lora_set.add(name)
                                loras.append(name)
                        else:
                            if "lora" in name.lower():
                                if name not in lora_set:
                                    lora_set.add(name)
                                    loras.append(name)
                            else:
                                if name not in ckpt_set:
                                    ckpt_set.add(name)
                                    ckpts.append(name)

            if not ckpts:
                ckpts = ["antiNOVA_vacancy_v10.safetensors", "sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly.safetensors"]

            self.installed_ckpts = ckpts
            self.installed_loras = loras

            curr_ckpt = self.ckpt_combo.currentText()
            self.ckpt_combo.blockSignals(True)
            self.ckpt_combo.clear()
            self.ckpt_combo.addItems(ckpts)
            if curr_ckpt:
                idx = self.ckpt_combo.findText(curr_ckpt)
                if idx >= 0:
                    self.ckpt_combo.setCurrentIndex(idx)
                else:
                    self.ckpt_combo.setEditText(curr_ckpt)
            self.ckpt_combo.blockSignals(False)

            curr_lora = self.lora_combo.currentText()
            self.lora_combo.blockSignals(True)
            self.lora_combo.clear()
            self.lora_combo.addItem(t("no_lora_model_only"))
            for item in loras:
                self.lora_combo.addItem(item)
            if curr_lora and curr_lora not in ("LoRA eklenmedi (yalnızca model)", "No LoRA added (model only)", t("no_lora_model_only")):
                idx = self.lora_combo.findText(curr_lora)
                if idx >= 0:
                    self.lora_combo.setCurrentIndex(idx)
                else:
                    self.lora_combo.setEditText(curr_lora)
            self.lora_combo.blockSignals(False)

            for row in self.lora_rows:
                curr_l = row.combo.currentText()
                row.combo.blockSignals(True)
                row.combo.clear()
                row.combo.addItem("None")
                for item in loras:
                    row.combo.addItem(item)
                if curr_l:
                    row.set_lora(curr_l)
                row.combo.blockSignals(False)

            self.update_schema_display()
            self.update_status_summary()

        except Exception as e:
            print(f"Error reading models for builder: {e}")
            if not self.installed_ckpts:
                self.ckpt_combo.addItems(["antiNOVA_vacancy_v10.safetensors"])

    def refresh_models(self, show_hidden: bool = None):
        self.load_models_from_db(show_hidden=show_hidden)

    def generate_random_seed(self):
        self.seed_edit.setText(str(random.randint(1000000000, 9999999999)))

    def on_metadata_detected(self, meta: dict):
        """Automatically fills inputs when a ComfyUI PNG is dropped."""
        if not meta:
            return

        if meta.get('positive_prompt'):
            self.pos_edit.setPlainText(meta['positive_prompt'])
        if meta.get('negative_prompt'):
            self.neg_edit.setPlainText(meta['negative_prompt'])

        params = meta.get('sampler_params', {})
        if 'seed' in params:
            self.seed_edit.setText(str(params['seed']))
        if 'steps' in params:
            try:
                self.steps_spin.setValue(int(params['steps']))
            except (ValueError, TypeError):
                pass
        if 'cfg' in params:
            try:
                self.cfg_spin.setValue(float(params['cfg']))
            except (ValueError, TypeError):
                pass
        if 'denoise' in params:
            try:
                self.denoise_spin.setValue(float(params['denoise']))
            except (ValueError, TypeError):
                pass
        if 'sampler_name' in params:
            idx = self.sampler_combo.findText(str(params['sampler_name']))
            if idx >= 0:
                self.sampler_combo.setCurrentIndex(idx)
        if 'scheduler' in params:
            idx = self.sched_combo.findText(str(params['scheduler']))
            if idx >= 0:
                self.sched_combo.setCurrentIndex(idx)

        # Checkpoints & LoRAs
        models = meta.get('models', [])
        lora_detected = []
        for m in models:
            if m.startswith('LoRA: '):
                lora_name = m.replace('LoRA: ', '').strip()
                lora_detected.append(lora_name)
            else:
                idx = self.ckpt_combo.findText(m)
                if idx >= 0:
                    self.ckpt_combo.setCurrentIndex(idx)
                else:
                    self.ckpt_combo.setEditText(m)

        if lora_detected:
            # Set first LoRA on primary node
            p_idx = self.lora_combo.findText(lora_detected[0])
            if p_idx >= 0:
                self.lora_combo.setCurrentIndex(p_idx)
            else:
                self.lora_combo.addItem(lora_detected[0])
                self.lora_combo.setCurrentIndex(self.lora_combo.count() - 1)

            # Clear extra nodes
            while self.lora_rows:
                self.remove_lora_row(self.lora_rows[0])

            # Add subsequent LoRAs as chained nodes
            for l_name in lora_detected[1:]:
                self.add_lora_row(name=l_name)

        self.update_schema_display()
        win = self.window()
        if win and hasattr(win, 'show_toast'):
            win.show_toast(t("auto_filled_from_image"), "info")

    def get_form_parameters(self) -> dict:
        """Gathers all view inputs into a parameter dictionary."""
        try:
            seed_val = int(self.seed_edit.text().strip())
        except ValueError:
            seed_val = random.randint(1000000000, 9999999999)

        loras_data = self.get_loras_data()
        first_lora = loras_data[0] if loras_data else {}
        first_lora_name = first_lora.get("name", "None")
        first_lora_m = first_lora.get("strength_model", 1.0)
        first_lora_c = first_lora.get("strength_clip", 1.0)

        return {
            "mode": self.mode,
            "image_path": self.drop_area.image_path or "",
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "batch_size": 1,
            "positive_prompt": self.pos_edit.toPlainText().strip(),
            "negative_prompt": self.neg_edit.toPlainText().strip(),
            "checkpoint": self.ckpt_combo.currentText().strip(),
            "loras": loras_data,
            "lora_name": first_lora_name,
            "lora_strength_model": first_lora_m,
            "lora_strength_clip": first_lora_c,
            "seed": seed_val,
            "steps": self.steps_spin.value(),
            "cfg": self.cfg_spin.value(),
            "denoise": self.denoise_spin.value(),
            "sampler_name": self.sampler_combo.currentText().strip(),
            "scheduler": self.sched_combo.currentText().strip()
        }

    # ==========================================================================
    # EXPORT HANDLERS
    # ==========================================================================
    def on_export_json_clicked(self):
        """Generates ComfyUI workflow JSON and saves to disk."""
        try:
            params = self.get_form_parameters()
            workflow, prompt = generate_workflow(params)

            default_name = "comfyui_workflow.json"
            if params.get("image_path"):
                base = os.path.splitext(os.path.basename(params["image_path"]))[0]
                default_name = f"{base}_workflow.json"
            else:
                default_name = f"comfy_{params.get('width', 1024)}x{params.get('height', 1024)}_workflow.json"

            parent_win = self.window() if self.window() else self
            save_path, _ = QFileDialog.getSaveFileName(
                parent_win,
                t("export_json"),
                default_name,
                "JSON Files (*.json)"
            )

            if not save_path:
                return

            success = export_workflow_to_json(save_path, workflow, prompt)
            win = self.window()
            if success:
                if win and hasattr(win, 'show_toast'):
                    win.show_toast(t('export_success_json'), "success")
                elif win and hasattr(win, 'statusBar') and win.statusBar():
                    win.statusBar().showMessage(t('export_success_json'), 3000)
                else:
                    QMessageBox.information(parent_win, t("msg_success_title"), t('export_success_json'))
            else:
                QMessageBox.critical(parent_win, t("msg_copy_error_title"), t("export_json_failed"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            parent_win = self.window() if self.window() else self
            QMessageBox.critical(parent_win, t("msg_copy_error_title"), t("export_json_error").format(error=e))

    def on_export_png_clicked(self):
        """Embeds workflow & prompt metadata into a PNG image."""
        try:
            params = self.get_form_parameters()
            parent_win = self.window() if self.window() else self

            if self.mode == "img2img" and not params.get("image_path"):
                reply = QMessageBox.question(
                    parent_win,
                    t("input_image"),
                    t("export_png_no_img_confirm"),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.drop_area.browse_file()
                    params = self.get_form_parameters()
                    if not params.get("image_path"):
                        return
                else:
                    self.set_mode("txt2img")
                    params = self.get_form_parameters()

            workflow, prompt = generate_workflow(params)

            if params.get("image_path"):
                base_name = os.path.splitext(os.path.basename(params["image_path"]))[0]
                default_out = f"{base_name}_comfy.png"
            else:
                default_out = f"workflow_{params.get('width', 1024)}x{params.get('height', 1024)}_comfy.png"

            save_path, _ = QFileDialog.getSaveFileName(
                parent_win,
                t("export_png"),
                default_out,
                "PNG Images (*.png)"
            )

            if not save_path:
                return

            subtitle = os.path.basename(params.get("checkpoint") or "")
            success = export_workflow_to_png(
                params.get("image_path", ""),
                save_path,
                workflow,
                prompt,
                width=params.get("width", 1024),
                height=params.get("height", 1024),
                subtitle=subtitle
            )

            win = self.window()
            if success:
                if win and hasattr(win, 'show_toast'):
                    win.show_toast(t('export_success_png'), "success")
                elif win and hasattr(win, 'statusBar') and win.statusBar():
                    win.statusBar().showMessage(t('export_success_png'), 3000)
                else:
                    QMessageBox.information(parent_win, t("msg_success_title"), t('export_success_png'))
            else:
                QMessageBox.critical(parent_win, t("msg_copy_error_title"), t("export_png_failed"))
        except Exception as e:
            import traceback
            traceback.print_exc()
            parent_win = self.window() if self.window() else self
            QMessageBox.critical(parent_win, t("msg_copy_error_title"), t("export_png_error").format(error=e))

    def init_palette(self):
        try:
            import database
            theme_name = database.get_setting("theme", "Koyu Gece")
            custom_colors = database.get_setting("custom_theme_colors", "{}")
            self.palette = get_palette(theme_name, custom_colors)
        except Exception:
            self.palette = get_palette("Koyu Gece")

    def _update_mode_buttons_style(self):
        p = self.palette or {}
        accent_color = p.get("accent_color", "#1A73E8")
        accent_hover = p.get("accent_hover", adjust_brightness(accent_color, 0.85))
        text_muted = p.get("text_muted", "#9AA0A6")
        text_main = p.get("text_main", "#E3E3E3")
        bg_input = p.get("bg_input", "#282A2E")

        is_txt = (self.mode == "txt2img")
        self.txt2img_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color if is_txt else 'transparent'};
                color: {'#FFFFFF' if is_txt else text_muted};
                border: none;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {text_main};
                background-color: {accent_hover if is_txt else bg_input};
            }}
        """)
        self.img2img_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color if not is_txt else 'transparent'};
                color: {'#FFFFFF' if not is_txt else text_muted};
                border: none;
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: {text_main};
                background-color: {accent_hover if not is_txt else bg_input};
            }}
        """)

    def apply_theme(self, palette: dict = None):
        """Applies theme palette synchronization to bottom action bar and controls."""
        if palette:
            self.palette = palette
        elif not self.palette:
            self.init_palette()

        p = self.palette or {}
        accent_color = p.get("accent_color", "#1A73E8")
        accent_hover = p.get("accent_hover", adjust_brightness(accent_color, 0.85))
        highlight_color = p.get("highlight_color", p.get("border_focus", accent_color))
        text_main = p.get("text_main", "#E3E3E3")
        text_muted = p.get("text_muted", "#9AA0A6")
        bg_card = p.get("bg_card", "#1A1A1A")
        bg_input = p.get("bg_input", "#282A2E")
        border_color = p.get("border_color", "#2F3136")
        border_focus = p.get("border_focus", highlight_color)

        def is_bright_color(hex_color: str) -> bool:
            hex_color = hex_color.lstrip('#')
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return ((r * 299) + (g * 587) + (b * 114)) / 1000 >= 160
            except Exception:
                return False

        btn_fg = "#000000" if is_bright_color(accent_color) else "#FFFFFF"

        # 1. Footer Bar
        self.footer_bar.setStyleSheet(f"""
            #BuilderFooterBar {{
                background-color: {bg_card};
                border-top: 1px solid {border_color};
            }}
        """)

        # 2. Status Summary Label (e.g. Txt2Img • 1024x1024 • Model • 2 LoRA)
        self.status_summary_lbl.setStyleSheet(f"""
            #BuilderStatusLabel {{
                color: {highlight_color};
                font-size: 12px;
                font-weight: 500;
            }}
        """)

        # 3. JSON Export Button
        self.export_json_btn.setStyleSheet(f"""
            #ExportJsonBtn {{
                background-color: {bg_input};
                color: {text_main};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 0px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            #ExportJsonBtn:hover {{
                background-color: {border_color};
                border-color: {border_focus};
            }}
        """)
        self.export_json_btn.setIcon(get_icon("workflows", text_main, 14))

        # 4. ComfyUI PNG Export Button (Primary Action)
        self.export_png_btn.setStyleSheet(f"""
            #ExportPngBtn {{
                background-color: {accent_color};
                color: {btn_fg};
                border: none;
                border-radius: 6px;
                padding: 0px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            #ExportPngBtn:hover {{
                background-color: {accent_hover};
            }}
        """)
        self.export_png_btn.setIcon(get_icon("upload", btn_fg, 14))

        # 5. Top Mode Buttons & Reset Layout Button
        self.reset_layout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_input};
                color: {text_muted};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 0px 12px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {border_color};
                color: {text_main};
                border-color: {border_focus};
            }}
        """)
        self._update_mode_buttons_style()

        self.canvas.update()
        self.style().polish(self)

    def retranslate_ui(self):
        """Retranslates all text labels when language switches."""
        self.title_label.setText(t("workflow_builder_title"))
        self.desc_label.setText(t("workflow_builder_desc"))
        self.txt2img_btn.setText(f"  {t('builder_mode_txt2img')}")
        self.img2img_btn.setText(f"  {t('builder_mode_img2img')}")
        self.reset_layout_btn.setText(f"  {t('builder_reset_layout')}")

        # Node titles
        if hasattr(self, 'node_ckpt') and self.node_ckpt:
            self.node_ckpt.set_title(t("node_load_checkpoint"))
        if hasattr(self, 'node_lora') and self.node_lora:
            self.node_lora.set_title(t("node_load_lora"))
        if hasattr(self, 'add_lora_btn') and self.add_lora_btn:
            self.add_lora_btn.setText(t("add_lora_btn"))
        if hasattr(self, 'node_image') and self.node_image:
            self.node_image.set_title(t("node_load_image"))
        if hasattr(self, 'node_vae_enc') and self.node_vae_enc:
            self.node_vae_enc.set_title(t("node_vae_encode"))
            if hasattr(self, 'enc_info') and self.enc_info:
                self.enc_info.setText(t("vae_encode_desc"))
        if hasattr(self, 'node_empty_latent') and self.node_empty_latent:
            self.node_empty_latent.set_title(t("node_empty_latent"))
            self._populate_presets()
            self.width_spin.setLabel(t("tag_width"))
            self.height_spin.setLabel(t("tag_height"))
        if hasattr(self, 'node_pos') and self.node_pos:
            self.node_pos.set_title(t("node_clip_positive"))
            self.pos_lbl.setText(t('positive_prompt'))
            self.pos_edit.setPlaceholderText(t("pos_prompt_placeholder"))
        if hasattr(self, 'node_neg') and self.node_neg:
            self.node_neg.set_title(t("node_clip_negative"))
            self.neg_lbl.setText(t('negative_prompt'))
            self.neg_edit.setPlaceholderText(t("neg_prompt_placeholder"))
        if hasattr(self, 'node_ksampler') and self.node_ksampler:
            self.node_ksampler.set_title(t("node_ksampler"))
            if hasattr(self, 'seed_lbl') and self.seed_lbl:
                self.seed_lbl.setText(t("tag_seed"))
            if hasattr(self, 'rand_btn') and self.rand_btn:
                self.rand_btn.setToolTip(t("tooltip_random_seed"))
            self.steps_spin.setLabel(t("tag_steps"))
            self.cfg_spin.setLabel(t("tag_cfg"))
            self.denoise_spin.setLabel(t("tag_denoise"))
            if hasattr(self, 's_lbl') and self.s_lbl:
                self.s_lbl.setText(t("tag_sampler"))
            if hasattr(self, 'sc_lbl') and self.sc_lbl:
                self.sc_lbl.setText(t("tag_scheduler"))
        if hasattr(self, 'node_vae_dec') and self.node_vae_dec:
            self.node_vae_dec.set_title(t("node_vae_decode"))
            if hasattr(self, 'dec_info') and self.dec_info:
                self.dec_info.setText(t("vae_decode_desc"))
        if hasattr(self, 'node_save_img') and self.node_save_img:
            self.node_save_img.set_title(t("node_save_image"))
            if hasattr(self, 'prefix_lbl') and self.prefix_lbl:
                self.prefix_lbl.setText(t("tag_prefix"))
            if hasattr(self, 'save_hint') and self.save_hint:
                self.save_hint.setText(t("image_output_hint"))

        # Steppers on primary LoRA
        if hasattr(self, 'lora_model_spin') and self.lora_model_spin:
            self.lora_model_spin.setLabel(t("tag_model_strength"))
        if hasattr(self, 'lora_clip_spin') and self.lora_clip_spin:
            self.lora_clip_spin.setLabel(t("tag_clip_strength"))

        # Extra LoRAs
        if hasattr(self, 'extra_lora_nodes'):
            for i, en in enumerate(self.extra_lora_nodes):
                en.set_title(t("node_load_lora_idx").format(idx=i+2))
                en.retranslate_sockets()
        if hasattr(self, 'lora_rows'):
            for row in self.lora_rows:
                row.m_strength_spin.setLabel(t("tag_model_strength"))
                row.c_strength_spin.setLabel(t("tag_clip_strength"))

        # Retranslate all standard node sockets
        for node_attr in (
            'node_ckpt', 'node_lora', 'node_image', 'node_vae_enc',
            'node_empty_latent', 'node_pos', 'node_neg', 'node_ksampler',
            'node_vae_dec', 'node_save_img'
        ):
            nd = getattr(self, node_attr, None)
            if nd and hasattr(nd, 'retranslate_sockets'):
                nd.retranslate_sockets()

        # Drop Area
        if hasattr(self, 'drop_area') and self.drop_area:
            self.drop_area.browse_btn.setText(t("drop_area_title"))
            if not self.drop_area.image_path:
                self.drop_area.file_dim_lbl.setText(t("drop_area_sub"))

        self.export_json_btn.setText(f"  {t('export_json')}")
        self.export_png_btn.setText(f"  {t('export_png')}")

        # Update combo first item for lora
        if hasattr(self, 'lora_combo') and self.lora_combo.count() > 0:
            self.lora_combo.setItemText(0, t("no_lora_model_only"))

        self.update_status_summary()
