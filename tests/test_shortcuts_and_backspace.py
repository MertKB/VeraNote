# tests/test_shortcuts_and_backspace.py
import unittest
import sys
from PySide6.QtWidgets import QApplication, QLineEdit, QTextEdit, QPlainTextEdit
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtGui import QKeyEvent, QKeySequence

app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

import database
from ui.main_window import MainWindow, NavigationEventFilter
from ui.settings_dialog import SettingsDialog


class TestShortcutsAndBackspace(unittest.TestCase):
    def setUp(self):
        self.win = MainWindow()

    def tearDown(self):
        self.win.close()
        self.win.deleteLater()

    def test_backspace_never_intercepted_by_navigation(self):
        """Verify that pressing Backspace does not trigger navigate_back and is not consumed by event filter."""
        nav_filter = NavigationEventFilter(self.win)
        called = []
        self.win.all_notebooks_requested_signal.connect(lambda: called.append(True))
        self.win.show_notes_panel([], is_trash=False, notebook_id=1, notebook_name="Not Defteri")

        # 1. Backspace on window
        bs_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Backspace, Qt.NoModifier)
        consumed = nav_filter.eventFilter(self.win, bs_event)
        self.assertFalse(consumed)
        self.assertEqual(len(called), 0)

        # 2. Backspace on QLineEdit
        line_edit = QLineEdit()
        line_edit.setText("Hello")
        consumed_line = nav_filter.eventFilter(line_edit, bs_event)
        self.assertFalse(consumed_line)
        self.assertEqual(len(called), 0)

        # 3. Backspace on QTextEdit
        text_edit = QTextEdit()
        consumed_text = nav_filter.eventFilter(text_edit, bs_event)
        self.assertFalse(consumed_text)
        self.assertEqual(len(called), 0)

        # 4. Delete key is also not consumed
        del_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
        consumed_del = nav_filter.eventFilter(text_edit, del_event)
        self.assertFalse(consumed_del)
        self.assertEqual(len(called), 0)

    def test_alt_left_triggers_navigation(self):
        """Verify that Alt+Left triggers navigate_back."""
        nav_filter = NavigationEventFilter(self.win)
        called = []
        self.win.all_notebooks_requested_signal.connect(lambda: called.append(True))
        self.win.show_notes_panel([], is_trash=False, notebook_id=1, notebook_name="Not Defteri")

        alt_left_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.AltModifier)
        consumed = nav_filter.eventFilter(self.win, alt_left_event)
        self.assertTrue(consumed)
        self.assertEqual(len(called), 1)

    def test_custom_navigation_shortcut(self):
        """Verify setting a custom navigation shortcut works."""
        self.win.set_navigation_shortcuts("Ctrl+Left", "Ctrl+Right")
        nav_filter = NavigationEventFilter(self.win)
        called = []
        self.win.all_notebooks_requested_signal.connect(lambda: called.append(True))
        self.win.show_notes_panel([], is_trash=False, notebook_id=1, notebook_name="Not Defteri")

        ctrl_left_event = QKeyEvent(QEvent.KeyPress, Qt.Key_Left, Qt.ControlModifier)
        consumed = nav_filter.eventFilter(self.win, ctrl_left_event)
        self.assertTrue(consumed)
        self.assertEqual(len(called), 1)

    def test_database_shortcuts_crud(self):
        """Verify database shortcut retrieval and saving."""
        defaults = database.get_shortcuts()
        self.assertIn("nav_back", defaults)
        self.assertIn("nav_forward", defaults)
        self.assertIn("new_note", defaults)
        self.assertIn("search", defaults)
        self.assertIn("incognito", defaults)

        custom = dict(defaults)
        custom["new_note"] = "Ctrl+Shift+T"
        database.set_shortcuts(custom)

        loaded = database.get_shortcuts()
        self.assertEqual(loaded["new_note"], "Ctrl+Shift+T")

        # Restore
        database.set_shortcuts(defaults)

    def test_settings_dialog_shortcuts_ui(self):
        """Verify SettingsDialog exposes shortcut controls and prevents lone Backspace."""
        dialog = SettingsDialog(self.win)
        shortcuts = database.get_shortcuts()
        dialog.set_shortcuts(shortcuts)

        self.assertIn("nav_back", dialog.shortcut_edits)
        self.assertIn("new_note", dialog.shortcut_edits)

        # Attempt to set Backspace as a shortcut
        nav_edit = dialog.shortcut_edits["nav_back"]
        nav_edit.setKeySequence(QKeySequence("Backspace"))
        # get_shortcuts should disallow lone Backspace and fallback to default
        retrieved = dialog.get_shortcuts()
        self.assertNotEqual(retrieved["nav_back"], "Backspace")
        self.assertEqual(retrieved["nav_back"], "Alt+Left")

        # Reset button test
        nav_edit.setKeySequence(QKeySequence("Ctrl+Shift+B"))
        self.assertEqual(dialog.shortcut_edits["nav_back"].keySequence().toString(), "Ctrl+Shift+B")
        dialog.reset_shortcuts_to_defaults()
        self.assertEqual(dialog.shortcut_edits["nav_back"].keySequence().toString(), "Alt+Left")

        dialog.close()
        dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
