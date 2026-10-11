import os
import sys
import unittest
import tempfile
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import database
from PySide6.QtWidgets import QApplication

# Ensure single QGuiApplication / QApplication instance for UI component tests
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)


class TestNotebooksAndTags(unittest.TestCase):
    def setUp(self):
        # Use temporary database for clean isolation
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        database.DB_NAME = self.temp_db_path
        if hasattr(database._thread_local, 'conn'):
            try:
                database._thread_local.conn.close()
            except Exception:
                pass
            database._thread_local.conn = None
        database.initialize_db()

    def tearDown(self):
        if hasattr(database._thread_local, 'conn') and database._thread_local.conn:
            try:
                database._thread_local.conn.close()
            except Exception:
                pass
            database._thread_local.conn = None
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_notebook_crud_and_recent_order(self):
        # 1. Create notebooks
        nb1_id = database.create_notebook("Proje A")
        nb2_id = database.create_notebook("Proje B")
        self.assertIsNotNone(nb1_id)
        self.assertIsNotNone(nb2_id)

        # 2. Get notebooks
        all_nbs = database.get_notebooks(order_by_recent=False)
        self.assertEqual(len(all_nbs), 2)
        names = [nb['name'] for nb in all_nbs]
        self.assertIn("Proje A", names)
        self.assertIn("Proje B", names)

        # 3. Touch notebook A to make it most recent
        database.touch_notebook(nb1_id)
        recent_nbs = database.get_notebooks(order_by_recent=True)
        self.assertEqual(recent_nbs[0]['id'], nb1_id)

        # 4. Rename notebook B
        database.update_notebook_name(nb2_id, "Proje B (Revize)")
        updated_nb2 = database.get_notebook_by_id(nb2_id)
        self.assertEqual(updated_nb2['name'], "Proje B (Revize)")

    def test_notebook_deletion_unassigns_notes(self):
        # Create notebook
        nb_id = database.create_notebook("Geçici Defter")

        # Create note assigned to notebook
        note_id = database.save_note(None, "Önemli Not", "<p>İçerik</p>", notebook_id=nb_id)
        note = database.get_note_by_id(note_id)
        self.assertEqual(note['notebook_id'], nb_id)
        self.assertEqual(note['notebook_name'], "Geçici Defter")

        # Delete notebook - Note MUST NOT be deleted, notebook_id should become NULL
        database.delete_notebook(nb_id)
        note_after = database.get_note_by_id(note_id)
        self.assertIsNotNone(note_after)
        self.assertIsNone(note_after['notebook_id'])
        self.assertEqual(note_after['is_deleted'], 0)

    def test_note_tags_crud_and_clear_all(self):
        # Create note
        note_id = database.save_note(None, "Etiketli Not", "<p>Metin</p>")

        # Add tags
        database.add_note_tag(note_id, "ai")
        database.add_note_tag(note_id, "comfyui")
        database.add_note_tag(note_id, "prompt")

        tags = database.get_note_tags(note_id)
        self.assertEqual(sorted(tags), ["ai", "comfyui", "prompt"])

        # Check all tags across system
        all_tags = database.get_all_note_tags()
        self.assertIn("ai", all_tags)
        self.assertIn("comfyui", all_tags)

        # Delete one tag
        database.delete_note_tag(note_id, "comfyui")
        tags_after_del = database.get_note_tags(note_id)
        self.assertEqual(sorted(tags_after_del), ["ai", "prompt"])

        # Set tags list
        database.set_note_tags(note_id, ["yeni_tag1", "yeni_tag2"])
        tags_set = database.get_note_tags(note_id)
        self.assertEqual(sorted(tags_set), ["yeni_tag1", "yeni_tag2"])

        # Clear all tags directly ("Temizle" feature)
        database.clear_note_tags(note_id)
        tags_cleared = database.get_note_tags(note_id)
        self.assertEqual(tags_cleared, [])

    def test_get_notes_filtering_scope_and_tags(self):
        nb1 = database.create_notebook("İş Notları")
        nb2 = database.create_notebook("Kişisel Notlar")

        # Note 1: Unassigned (no notebook), tag 'fikir'
        n1 = database.save_note(None, "Deftersiz Not", "<p>Fikirler</p>")
        database.add_note_tag(n1, "fikir")

        # Note 2: In nb1, tag 'fikir' and 'is'
        n2 = database.save_note(None, "İş Projesi", "<p>Toplantı</p>", notebook_id=nb1)
        database.add_note_tag(n2, "fikir")
        database.add_note_tag(n2, "is")

        # Note 3: In nb2, tag 'hobi'
        n3 = database.save_note(None, "Kişisel Plan", "<p>Gezi</p>", notebook_id=nb2)
        database.add_note_tag(n3, "hobi")

        # Scope 'unassigned' should only return Note 1
        unassigned_notes = database.get_notes(scope="unassigned")
        unassigned_ids = [n['id'] for n in unassigned_notes]
        self.assertIn(n1, unassigned_ids)
        self.assertNotIn(n2, unassigned_ids)
        self.assertNotIn(n3, unassigned_ids)

        # Scope None (Tüm Notlar) should return all 3 notes
        all_notes = database.get_notes(scope=None)
        all_ids = [n['id'] for n in all_notes]
        self.assertIn(n1, all_ids)
        self.assertIn(n2, all_ids)
        self.assertIn(n3, all_ids)

        # By notebook_id=nb1
        nb1_notes = database.get_notes(notebook_id=nb1)
        nb1_ids = [n['id'] for n in nb1_notes]
        self.assertEqual(nb1_ids, [n2])

        # By tag 'fikir' (should return n1 and n2)
        fikir_notes = database.get_notes(tag="fikir")
        fikir_ids = [n['id'] for n in fikir_notes]
        self.assertIn(n1, fikir_ids)
        self.assertIn(n2, fikir_ids)
        self.assertNotIn(n3, fikir_ids)

    def test_sidebar_notebooks_limit_setting(self):
        default_limit = database.get_setting("sidebar_notebooks_limit", "5")
        self.assertEqual(str(default_limit), "5")

        database.set_setting("sidebar_notebooks_limit", "8")
        saved_limit = database.get_setting("sidebar_notebooks_limit")
        self.assertEqual(saved_limit, "8")

    def test_ui_components_integration(self):
        from ui.notes_view import NotesView, NoteCardWidget
        from ui.detail.note_section import NoteSection

        # Test NotesView header elements
        notes_view = NotesView()
        self.assertIsNotNone(notes_view.scope_combo)
        self.assertIsNotNone(notes_view.tag_combo)
        self.assertFalse(notes_view.scope_combo.isHidden())

        # Test NoteCardWidget with notebook and tags
        note_dict = {
            'id': 99,
            'title': 'Test Kartı',
            'content': '<p>Kart İçeriği</p>',
            'notebook_name': 'Test Defter',
            'tags': ['tag1', 'tag2'],
            'created_at': '2026-10-09 00:00:00',
            'updated_at': '2026-10-09 00:00:00',
            'is_favorite': 0,
            'is_hidden': 0
        }
        card = NoteCardWidget(note_dict)
        self.assertIn('Test Defter', card.tags_label.toolTip())
        self.assertIn('#tag1', card.tags_label.toolTip())

        # Test NoteSection notebook selector and clear tags button
        note_section = NoteSection()
        self.assertIsNotNone(note_section.notebook_combo)
        self.assertIsNotNone(note_section.clear_tags_btn)

        # Test Sidebar.update_notebooks_list keyword arguments
        from ui.sidebar import Sidebar
        sidebar = Sidebar()
        test_nbs = [{'id': 1, 'name': 'Defter 1', 'note_count': 3}, {'id': 2, 'name': 'Defter 2', 'note_count': 0}]
        # Call with active_id and limit keyword arguments as in main.py
        sidebar.update_notebooks_list(test_nbs, active_id=1, limit=5)
        self.assertEqual(sidebar.notebooks_list.count(), 2)
        # Call with positional argument as in sidebar context menu
        sidebar.update_notebooks_list(test_nbs, 2)
        self.assertEqual(sidebar.notebooks_list.count(), 2)


if __name__ == "__main__":
    unittest.main()
