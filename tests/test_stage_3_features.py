"""
Automated tests for Aşama 3:
- Toast / Snackbar Notification System
- ModelCardWidget QDrag & Multi-Select
- LibraryView Bulk Action Bar & Operations
- i18n Translation Completeness & Parity
"""
import sys
import os

# Set headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote")

from PySide6.QtWidgets import QApplication, QWidget, QFrame
from PySide6.QtCore import Qt, QPoint, QEvent, QUrl
from PySide6.QtGui import QMouseEvent, QResizeEvent, QGuiApplication

import database
from utils import i18n
from ui.widgets.toast import ToastWidget, show_toast, _window_toasts
from ui.library_view import ModelCardWidget, LibraryView
from ui.main_window import MainWindow

def test_i18n_parity():
    print("Testing i18n translation parity...")
    tr_dict = i18n.TRANSLATIONS["tr"]
    en_dict = i18n.TRANSLATIONS["en"]

    new_keys = [
        "toast_copied", "toast_scan_completed", "toast_saved",
        "bulk_models_selected_count", "bulk_select_all", "bulk_clear_selection",
        "bulk_add_tag", "bulk_remove_tag", "bulk_set_fav",
        "bulk_add_tag_title", "bulk_add_tag_label",
        "bulk_remove_tag_title", "bulk_remove_tag_label",
        "bulk_fav_done", "bulk_tag_done", "bulk_tag_removed"
    ]

    for key in new_keys:
        assert key in tr_dict, f"Missing key in TR: {key}"
        assert key in en_dict, f"Missing key in EN: {key}"
        assert len(tr_dict[key].strip()) > 0, f"Empty TR string for: {key}"
        assert len(en_dict[key].strip()) > 0, f"Empty EN string for: {key}"

    print(f"  [OK] All {len(new_keys)} Stage 3 translation keys verified in TR and EN.")

def test_toast_system(app):
    print("Testing Toast / Snackbar system...")
    win = QWidget()
    win.resize(800, 600)
    win.show()

    # 1. Single toast creation
    t1 = show_toast(win, "Test message 1", "info", duration_ms=1000)
    assert t1 is not None
    assert t1.text_label.text() == "Test message 1"
    assert t1.isVisible()

    # Check positioning at bottom right
    expected_x = win.width() - t1.width() - 24
    expected_y = win.height() - t1.height() - 24
    assert t1.x() == expected_x
    assert t1.y() == expected_y

    # 2. Toast stacking
    t2 = show_toast(win, "Test message 2", "success", duration_ms=1000)
    assert t2 in _window_toasts[win]
    assert len(_window_toasts[win]) == 2
    # t2 should be stacked above t1
    assert t2.y() < t1.y()

    # 3. Window resize repositioning
    win.resize(1000, 700)
    # Deliver resize event
    QApplication.sendEvent(win, QResizeEvent(win.size(), win.size()))
    assert t1.x() == 1000 - t1.width() - 24

    # 4. Dismiss
    t1.dismiss()
    t2.dismiss()
    t1._on_fade_out_finished()
    t2._on_fade_out_finished()
    assert win not in _window_toasts or len(_window_toasts[win]) == 0

    win.close()
    print("  [OK] ToastWidget positioning, stacking, and dismissal verified.")

