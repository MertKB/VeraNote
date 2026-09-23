import sys
import os
import json

os.environ["QT_QPA_PLATFORM"] = "offscreen"
workspace_dir = r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote"
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ui.library_view import LibraryView, ModelCardWidget
from ui.notes_view import NotesView, NoteCardWidget
from ui.workflow_view import WorkflowView, WorkflowCardWidget
from ui.settings_dialog import SettingsDialog, CUSTOM_PRESETS, COLOR_ATTRIBUTES
from ui.styles import get_palette, get_stylesheet

def test_cards_and_custom_theme():
    app = QApplication.instance() or QApplication(sys.argv)

    print("1. Checking WA_StyledBackground on cards...")
    model_card = ModelCardWidget({'id': 1, 'name': 'TestModel', 'file_path': 'C:/test.safetensors'})
    assert model_card.testAttribute(Qt.WA_StyledBackground), "ModelCardWidget missing WA_StyledBackground"
    assert model_card.info_panel.testAttribute(Qt.WA_StyledBackground), "ModelCardWidget.info_panel missing WA_StyledBackground"

    note_card = NoteCardWidget({'id': 1, 'title': 'TestNote', 'content': 'Content', 'color_hex': 'default'})
    assert note_card.testAttribute(Qt.WA_StyledBackground), "NoteCardWidget missing WA_StyledBackground"

    wf_card = WorkflowCardWidget({'id': 1, 'name': 'TestWF', 'data': '{}'})
    assert wf_card.testAttribute(Qt.WA_StyledBackground), "WorkflowCardWidget missing WA_StyledBackground"
    assert wf_card.info_panel.testAttribute(Qt.WA_StyledBackground), "WorkflowCardWidget.info_panel missing WA_StyledBackground"
    print("   [OK] WA_StyledBackground verified on all cards.")

    print("2. Checking grid container objectNames and stylesheet hygiene...")
    lib_view = LibraryView()
    assert lib_view.grid_container.objectName() == "LibraryGridContainer"
    assert "background-color: transparent" not in lib_view.grid_container.styleSheet(), "Inline transparent found on LibraryGridContainer!"

    notes_view = NotesView()
    assert notes_view.grid_container.objectName() == "NotesGridContainer"
    assert "background-color: transparent" not in notes_view.grid_container.styleSheet(), "Inline transparent found on NotesGridContainer!"

    wf_view = WorkflowView()
    assert wf_view.grid_container.objectName() == "WorkflowGridContainer"
    assert "background-color: transparent" not in wf_view.grid_container.styleSheet(), "Inline transparent found on WorkflowGridContainer!"
    print("   [OK] Grid containers correctly identified and no longer leak inline cascading transparency.")

    print("3. Checking get_palette with granular custom colors...")
    custom_dict = {
        "bg_main": "#101010",
        "bg_card": "#202020",
        "border_color": "#303030",
        "bg_sidebar": "#151515",
        "bg_input": "#252525",
        "accent_color": "#00FF00",
        "text_main": "#FFFFFF",
        "text_muted": "#888888"
    }
    p = get_palette("Özel Tema", custom_dict)
    assert p["bg_main"] == "#101010"
    assert p["bg_card"] == "#202020"
    assert p["border_color"] == "#303030"
    assert p["bg_sidebar"] == "#151515"
    assert p["bg_input"] == "#252525"
    assert p["accent_color"] == "#00FF00"
    assert p["text_main"] == "#FFFFFF"
    assert p["text_muted"] == "#888888"
    print("   [OK] All 8 custom colors properly parsed and applied in get_palette.")

    print("4. Checking SettingsDialog custom theme controls and presets...")
    dialog = SettingsDialog()
    assert len(dialog.color_buttons) == 10, f"Expected 10 color buttons, got {len(dialog.color_buttons)}"
    assert len(dialog.preset_buttons) == len(CUSTOM_PRESETS)

    # Test applying a preset
    preset_key, preset_data = CUSTOM_PRESETS[1] # AMOLED
    dialog.apply_preset(preset_data)
    assert dialog.custom_colors["bg_card"] == preset_data["bg_card"]
    assert dialog.custom_colors["border_color"] == preset_data["border_color"]

    settings = dialog.get_settings()
    assert settings["custom_theme_colors"]["bg_card"] == preset_data["bg_card"]
    print("   [OK] SettingsDialog presets and 8-color grid verified.")

    print("ALL CUSTOM THEME AND CARD TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_cards_and_custom_theme()
