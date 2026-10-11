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
    assert len(dialog.color_buttons) == len(COLOR_ATTRIBUTES), f"Expected {len(COLOR_ATTRIBUTES)} color buttons, got {len(dialog.color_buttons)}"
    assert len(dialog.preset_buttons) == len(CUSTOM_PRESETS)

    # Test applying a preset
    preset_key, preset_data = CUSTOM_PRESETS[1] # AMOLED
    dialog.apply_preset(preset_data)
    assert dialog.custom_colors["bg_card"] == preset_data["bg_card"]
    assert dialog.custom_colors["border_color"] == preset_data["border_color"]

    settings = dialog.get_settings()
    print("5. Checking Detail Panel theme harmonization...")
    from ui.detail.workflow_section import WorkflowSection
    from ui.detail.model_section import ModelSection
    from ui.detail.note_section import NoteSection

    wf_sec = WorkflowSection()
    wf_sec.set_workflow({
        'id': 1,
        'name': 'TestWF',
        'workflow_json': '{"1": {"class_type": "KSampler"}, "2": {"class_type": "VAEDecode"}}'
    })
    
    # Check node pills
    assert len(wf_sec.node_widgets) == 2, f"Expected 2 node pills, got {len(wf_sec.node_widgets)}"
    for pill in wf_sec.node_widgets:
        assert pill.objectName() == "WorkflowNodePill"
        assert "#242936" not in pill.styleSheet(), "Hardcoded #242936 background found in node pill!"
        assert "55;" not in pill.styleSheet(), "Broken alpha hex found in node pill!"

    # Test applying Derin Mor theme
    mor_palette = get_palette("Derin Mor")
    wf_sec.apply_theme(mor_palette)
    assert "#2D2F31" not in wf_sec.copy_pos_btn.styleSheet(), "Hardcoded #2D2F31 found on copy_pos_btn!"
    assert "#2D2F31" not in wf_sec.copy_params_btn.styleSheet(), "Hardcoded #2D2F31 found on copy_params_btn!"
    assert "#2D2F31" not in wf_sec.copy_seed_btn.styleSheet(), "Hardcoded #2D2F31 found on copy_seed_btn!"

    model_sec = ModelSection()
    model_sec.apply_theme(mor_palette)
    assert "#2D2F31" not in model_sec.name_edit.styleSheet(), "Hardcoded #2D2F31 found on model name_edit!"
    assert "#2D2F31" not in model_sec.arch_combo.styleSheet(), "Hardcoded #2D2F31 found on arch_combo!"

    note_sec = NoteSection()
    note_sec.apply_theme(mor_palette)
    assert "#2D2F31" not in note_sec.note_title_edit.styleSheet(), "Hardcoded #2D2F31 found on note_title_edit!"
    print("   [OK] Detail Panel theme harmonization verified.")

    print("ALL CUSTOM THEME AND CARD TESTS PASSED SUCCESSFULLY! [OK]")

if __name__ == "__main__":
    test_cards_and_custom_theme()