def test_model_card_selection_and_drag(app):
    print("Testing ModelCardWidget selection and drag data...")
    test_data = {
        'id': 101,
        'name': 'SDXL Turbo Model',
        'file_path': r'C:\models\sdxl_turbo.safetensors',
        'image_path': '',
        'is_favorite': 0
    }

    card = ModelCardWidget(test_data)
    card.show()

    # 1. Selection toggle
    assert not card.is_selected
    signals_received = []
    card.selection_toggled.connect(lambda d, s: signals_received.append((d['id'], s)))

    # Toggle via select_btn click
    card.on_select_clicked()
    assert card.is_selected
    assert card.select_btn.text() == "✓"
    assert len(signals_received) == 1
    assert signals_received[0] == (101, True)

    card.on_select_clicked()
    assert not card.is_selected
    assert card.select_btn.text() == ""
    assert len(signals_received) == 2
    assert signals_received[1] == (101, False)

    # 2. Ctrl+Click selection toggle
    # Press event
    press_ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card.mousePressEvent(press_ev)
    assert card.drag_start_pos == QPoint(50, 50)

    # Release event with Ctrl
    release_ev = QMouseEvent(QEvent.Type.MouseButtonRelease, QPoint(52, 52), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card.mouseReleaseEvent(release_ev)
    assert card.is_selected
    assert len(signals_received) == 3
    assert signals_received[2] == (101, True)

    # 3. Normal click without Ctrl
    click_signals = []
    card.clicked.connect(lambda d: click_signals.append(d['id']))

    card.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    card.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPoint(51, 51), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier))
    assert len(click_signals) == 1
    assert click_signals[0] == 101

    card.prepare_for_deletion()
    card.close()
    print("  [OK] ModelCardWidget selection and click distinction verified.")

def test_library_view_bulk_bar(app):
    print("Testing LibraryView bulk action bar & operations...")
    lib_view = LibraryView()
    lib_view.resize(900, 600)
    lib_view.show()

    mock_models = [
        {'id': 1, 'name': 'Model A', 'file_path': r'C:\models\a.safetensors', 'is_favorite': 0, 'tags': []},
        {'id': 2, 'name': 'Model B', 'file_path': r'C:\models\b.safetensors', 'is_favorite': 1, 'tags': ['anime']},
        {'id': 3, 'name': 'Model C', 'file_path': r'C:\models\c.safetensors', 'is_favorite': 0, 'tags': ['photo']},
    ]

    lib_view.set_library("Lora Modelleri", mock_models)
    # Finish incremental loading immediately
    if getattr(lib_view, 'loading_timer', None):
        while lib_view.loading_timer.isActive():
            app.processEvents()
    else:
        app.processEvents()

    assert len(lib_view.cards) == 3
    assert not lib_view.bulk_bar.isVisible()

    # 1. Select card 1
    card1 = lib_view.cards[0]
    card1.on_select_clicked()
    assert 1 in lib_view.selected_model_ids
    assert lib_view.bulk_bar.isVisible()
    assert "1" in lib_view.bulk_count_label.text()

    # 2. Select All
    lib_view.select_all_cards()
    assert len(lib_view.selected_model_ids) == 3
    assert "3" in lib_view.bulk_count_label.text()
    for c in lib_view.cards:
        assert c.is_selected

    # 3. Bulk signals
    fav_reqs = []
    lib_view.bulk_favorite_requested.connect(lambda ids, fav: fav_reqs.append((sorted(ids), fav)))
    lib_view.on_bulk_fav_clicked(True)
    assert len(fav_reqs) == 1
    assert fav_reqs[0] == ([1, 2, 3], True)

    tag_add_reqs = []
    lib_view.bulk_add_tag_requested.connect(lambda ids: tag_add_reqs.append(sorted(ids)))
    lib_view.on_bulk_add_tag_clicked()
    assert len(tag_add_reqs) == 1
    assert tag_add_reqs[0] == [1, 2, 3]

    # 4. Clear Selection
    lib_view.clear_selection()
    assert len(lib_view.selected_model_ids) == 0
    assert not lib_view.bulk_bar.isVisible()
    for c in lib_view.cards:
        assert not c.is_selected

    # 5. Esc key clears selection
    card1.on_select_clicked()
    assert lib_view.bulk_bar.isVisible()
    from PySide6.QtGui import QKeyEvent
    esc_event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    lib_view.keyPressEvent(esc_event)
    assert len(lib_view.selected_model_ids) == 0
    assert not lib_view.bulk_bar.isVisible()

    lib_view.close()
    print("  [OK] LibraryView bulk action bar, Select All, Clear, and Escape verified.")

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    database.initialize_db()

    test_i18n_parity()
    test_toast_system(app)
    test_model_card_selection_and_drag(app)
    test_library_view_bulk_bar(app)

    print("\n==========================================")
    print("ALL STAGE 3 AUTOMATED TESTS PASSED SUCCESSFULLY! [OK]")
    print("==========================================")

if __name__ == "__main__":
    main()
