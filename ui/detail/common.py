"""
Common reusable widgets and layouts for Detail Panel sections.
"""
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, 
                             QTextEdit, QLayout)
from PySide6.QtCore import Signal, Qt, QSize, QPoint, QRect
from PySide6.QtGui import QTextCursor
from utils.i18n import t


class ZoomableTextEdit(QTextEdit):
    """QTextEdit with Ctrl+Wheel zoom support."""
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
    """Custom FlowLayout to display items in wrapping pill style."""
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
        self.setToolTip(t("detail_trigger_tooltip"))

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
