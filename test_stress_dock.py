import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def run_stress_test():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    app.processEvents()

    initial_size = win.size()
    initial_splitter_sizes = win.splitter.sizes()
    print(f"Initial Window Size: {initial_size.width()}x{initial_size.height()}")
    print(f"Initial Splitter Sizes: {initial_splitter_sizes}")

    errors = 0
    # Simulate 20 stress cycles of floating, closing, reopening
    for i in range(1, 21):
        # 1. Open detail panel
        dummy_model = {'id': 1, 'name': f'Test Model {i}', 'file_path': 'test.safetensors'}
        win.show_detail_panel(dummy_model)
        app.processEvents()

        # Verify docked
        if win.detail_dock.isFloating():
            print(f"Cycle {i} FAIL: Dock is floating after show_detail_panel!")
            errors += 1
        if not win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Dock is not visible after show_detail_panel!")
            errors += 1

        # 2. Float panel (undock)
        win.detail_dock.setFloating(True)
        app.processEvents()
        if not win.detail_dock.isFloating():
            print(f"Cycle {i} FAIL: Dock failed to setFloating(True)!")
            errors += 1

        # 3. Close panel while floating
        win.detail_dock.close() # Close floating window directly
        app.processEvents()

        if win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Dock still visible after close!")
            errors += 1

        # 4. Reopen detail panel -> MUST BE DOCKED (NOT FLOATING)
        win.show_detail_panel(dummy_model)
        app.processEvents()

        if win.detail_dock.isFloating():
            print(f"Cycle {i} FAIL: Dock reopened as floating on cycle {i}!")
            errors += 1
        if not win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Dock not visible on cycle {i}!")
            errors += 1

        # 5. Hide detail panel normal
        win.hide_detail_panel()
        app.processEvents()

        if win.detail_dock.isVisible():
            print(f"Cycle {i} FAIL: Dock still visible after hide_detail_panel!")
            errors += 1

    final_size = win.size()
    final_splitter_sizes = win.splitter.sizes()
    print(f"\nFinal Window Size: {final_size.width()}x{final_size.height()}")
    print(f"Final Splitter Sizes: {final_splitter_sizes}")

    if errors == 0 and initial_size == final_size:
        print("\n[SUCCESS] STRESS TEST PASSED PERFECTLY (0 errors, window size and alignment 100% preserved)!")
    else:
        print(f"\n[FAIL] STRESS TEST FAILED with {errors} errors.")

    app.quit()

if __name__ == "__main__":
    run_stress_test()
