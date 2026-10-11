# tests/test_notebooks_view.py
import sys
import os
import unittest
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure QApplication exists for widget testing
app = QApplication.instance() or QApplication(sys.argv)

import database
from ui.notebooks_view import NotebooksView, NotebookCardWidget
from ui.sidebar import Sidebar
from utils.i18n import t

class TestNotebooksViewAndSidebar(unittest.TestCase):
    def setUp(self):
        database.initialize_db()

    def test_notebook_card_widget(self):
        nb_data = {
            'id': 101,
            'name': 'Proje Alpha',
            'note_count': 7,
            'updated_at': '2026-10-09 12:00:00'
        }
        card = NotebookCardWidget(nb_data)
        self.assertEqual(card.nb_id, 101)
        self.assertEqual(card.nb_name, 'Proje Alpha')
        self.assertEqual(card.name_label.text(), 'Proje Alpha')
        self.assertIn('7', card.count_badge.text())

        # Test signals
        clicked_args = []
        card.clicked.connect(lambda i, n: clicked_args.append((i, n)))
        card.on_rename_clicked()
        card.on_delete_clicked()

    def test_notebooks_view_rendering_and_filter(self):
        view = NotebooksView()
        test_data = [
            {'id': 1, 'name': 'Zeta Notlar', 'note_count': 1, 'updated_at': '2026-10-09 10:00:00'},
            {'id': 2, 'name': 'Beta Projesi', 'note_count': 5, 'updated_at': '2026-10-09 12:00:00'},
            {'id': 3, 'name': 'Alfa Günlük', 'note_count': 0, 'updated_at': '2026-10-09 08:00:00'}
        ]
        view.set_notebooks(test_data)
        self.assertEqual(len(view.filtered_notebooks), 3)
        self.assertEqual(view.count_badge.text(), "3")
        self.assertFalse(view.empty_widget.isVisible())

        # Test search filter
        view.search_edit.setText("Beta")
        self.assertEqual(len(view.filtered_notebooks), 1)
        self.assertEqual(view.filtered_notebooks[0]['name'], 'Beta Projesi')

        # Test empty state
        view.search_edit.setText("BöyleBirDefterYok12345")
        self.assertEqual(len(view.filtered_notebooks), 0)
        self.assertFalse(view.empty_widget.isHidden())

        # Test clearing search restores all
        view.search_edit.setText("")
        self.assertEqual(len(view.filtered_notebooks), 3)

        # Test sorting name_asc
        idx = view.sort_combo.findData("name_asc")
        view.sort_combo.setCurrentIndex(idx)
        self.assertEqual(view.filtered_notebooks[0]['name'], 'Alfa Günlük')

        # Test sorting count_desc
        idx = view.sort_combo.findData("count_desc")
        view.sort_combo.setCurrentIndex(idx)
        self.assertEqual(view.filtered_notebooks[0]['name'], 'Beta Projesi')

    def test_sidebar_notebook_order_and_styling(self):
        sidebar = Sidebar()

        # Verify new_notebook_btn is before notebooks_header in main_layout
        layout = sidebar.main_layout
        idx_new_nb = layout.indexOf(sidebar.new_notebook_btn)
        idx_header = layout.indexOf(sidebar.notebooks_header)
        idx_list = layout.indexOf(sidebar.notebooks_list)

        self.assertNotEqual(idx_new_nb, -1, "new_notebook_btn should be in main_layout")
        self.assertNotEqual(idx_header, -1, "notebooks_header should be in main_layout")
        self.assertLess(idx_new_nb, idx_header, "new_notebook_btn must appear ABOVE notebooks_header")
        self.assertLess(idx_header, idx_list, "notebooks_header must appear ABOVE notebooks_list")

        # Verify no duplicate plus in new_notebook_label
        label_text = sidebar.new_notebook_label.text()
        self.assertFalse(label_text.strip().startswith("+"), f"new_notebook_label should not start with '+' but was '{label_text}'")

        # Verify all_notebooks_requested signal is fired when notebooks_header is clicked
        signal_fired = []
        sidebar.all_notebooks_requested.connect(lambda: signal_fired.append(True))
        sidebar.on_notebooks_header_clicked()
        self.assertTrue(len(signal_fired) > 0, "notebooks_header click must emit all_notebooks_requested")

        # Verify height calculation avoids clipping
        test_data = [{'id': i, 'name': f'Defter {i}', 'note_count': i} for i in range(1, 6)]
        sidebar.update_notebooks_list(test_data, limit=5)
        expected_min_height = 5 * 44 + 8 # 228px
        self.assertGreaterEqual(sidebar.notebooks_list.height(), expected_min_height)
        self.assertEqual(sidebar.notebooks_badge.text(), "5")

        # Verify limit 0 hides the list completely
        sidebar.update_notebooks_list(test_data, limit=0)
        self.assertEqual(sidebar.notebooks_list.count(), 0)
        self.assertFalse(sidebar.notebooks_list.isVisible())

        # Verify "Tümünü Göster..." is never added even when notebooks > limit
        sidebar.update_notebooks_list(test_data, limit=3)
        self.assertEqual(sidebar.notebooks_list.count(), 3)
        for i in range(sidebar.notebooks_list.count()):
            it = sidebar.notebooks_list.item(i)
            self.assertNotEqual(it.data(Qt.UserRole), -1)

    def test_notebook_recent_ordering(self):
        # Create notebooks and verify microsecond ordering
        t_now = time.time()
        id1 = database.create_notebook(f"Recent Test 1 {t_now}")
        id2 = database.create_notebook(f"Recent Test 2 {t_now}")
        id3 = database.create_notebook(f"Recent Test 3 {t_now}")
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertIsNotNone(id3)

        # Touch id1 -> it should be first
        database.touch_notebook(id1)
        nbs = database.get_notebooks(order_by_recent=True)
        self.assertEqual(nbs[0]['id'], id1)

        # Touch id2 -> id2 should now be first, id1 second
        database.touch_notebook(id2)
        nbs = database.get_notebooks(order_by_recent=True)
        self.assertEqual(nbs[0]['id'], id2)
        self.assertEqual(nbs[1]['id'], id1)

    def test_settings_dialog_zero_limit(self):
        from ui.settings_dialog import SettingsDialog
        dialog = SettingsDialog()
        idx_zero = dialog.sidebar_nb_combo.findData(0)
        self.assertTrue(idx_zero >= 0)
        dialog.set_settings("", "", 1, 1.5, "Koyu Gece", "tr", sidebar_notebooks_limit=0)
        self.assertEqual(dialog.sidebar_nb_combo.currentData(), 0)
        self.assertEqual(dialog.sidebar_nb_spin.value(), 0)
        settings = dialog.get_settings()
        self.assertEqual(settings['sidebar_notebooks_limit'], 0)

    def test_trash_title_i18n(self):
        from utils import i18n
        i18n.set_lang("tr")
        self.assertEqual(i18n.t("trash_title"), "Çöp Kutusu")
        i18n.set_lang("en")
        self.assertEqual(i18n.t("trash_title"), "Recycle Bin")

    def test_notes_renaming_and_card_badge(self):
        from utils import i18n
        i18n.set_lang("tr")
        self.assertEqual(i18n.t("notes"), "Notlar")
        self.assertEqual(i18n.t("view_all_notes"), "Notlar")

        nb_data = {'id': 201, 'name': 'Test Defter', 'note_count': 3}
        card = NotebookCardWidget(nb_data, highlight_color="#FF5500")
        self.assertEqual(card.count_badge.text().strip(), "3 Not")
        self.assertEqual(card.highlight_color, "#FF5500")

    def test_notes_view_back_btn_and_ctrl_a(self):
        from ui.notes_view import NotesView, NoteCardWidget
        notes_view = NotesView()
        
        # Initially (no notebook), back_btn is hidden
        self.assertTrue(notes_view.back_btn.isHidden())

        # When entering notebook context, back_btn becomes visible
        notes_view.set_notebook_context(notebook_id=42, notebook_name="Özel Defter")
        self.assertFalse(notes_view.back_btn.isHidden())
        self.assertEqual(notes_view.title_label.text(), "Özel Defter")

        # Verify back_to_notebooks_requested signal
        back_fired = []
        notes_view.back_to_notebooks_requested.connect(lambda: back_fired.append(True))
        notes_view.back_btn.click()
        self.assertEqual(len(back_fired), 1)

        # When leaving notebook context, back_btn hides
        notes_view.set_notebook_context(notebook_id=None, notebook_name=None)
        self.assertTrue(notes_view.back_btn.isHidden())

        # Test Ctrl+A / select_all_notes
        sample_notes = [
            {'id': 1001, 'title': 'N1', 'content': 'C1'},
            {'id': 1002, 'title': 'N2', 'content': 'C2'}
        ]
        notes_view.set_notes(sample_notes)
        self.assertEqual(len(notes_view.selected_note_ids), 0)
        
        notes_view.select_all_notes()
        self.assertEqual(len(notes_view.selected_note_ids), 2)
        self.assertIn(1001, notes_view.selected_note_ids)
        self.assertIn(1002, notes_view.selected_note_ids)

    def test_custom_theme_highlight_color(self):
        from ui.styles import get_palette
        p_dark = get_palette("Koyu Gece")
        self.assertEqual(p_dark.get("highlight_color"), "#8AB4F8")

        p_custom = get_palette("Özel Tema", {"highlight_color": "#FF00FF", "border_focus": "#00FF00"})
        self.assertEqual(p_custom.get("highlight_color"), "#FF00FF")
        self.assertEqual(p_custom.get("border_focus"), "#00FF00")

        # Verify NotebooksView apply_theme
        nb_view = NotebooksView()
        nb_view.apply_theme(p_custom)
        self.assertEqual(nb_view.highlight_color, "#FF00FF")

if __name__ == "__main__":
    unittest.main()
