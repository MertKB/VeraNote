"""
Comprehensive automated tests for VeraNote Faz 1 - Ajanda, Takvim ve Günlük Notlar:
1. Database schema and migration (daily_notes, tasks tables, indexes)
2. AgendaRepository CRUD operations and indicators
3. MVC isolation verification (no database imports in ui/agenda/)
4. Headless Qt UI components rendering, signals, and debounce autosave
5. MainWindow & AppController end-to-end integration
"""
import sys
import os
import sqlite3

# Configure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QDate, QTimer

import database
from database import AgendaRepository

# Ensure single QApplication instance
app = QApplication.instance() or QApplication(sys.argv)

def test_database_schema():
    print("Testing database schema & indexes...")
    with database.get_connection() as conn:
        cursor = conn.cursor()

        # Check daily_notes table
        cursor.execute("PRAGMA table_info(daily_notes);")
        dn_cols = {row['name']: row['type'] for row in cursor.fetchall()}
        assert "date" in dn_cols, "daily_notes missing 'date' column"
        assert "content" in dn_cols, "daily_notes missing 'content' column"
        assert "summary" in dn_cols, "daily_notes missing 'summary' column"
        assert "created_at" in dn_cols, "daily_notes missing 'created_at' column"
        assert "updated_at" in dn_cols, "daily_notes missing 'updated_at' column"

        # Check tasks table
        cursor.execute("PRAGMA table_info(tasks);")
        task_cols = {row['name']: row['type'] for row in cursor.fetchall()}
        assert "id" in task_cols, "tasks missing 'id' column"
        assert "title" in task_cols, "tasks missing 'title' column"
        assert "is_completed" in task_cols, "tasks missing 'is_completed' column"
        assert "due_date" in task_cols, "tasks missing 'due_date' column"
        assert "priority" in task_cols, "tasks missing 'priority' column"
        assert "daily_note_date" in task_cols, "tasks missing 'daily_note_date' column"
        assert "note_id" in task_cols, "tasks missing 'note_id' column"

        # Check indexes
        cursor.execute("PRAGMA index_list(tasks);")
        indexes = [row['name'] for row in cursor.fetchall()]
        assert "idx_tasks_due_date" in indexes, "idx_tasks_due_date missing"
        assert "idx_tasks_daily_date" in indexes, "idx_tasks_daily_date missing"
        assert "idx_tasks_completed" in indexes, "idx_tasks_completed missing"

    print("  [OK] Database schema and indexes verified successfully!")

def test_agenda_repository():
    print("Testing AgendaRepository operations...")
    test_date = "2026-09-18"

    # 1. get_or_create_daily_note
    note = AgendaRepository.get_or_create_daily_note(test_date)
    assert note["date"] == test_date, f"Expected {test_date}, got {note['date']}"
    assert "content" in note

    # 2. save_daily_note
    test_content = "# Günlük Not\nBugün harika bir gündü."
    success = AgendaRepository.save_daily_note(test_date, test_content, "Günün özeti")
    assert success is True
    updated_note = AgendaRepository.get_or_create_daily_note(test_date)
    assert updated_note["content"] == test_content
    assert updated_note["summary"] == "Günün özeti"

    # 3. add_task
    task_id1 = AgendaRepository.add_task(
        title="Model checkpointlerini yedekle",
        description="Harici diske kopyala",
        due_date=test_date,
        priority=3,  # Urgent
        daily_note_date=test_date
    )
    assert task_id1 > 0, "Task 1 ID should be positive"

    task_id2 = AgendaRepository.add_task(
        title="LoRA parametrelerini test et",
        due_date=test_date,
        priority=1,  # Normal
        daily_note_date=test_date
    )
    assert task_id2 > 0, "Task 2 ID should be positive"

    # 4. get_tasks_for_date
    tasks = AgendaRepository.get_tasks_for_date(test_date)
    assert len(tasks) >= 2, f"Expected at least 2 tasks, got {len(tasks)}"
    # Verify priority sorting (Urgent priority 3 should be first)
    assert tasks[0]["priority"] >= tasks[1]["priority"], "Tasks should be ordered by priority DESC"

    # 5. toggle_task_completed
    new_status = AgendaRepository.toggle_task_completed(task_id2, 1)
    assert new_status == 1, "Expected completed status 1"
    tasks_after_toggle = AgendaRepository.get_tasks_for_date(test_date)
    t2 = next(t for t in tasks_after_toggle if t["id"] == task_id2)
    assert t2["is_completed"] == 1
    assert t2["completed_at"] is not None

    # Toggle back to 0
    new_status = AgendaRepository.toggle_task_completed(task_id2, 0)
    assert new_status == 0
    tasks_after_toggle2 = AgendaRepository.get_tasks_for_date(test_date)
    t2_reopened = next(t for t in tasks_after_toggle2 if t["id"] == task_id2)
    assert t2_reopened["is_completed"] == 0
    assert t2_reopened["completed_at"] is None

    # 6. get_month_task_indicators
    indicators = AgendaRepository.get_month_task_indicators(2026, 9)
    assert test_date in indicators, f"{test_date} should be in month indicators"
    assert indicators[test_date]["has_note"] is True
    assert indicators[test_date]["pending_tasks"] >= 2

    # 7. delete_task
    deleted = AgendaRepository.delete_task(task_id1)
    assert deleted is True
    remaining_tasks = AgendaRepository.get_tasks_for_date(test_date)
    assert all(t["id"] != task_id1 for t in remaining_tasks)

    # Clean up test task 2
    AgendaRepository.delete_task(task_id2)

    print("  [OK] AgendaRepository operations verified successfully!")

