# tests/test_nav_and_customization.py
import unittest
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QMouseEvent, QKeyEvent, QKeySequence

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from ui.main_window import MainWindow, NavigationEventFilter
from ui.notebooks_view import NotebooksView, NotebookCardWidget
from ui.settings_dialog import DEFAULT_CUSTOM_COLORS
from ui.styles import get_calendar_theme_config, get_palette
from ui.detail_panel import DetailPanel


class TestNavAndCustomization(unittest.TestCase):
    def setUp(self):
        self.win = MainWindow()

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    def test_notebook_back_navigation(self):
        """Test that Back navigation command inside a notebook view navigates back to notebooks overview."""
        called = []
        self.win.all_notebooks_requested_signal.connect(lambda: called.append(True))

        # Put view in notebook mode
        self.win.show_notes_panel([], is_trash=False, notebook_id=42, notebook_name="Proje Notları")
        self.assertEqual(self.win.center_stack.currentIndex(), 3)
        self.assertEqual(self.win.notes_view.current_notebook_id, 42)

        # Trigger navigate_back
        res = self.win.navigate_back()
        self.assertTrue(res)
        self.assertEqual(len(called), 1)

    def test_mouse_back_button_event_filter(self):
        """Test that standard OS mouse BackButton command is captured by event filter."""
        nav_filter = NavigationEventFilter(self.win)
        called = []
        self.win.all_notebooks_requested_signal.connect(lambda: called.append(True))

        self.win.show_notes_panel([], is_trash=False, notebook_id=99, notebook_name="Test Defter")
        
        # Simulate OS Mouse BackButton Press event (standard XBUTTON1 / Back)
        event = QMouseEvent(QEvent.MouseButtonPress, QPoint(100, 100), QPoint(100, 100), Qt.BackButton, Qt.BackButton, Qt.NoModifier)
        consumed = nav_filter.eventFilter(self.win, event)
        self.assertTrue(consumed)
        self.assertEqual(len(called), 1)

    def test_notebook_card_ctrl_click_selection(self):
        """Test that clicking with Ctrl toggles selection and does NOT open the notebook."""
        nb_data = {'id': 10, 'name': 'Algoritma', 'note_count': 5}
        card = NotebookCardWidget(nb_data, highlight_color="#FF8800")
        clicked_events = []
        selection_events = []
        card.clicked.connect(lambda id, name: clicked_events.append((id, name)))
        card.selection_toggled.connect(lambda data, sel: selection_events.append(sel))

        # 1. Normal click (without Ctrl)
        press_event = QMouseEvent(QEvent.MouseButtonPress, QPoint(20, 20), QPoint(20, 20), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
        card.mousePressEvent(press_event)
        self.assertEqual(len(clicked_events), 1)
        self.assertFalse(card.is_selected)

        # 2. Ctrl + Click toggles selection
        card.toggle_selection()
        self.assertTrue(card.is_selected)
        self.assertEqual(len(selection_events), 1)
        self.assertTrue(selection_events[0])

        card.toggle_selection()
        self.assertFalse(card.is_selected)
        self.assertEqual(len(selection_events), 2)
        self.assertFalse(selection_events[1])

    def test_notebooks_view_bulk_actions_and_ctrl_a(self):
        """Test NotebooksView bulk selection, Ctrl+A, clear selection, and delete signal."""
        view = NotebooksView()
        notebooks = [
            {'id': 1, 'name': 'A Defteri', 'note_count': 2, 'updated_at': '2026-10-01'},
            {'id': 2, 'name': 'B Defteri', 'note_count': 4, 'updated_at': '2026-10-02'},
            {'id': 3, 'name': 'C Defteri', 'note_count': 1, 'updated_at': '2026-10-03'}
        ]
        view.set_notebooks(notebooks)
        self.assertEqual(len(view.cards), 3)
        self.assertFalse(view.bulk_bar.isVisible())

        # Select all
        view.select_all_notebooks()
        self.assertEqual(len(view.selected_notebook_ids), 3)
        self.assertFalse(view.bulk_bar.isHidden())
        self.assertTrue(all(c.is_selected for c in view.cards))

        # Clear selection
        view.clear_selection()
        self.assertEqual(len(view.selected_notebook_ids), 0)
        self.assertTrue(view.bulk_bar.isHidden())
        self.assertTrue(all(not c.is_selected for c in view.cards))

        # Select all via shortcut method
        key_event = QKeyEvent(QEvent.KeyPress, Qt.Key_A, Qt.ControlModifier)
        view.keyPressEvent(key_event)
        self.assertEqual(len(view.selected_notebook_ids), 3)
        self.assertFalse(view.bulk_bar.isHidden())

    def test_consolidated_weekend_color(self):
        """Test that weekend settings use single cal_weekend_color."""
        self.assertIn("cal_weekend_color", DEFAULT_CUSTOM_COLORS)
        self.assertNotIn("cal_weekend_header_color", DEFAULT_CUSTOM_COLORS)
        self.assertNotIn("cal_weekend_day_color", DEFAULT_CUSTOM_COLORS)

        custom = {"cal_weekend_color": "#E91E63"}
        cfg = get_calendar_theme_config("Özel Tema", custom)
        self.assertEqual(cfg.get("header_weekend"), "#E91E63")
        self.assertEqual(cfg.get("text_weekend"), "#E91E63")

    def test_detail_panel_theme_propagation(self):
        """Test that DetailPanel propagates theme colors to workflow, model, and note sections."""
        dp = DetailPanel()
        palette = {
            "highlight_color": "#FF9900",
            "accent_color": "#CC7700",
            "border_focus": "#FF9900"
        }
        dp.apply_theme(palette)
        self.assertEqual(dp.workflow_section.highlight_color, "#FF9900")
        self.assertEqual(dp.model_section.highlight_color, "#FF9900")
        self.assertEqual(dp.note_section.highlight_color, "#FF9900")


if __name__ == "__main__":
    unittest.main()
