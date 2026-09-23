import os
import sys
import tempfile
import unittest
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure QApplication exists for Qt widgets
app = QApplication.instance() or QApplication(sys.argv)

import database
from ui.styles import get_stylesheet
from ui.detail.note_section import NoteSection
from ui.notes_view import NoteCardWidget
from utils.i18n import t

class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        database.initialize_db()

    def test_scrollbar_styles(self):
        css = get_stylesheet("Koyu Gece")
        self.assertIn("QScrollBar:vertical", css)
        self.assertIn("QScrollBar:horizontal", css)
        self.assertIn("width: 10px;", css)
        self.assertIn("margin: 4px 2px 4px 2px;", css)
        self.assertIn("background: transparent;", css)
        print("  [OK] Modern scrollbar styles verified.")

    def test_workflow_library_deletion(self):
        lib_name = "Test_Wf_Lib_ToDelete"
        added = database.add_workflow_library(lib_name)
        self.assertTrue(added)
        
        wf_libs = database.get_workflow_libraries()
        lib_entry = next((l for l in wf_libs if l['name'] == lib_name), None)
        self.assertIsNotNone(lib_entry)
        lib_id = lib_entry['id']

        # Create dummy workflow file and image
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"test": 123}')
            dummy_wf_path = f.name

        try:
            wf_id = database.add_workflow(lib_id, "Test Workflow", dummy_wf_path, description="desc")
            self.assertIsNotNone(wf_id)
            
            # Check workflow is in library
            wfs = database.get_workflows_in_library(lib_id, show_hidden=True)
            self.assertEqual(len(wfs), 1)

            # Delete library
            del_result = database.delete_workflow_library(lib_id)
            self.assertTrue(del_result)

            # Verify library is gone
            wf_libs_after = database.get_workflow_libraries()
            self.assertFalse(any(l['id'] == lib_id for l in wf_libs_after))

            # Verify workflows in library are gone
            wfs_after = database.get_workflows_in_library(lib_id, show_hidden=True)
            self.assertEqual(len(wfs_after), 0)
            print("  [OK] Workflow library deletion and cascading workflow removal verified.")
        finally:
            if os.path.exists(dummy_wf_path):
                os.remove(dummy_wf_path)

    def test_note_timestamp_display(self):
        note_sec = NoteSection()
        # New note with no id
        note_sec.set_note({'title': 'Draft', 'content': 'hello'})
        self.assertIn(t("note_not_saved_yet"), note_sec.note_timestamps_label.text())

        # Saved note with timestamps
        note_data = {
            'id': 9999,
            'title': 'Saved Note',
            'content': '<p>content</p>',
            'created_at': '2026-09-19 14:00:00',
            'updated_at': '2026-09-19 14:30:00'
        }
        note_sec.set_note(note_data)
        txt = note_sec.note_timestamps_label.text()
        self.assertIn("19.09.2026", txt)
        self.assertIn("14:00", txt)
        self.assertIn("14:30", txt)
        print("  [OK] NoteSection timestamps formatting verified.")

        # NoteCardWidget
        card = NoteCardWidget(note_data)
        self.assertTrue(hasattr(card, 'date_label'))
        self.assertIn("19.09.2026", card.date_label.text())
        print("  [OK] NoteCardWidget date_label verified.")

if __name__ == "__main__":
    unittest.main()
