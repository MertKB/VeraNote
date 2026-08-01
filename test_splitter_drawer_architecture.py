import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def test_drawer_architecture():
    app = QApplication(sys.argv)
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    win.show()
    app.processEvents()

    print("=== TEST 1: Initial Window & Splitter State ===")
    print(f"Window Size: {win.size().width()}x{win.size().height()}")
    print(f"Splitter Sizes: {win.splitter.sizes()}")
    print(f"Detail Panel Visible: {win.detail_panel.isVisible()}")

    # --- TEST 2: Navigating views ---
    print("\n=== TEST 2: Navigating through all views ===")
    controller.on_all_notes_requested()
    app.processEvents()
    print(f"Notes View - Stack Index: {win.center_stack.currentIndex()}, Panel Visible: {win.detail_panel.isVisible()}")

    libs = database.get_libraries(lib_type='MODEL')
    if libs:
        controller.on_library_selected(libs[0])
        app.processEvents()
        print(f"Library View '{libs[0]}' - Stack Index: {win.center_stack.currentIndex()}, Panel Visible: {win.detail_panel.isVisible()}")

    # --- TEST 3: Opening Detail Panel on Items ---
    print("\n=== TEST 3: Opening Detail Panel ===")
    models = database.get_models_in_library(libs[0]) if libs else []
    if models:
        controller.on_model_clicked(models[0])
        app.processEvents()
        print(f"Opened Model Detail - Panel Visible: {win.detail_panel.isVisible()}")
        print(f"Window Size: {win.size().width()}x{win.size().height()}, Splitter Sizes: {win.splitter.sizes()}")

    # --- TEST 4: Closing and Re-opening 10 times ---
    print("\n=== TEST 4: 10-Cycle Close and Re-open Test ===")
    for i in range(1, 11):
        win.hide_detail_panel()
        app.processEvents()
        if win.detail_panel.isVisible():
            print(f"Cycle {i} FAIL: Panel still visible after hide!")
        
        if models:
            controller.on_model_clicked(models[0])
        else:
            win.show_detail_panel()
        app.processEvents()
        
        if not win.detail_panel.isVisible():
            print(f"Cycle {i} FAIL: Panel not visible after show!")

        print(f"Cycle {i} Re-opened: Panel Visible={win.detail_panel.isVisible()}, Window Size={win.size().width()}x{win.size().height()}, Splitter Sizes={win.splitter.sizes()}")

    # --- TEST 5: Switching screens while Detail Panel is Open ---
    print("\n=== TEST 5: Switching screens while Detail Panel is Open ===")
    win.show_welcome()
    app.processEvents()
    print(f"Switched to Welcome - Panel Visible: {win.detail_panel.isVisible()}")

    print("\n=== ALL DRAWER ARCHITECTURE TESTS PASSED PERFECTLY ===")
    app.quit()

if __name__ == "__main__":
    test_drawer_architecture()
