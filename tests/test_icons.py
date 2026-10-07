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
        self.assertFalse(sidebar.brand_logo.pixmap().isNull())

    def test_notes_view_trash_icon(self):
        from ui.notes_view import NotesView
        notes_view = NotesView()
        self.assertFalse(notes_view.empty_trash_btn.icon().isNull())
        self.assertFalse(notes_view.new_note_btn.icon().isNull())
        self.assertFalse(notes_view.fav_toggle_btn.icon().isNull())

    def test_welcome_screen_home_settings_icon(self):
        from ui.welcome_screen import WelcomeScreen
        ws = WelcomeScreen()
        self.assertFalse(ws.home_settings_btn.icon().isNull())

    def test_library_view_icons(self):
        from ui.library_view import LibraryView
        lv = LibraryView()
        self.assertFalse(lv.fav_toggle_btn.icon().isNull())
        self.assertFalse(lv.scan_btn.icon().isNull())
        self.assertFalse(lv.bulk_fav_btn.icon().isNull())
        self.assertFalse(lv.bulk_add_tag_btn.icon().isNull())
        self.assertFalse(lv.bulk_delete_btn.icon().isNull())

    def test_workflow_view_icons(self):
        from ui.workflow_view import WorkflowView
        wv = WorkflowView()
        self.assertFalse(wv.fav_toggle_btn.icon().isNull())
        self.assertFalse(wv.add_btn.icon().isNull())
        self.assertFalse(wv.delete_lib_btn.icon().isNull())

    def test_theme_aware_active_colors(self):
        from ui.sidebar import Sidebar
        from ui.styles import get_palette
        sidebar = Sidebar()
        purple_pal = get_palette("Derin Mor")
        sidebar.apply_theme(purple_pal)
        self.assertEqual(sidebar.get_active_color(), "#D7AEF5")
        self.assertFalse(sidebar.brand_logo.pixmap().isNull())
        self.assertEqual(sidebar.brand_logo.width(), 32)
        self.assertEqual(sidebar.brand_logo.height(), 32)

    def test_sidebar_collapsible_rail_mode(self):
        from ui.sidebar import Sidebar
        sidebar = Sidebar()
        self.assertFalse(sidebar.collapse_btn.icon().isNull())
        self.assertFalse(sidebar.lock_badge.pixmap().isNull())
        
        # Test collapse
        sidebar.set_collapsed(True)
        self.assertTrue(sidebar.is_collapsed)
        self.assertEqual(sidebar.width(), 64)
        self.assertTrue(sidebar.brand_label.isHidden())
        self.assertTrue(sidebar.home_label.isHidden())
        self.assertTrue(sidebar.all_notes_label.isHidden())
        self.assertTrue(sidebar.models_list.isHidden())
        self.assertEqual(sidebar.home_btn.width(), 44)

        # Test expand
        sidebar.set_collapsed(False)
        self.assertFalse(sidebar.is_collapsed)
        self.assertEqual(sidebar.width(), 260)
        self.assertFalse(sidebar.brand_label.isHidden())
        self.assertFalse(sidebar.home_label.isHidden())
        self.assertFalse(sidebar.all_notes_label.isHidden())
        self.assertEqual(sidebar.home_btn.width(), 236)

    def test_incognito_mode_no_layout_shift(self):
        from ui.sidebar import Sidebar
        sidebar = Sidebar()
        sidebar.set_collapsed(False)
        initial_label_text = sidebar.brand_label.text()
        initial_width = sidebar.width()

        # Enter incognito
        sidebar.set_incognito_active(True)
        self.assertEqual(sidebar.brand_label.text(), initial_label_text) # Must stay "Vera Note"
        self.assertEqual(sidebar.width(), initial_width) # Width must NOT expand
        self.assertFalse(sidebar.lock_badge.isHidden())

        # Exit incognito
        sidebar.set_incognito_active(False)
        self.assertEqual(sidebar.brand_label.text(), initial_label_text)
        self.assertTrue(sidebar.lock_badge.isHidden())

    def test_notes_view_favorite_filter_preserved_on_unfavorite(self):
        from ui.notes_view import NotesView
        nv = NotesView()
        test_notes = [
            {"id": 1, "title": "Note 1", "content": "Text 1", "is_favorite": 1, "created_at": "2026-10-01", "updated_at": "2026-10-01"},
            {"id": 2, "title": "Note 2", "content": "Text 2", "is_favorite": 1, "created_at": "2026-10-01", "updated_at": "2026-10-01"},
        ]
        nv.set_notes(test_notes)
        nv.fav_toggle_btn.setChecked(True)
        nv.on_filter_changed()
        self.assertTrue(nv.fav_toggle_btn.isChecked())

        # Un-favorite card 1
        nv.on_card_favorite_toggled(1, False)
        # Verify favorite filter remains active!
        self.assertTrue(nv.fav_toggle_btn.isChecked())
        # Only Note 2 should remain visible in cards
        visible_cards = [c for c in nv.cards if not c.isHidden()]
        self.assertEqual(len(visible_cards), 1)
        self.assertEqual(visible_cards[0].note_data["id"], 2)

    def test_fav_toggle_button_states(self):
        from ui.library_view import LibraryView
        lv = LibraryView()
        self.assertFalse(lv.fav_toggle_btn.isChecked())
        # Simulate toggle
        lv.fav_toggle_btn.setChecked(True)
        lv.on_fav_toggle_clicked()
        self.assertTrue(lv.fav_toggle_btn.isChecked())
        self.assertFalse(lv.fav_toggle_btn.icon().isNull())

    def test_i18n_no_emojis(self):
        import re
        from utils.i18n import TRANSLATIONS
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]')
        for lang in ['tr', 'en']:
            for k, v in TRANSLATIONS[lang].items():
                self.assertIsNone(emoji_pattern.search(v), f"Found emoji in {lang}.{k}: {v}")

if __name__ == "__main__":
    unittest.main()
