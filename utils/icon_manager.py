# utils/icon_manager.py
"""
Centralized Icon Manager for VeraNote.
Provides dynamic SVG/PNG vector icon retrieval, scaling, and theme-aware color tinting.
"""

import os
import sys
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt

_ICON_CACHE = {}
_PIXMAP_CACHE = {}

def get_icons_dir() -> str:
    """Returns the absolute path to the assets/icons directory."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.join(sys._MEIPASS, 'assets', 'icons')
        if os.path.isdir(base_dir):
            return base_dir
    # Standard source directory
    base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'icons')
    if os.path.isdir(base_dir):
        return base_dir
    # Fallback to current working directory
    return os.path.abspath(os.path.join('assets', 'icons'))

ICON_MAP = {
    'home': 'nav_home.png',
    'nav_home': 'nav_home.png',
    'calendar': 'nav_calendar.png',
    'agenda': 'nav_calendar.png',
    'nav_calendar': 'nav_calendar.png',
    'add': 'nav_add.png',
    'plus': 'nav_add.png',
    'new': 'nav_add.png',
    'nav_add': 'nav_add.png',
    'notes': 'nav_notes.png',
    'all_notes': 'nav_notes.png',
    'nav_notes': 'nav_notes.png',
    'trash': 'nav_trash.png',
    'recycle_bin': 'nav_trash.png',
    'nav_trash': 'nav_trash.png',
    'models': 'nav_models.png',
    'box': 'nav_models.png',
    'nav_models': 'nav_models.png',
    'workflows': 'nav_workflows.png',
    'puzzle': 'nav_workflows.png',
    'nav_workflows': 'nav_workflows.png',
    'settings': 'nav_settings.png',
    'gear': 'nav_settings.png',
    'nav_settings': 'nav_settings.png',
    'concept': 'nav_concept.png',
    'nav_concept': 'nav_concept.png',
}

def get_pixmap(name: str, color_hex: str = "#E3E3E3", size: int = 18) -> QPixmap:
    """
    Returns a tinted QPixmap of the requested icon at the requested size.
    Caches results for high performance.
    """
    key = (name, color_hex, size)
    if key in _PIXMAP_CACHE:
        return _PIXMAP_CACHE[key]
    
    filename = ICON_MAP.get(name, f"{name}.png" if not name.endswith(".png") else name)
    icon_path = os.path.join(get_icons_dir(), filename)
    
    if not os.path.exists(icon_path):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        _PIXMAP_CACHE[key] = pm
        return pm
    
    src_pixmap = QPixmap(icon_path)
    if src_pixmap.isNull():
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        _PIXMAP_CACHE[key] = pm
        return pm
    
    scaled = src_pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    tinted = QPixmap(scaled.size())
    tinted.fill(Qt.transparent)
    
    painter = QPainter(tinted)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.drawPixmap(0, 0, scaled)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(tinted.rect(), QColor(color_hex))
    painter.end()
    
    _PIXMAP_CACHE[key] = tinted
    return tinted

def get_icon(name: str, color_hex: str = "#E3E3E3", size: int = 18) -> QIcon:
    """
    Returns a QIcon of the requested tinted icon.
    """
    key = (name, color_hex, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    
    pm = get_pixmap(name, color_hex, size)
    icon = QIcon(pm)
    _ICON_CACHE[key] = icon
    return icon
