# tests/test_icons.py
import unittest
import os
import sys
from PySide6.QtWidgets import QApplication
from utils.icon_manager import get_icon, get_pixmap, ICON_MAP, get_icons_dir

# Ensure QApplication instance
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestIconManager(unittest.TestCase):
    def test_icons_dir_exists(self):
        icon_dir = get_icons_dir()
        self.assertTrue(os.path.isdir(icon_dir), f"Icon directory not found: {icon_dir}")

    def test_all_mapped_icons_load(self):
        for name in ICON_MAP:
            pixmap = get_pixmap(name, "#8AB4F8", 18)
            self.assertFalse(pixmap.isNull(), f"Failed to load pixmap for alias: {name}")
            self.assertEqual(pixmap.width(), 18)
            self.assertEqual(pixmap.height(), 18)

            icon = get_icon(name, "#E3E3E3", 18)
            self.assertFalse(icon.isNull(), f"Failed to load icon for alias: {name}")

    def test_sidebar_uses_vector_icons(self):
        from ui.sidebar import Sidebar
        sidebar = Sidebar()
        # Verify sidebar button icons are set
        self.assertFalse(sidebar.home_icon.pixmap().isNull())
        self.assertFalse(sidebar.agenda_icon.pixmap().isNull())
        self.assertFalse(sidebar.all_notes_icon.pixmap().isNull())
        self.assertFalse(sidebar.trash_icon.pixmap().isNull())
        self.assertFalse(sidebar.settings_icon.pixmap().isNull())
        self.assertFalse(sidebar.new_note_btn.icon().isNull())
        self.assertFalse(sidebar.new_lib_btn.icon().isNull())
        # Verify section headers have vector icons
        self.assertFalse(sidebar.models_icon.pixmap().isNull())
        self.assertFalse(sidebar.lib_icon.pixmap().isNull())
        # Verify subitems do NOT have icons
        sidebar.update_models_list([("Lora Modelleri", 10), ("Checkpoint Modelleri", 5)])
        self.assertTrue(sidebar.models_list.item(0).icon().isNull())
        self.assertTrue(sidebar.models_list.item(1).icon().isNull())

    def test_notes_view_trash_icon(self):
        from ui.notes_view import NotesView
        notes_view = NotesView()
        self.assertFalse(notes_view.empty_trash_btn.icon().isNull())
        self.assertFalse(notes_view.new_note_btn.icon().isNull())

    def test_welcome_screen_home_settings_icon(self):
        from ui.welcome_screen import WelcomeScreen
        ws = WelcomeScreen()
        self.assertFalse(ws.home_settings_btn.icon().isNull())

if __name__ == "__main__":
    unittest.main()
