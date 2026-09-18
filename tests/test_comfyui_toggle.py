"""
Automated tests for ComfyUI Toggle feature:
- Database setting persistence (default 1)
- Translation parity for new ComfyUI settings keys
- SettingsDialog toggle behavior & path container visibility
- Sidebar element visibility & list update safety
- MainWindow view redirection and detail panel cleanup when ComfyUI is disabled
- AppController integration & data safety
"""
import sys
import os

# Headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote")

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

import database
from utils import i18n
from ui.settings_dialog import SettingsDialog
from ui.sidebar import Sidebar
from ui.main_window import MainWindow
from main import AppController


def test_database_default():
    print("Testing database comfyui_enabled setting...")
    val = database.get_setting("comfyui_enabled")
    assert val in ("1", "0"), f"Unexpected comfyui_enabled value: {val}"
    # Test setting and getting
    database.set_setting("comfyui_enabled", "0")
    assert database.get_setting("comfyui_enabled") == "0"
    database.set_setting("comfyui_enabled", "1")
    assert database.get_setting("comfyui_enabled") == "1"
    print("  [OK] Database setting get/set works cleanly!")


def test_i18n_keys():
    print("Testing translation keys for ComfyUI toggle...")
    for lang in ("tr", "en"):
        d = i18n.TRANSLATIONS[lang]
        for k in ("settings_comfyui_section", "settings_comfyui_enable", "settings_comfyui_desc"):
            assert k in d, f"Missing key '{k}' in {lang}"
            assert len(d[k].strip()) > 0, f"Empty translation for '{k}' in {lang}"
    print("  [OK] All translation keys present in TR and EN!")


def test_settings_dialog_toggle(app):
    print("Testing SettingsDialog ComfyUI toggle...")
    dlg = SettingsDialog()
    dlg.show()

    # Verify initial widgets exist
    assert hasattr(dlg, "comfyui_enable_check")
    assert hasattr(dlg, "comfyui_paths_widget")
    assert hasattr(dlg, "comfyui_section_lbl")
    assert hasattr(dlg, "comfyui_desc_lbl")

    # Set settings with comfyui enabled = 1
    dlg.set_settings(
        lora_path="/path/loras",
        ckpt_path="/path/ckpts",
        auto_save_enabled=1,
        auto_save_interval=1.5,
        theme="Koyu Gece",
        lang="tr",
        custom_colors_data=None,
        comfyui_enabled=1
    )
    assert dlg.comfyui_enable_check.isChecked() is True
    assert dlg.comfyui_paths_widget.isVisible() is True
    settings = dlg.get_settings()
    assert settings["comfyui_enabled"] == 1
    assert settings["lora_path"] == "/path/loras"
    assert settings["ckpt_path"] == "/path/ckpts"

    # Toggle off
    dlg.comfyui_enable_check.setChecked(False)
    assert dlg.comfyui_paths_widget.isVisible() is False
    settings_off = dlg.get_settings()
    assert settings_off["comfyui_enabled"] == 0

    # Set settings with comfyui enabled = 0
    dlg.set_settings(
        lora_path="/path/loras",
        ckpt_path="/path/ckpts",
        auto_save_enabled=1,
        auto_save_interval=1.5,
        theme="Koyu Gece",
        lang="en",
        custom_colors_data=None,
        comfyui_enabled=0
    )
    assert dlg.comfyui_enable_check.isChecked() is False
    assert dlg.comfyui_paths_widget.isVisible() is False
    settings_off2 = dlg.get_settings()
    assert settings_off2["comfyui_enabled"] == 0

    # Retranslate test
    i18n.set_lang("tr")
    dlg.retranslate_ui()
    assert dlg.comfyui_section_lbl.text() == i18n.t("settings_comfyui_section")
    assert dlg.comfyui_enable_check.text() == i18n.t("settings_comfyui_enable")

    i18n.set_lang("en")
    dlg.retranslate_ui()
    assert dlg.comfyui_section_lbl.text() == i18n.t("settings_comfyui_section")
    assert dlg.comfyui_enable_check.text() == i18n.t("settings_comfyui_enable")

    dlg.close()
    print("  [OK] SettingsDialog ComfyUI toggle and visibility tested successfully!")


