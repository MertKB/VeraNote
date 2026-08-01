import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def test_architecture():
    app = QApplication(sys.argv)
    
    # Ensure database is initialized
    # database initializes automatically on import
    
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    
    win.show()
    app.processEvents()

    print("=== TEST 1: Initial Window & Splitter State ===")
    print(f"Window Size: {win.size().width()}x{win.size().height()}")
    print(f"Splitter Sizes: {win.splitter.sizes()}")
    print(f"Detail Dock Floating: {win.detail_dock.isFloating()}, Visible: {win.detail_dock.isVisible()}")

    # --- TEST 2: Navigation across views ---
    print("\n=== TEST 2: Navigating through all views ===")
    
    # 2a. Welcome Screen
    win.show_welcome()
    app.processEvents()
    print(f"Welcome Screen - Stack Index: {win.center_stack.currentIndex()}, Dock Visible: {win.detail_dock.isVisible()}")

    # 2b. All Notes
    controller.on_all_notes_requested()
    app.processEvents()
    print(f"Notes View - Stack Index: {win.center_stack.currentIndex()}, Dock Visible: {win.detail_dock.isVisible()}")

    # 2c. Libraries
    libs = database.get_libraries(lib_type='MODEL')
    if libs:
        controller.on_library_selected(libs[0])
        app.processEvents()
        print(f"Library View '{libs[0]}' - Stack Index: {win.center_stack.currentIndex()}, Dock Visible: {win.detail_dock.isVisible()}")

    # 2d. Workflow Libraries
    wf_libs = database.get_workflow_libraries()
    if wf_libs:
        controller.on_workflow_library_selected(wf_libs[0]['name'])
        app.processEvents()
        print(f"Workflow View '{wf_libs[0]['name']}' - Stack Index: {win.center_stack.currentIndex()}, Dock Visible: {win.detail_dock.isVisible()}")

    # --- TEST 3: Opening Detail Panel on Items ---
    print("\n=== TEST 3: Opening Detail Panel on Models, Notes, Workflows ===")
    models = database.get_models_in_library(libs[0]) if libs else []
    if models:
        controller.on_model_clicked(models[0])
        app.processEvents()
        print(f"Opened Model Detail - Dock Visible: {win.detail_dock.isVisible()}, Dock Floating: {win.detail_dock.isFloating()}")
        print(f"Window Size: {win.size().width()}x{win.size().height()}, Splitter Sizes: {win.splitter.sizes()}")

    # --- TEST 4: Undocking (Floating), Closing, and Re-opening ---
    print("\n=== TEST 4: Undocking (Floating), Closing, Re-opening ===")
    win.detail_dock.setFloating(True)
    app.processEvents()
    print(f"Undocked - Dock Floating: {win.detail_dock.isFloating()}")

    win.hide_detail_panel()
    app.processEvents()
    print(f"Closed Floating Panel - Dock Visible: {win.detail_dock.isVisible()}")

    if models:
        controller.on_model_clicked(models[0])
        app.processEvents()
        print(f"Re-opened Model Detail - Dock Visible: {win.detail_dock.isVisible()}, Dock Floating: {win.detail_dock.isFloating()}")
        print(f"Window Size: {win.size().width()}x{win.size().height()}, Splitter Sizes: {win.splitter.sizes()}")

    # --- TEST 5: Switching screens while Detail Panel is Open ---
    print("\n=== TEST 5: Switching screens while Detail Panel is Open ===")
    win.show_welcome()
    app.processEvents()
    print(f"Switched to Welcome - Dock Visible: {win.detail_dock.isVisible()}")

    print("\n=== ALL ARCHITECTURE TESTS COMPLETED SUCCESSFULLY ===")
    app.quit()

if __name__ == "__main__":
    test_architecture()
