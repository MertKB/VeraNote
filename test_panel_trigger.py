import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def test_triggers():
    app = QApplication(sys.argv)
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    win.show()
    app.processEvents()

    print("=== TEST 1: Initial Panel State ===")
    print("Panel Visible:", win.detail_panel.isVisible())
    print("Splitter Sizes:", win.splitter.sizes())

    # --- TEST 2: Clicking a Model Card ---
    print("\n=== TEST 2: Clicking a Model Card ===")
    models = database.get_models_in_library("Checkpoint Modelleri")
    if models:
        print(f"Triggering on_model_clicked for model: {models[0]['name']}")
        controller.on_model_clicked(models[0])
        app.processEvents()
        print("Panel Visible:", win.detail_panel.isVisible())
        print("Detail Panel Mode:", win.detail_panel.mode)
        print("Detail Header Text:", win.detail_panel.header_label.text())
        print("Splitter Sizes:", win.splitter.sizes())
    else:
        print("No models found in database to test model click!")

    # --- TEST 3: Clicking a Note Card ---
    print("\n=== TEST 3: Clicking a Note Card ===")
    notes = database.get_notes()
    if notes:
        print(f"Triggering open_note_in_drawer for note: {notes[0]['title']}")
        controller.open_note_in_drawer(notes[0]['id'])
        app.processEvents()
        print("Panel Visible:", win.detail_panel.isVisible())
        print("Detail Panel Mode:", win.detail_panel.mode)
        print("Detail Header Text:", win.detail_panel.header_label.text())
        print("Splitter Sizes:", win.splitter.sizes())
    else:
        print("No notes found in database to test note click!")

    # --- TEST 4: Clicking a Workflow Card ---
    print("\n=== TEST 4: Clicking a Workflow Card ===")
    wf_libs = database.get_workflow_libraries()
    if wf_libs:
        wfs = database.get_workflows_in_library(wf_libs[0]['id'])
        if wfs:
            print(f"Triggering on_workflow_clicked for workflow: {wfs[0]['name']}")
            controller.on_workflow_clicked(wfs[0])
            app.processEvents()
            print("Panel Visible:", win.detail_panel.isVisible())
            print("Detail Panel Mode:", win.detail_panel.mode)
            print("Detail Header Text:", win.detail_panel.header_label.text())
            print("Splitter Sizes:", win.splitter.sizes())

    # --- TEST 5: Hiding and Re-opening multiple times ---
    print("\n=== TEST 5: Hiding and Re-opening 5 times ===")
    for i in range(1, 6):
        win.hide_detail_panel()
        app.processEvents()
        print(f"Cycle {i} Hidden - Panel Visible: {win.detail_panel.isVisible()}, Splitter Sizes: {win.splitter.sizes()}")
        
        if models:
            controller.on_model_clicked(models[0])
            app.processEvents()
            print(f"Cycle {i} Re-opened - Panel Visible: {win.detail_panel.isVisible()}, Splitter Sizes: {win.splitter.sizes()}")

    app.quit()

if __name__ == "__main__":
    test_triggers()
