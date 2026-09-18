"""
Corkboard and Welcome Screen components for VeraNote.
"""
from .cards import (
    ImageLoadWorker, ImageLoadWorkerSignals,
    get_pastel_palette, get_palette_colors,
    QuickNoteCardWidget, CorkboardNoteCard
)
from .title import OutlinedLabel, EditableLabel
from .dialogs import NoWheelSlider, HomePageSettingsDialog

__all__ = [
    "ImageLoadWorker",
    "ImageLoadWorkerSignals",
    "get_pastel_palette",
    "get_palette_colors",
    "QuickNoteCardWidget",
    "CorkboardNoteCard",
    "OutlinedLabel",
    "EditableLabel",
    "NoWheelSlider",
    "HomePageSettingsDialog",
]
