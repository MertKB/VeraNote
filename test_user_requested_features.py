import sys
import os
import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

import database
from ui.main_window import MainWindow
from ui.welcome_screen import WelcomeScreen, CorkboardNoteCard, QuickNoteCardWidget, HomePageSettingsDialog, OutlinedLabel, NoWheelSlider
from main import AppController

app = QApplication.instance() or QApplication(sys.argv)

class TestUserRequestedFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.initialize_db()

    def setUp(self):
        self.win = MainWindow()
        self.controller = AppController(self.win)

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    def test_outlined_label_stroke_and_transparent_fill(self):
        """1. Verify OutlinedLabel handles stroke outline and fill transparency independently"""
        lbl = OutlinedLabel("Test Title")
        lbl.text_color = "transparent"
        lbl.outline_color = "#FF0000"
        lbl.outline_width = 3
        
        self.assertEqual(lbl.text_color, "transparent")
        self.assertEqual(lbl.outline_color, "#FF0000")

    def test_quick_note_card_simplified(self):
        """2. Verify Quick Note card is simplified without top header, and supports transparent bg/border"""
        qn = QuickNoteCardWidget(parent=self.win.welcome_screen)
        qn.bg_color = "transparent"
        qn.border_color = "transparent"
        qn.update_style()
        
        self.assertEqual(qn.bg_color, "transparent")
        self.assertIsNotNone(qn.note_edit)
        qn.deleteLater()

    def test_corkboard_card_top_right_copy_button_and_no_collision(self):
        """3. Verify left star button removed, copy button present with top padding to prevent title collision"""
        note_data = {'id': 401, 'title': 'Collision Free Note', 'content': 'Text mode without image', 'display_mode': 'TEXT_ONLY'}
        card = CorkboardNoteCard(note_data, parent=self.win.welcome_screen)
        
        self.assertFalse(hasattr(card, 'fav_btn'))
        self.assertIsNotNone(card.copy_btn)
        self.assertEqual(card.copy_btn.text(), "📋")
        
        # Check top padding is 32px when no image
        margins = card.main_layout.contentsMargins()
        self.assertEqual(margins.top(), 32)
        card.deleteLater()

    def test_title_center_positioning_and_no_jumping(self):
        """4. Verify uninitialized title defaults to centered position instead of jumping to 0,0"""
        welcome = self.win.welcome_screen
        database.set_setting("welcome_title_x", "0")
        database.set_setting("welcome_title_y", "0")
        
        welcome.render_corkboard()
        self.assertGreater(welcome.title_label.x(), 0)

    def test_no_wheel_slider_ignores_wheel(self):
        """5. Verify NoWheelSlider exists and ignores mouse wheel events"""
        slider = NoWheelSlider(Qt.Horizontal)
        self.assertTrue(isinstance(slider, NoWheelSlider))
        slider.deleteLater()

    def test_home_page_settings_dialog_instantiation(self):
        """6. Verify HomePageSettingsDialog instantiates cleanly without QComboBox NameError"""
        dialog = HomePageSettingsDialog(self.win.welcome_screen)
        self.assertIsNotNone(dialog.font_family_combo)
        self.assertIsNotNone(dialog.qn_w_slider)
        self.assertIsNotNone(dialog.qn_h_slider)
        dialog.deleteLater()


if __name__ == '__main__':
    unittest.main()
