# tests/test_model_selection_and_deletion.py
import sys
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QMouseEvent, QKeyEvent

from ui.library_view import ModelCardWidget, LibraryView
import database
from utils.i18n import t

def test_card_checkbox_visibility_and_ctrl_click():
    app = QApplication.instance() or QApplication(sys.argv)

    model_data = {
        'id': 991,
        'name': 'Test Model 1',
        'file_path': 'C:/non_existent_model_file.safetensors',
        'is_favorite': 0
    }
    card = ModelCardWidget(model_data)
    card.show()
    app.processEvents()

    # 1. By default, select_btn must be hidden!
    assert not card.select_btn.isVisible(), 'Checkbox must NOT be visible initially'

    # 2. Ctrl + click should toggle selection
    press_ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card.mousePressEvent(press_ev)
    release_ev = QMouseEvent(QEvent.Type.MouseButtonRelease, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card.mouseReleaseEvent(release_ev)

    assert card.is_selected, 'Card must be selected after Ctrl+Click'

    # 3. set_checkbox_visible
    card.set_checkbox_visible(True)
    assert card.select_btn.isVisible()
    card.set_checkbox_visible(False)
    assert not card.select_btn.isVisible()

    card.prepare_for_deletion()
    card.close()

def test_missing_on_disk_warning_badge():
    app = QApplication.instance() or QApplication(sys.argv)

    # Missing file
    card_missing = ModelCardWidget({'id': 992, 'name': 'Missing Model', 'file_path': 'C:/definitely_fake_model.safetensors'})
    card_missing.show()
    card_missing.set_file_exists(False)
    app.processEvents()
    assert card_missing.warning_badge is not None
    assert not card_missing.warning_badge.isHidden()
    assert card_missing.warning_badge.text() == t('not_on_disk')

    # Existing file (known path sys.executable)
    card_exists = ModelCardWidget({'id': 993, 'name': 'Existing Model', 'file_path': sys.executable})
    card_exists.set_file_exists(True)
    if getattr(card_exists, 'warning_badge', None):
        assert not card_exists.warning_badge.isVisible()

    card_missing.prepare_for_deletion()
    card_missing.close()
    card_exists.prepare_for_deletion()
    card_exists.close()

def test_library_view_selection_mode_and_bulk_bar():
    app = QApplication.instance() or QApplication(sys.argv)

    lib_view = LibraryView()
    lib_view.resize(900, 600)
    lib_view.show()

    mock_models = [
        {'id': 101, 'name': 'Model 101', 'file_path': 'C:/fake1.safetensors', 'is_favorite': 0, 'tags': []},
        {'id': 102, 'name': 'Model 102', 'file_path': 'C:/fake2.safetensors', 'is_favorite': 0, 'tags': []},
        {'id': 103, 'name': 'Model 103', 'file_path': 'C:/fake3.safetensors', 'is_favorite': 0, 'tags': []},
    ]

    lib_view.set_library('Test Library', mock_models)
    app.processEvents()

    # All cards must have checkboxes hidden initially
    for card in lib_view.cards:
        if isinstance(card, ModelCardWidget):
            assert not card.select_btn.isVisible(), 'All checkboxes should be hidden when no selection is active'

    # Ctrl+Click first card
    card1 = lib_view.cards[0]
    press_ev = QMouseEvent(QEvent.Type.MouseButtonPress, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card1.mousePressEvent(press_ev)
    release_ev = QMouseEvent(QEvent.Type.MouseButtonRelease, QPoint(50, 50), Qt.LeftButton, Qt.LeftButton, Qt.ControlModifier)
    card1.mouseReleaseEvent(release_ev)
    app.processEvents()

    assert 101 in lib_view.selected_model_ids
    assert lib_view.bulk_bar.isVisible()

    # Now ALL cards should have visible checkboxes
    for card in lib_view.cards:
        if isinstance(card, ModelCardWidget):
            assert card.select_btn.isVisible(), 'All checkboxes must become visible when selection mode starts'

    # Select Missing Cards
    for card in lib_view.cards:
        if isinstance(card, ModelCardWidget):
            card.file_exists = False
    lib_view.select_missing_cards()
    assert len(lib_view.selected_model_ids) == 3

    # Clear Selection -> All checkboxes should become invisible again!
    lib_view.clear_selection()
    assert len(lib_view.selected_model_ids) == 0
    assert not lib_view.bulk_bar.isVisible()
    for card in lib_view.cards:
        if isinstance(card, ModelCardWidget):
            assert not card.select_btn.isVisible(), 'Checkboxes must be hidden again when selection is cleared'

    lib_view.close()

def test_database_delete_model():
    dummy_path = 'C:/test_dummy_model_to_delete.safetensors'
    database.register_model(1, 'Dummy Model Delete Test', dummy_path, 'dummyhash123')
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM models WHERE file_path = ?;', (dummy_path,))
        row = cursor.fetchone()
        assert row is not None
        m_id = row['id']

    database.add_model_tag(m_id, 'test_tag')
    database.add_trigger_word(m_id, 'test_trigger')

    success = database.delete_model(m_id)
    assert success is True

    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM models WHERE id = ?;', (m_id,))
        assert cursor.fetchone() is None
        cursor.execute('SELECT tag_id FROM model_tags WHERE model_id = ?;', (m_id,))
        assert cursor.fetchone() is None
        cursor.execute('SELECT id FROM trigger_words WHERE model_id = ?;', (m_id,))
        assert cursor.fetchone() is None

    dummy_path2 = 'C:/test_dummy2.safetensors'
    dummy_path3 = 'C:/test_dummy3.safetensors'
    database.register_model(1, 'Dummy 2', dummy_path2, 'hash2')
    database.register_model(1, 'Dummy 3', dummy_path3, 'hash3')
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM models WHERE file_path IN (?, ?);', (dummy_path2, dummy_path3))
        ids = [r['id'] for r in cursor.fetchall()]
        assert len(ids) == 2

    assert database.delete_models(ids) is True
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM models WHERE id IN (?, ?);', tuple(ids))
        assert len(cursor.fetchall()) == 0

if __name__ == '__main__':
    print('Running Model Selection and Deletion Tests...')
    test_card_checkbox_visibility_and_ctrl_click()
    print('  [OK] test_card_checkbox_visibility_and_ctrl_click passed')
    test_missing_on_disk_warning_badge()
    print('  [OK] test_missing_on_disk_warning_badge passed')
    test_library_view_selection_mode_and_bulk_bar()
    print('  [OK] test_library_view_selection_mode_and_bulk_bar passed')
    test_database_delete_model()
    print('  [OK] test_database_delete_model passed')
    print('ALL SELECTION AND DELETION TESTS PASSED SUCCESSFULLY!')
