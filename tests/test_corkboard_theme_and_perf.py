import unittest
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
import sys

from ui.welcome_screen import WelcomeScreen
from ui.corkboard.dialogs import HomePageSettingsDialog
from ui.corkboard.cards import QuickNoteCardWidget, CorkboardNoteCard
from ui.notes_view import NotesView, html_to_plain

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestCorkboardThemeAndPerf(unittest.TestCase):
    def setUp(self):
        self.welcome = WelcomeScreen()
        self.custom_palette = {
            "highlight_color": "#FF55AA",
            "accent_color": "#AA0055"
        }
        self.welcome.apply_theme(self.custom_palette)

    def test_home_settings_dialog_inherits_theme_colors(self):
        dialog = HomePageSettingsDialog(self.welcome)
        self.assertEqual(dialog.highlight_color, "#FF55AA")
        self.assertEqual(dialog.accent_color, "#AA0055")
        
        # Verify dialog stylesheet contains custom colors instead of hardcoded blue
        qss = dialog.styleSheet()
        self.assertIn("#FF55AA", qss)
        self.assertIn("#AA0055", qss)
        self.assertNotIn("#8AB4F8", qss)
        self.assertNotIn("#1A73E8", qss)

        # Verify combo box stylesheet contains custom accent
        combo_qss = dialog.coord_mode_combo.styleSheet()
        self.assertIn("#AA0055", combo_qss)

    def test_quick_note_card_theme_colors(self):
        qn = QuickNoteCardWidget(highlight_color="#FF55AA", accent_color="#AA0055")
        self.assertIn("#AA0055", qn.save_btn.styleSheet())
        
        # Test apply_theme updates save button
        qn.apply_theme("#10B981", "#059669")
        self.assertEqual(qn.highlight_color, "#10B981")
        self.assertEqual(qn.accent_color, "#059669")
        self.assertIn("#059669", qn.save_btn.styleSheet())

    def test_corkboard_note_card_theme_colors(self):
        note_data = {'id': 1, 'title': 'Test', 'content': 'Sample content'}
        card = CorkboardNoteCard(note_data, highlight_color="#FF55AA", accent_color="#AA0055")
        self.assertEqual(card.highlight_color, "#FF55AA")
        self.assertEqual(card.accent_color, "#AA0055")
        self.assertIn("#AA0055", card.copy_btn.styleSheet())
        self.assertIn("#FF55AA", card.copy_btn.styleSheet())

    def test_html_to_plain_performance(self):
        # Very long HTML content (e.g. 100,000 characters)
        huge_html = "<div><p>Hello world <b>bold</b> <i>italic</i></p></div>" * 2000
        plain = html_to_plain(huge_html)
        self.assertTrue(plain.startswith("Hello world bold italic"))
        # Must execute instantaneously without freezing
        self.assertLess(len(plain), 2500)

    def test_notes_view_chunked_rendering(self):
        notes_view = NotesView()
        mock_notes = [{'id': i, 'title': f'Note {i}', 'content': f'Content {i}'} for i in range(50)]
        notes_view.set_notes(mock_notes)
        
        # Initial batch should be exactly 12 cards for fast responsive entry
        self.assertEqual(len(notes_view.cards), 12)
        # Should have chunk timer active for streaming the rest
        self.assertTrue(notes_view._chunk_timer.isActive())

if __name__ == '__main__':
    unittest.main()