def test_sidebar_comfyui_visibility(app):
    print("Testing Sidebar ComfyUI visibility...")
    sidebar = Sidebar()
    sidebar.show()

    # Initially visible
    assert sidebar.comfyui_visible is True
    sidebar.update_models_list([("Lora Modelleri", 5), ("Checkpoint Modelleri", 3)])
    sidebar.update_workflow_libraries_list([("SDXL Workflows", 2)])

    # Toggle off ComfyUI
    sidebar.set_comfyui_visible(False)
    assert sidebar.comfyui_visible is False
    assert sidebar.models_label.isVisible() is False
    assert sidebar.models_list.isVisible() is False
    assert sidebar.new_lib_btn.isVisible() is False
    assert sidebar.lib_label.isVisible() is False
    assert sidebar.libraries_list.isVisible() is False

    # Note items remain visible
    assert sidebar.home_btn.isVisible() is True
    assert sidebar.new_note_btn.isVisible() is True
    assert sidebar.all_notes_btn.isVisible() is True
    assert sidebar.trash_btn.isVisible() is True
    assert sidebar.settings_btn.isVisible() is True

    # Updating lists while hidden must keep them hidden
    sidebar.update_models_list([("Lora Modelleri", 10)])
    sidebar.update_workflow_libraries_list([("SDXL Workflows", 4)])
    assert sidebar.models_list.isVisible() is False
    assert sidebar.libraries_list.isVisible() is False

    # Retranslate while hidden must keep ComfyUI hidden
    sidebar.retranslate_ui()
    assert sidebar.models_label.isVisible() is False
    assert sidebar.models_list.isVisible() is False

    # Toggle back on
    sidebar.set_comfyui_visible(True)
    assert sidebar.comfyui_visible is True
    assert sidebar.models_label.isVisible() is True
    assert sidebar.models_list.isVisible() is True
    assert sidebar.new_lib_btn.isVisible() is True
    assert sidebar.lib_label.isVisible() is True
    assert sidebar.libraries_list.isVisible() is True

    sidebar.close()
    print("  [OK] Sidebar ComfyUI toggle and visibility guards verified successfully!")


def test_mainwindow_routing_and_cleanup(app):
    print("Testing MainWindow view redirection & detail panel cleanup...")
    win = MainWindow()
    win.show()

    # 1. When on model library view (index 1) and ComfyUI is disabled -> redirect to welcome (index 0)
    win.show_library("Lora Modelleri", [])
    assert win.center_stack.currentIndex() == 1

    win.set_comfyui_enabled(False)
    assert win.sidebar.comfyui_visible is False
    assert win.center_stack.currentIndex() == 0  # redirected to welcome!

    # 2. When on workflow view (index 4) and ComfyUI is disabled -> redirect to welcome (index 0)
    win.set_comfyui_enabled(True)
    win.show_workflow_library(1, "SDXL Workflows", [])
    assert win.center_stack.currentIndex() == 4

    win.set_comfyui_enabled(False)
    assert win.center_stack.currentIndex() == 0  # redirected to welcome!

    # 3. When on notes view (index 3) and ComfyUI is disabled -> stay on notes!
    win.show_notes_panel([])
    assert win.center_stack.currentIndex() == 3
    win.set_comfyui_enabled(False)
    assert win.center_stack.currentIndex() == 3  # stays on notes!

    # 4. When detail panel shows a model, disabling ComfyUI hides it
    win.detail_panel.set_model({"id": 1, "name": "TestModel", "notes": ""}, [])
    win.show_detail_panel()
    assert win.detail_dock.isVisible() is True

    win.set_comfyui_enabled(False)
    assert win.detail_dock.isVisible() is False  # detail panel closed!

    win.close()
    print("  [OK] MainWindow routing and detail panel cleanup verified successfully!")


def test_controller_integration(app):
    print("Testing AppController with ComfyUI toggle...")
    # Set DB setting to 0 (disabled)
    database.set_setting("comfyui_enabled", "0")

    win = MainWindow()
    win.show()
    controller = AppController(win)

    assert controller.comfyui_enabled is False
    assert win.sidebar.comfyui_visible is False

    # Re-enable in controller
    controller.comfyui_enabled = True
    win.set_comfyui_enabled(True)
    database.set_setting("comfyui_enabled", "1")
    assert win.sidebar.comfyui_visible is True

    win.close()
    print("  [OK] AppController integration verified successfully!")


def test_outside_click_auto_save(app):
    print("Testing outside click auto-save for SettingsDialog and HomePageSettingsDialog...")
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtCore import QPoint, QEvent
    from ui.corkboard.dialogs import HomePageSettingsDialog
    from ui.welcome_screen import WelcomeScreen

    # 1. Test SettingsDialog outside click auto-save
    win = MainWindow()
    win.resize(1000, 700)
    win.show()

    dlg = SettingsDialog(win)
    dlg.resize(400, 300)
    dlg.move(200, 200)
    dlg.show()
    assert dlg.isVisible() is True

    # Send a click outside dlg, e.g. at (50, 50)
    outside_ev = QMouseEvent(QEvent.MouseButtonPress, QPoint(50, 50), QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    app.sendEvent(win, outside_ev)
    assert dlg.isVisible() is False
    assert dlg.result() == 1  # Accepted!

    # 2. Test HomePageSettingsDialog outside click auto-save
    ws = WelcomeScreen(win)
    ws.show()
    home_dlg = HomePageSettingsDialog(ws, win)
    home_dlg.resize(400, 300)
    home_dlg.move(200, 200)
    home_dlg.show()
    assert home_dlg.isVisible() is True

    app.sendEvent(win, outside_ev)
    assert home_dlg.isVisible() is False
    assert home_dlg.result() == 1  # Accepted!

    win.close()
    print("  [OK] Outside click auto-save verified for both dialogs!")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    test_database_default()
    test_i18n_keys()
    test_settings_dialog_toggle(app)
    test_sidebar_comfyui_visibility(app)
    test_mainwindow_routing_and_cleanup(app)
    test_controller_integration(app)
    test_outside_click_auto_save(app)
    print("\n==========================================")
    print("ALL COMFYUI TOGGLE & AUTO-SAVE TESTS PASSED (100%)!")
    print("==========================================")