def test_mvc_isolation():
    print("Testing MVC isolation (no direct database imports in ui/agenda/)...")
    agenda_dir = r"c:\Users\Victoria\.gemini\antigravity-ide\scratch\VeraNote\ui\agenda"
    agenda_files = ["calendar_widget.py", "daily_note_panel.py", "tasks_panel.py", "agenda_view.py", "__init__.py"]

    for fname in agenda_files:
        path = os.path.join(agenda_dir, fname)
        assert os.path.exists(path), f"File {path} does not exist"
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("import database") or stripped.startswith("from database import"):
                raise AssertionError(f"Direct database import found in {fname}:{idx} -> {stripped}")

    print("  [OK] Zero direct database imports in ui/agenda/ modules!")

def test_ui_components():
    print("Testing UI components (Headless Qt)...")
    from ui.agenda import CalendarPanel, DailyNotePanel, TasksPanel, AgendaView

    # 1. CalendarPanel
    cal = CalendarPanel()
    cal.set_indicators({"2026-09-18": {"has_note": True, "pending_tasks": 2, "completed_tasks": 1}})
    cal.go_to_today()
    assert cal.get_selected_date_str() == QDate.currentDate().toString("yyyy-MM-dd")

    # 2. DailyNotePanel
    note_panel = DailyNotePanel()
    note_panel.load_note("2026-09-18", "# Test Not")
    assert note_panel.current_date == "2026-09-18"
    assert note_panel.editor.toPlainText() == "# Test Not"

    # Test debounce autosave
    captured_saves = []
    note_panel.note_autosave_requested.connect(lambda d, c: captured_saves.append((d, c)))
    note_panel.editor.setPlainText("# Yeni içerik")
    # Simulate debounce timer expiration
    note_panel.debounce_timer.timeout.emit()
    assert len(captured_saves) == 1
    assert captured_saves[0][0] == "2026-09-18"
    assert captured_saves[0][1] == "# Yeni içerik"

    # 3. TasksPanel
    tasks_panel = TasksPanel()
    test_tasks = [
        {"id": 101, "title": "Görev 1", "priority": 1, "is_completed": 0},
        {"id": 102, "title": "Görev 2", "priority": 3, "is_completed": 1},
    ]
    tasks_panel.set_tasks(test_tasks, "2026-09-18")
    assert tasks_panel.count_badge.text() == "2"

    # 4. AgendaView Splitter
    agenda_view = AgendaView()
    agenda_view.set_date_data("2026-09-18", "Not içeriği", test_tasks)
    assert agenda_view.current_date == "2026-09-18"

    print("  [OK] UI components tested successfully!")

def test_mainwindow_controller_integration():
    print("Testing MainWindow and AppController integration with Agenda...")
    from ui.main_window import MainWindow
    from main import AppController

    win = MainWindow()
    controller = AppController(win)

    # Trigger agenda view from sidebar
    win.sidebar.agenda_requested.emit()
    assert win.center_stack.currentIndex() == 5, f"Expected center_stack index 5, got {win.center_stack.currentIndex()}"

    # Verify active date is set
    assert hasattr(controller, 'agenda_active_date')
    assert controller.agenda_active_date is not None

    # Simulate date selection
    controller.on_agenda_date_selected("2026-09-18")
    assert win.agenda_view.current_date == "2026-09-18"

    # Simulate autosave
    controller.on_agenda_note_autosave("2026-09-18", "Otomatik kayıt notu")
    saved_note = database.get_or_create_daily_note("2026-09-18")
    assert saved_note["content"] == "Otomatik kayıt notu"

    print("  [OK] Full MainWindow and AppController integration verified!")

if __name__ == "__main__":
    test_database_schema()
    test_agenda_repository()
    test_mvc_isolation()
    test_ui_components()
    test_mainwindow_controller_integration()
    print("\n==============================================")
    print("ALL AGENDA PHASE 1 TESTS PASSED SUCCESSFULLY!")
    print("==============================================")
