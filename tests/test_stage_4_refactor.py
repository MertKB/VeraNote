"""
Automated tests for Aşama 4:
- God Object refactor: ui/corkboard subpackage & lean WelcomeScreen
- God Object refactor: ui/detail subpackage & lean DetailPanel
- Zero direct database imports in ui/ views
- MVC Signal wiring & backward compatibility
- Theme system & get_palette integration
"""
import sys
import os

# Headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QPoint, QSize

def test_no_database_in_ui_views():
    print("Testing MVC isolation (no direct database imports in views)...")
    ui_dir = r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote\ui"
    views_to_check = [
        "welcome_screen.py",
        "detail_panel.py",
        "library_view.py",
        "workflow_view.py",
        "corkboard/cards.py",
        "corkboard/title.py",
        "corkboard/dialogs.py",
        "detail/model_section.py",
        "detail/note_section.py",
        "detail/workflow_section.py",
        "detail/common.py",
    ]
    for rel_path in views_to_check:
        full_path = os.path.join(ui_dir, rel_path)
        assert os.path.exists(full_path), f"File missing: {full_path}"
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = [line.strip() for line in content.splitlines()]
        for line_num, line in enumerate(lines, start=1):
            # Check top-level or method imports of database
            if line.startswith("import database") or line.startswith("from database import"):
                raise AssertionError(f"Direct database import found in {rel_path}:{line_num} -> {line}")
    print("  [OK] No direct database imports found in any UI view modules!")

def test_styles_palette():
    print("Testing ui/styles.py get_palette...")
    from ui.styles import get_palette, PALETTES
    for theme_name in PALETTES.keys():
        pal = get_palette(theme_name)
        assert "bg_main" in pal, f"Missing bg_main in palette for {theme_name}"
        assert "bg_card" in pal, f"Missing bg_card in palette for {theme_name}"
        assert "accent_color" in pal, f"Missing accent_color in palette for {theme_name}"
        assert pal["bg_main"].startswith("#"), f"Invalid color hex: {pal['bg_main']}"

    # Test custom theme
    custom = {"bg_main": "#112233", "bg_card": "#445566", "accent_color": "#FF00AA"}
    pal_custom = get_palette("Özel Tema", custom)
    assert pal_custom["bg_main"] == "#112233"
    assert pal_custom["bg_card"] == "#445566"
    assert pal_custom["accent_color"] == "#FF00AA"
    print("  [OK] Styles get_palette successfully generates palettes for all themes & custom!")

def test_corkboard_subpackage(app):
    print("Testing ui/corkboard subpackage & WelcomeScreen...")
    import ui.corkboard as cb
    assert hasattr(cb, "CorkboardNoteCard")
    assert hasattr(cb, "QuickNoteCardWidget")
    assert hasattr(cb, "OutlinedLabel")
    assert hasattr(cb, "EditableLabel")
    assert hasattr(cb, "HomePageSettingsDialog")
    assert hasattr(cb, "get_pastel_palette")

    import ui.welcome_screen as ws
    assert hasattr(ws, "WelcomeScreen")
    assert hasattr(ws, "CorkboardNoteCard") # backward compatibility check

    welcome = ws.WelcomeScreen()
    welcome.resize(1000, 700)
    welcome.show()

    # Verify signals exist
    assert hasattr(welcome, "note_open_requested")
    assert hasattr(welcome, "corkboard_position_changed")
    assert hasattr(welcome, "setting_changed")
    assert hasattr(welcome, "corkboard_unpin_requested")

    # Test setting changed signal
    emitted_settings = []
    welcome.setting_changed.connect(lambda k, v: emitted_settings.append((k, v)))
    welcome.set_positions_locked(True)
    assert ("home_positions_locked", "1") in emitted_settings

    welcome.set_title_visible(False)
    assert ("welcome_title_visible", "0") in emitted_settings

    # Test load_settings
    welcome.load_settings({"home_positions_locked": "0", "welcome_title_visible": "1", "welcome_title_font_size": "32"})
    assert welcome.positions_locked is False
    assert welcome.title_visible is True
    assert welcome.title_font_size == 32
    print("  [OK] Corkboard subpackage and WelcomeScreen tested successfully!")

