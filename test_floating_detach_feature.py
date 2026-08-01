import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def test_floating_feature():
    app = QApplication(sys.argv)
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    win.show()
    app.processEvents()

    print("=== STARTING FLOATING / DETACH FEATURE TEST ===")

    # 1. Open model detail
    models = database.get_models_in_library("Checkpoint Modelleri")
    if models:
        controller.on_model_clicked(models[0])
        app.processEvents()
        print("1. Detail Panel opened in docked mode. Floating:", win.detail_dock.isFloating())
        assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible!"
        assert not win.detail_dock.isFloating(), "FAIL: Panel should start docked!"

    # 2. Click Detach / Float button ('[Detach]')
    print("\n2. Detaching panel to floating mode...")
    win.detail_dock.setFloating(True)
    app.processEvents()
    
    assert win.detail_dock.isFloating(), "FAIL: detail_dock should be floating!"
    print("   -> Detail Panel DETACHED into floating window successfully!")
    print("   -> Floating Window Title:", win.detail_dock.windowTitle())
    print("   -> Floating Window Size:", win.detail_dock.size().width(), "x", win.detail_dock.size().height())

    # 3. Click Note Card while floating
    notes = database.get_notes()
    if notes:
        print(f"\n3. Clicking Note Card while floating: {notes[0]['title']}")
        controller.open_note_in_drawer(notes[0]['id'])
        app.processEvents()
        assert win.detail_panel.mode == "NOTE", "FAIL: Detail panel not in NOTE mode!"
        print("   -> Detail panel updated to NOTE mode successfully!")

    # 4. Click Detach / Re-dock button to Re-dock
    print("\n4. Re-docking back to main window...")
    win.detail_dock.setFloating(False)
    app.processEvents()
    
    assert not win.detail_dock.isFloating(), "FAIL: detail_dock should be False after re-dock!"
    assert win.detail_panel.isVisible(), "FAIL: Detail panel not visible in splitter after re-dock!"
    print("   -> Detail Panel RE-DOCKED back to main window splitter successfully!")

    # 5. 5-Cycle Detach -> Close -> Re-open -> Re-dock Test
    print("\n5. Running 5-Cycle Detach -> Close -> Re-open -> Re-dock Test...")
    for i in range(1, 6):
        # Detach
        win.detail_dock.setFloating(True)
        app.processEvents()
        assert win.detail_dock.isFloating(), f"Cycle {i} FAIL: Detach failed!"
        
        # Close floating window
        win.detail_dock.close()
        app.processEvents()
        assert not win.detail_dock.isVisible(), f"Cycle {i} FAIL: Close failed!"
        
        # Re-open panel
        if models:
            controller.on_model_clicked(models[0])
            app.processEvents()
            assert win.detail_panel.isVisible(), f"Cycle {i} FAIL: Re-open failed!"
            
        print(f"   Cycle {i}: Detach -> Close -> Re-open -> Re-dock PASSED!")

    print("\n=== ALL FLOATING / DETACH FEATURE TESTS PASSED PERFECTLY ===")
    app.quit()

if __name__ == "__main__":
    test_floating_feature()
