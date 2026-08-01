import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def run_integration_test():
    app = QApplication(sys.argv)
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    win.show()
    app.processEvents()

    print("=== STARTING COMPLETE USER SCENARIO INTEGRATION TEST ===")
    
    # 1. Test Model Click
    models = database.get_models_in_library("Checkpoint Modelleri")
    if models:
        print(f"\n1. Testing Model Card Click: {models[0]['name']}")
        controller.on_model_clicked(models[0])
        app.processEvents()
        assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible on model click!"
        assert win.detail_panel.mode == "MODEL", f"FAIL: Expected mode MODEL, got {win.detail_panel.mode}"
        print("   -> Detail Panel is VISIBLE in MODEL mode! Header:", win.detail_panel.header_label.text())

    # 2. Test Close Button inside Detail Panel
    print("\n2. Testing Detail Panel Close Button")
    win.detail_panel.close_requested.emit()
    app.processEvents()
    assert not win.detail_panel.isVisible(), "FAIL: Detail panel still visible after close click!"
    print("   -> Detail Panel HIDDEN successfully!")

    # 3. Test Note Click from NotesView Grid
    notes = database.get_notes()
    if notes:
        print(f"\n3. Testing Note Card Click: {notes[0]['title']}")
        controller.on_note_clicked_from_grid(notes[0])
        app.processEvents()
        assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible on note click!"
        assert win.detail_panel.mode == "NOTE", f"FAIL: Expected mode NOTE, got {win.detail_panel.mode}"
        print("   -> Detail Panel is VISIBLE in NOTE mode! Title:", win.detail_panel.note_title_edit.text())

    # 4. Test Sidebar "+ Yeni Not"
    print("\n4. Testing Sidebar '+ Yeni Not'")
    controller.on_create_new_note()
    app.processEvents()
    assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible on new note create!"
    assert win.detail_panel.mode == "NOTE", "FAIL: Detail panel not in NOTE mode!"
    print("   -> New Note created & opened in Detail Panel!")

    # 5. Test Workflow Click
    wf_libs = database.get_workflow_libraries()
    if wf_libs:
        wfs = database.get_workflows_in_library(wf_libs[0]['id'])
        if wfs:
            print(f"\n5. Testing Workflow Click: {wfs[0]['name']}")
            controller.on_workflow_clicked(wfs[0])
            app.processEvents()
            assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible on workflow click!"
            assert win.detail_panel.mode == "WORKFLOW", f"FAIL: Expected mode WORKFLOW, got {win.detail_panel.mode}"
            print("   -> Detail Panel is VISIBLE in WORKFLOW mode! Name:", win.detail_panel.name_edit.text())

    # 6. Test Sidebar Home Navigation
    print("\n6. Testing Sidebar 'Ana Sayfa' Navigation")
    win.sidebar.home_requested.emit()
    app.processEvents()
    assert not win.detail_panel.isVisible(), "FAIL: Detail panel not hidden on home navigation!"
    assert win.center_stack.currentIndex() == 0, "FAIL: Center stack not on welcome screen!"
    print("   -> Switched to Home / Welcome Screen! Detail Panel auto-hidden.")

    # 7. Test 10 Repeated Clicks
    print("\n7. Testing 10 Repeated Rapid Clicks on Cards")
    for i in range(1, 11):
        if models:
            controller.on_model_clicked(models[0])
            app.processEvents()
            assert win.detail_panel.isVisible(), f"Cycle {i} FAIL: Model click failed!"
        win.hide_detail_panel()
        app.processEvents()
        assert not win.detail_panel.isVisible(), f"Cycle {i} FAIL: Hide failed!"

    print("\n=== ALL 10 INTEGRATION SCENARIOS PASSED WITH ZERO ERRORS ===")
    app.quit()

if __name__ == "__main__":
    run_integration_test()