def test_detail_subpackage(app):
    print("Testing ui/detail subpackage & DetailPanel...")
    import ui.detail as dt
    assert hasattr(dt, "ZoomableTextEdit")
    assert hasattr(dt, "FlowLayout")
    assert hasattr(dt, "TriggerPillButton")
    assert hasattr(dt, "TagPillWidget")
    assert hasattr(dt, "ModelSection")
    assert hasattr(dt, "NoteSection")
    assert hasattr(dt, "WorkflowSection")

    import ui.detail_panel as dp
    assert hasattr(dp, "DetailPanel")
    assert hasattr(dp, "ZoomableTextEdit")
    assert hasattr(dp, "FlowLayout")

    panel = dp.DetailPanel()
    panel.resize(400, 700)
    panel.show()

    # 1. Test Model mode & signals
    model_data = {"id": 42, "name": "Protogen v2.2", "file_path": "models/loras/protogen.safetensors", "notes": "Great prompt", "tags": ["anime", "portrait"]}
    trigger_words = ["protogen", "masterpiece"]
    panel.set_model(model_data, trigger_words)
    assert panel.mode == "MODEL"
    assert panel.model_data["id"] == 42
    assert panel.trigger_words == trigger_words
    assert panel.stack.currentIndex() == 0

    # Model signal emission test
    emitted_model_saves = []
    panel.save_model_data_requested.connect(lambda mid, name, notes, arch="": emitted_model_saves.append((mid, name, notes)))
    panel.model_section.name_edit.setText("Protogen v2.2 Updated")
    panel.model_section.on_save_clicked()
    assert len(emitted_model_saves) == 1
    assert emitted_model_saves[0] == (42, "Protogen v2.2 Updated", "Great prompt")

    # 2. Test Note mode & signals
    note_data = {"id": 101, "title": "Meeting Notes", "content": "<p>Review architecture</p>", "display_mode": "WITH_IMAGE", "is_corkboard": 0, "color_hex": "#FFD700"}
    panel.set_note(note_data, [])
    assert panel.mode == "NOTE"
    assert panel.note_data["id"] == 101
    assert panel.stack.currentIndex() == 1

    emitted_pins = []
    panel.corkboard_pin_toggled.connect(lambda nid, pin: emitted_pins.append((nid, pin)))
    panel.note_section.on_toggle_pin_corkboard()
    assert len(emitted_pins) == 1
    assert emitted_pins[0] == (101, True)

    emitted_colors = []
    panel.note_color_changed.connect(lambda nid, color: emitted_colors.append((nid, color)))
    panel.note_section.on_swatch_color_selected("#AECBFA")
    assert len(emitted_colors) == 1
    assert emitted_colors[0] == (101, "#AECBFA")

    # 3. Test Workflow mode & signals
    workflow_data = {"id": 7, "name": "Upscaler Workflow", "description": "4x UltraSharp", "notes": "Use with SDXL", "workflow_json": '{"nodes": []}'}
    panel.set_workflow(workflow_data)
    assert panel.mode == "WORKFLOW"
    assert panel.workflow_data["id"] == 7
    assert panel.stack.currentIndex() == 2

    emitted_wf_saves = []
    panel.save_workflow_data_requested.connect(lambda wid, name, desc, notes: emitted_wf_saves.append((wid, name, desc, notes)))
    panel.workflow_section.name_edit.setText("Upscaler Workflow 2.0")
    panel.workflow_section.on_save_clicked()
    assert len(emitted_wf_saves) == 1
    assert emitted_wf_saves[0] == (7, "Upscaler Workflow 2.0", "4x UltraSharp", "Use with SDXL")

    # Retranslate
    panel.retranslate_ui()

    print("  [OK] Detail subpackage and DetailPanel coordinator tested successfully!")

def test_full_app_controller_and_window(app):
    print("Testing full MainWindow & AppController integration...")
    from ui.main_window import MainWindow
    from main import AppController

    main_win = MainWindow()
    main_win.show()
    controller = AppController(main_win)
    assert controller.win is not None
    assert controller.win.welcome_screen is not None
    assert controller.win.detail_panel is not None
    assert controller.win.library_view is not None
    assert controller.win.notes_view is not None

    # Test show_detail_panel
    controller.win.detail_panel.set_model({"id": 1, "name": "M", "notes": ""}, [])
    controller.win.show_detail_panel()
    assert controller.win.detail_dock.isVisible()

    controller.win.hide_detail_panel()
    assert not controller.win.detail_dock.isVisible()

    print("  [OK] MainWindow & AppController initialized and integrated seamlessly!")

if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    test_no_database_in_ui_views()
    test_styles_palette()
    test_corkboard_subpackage(app)
    test_detail_subpackage(app)
    test_full_app_controller_and_window(app)
    print("\n==========================================")
    print("ALL AŞAMA 4 AUTOMATED TESTS PASSED (100%)!")
    print("==========================================")
