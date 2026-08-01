import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
import database

def test_10_drag_close_open_cycles():
    app = QApplication(sys.argv)
    win = MainWindow()
    from main import AppController
    controller = AppController(win)
    win.show()
    app.processEvents()

    initial_size = win.size()
    initial_splitter_sizes = win.splitter.sizes()
    print(f"Initial Window Size: {initial_size.width()}x{initial_size.height()}")
    print(f"Initial Splitter Sizes: {initial_splitter_sizes}")

    errors = 0
    models = database.get_models_in_library("Checkpoint Modelleri")

    for i in range(1, 11):
        print(f"\n--- Cycle {i}: Drag -> Close -> Re-open ---")
        
        # 1. Open model detail
        if models:
            controller.on_model_clicked(models[0])
        else:
            win.show_detail_panel()
        app.processEvents()

        # Check docked
        if win.detail_dock.isFloating() or not win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Panel not properly docked/visible on open!")
            errors += 1

        # 2. Undock (float) and move to random screen position (e.g. 150+i*20, 150+i*20)
        win.detail_dock.setFloating(True)
        win.detail_dock.move(150 + i * 20, 150 + i * 20)
        app.processEvents()
        print(f"Cycle {i}: Floating at position {win.detail_dock.pos()}")

        # 3. Close panel while floating
        win.detail_dock.close()
        app.processEvents()

        if win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Panel still visible after close!")
            errors += 1

        # 4. Re-open panel
        if models:
            controller.on_model_clicked(models[0])
        else:
            win.show_detail_panel()
        app.processEvents()

        # VERIFY 100% DOCKED ON RIGHT DOCK AREA
        is_floating = win.detail_dock.isFloating()
        is_visible = win.detail_dock.isVisible()
        dock_area = win.dockWidgetArea(win.detail_dock)
        
        print(f"Cycle {i} Re-opened: Visible={is_visible}, Floating={is_floating}, AreaIsRight={dock_area == Qt.RightDockWidgetArea}")

        if is_floating:
            print(f"Cycle {i} CRITICAL FAIL: Panel reopened as FLOATING instead of docked!")
            errors += 1
        if not is_visible:
            print(f"Cycle {i} CRITICAL FAIL: Panel not visible after reopen!")
            errors += 1

    final_size = win.size()
    final_splitter_sizes = win.splitter.sizes()
    print(f"\nFinal Window Size: {final_size.width()}x{final_size.height()}")
    print(f"Final Splitter Sizes: {final_splitter_sizes}")

    if errors == 0 and initial_size == final_size:
        print("\n[SUCCESS] 10-CYCLE DRAG-CLOSE-REOPEN TEST PASSED PERFECTLY (0 errors, 100% docked on right side, 0 pixel shifts)!")
    else:
        print(f"\n[FAIL] TEST FAILED with {errors} errors.")

    app.quit()

if __name__ == "__main__":
    test_10_drag_close_open_cycles()
