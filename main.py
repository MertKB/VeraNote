# Vera Note - AI Model & Workflow Manager
# Copyright (C) 2026 Vera Note Contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# main.py
import sys
import os
os.environ["QT_LOGGING_RULES"] = "qt.qpa.gl=false;*.warning=false"
import shutil
import time
import json
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog, QInputDialog
from PySide6.QtCore import Slot, Qt

import database
from ui.main_window import MainWindow
from ui.settings_dialog import SettingsDialog
from scanner import ModelScanner
from utils import i18n

class AppController:
    def __init__(self, main_window):
        self.win = main_window
        self.active_library = ""
        self.active_workflow_library = ""
        self.active_note_id = None
        self.scan_thread = None
        self.running_scanners = []
        self.showing_trash = False
        self.incognito_active = False

        # Setup Incognito Shortcut
        from PySide6.QtGui import QKeySequence, QShortcut
        self.incognito_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), self.win)
        self.incognito_shortcut.activated.connect(self.toggle_incognito_mode)

        # Connect MainWindow signals
        self.win.save_note_signal.connect(self.on_save_note)
        self.win.sidebar.note_selected.connect(self.on_note_selected)
        self.win.sidebar.library_selected.connect(self.on_library_selected)
        self.win.sidebar.workflow_library_selected.connect(self.on_workflow_library_selected)
        self.win.sidebar.new_library_requested.connect(self.on_new_library_requested)
        self.win.sidebar.delete_workflow_library_requested.connect(self.on_delete_workflow_library)
        self.win.workflow_view.delete_library_requested.connect(self.on_delete_workflow_library)
        self.win.settings_requested_signal.connect(self.on_settings_requested)
        self.win.save_model_data_signal.connect(self.on_save_model_data)
        self.win.add_trigger_signal.connect(self.on_add_trigger)
        self.win.delete_trigger_signal.connect(self.on_delete_trigger)
        self.win.image_changed_signal.connect(self.on_model_image_changed)
        self.win.scan_library_signal.connect(self.on_scan_library)
        
        # Connect Favorites and Tagging signals
        self.win.favorite_toggled_signal.connect(self.on_favorite_toggled)
        self.win.workflow_favorite_toggled_signal.connect(self.on_workflow_favorite_toggled)
        self.win.add_tag_signal.connect(self.on_add_tag)
        self.win.delete_tag_signal.connect(self.on_delete_tag)
        self.win.bulk_add_tag_signal.connect(self.on_bulk_add_tag)
        self.win.bulk_remove_tag_signal.connect(self.on_bulk_remove_tag)
        self.win.bulk_favorite_signal.connect(self.on_bulk_favorite)
        self.win.bulk_delete_signal.connect(self.on_bulk_delete)
        self.win.delete_model_signal.connect(self.on_detail_delete_model)
        
        # Connect Sidebar "Tüm Notlar", "Çöp Kutusu" and "+ Yeni Not" redirect
        self.win.sidebar.all_notes_requested.connect(self.on_all_notes_requested)
        self.win.sidebar.trash_requested.connect(self.on_trash_requested)
        try:
            self.win.sidebar.new_note_requested.disconnect()
        except RuntimeError:
            pass
        self.win.sidebar.new_note_requested.connect(self.on_create_new_note)
        
        # Connect NotesView & note editor signals
        self.win.note_clicked_signal.connect(self.on_note_clicked_from_grid)
        self.win.note_favorite_toggled_signal.connect(self.on_note_favorite_toggled)
        self.win.save_note_new_signal.connect(self.on_note_save)
        
        self.win.notes_view.note_restore_requested.connect(self.on_note_restore_requested)
        self.win.notes_view.note_perm_delete_requested.connect(self.on_note_perm_delete_requested)
        self.win.notes_view.empty_trash_requested.connect(self.on_empty_trash)
        self.win.detail_panel.delete_note_requested.connect(self.on_detail_delete_note)
        self.win.note_associate_model_signal.connect(self.on_note_associate_model)
        self.win.note_dissociate_model_signal.connect(self.on_note_dissociate_model)
        self.win.file_dropped_signal.connect(self.on_global_file_dropped)
        
        # Connect library model click to retrieve details & trigger words
        self.win.library_view.model_clicked.connect(self.on_model_clicked)

        # Connect workflow signals
        self.win.save_workflow_data_signal.connect(self.on_save_workflow_data)
        self.win.delete_workflow_signal.connect(self.on_delete_workflow)
        self.win.workflow_image_changed_signal.connect(self.on_workflow_image_changed)
        self.win.workflow_clicked_signal.connect(self.on_workflow_clicked)
        self.win.add_workflow_signal.connect(self.on_add_workflow)

        # Connect Incognito Context Menu signals
        self.win.model_hide_signal.connect(self.on_model_hide)
        self.win.model_unhide_signal.connect(self.on_model_unhide)
        self.win.workflow_hide_signal.connect(self.on_workflow_hide)
        self.win.workflow_unhide_signal.connect(self.on_workflow_unhide)
        self.win.note_hide_signal.connect(self.on_note_hide)
        self.win.note_unhide_signal.connect(self.on_note_unhide)

        # Connect Welcome Screen customizations & Corkboard
        self.win.welcome_screen.title_changed.connect(self.on_welcome_title_changed)
        self.win.welcome_screen.wallpaper_selected.connect(self.on_welcome_wallpaper_changed)
        self.win.welcome_screen.paste_corkboard_requested.connect(self.on_paste_corkboard_note)
        self.win.welcome_screen.corkboard_unpin_requested.connect(self.on_corkboard_unpin)
        self.win.welcome_screen.corkboard_position_changed.connect(self.on_corkboard_position_changed)
        self.win.welcome_screen.note_open_requested.connect(self.open_note_in_drawer)
        self.win.welcome_screen.setting_changed.connect(database.set_setting)

        # Connect NotesView Corkboard & Bulk Actions
        self.win.notes_view.corkboard_pin_toggled.connect(self.on_corkboard_pin_toggled)
        self.win.notes_view.note_color_changed.connect(self.on_note_color_changed)
        self.win.notes_view.bulk_delete_requested.connect(self.on_bulk_delete_notes)
        self.win.notes_view.bulk_restore_requested.connect(self.on_bulk_restore_notes)
        self.win.detail_panel.corkboard_pin_toggled.connect(self.on_corkboard_pin_toggled)
        self.win.detail_panel.note_color_changed.connect(self.on_note_color_changed)

        # Connect Agenda Signals
        self.win.sidebar.agenda_requested.connect(self.on_agenda_requested)
        self.win.agenda_view.date_selected.connect(self.on_agenda_date_selected)
        self.win.agenda_view.month_changed.connect(self.on_agenda_month_changed)
        self.win.agenda_view.monthly_stats_requested.connect(self.on_agenda_monthly_stats_requested)
        self.win.agenda_view.note_autosave_requested.connect(self.on_agenda_note_autosave)
        self.win.agenda_view.task_add_requested.connect(self.on_agenda_task_add)
        self.win.agenda_view.task_toggle_requested.connect(self.on_agenda_task_toggle)
        self.win.agenda_view.task_delete_requested.connect(self.on_agenda_task_delete)
        self.win.agenda_view.clear_completed_requested.connect(self.on_agenda_clear_completed)
        self.win.agenda_view.routines_dialog_requested.connect(self.on_agenda_routines_dialog_requested)

        # Initialize agenda active date
        import datetime
        self.agenda_active_date = datetime.date.today().isoformat()

        # Load theme and language settings from DB
        lang = database.get_setting("lang", "en")
        theme = database.get_setting("theme", "Koyu Gece")
        custom_colors = database.get_setting("custom_theme_colors", "{}")
        i18n.set_lang(lang)
        self.win.change_theme(theme, custom_colors)
        self.win.retranslate_ui()

        # Load Welcome customizations from DB
        w_title = database.get_setting("welcome_title", i18n.t("welcome_title_default"))
        w_wallpaper = database.get_setting("welcome_wallpaper", "")
        welcome_keys = [
            "corkboard_mode", "corkboard_coord_mode", "home_positions_locked", "welcome_title_visible",
            "welcome_title_font_size", "welcome_title_font_family", "welcome_title_font_weight",
            "welcome_title_w", "welcome_title_h", "welcome_title_color",
            "welcome_title_outline_color", "welcome_title_outline_width",
            "welcome_title_frame_enabled", "welcome_title_frame_bg", "welcome_title_frame_border_color",
            "quick_note_visible", "quick_note_bg", "quick_note_border_color",
            "quick_note_w", "quick_note_h", "corkboard_notes_visible", "corkboard_show_images",
            "welcome_title_x", "welcome_title_y", "quick_note_x", "quick_note_y"
        ]
        welcome_settings = {k: database.get_setting(k) for k in welcome_keys if database.get_setting(k) is not None}
        self.win.welcome_screen.load_settings(welcome_settings)
        self.win.welcome_screen.title_label.setText(w_title)
        self.win.welcome_screen.set_wallpaper(w_wallpaper)

        # ComfyUI Features Enabled state
        self.comfyui_enabled = database.get_setting("comfyui_enabled", "1") == "1"
        self.win.set_comfyui_enabled(self.comfyui_enabled)

        # Initial UI populate
        self.refresh_notes()
        if self.comfyui_enabled:
            self.refresh_libraries()
        self.win.show_welcome()

    def refresh_notes(self, search_query=None):
        notes = database.get_notes(search_query, show_hidden=self.incognito_active)
        
        # Update dynamic badge count
        total_count = database.get_note_count(show_hidden=self.incognito_active)
        self.win.sidebar.update_notes_count(total_count)
        
        # Update Recycle Bin badge count
        trash_count = database.get_deleted_note_count(show_hidden=self.incognito_active)
        self.win.sidebar.update_trash_count(trash_count)

        # Refresh Corkboard (Mantar Pano) on Welcome Screen
        cork_notes = database.get_corkboard_notes(show_hidden=self.incognito_active)
        self.win.welcome_screen.set_corkboard_notes(cork_notes)
        
        # Keep NotesView grid updated based on whether we are showing trash or normal notes
        if getattr(self, 'showing_trash', False):
            deleted_notes = database.get_notes(only_deleted=True, show_hidden=self.incognito_active)
            self.win.notes_view.set_notes(deleted_notes, is_trash=True)
        else:
            all_notes = database.get_notes(show_hidden=self.incognito_active)
            self.win.notes_view.set_notes(all_notes, is_trash=False)

    def refresh_libraries(self):
        # 1. Models
        model_libs = database.get_libraries(lib_type='MODEL')
        models_with_counts = []
        for lib in model_libs:
            count = database.get_model_count_in_library(lib, show_hidden=self.incognito_active)
            models_with_counts.append((lib, count))
        self.win.sidebar.update_models_list(models_with_counts, self.active_library)

        # 2. Workflow Libraries
        wf_libs = database.get_workflow_libraries()
        wf_with_counts = []
        for lib in wf_libs:
            count = database.get_workflow_count_in_library(lib['id'], show_hidden=self.incognito_active)
            wf_with_counts.append((lib['name'], count))
        self.win.sidebar.update_workflow_libraries_list(wf_with_counts, self.active_workflow_library)

    @Slot(object, str, str)
    def on_save_note(self, note_id, title, content):
        saved_id = database.save_note(note_id, title, content)
        self.refresh_notes()
        self.open_note_in_drawer(saved_id)
        self.win.statusBar().showMessage(i18n.t("note_saved"), 2000)

    @Slot(int)
    def on_note_selected(self, note_id):
        self.open_note_in_drawer(note_id)

    def open_note_in_drawer(self, note_id):
        note = database.get_note_by_id(note_id)
        if note:
            self.active_note_id = note_id
            all_models = database.get_all_models_for_association()
            self.win.detail_panel.set_note(note, all_models)
            self.win.show_detail_panel(note)

    @Slot()
    def on_create_new_note(self):
        new_id = database.save_note(None, i18n.t("notes_new_title"), "<p></p>", None, "WITH_IMAGE", 0)
        self.refresh_notes()
        self.open_note_in_drawer(new_id)
        self.win.statusBar().showMessage(i18n.t("status_new_note"), 2000)

    @Slot(dict)
    def on_note_clicked_from_grid(self, note_data):
        self.open_note_in_drawer(note_data['id'])

    @Slot()
    def on_all_notes_requested(self):
        self.showing_trash = False
        self.active_library = ""
        self.win.sidebar.libraries_list.clearSelection()
        all_notes = database.get_notes(show_hidden=self.incognito_active)
        self.win.show_notes_panel(all_notes, is_trash=False)

    @Slot()
    def on_trash_requested(self):
        self.showing_trash = True
        self.active_library = ""
        self.win.sidebar.libraries_list.clearSelection()
        deleted_notes = database.get_notes(only_deleted=True, show_hidden=self.incognito_active)
        self.win.show_notes_panel(deleted_notes, is_trash=True)

    @Slot()
    def on_agenda_requested(self):
        self.win.show_agenda()
        if not hasattr(self, 'agenda_active_date') or not self.agenda_active_date:
            import datetime
            self.agenda_active_date = datetime.date.today().isoformat()
        self.on_agenda_date_selected(self.agenda_active_date)

    @Slot(str)
    def on_agenda_date_selected(self, date_str: str):
        self.agenda_active_date = date_str
        # Seed recurring routines for the date (if active, not weekend for weekdays, non-duplicate)
        database.seed_daily_tasks_from_routines(date_str)
        note = database.get_or_create_daily_note(date_str)
        tasks = database.get_tasks_for_date(date_str)
        self.win.agenda_view.set_date_data(date_str, note.get('content', ''), tasks)
        # Also refresh indicators, monthly stats, and upcoming tasks
        try:
            import datetime
            dt = datetime.date.fromisoformat(date_str)
            indicators = database.get_month_task_indicators(dt.year, dt.month)
            self.win.agenda_view.set_indicators(indicators)
            stats = database.get_monthly_agenda_stats(dt.year, dt.month)
            self.win.agenda_view.set_monthly_stats(stats)
            upcoming = database.get_upcoming_tasks(days_ahead=3)
            self.win.agenda_view.set_upcoming_tasks(upcoming)
        except Exception:
            pass

    @Slot(str)
    def on_agenda_clear_completed(self, date_str: str):
        target_date = date_str or getattr(self, 'agenda_active_date', None)
        if target_date:
            database.clear_completed_tasks(target_date)
            tasks = database.get_tasks_for_date(target_date)
            self.win.agenda_view.set_tasks(tasks, target_date)
            self.refresh_agenda_indicators()

    @Slot()
    def on_agenda_routines_dialog_requested(self):
        from ui.agenda.routine_manager_dialog import RoutineManagerDialog
        dialog = RoutineManagerDialog(self.win)

        def refresh_dialog_routines():
            routines = database.get_all_routines()
            dialog.set_routines(routines)

        def on_add_routine(title, freq, priority):
            database.add_routine(title, freq, priority)
            refresh_dialog_routines()
            target_date = getattr(self, 'agenda_active_date', None)
            if target_date:
                seeded = database.seed_daily_tasks_from_routines(target_date)
                if seeded > 0:
                    tasks = database.get_tasks_for_date(target_date)
                    self.win.agenda_view.set_tasks(tasks, target_date)
                    self.refresh_agenda_indicators()

        def on_toggle_routine(routine_id, is_active):
            database.toggle_routine(routine_id, is_active)
            refresh_dialog_routines()

        def on_delete_routine(routine_id):
            database.delete_routine(routine_id)
            refresh_dialog_routines()

        dialog.routine_add_requested.connect(on_add_routine)
        dialog.routine_toggle_requested.connect(on_toggle_routine)
        dialog.routine_delete_requested.connect(on_delete_routine)

        refresh_dialog_routines()
        dialog.exec()

    @Slot(int, int)
    def on_agenda_month_changed(self, year: int, month: int):
        indicators = database.get_month_task_indicators(year, month)
        self.win.agenda_view.set_indicators(indicators)
        stats = database.get_monthly_agenda_stats(year, month)
        self.win.agenda_view.set_monthly_stats(stats)
        upcoming = database.get_upcoming_tasks(days_ahead=3)
        self.win.agenda_view.set_upcoming_tasks(upcoming)

    @Slot(int, int)
    def on_agenda_monthly_stats_requested(self, year: int, month: int):
        stats = database.get_monthly_agenda_stats(year, month)
        self.win.agenda_view.set_monthly_stats(stats)

    def refresh_agenda_indicators(self):
        import datetime
        target_date = getattr(self, 'agenda_active_date', None) or datetime.date.today().isoformat()
        try:
            dt = datetime.date.fromisoformat(target_date)
            y, m = dt.year, dt.month
        except Exception:
            today = datetime.date.today()
            y, m = today.year, today.month
        indicators = database.get_month_task_indicators(y, m)
        self.win.agenda_view.set_indicators(indicators)
        stats = database.get_monthly_agenda_stats(y, m)
        self.win.agenda_view.set_monthly_stats(stats)
        upcoming = database.get_upcoming_tasks(days_ahead=3)
        self.win.agenda_view.set_upcoming_tasks(upcoming)

    @Slot(str, str)
    def on_agenda_note_autosave(self, date_str: str, content: str):
        database.save_daily_note(date_str, content)
        self.refresh_agenda_indicators()

    @Slot(str, int, str)
    def on_agenda_task_add(self, title: str, priority: int, due_date: str):
        database.add_task(
            title=title,
            priority=priority,
            due_date=due_date,
            daily_note_date=due_date
        )
        tasks = database.get_tasks_for_date(due_date)
        self.win.agenda_view.set_tasks(tasks, due_date)
        self.refresh_agenda_indicators()

    @Slot(int, int)
    def on_agenda_task_toggle(self, task_id: int, is_completed: int):
        database.toggle_task_completed(task_id, is_completed)
        self.refresh_agenda_indicators()

    @Slot(int)
    def on_agenda_task_delete(self, task_id: int):
        database.delete_task(task_id)
        target_date = getattr(self, 'agenda_active_date', None)
        if target_date:
            tasks = database.get_tasks_for_date(target_date)
            self.win.agenda_view.set_tasks(tasks, target_date)
        self.refresh_agenda_indicators()

    @Slot(int)
    def on_note_restore_requested(self, note_id):
        database.restore_note(note_id)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_restored"), 2000)

    @Slot(int)
    def on_note_perm_delete_requested(self, note_id):
        database.permanently_delete_note(note_id)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_perm_deleted"), 2000)

    @Slot()
    def on_empty_trash(self):
        database.empty_recycle_bin()
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_trash_emptied"), 2000)

    @Slot(int)
    def on_detail_delete_note(self, note_id):
        database.soft_delete_note(note_id)
        self.win.hide_detail_panel()
        self.refresh_notes()

    @Slot(str, str)
    def on_paste_corkboard_note(self, title, content):
        new_id = database.save_note(None, title, content, None, "WITH_IMAGE", 0)
        database.toggle_corkboard_pin(new_id, is_pinned=True)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_pasted_corkboard"), 2500)

    @Slot(int)
    def on_corkboard_unpin(self, note_id):
        database.toggle_corkboard_pin(note_id, is_pinned=False)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_unpinned_corkboard"), 2000)

    @Slot(int, str)
    def on_note_color_changed(self, note_id, color_hex):
        database.update_note_color(note_id, color_hex)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_color_updated"), 2000)

    @Slot(object)
    def on_corkboard_position_changed(self, note_id, x, y, w=None, h=None):
        database.update_corkboard_geometry(note_id, x, y, w, h)

    @Slot(int, bool)
    def on_corkboard_pin_toggled(self, note_id, is_pinned):
        database.toggle_corkboard_pin(note_id, is_pinned=is_pinned)
        self.refresh_notes()
        msg = i18n.t("status_pinned_corkboard") if is_pinned else i18n.t("status_unpinned_corkboard")
        self.win.statusBar().showMessage(msg, 2000)

    @Slot(list, bool)
    def on_bulk_delete_notes(self, note_ids, is_trash):
        database.delete_notes_bulk(note_ids, is_trash=is_trash)
        self.refresh_notes()
        self.win.statusBar().showMessage(f"{len(note_ids)} " + (i18n.t("status_deleted") if is_trash else i18n.t("status_moved_trash")), 2500)

    @Slot(list)
    def on_bulk_restore_notes(self, note_ids):
        database.restore_notes_bulk(note_ids)
        self.refresh_notes()
        self.win.statusBar().showMessage(i18n.t("status_restored"), 2000)

    @Slot(int, bool)
    def on_note_favorite_toggled(self, note_id, is_favorite):
        database.toggle_note_favorite(note_id, is_favorite)
        self.refresh_notes()
        if self.win.detail_panel.isVisible() and self.win.detail_panel.note_data and self.win.detail_panel.note_data['id'] == note_id:
            self.win.detail_panel.note_data['is_favorite'] = 1 if is_favorite else 0

    @Slot(int, bool)
    def on_workflow_favorite_toggled(self, workflow_id, is_favorite):
        database.toggle_workflow_favorite(workflow_id, is_favorite)
        if self.active_workflow_library:
            self.refresh_libraries()

    @Slot(int, str, str, str, str, int, bool)
    def on_note_save(self, note_id, title, content, image_path, display_mode, is_fav, is_auto_save=False):
        image_path = image_path or ""
        dest_path = image_path
        
        if image_path and os.path.exists(image_path):
            project_images_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
            image_dir = os.path.abspath(os.path.dirname(image_path))
            
            try:
                os.makedirs(project_images_dir, exist_ok=True)
                
                # Copy file if it is not already in the database's local images directory
                if image_dir != project_images_dir:
                    ext = os.path.splitext(image_path)[1].lower()
                    timestamp = int(time.time())
                    dest_path = os.path.join(project_images_dir, f"note_{note_id}_{timestamp}{ext}")
                    
                    shutil.copy2(image_path, dest_path)
                    
                    # Clean up old note image if it was also in project images directory and is different
                    old_note = database.get_note_by_id(note_id)
                    if old_note and old_note.get('image_path'):
                        old_path = os.path.abspath(old_note['image_path'])
                        if os.path.dirname(old_path) == project_images_dir and os.path.exists(old_path) and old_path != os.path.abspath(dest_path):
                            try:
                                os.remove(old_path)
                            except Exception as clean_err:
                                print(f"Error removing old note image file {old_path}: {clean_err}")
            except Exception as e:
                print(f"Error copying note image: {e}")
                dest_path = image_path
        elif not image_path:
            # Clean up old image if removed
            old_note = database.get_note_by_id(note_id)
            if old_note and old_note.get('image_path'):
                project_images_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
                old_path = os.path.abspath(old_note['image_path'])
                if os.path.dirname(old_path) == project_images_dir and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as clean_err:
                        print(f"Error removing old note image file {old_path}: {clean_err}")
            dest_path = ""

        database.save_note(note_id, title, content, dest_path, display_mode, is_fav)
        
        # If it is auto-save, update the GUI elements in-place silently.
        # No full list redraws, no QTimer card recreations, no flashes!
        if is_auto_save:
            # Update card in notes grid in-place
            for card in self.win.notes_view.cards:
                from ui.notes_view import NoteCardWidget
                if isinstance(card, NoteCardWidget) and card.note_data.get('id') == note_id:
                    card.note_data['title'] = title
                    card.note_data['content'] = content
                    card.note_data['image_path'] = dest_path
                    card.note_data['display_mode'] = display_mode
                    card.note_data['is_favorite'] = is_fav
                    card.is_fav = bool(is_fav)
                    card.image_path = dest_path or ""
                    card.display_mode = display_mode or "WITH_IMAGE"
                    card.update_layout()
                    break
        else:
            # Full save (explicit save): refresh everything normally
            self.refresh_notes()
            self.open_note_in_drawer(note_id)
            self.win.statusBar().showMessage(i18n.t("note_saved"), 2000)

    @Slot(int, int)
    def on_note_associate_model(self, note_id, model_id):
        database.associate_note_model(note_id, model_id)
        note = database.get_note_by_id(note_id)
        if note and self.active_note_id == note_id:
            all_models = database.get_all_models_for_association()
            self.win.detail_panel.set_note(note, all_models)

    @Slot(int, int)
    def on_note_dissociate_model(self, note_id, model_id):
        database.dissociate_note_model(note_id, model_id)
        note = database.get_note_by_id(note_id)
        if note and self.active_note_id == note_id:
            all_models = database.get_all_models_for_association()
            self.win.detail_panel.set_note(note, all_models)

    @Slot(str)
    def on_global_file_dropped(self, file_path):
        if not file_path or not os.path.exists(file_path):
            return

        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.png', '.json'):
            is_workflow = ext == '.json'
            if ext == '.png':
                from utils.png_parser import extract_comfyui_metadata_from_png
                meta = extract_comfyui_metadata_from_png(file_path)
                if meta.get('workflow') or meta.get('prompt') or meta.get('positive_prompt'):
                    is_workflow = True

            if is_workflow:
                wf_libs = database.get_workflow_libraries()
                target_lib_id = None
                target_lib_name = ""

                if self.active_workflow_library:
                    for l in wf_libs:
                        if l['name'] == self.active_workflow_library:
                            target_lib_id = l['id']
                            target_lib_name = l['name']
                            break

                if not target_lib_id:
                    if wf_libs:
                        target_lib_id = wf_libs[0]['id']
                        target_lib_name = wf_libs[0]['name']
                    else:
                        default_name = "ComfyUI Workflows"
                        database.add_workflow_library(default_name)
                        wf_libs = database.get_workflow_libraries()
                        if wf_libs:
                            target_lib_id = wf_libs[0]['id']
                            target_lib_name = wf_libs[0]['name']

                if target_lib_id:
                    wf_name = os.path.splitext(os.path.basename(file_path))[0]
                    new_wf_id = database.add_workflow(target_lib_id, wf_name, file_path, "", file_path if ext == '.png' else "")
                    if new_wf_id:
                        self.refresh_workflow_libraries()
                        self.on_workflow_library_selected(target_lib_name)
                        wf_data = database.get_workflow_by_id(new_wf_id)
                        if wf_data:
                            self.on_workflow_clicked(wf_data)
                        from ui.toast_notification import ToastNotification
                        ToastNotification.show_toast(self.win, f"✨ {wf_name}: {i18n.t('toast_png_workflow_imported')}", duration=3000)
                        return

        # If user dropped an image while editing a note in the detail panel
        if ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
            if hasattr(self.win, 'detail_panel') and getattr(self.win.detail_panel, 'mode', None) == "NOTE":
                self.win.detail_panel.update_image(file_path)
                self.win.detail_panel.note_section.check_changes()
                from ui.toast_notification import ToastNotification
                ToastNotification.show_toast(self.win, f"🖼️ {os.path.basename(file_path)}", duration=2000)

    @Slot(str)
    def on_library_selected(self, library_name):
        self.showing_trash = False
        self.active_library = library_name
        self.active_workflow_library = ""
        self.win.sidebar.libraries_list.clearSelection()
        models = database.get_models_in_library(library_name, show_hidden=self.incognito_active)
        self.win.show_library(library_name, models)

    @Slot(str)
    def on_workflow_library_selected(self, library_name):
        self.showing_trash = False
        self.active_library = ""
        self.win.sidebar.models_list.clearSelection()
        self.active_workflow_library = library_name
        
        lib_id = database.get_library_id(library_name)
        workflows = database.get_workflows_in_library(lib_id, show_hidden=self.incognito_active)
        self.win.show_workflow_library(lib_id, library_name, workflows)

    @Slot()
    def on_new_library_requested(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self.win, i18n.t("view_new_library_dialog_title"), i18n.t("view_new_library_dialog_label"))
        if ok and name.strip():
            name = name.strip()
            # Prevent collisions with default libraries
            if name in ["Lora Modelleri", "Checkpoint Modelleri", "Favoriler"]:
                QMessageBox.warning(self.win, i18n.t("settings_error_path"), i18n.t("view_duplicate_library_error"), QMessageBox.Ok)
                return
            
            # Prevent duplicate creation
            if database.add_workflow_library(name):
                self.refresh_libraries()
                self.win.statusBar().showMessage(i18n.t("view_library_created").format(name=name), 3000)
            else:
                QMessageBox.warning(self.win, i18n.t("settings_error_path"), i18n.t("view_duplicate_exists").format(name=name), QMessageBox.Ok)

    @Slot(str)
    def on_delete_workflow_library(self, library_name):
        lib_name = (library_name or "").strip()
        wf_libs = database.get_workflow_libraries()
        target_lib = None
        for lib in wf_libs:
            if lib['name'] == lib_name:
                target_lib = lib
                break
        if not target_lib:
            return

        lib_id = target_lib['id']
        count = database.get_workflow_count_in_library(lib_id, show_hidden=True)

        reply = QMessageBox.question(
            self.win,
            i18n.t("workflow_delete_library"),
            i18n.t("workflow_delete_library_confirm").format(name=lib_name, count=count),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            database.delete_workflow_library(lib_id)
            if self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "WORKFLOW":
                self.win.hide_detail_panel()

            if self.active_workflow_library == lib_name:
                self.active_workflow_library = None
                self.win.show_welcome()

            self.refresh_libraries()
            self.win.show_toast(i18n.t("workflow_delete_library_success").format(name=lib_name), "success")

    @Slot(dict)
    def on_workflow_clicked(self, workflow_data):
        fresh_wf = database.get_workflow_by_id(workflow_data['id'])
        if fresh_wf:
            self.win.detail_panel.set_workflow(fresh_wf)
            self.win.show_detail_panel(fresh_wf)

    @Slot(int, str, str, str, str)
    def on_add_workflow(self, library_id, name, file_path, description, image_path):
        database.add_workflow(library_id, name, file_path, description, image_path)
        self.refresh_workflow_grid(library_id)
        self.refresh_libraries() # update badge counts in sidebar
        self.win.statusBar().showMessage(i18n.t("status_wf_added").format(name=name), 3000)

    @Slot(int, str, str, str)
    def on_save_workflow_data(self, workflow_id, name, description, notes):
        database.update_workflow_data(workflow_id, name, description, notes)
        self.win.statusBar().showMessage(i18n.t("status_wf_saved"), 3000)
        
        wf = database.get_workflow_by_id(workflow_id)
        if wf:
            self.win.detail_panel.set_workflow(wf)
            self.refresh_workflow_grid(wf['library_id'])

    @Slot(int)
    def on_delete_workflow(self, workflow_id):
        wf = database.get_workflow_by_id(workflow_id)
        if wf:
            library_id = wf['library_id']
            if wf.get('image_path'):
                img_path = wf['image_path']
                project_images_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
                if os.path.dirname(os.path.abspath(img_path)) == project_images_dir and os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                        
            database.delete_workflow(workflow_id)
            self.win.hide_detail_panel()
            self.refresh_workflow_grid(library_id)
            self.refresh_libraries()
            self.win.statusBar().showMessage(i18n.t("status_wf_deleted"), 3000)

    @Slot(int, str)
    def on_workflow_image_changed(self, workflow_id, file_path):
        dest_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_folder_error_title"), i18n.t("msg_folder_error_text").format(error=e), QMessageBox.Ok)
            return

        ext = os.path.splitext(file_path)[1].lower()
        timestamp = int(time.time())
        dest_path = os.path.join(dest_dir, f"wf_preview_{workflow_id}_{timestamp}{ext}")
        
        try:
            shutil.copy2(file_path, dest_path)
            
            old_wf = database.get_workflow_by_id(workflow_id)
            if old_wf and old_wf.get('image_path'):
                old_path = old_wf['image_path']
                if os.path.exists(old_path) and old_path != dest_path:
                    try:
                        os.remove(old_path)
                    except Exception as clean_err:
                        print(f"Error removing old image file {old_path}: {clean_err}")

            database.update_workflow_image(workflow_id, dest_path)
            self.win.statusBar().showMessage(i18n.t("status_wf_img_updated"), 3000)
            
            wf = database.get_workflow_by_id(workflow_id)
            if wf:
                self.win.detail_panel.set_workflow(wf)
                self.refresh_workflow_grid(wf['library_id'])
        except OSError as e:
            QMessageBox.critical(
                self.win, i18n.t("msg_copy_error_title"), 
                i18n.t("msg_copy_error_text").format(error=e),
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_copy_error_title"), i18n.t("msg_copy_error_text").format(error=e), QMessageBox.Ok)

    def refresh_workflow_grid(self, library_id):
        # Retrieve name
        wf_libs = database.get_workflow_libraries()
        library_name = ""
        for lib in wf_libs:
            if lib['id'] == library_id:
                library_name = lib['name']
                break
        if library_name:
            workflows = database.get_workflows_in_library(library_id, show_hidden=self.incognito_active)
            self.win.workflow_view.set_workflows(library_id, library_name, workflows)

    @Slot(dict)
    def on_model_clicked(self, model_data):
        model_id = model_data['id']
        fresh_model_data = database.get_model_by_id(model_id)
        trigger_words = database.get_trigger_words(model_id)
        if fresh_model_data:
            self.win.detail_panel.set_model(fresh_model_data, trigger_words)
            self.win.show_detail_panel(fresh_model_data)

    @Slot(str)
    def on_welcome_title_changed(self, new_title):
        database.set_setting("welcome_title", new_title)
        self.win.statusBar().showMessage(i18n.t("status_title_updated"), 3000)

    @Slot(str)
    def on_welcome_wallpaper_changed(self, file_path):
        dest_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_folder_error_title"), i18n.t("msg_folder_error_text").format(error=e), QMessageBox.Ok)
            return

        ext = os.path.splitext(file_path)[1].lower()
        timestamp = int(time.time())
        dest_path = os.path.join(dest_dir, f"welcome_wallpaper_{timestamp}{ext}")

        try:
            shutil.copy2(file_path, dest_path)
            
            # Clean up old wallpaper
            old_wallpaper = database.get_setting("welcome_wallpaper", "")
            if old_wallpaper and os.path.exists(old_wallpaper) and old_wallpaper != dest_path:
                try:
                    os.remove(old_wallpaper)
                except Exception as clean_err:
                    print(f"Error cleaning up old wallpaper {old_wallpaper}: {clean_err}")

            database.set_setting("welcome_wallpaper", dest_path)
            self.win.welcome_screen.set_wallpaper(dest_path)
            self.win.statusBar().showMessage(i18n.t("status_bg_updated"), 3000)
        except OSError as e:
            QMessageBox.critical(
                self.win, i18n.t("msg_copy_error_title"), 
                i18n.t("msg_copy_error_text").format(error=e),
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_copy_error_title"), i18n.t("msg_copy_error_text").format(error=e), QMessageBox.Ok)

    @Slot()
    def on_settings_requested(self):
        dialog = SettingsDialog(self.win)
        comfyui_enabled = int(database.get_setting("comfyui_enabled", "1"))
        lora_path = database.get_setting("lora_path", "")
        ckpt_path = database.get_setting("ckpt_path", "")
        auto_save_enabled = database.get_setting("auto_save_enabled", "1")
        auto_save_interval = database.get_setting("auto_save_interval", "1.5")
        theme = database.get_setting("theme", "Koyu Gece")
        lang = database.get_setting("lang", "en")
        custom_colors = database.get_setting("custom_theme_colors", "{}")
        
        dialog.set_settings(lora_path, ckpt_path, int(auto_save_enabled), float(auto_save_interval), theme, lang, custom_colors, comfyui_enabled=comfyui_enabled)

        def on_backup_restored(path):
            self.refresh_libraries()
            self.refresh_workflow_libraries()
            self.refresh_notes()
            self.load_corkboard_notes()
            self.win.statusBar().showMessage(i18n.t("settings_restore_success"), 3000)

        dialog.backup_restored.connect(on_backup_restored)

        if dialog.exec():
            settings = dialog.get_settings()
            new_comfyui = settings.get('comfyui_enabled', 1)
            new_lora = settings['lora_path']
            new_ckpt = settings['ckpt_path']
            new_ase = settings['auto_save_enabled']
            new_asi = settings['auto_save_interval']
            new_theme = settings['theme']
            new_lang = settings['lang']
            new_custom_colors = settings.get('custom_theme_colors', {})

            new_custom_colors_str = json.dumps(new_custom_colors)

            database.set_setting("comfyui_enabled", str(new_comfyui))
            database.set_setting("lora_path", new_lora)
            database.set_setting("ckpt_path", new_ckpt)
            database.set_setting("auto_save_enabled", str(new_ase))
            database.set_setting("auto_save_interval", str(new_asi))
            database.set_setting("theme", new_theme)
            database.set_setting("lang", new_lang)
            database.set_setting("custom_theme_colors", new_custom_colors_str)

            self.comfyui_enabled = bool(new_comfyui)
            self.win.set_comfyui_enabled(self.comfyui_enabled)
            
            # Sync settings with DetailPanel so that it updates instantly!
            self.win.detail_panel.sync_auto_save_settings(new_ase, new_asi)

            # Apply new language and theme
            i18n.set_lang(new_lang)
            self.win.change_theme(new_theme, new_custom_colors_str)
            self.win.retranslate_ui()
            
            # Refresh sidebar counts, names, and notes translation
            if self.comfyui_enabled:
                self.refresh_libraries()
            self.refresh_notes()
            
            self.win.statusBar().showMessage(i18n.t("status_saved"), 3000)
            
            if self.comfyui_enabled:
                if new_lora and os.path.exists(new_lora):
                    self.run_silent_scan(new_lora, "Lora Modelleri")
                if new_ckpt and os.path.exists(new_ckpt):
                    self.run_silent_scan(new_ckpt, "Checkpoint Modelleri")

    def run_silent_scan(self, path, library_name):
        scanner = ModelScanner(path, library_name, self.win)
        self.running_scanners.append(scanner)
        
        def on_finished(count):
            disp_name = self.win.sidebar.tr_lib_name(library_name)
            self.win.statusBar().showMessage(i18n.t("status_auto_scanned").format(name=disp_name, count=count), 4000)
            self.refresh_libraries() # Refresh counts in sidebar
            if self.active_library == library_name:
                self.on_library_selected(library_name)
            if scanner in self.running_scanners:
                self.running_scanners.remove(scanner)
            scanner.deleteLater()

        scanner.finished_signal.connect(on_finished)
        scanner.start()

    @Slot(int, str, str, str)
    def on_save_model_data(self, model_id, name, notes, base_architecture=""):
        database.update_model_data(model_id, name, notes, base_architecture)
        self.win.statusBar().showMessage(i18n.t("status_model_saved"), 3000)
        self.win.show_toast(i18n.t("toast_saved"), "success")
        
        model_data = database.get_model_by_id(model_id)
        trigger_words = database.get_trigger_words(model_id)
        if model_data:
            self.win.detail_panel.set_model(model_data, trigger_words)
        
        self.win.library_view.update_card_model_data(model_id, name, base_architecture)

    @Slot(int, str)
    def on_add_trigger(self, model_id, word):
        if database.add_trigger_word(model_id, word):
            self.win.statusBar().showMessage(i18n.t("status_trigger_added").format(word=word), 2000)
            model_data = database.get_model_by_id(model_id)
            trigger_words = database.get_trigger_words(model_id)
            if model_data:
                self.win.detail_panel.set_model(model_data, trigger_words)

    @Slot(int, str)
    def on_delete_trigger(self, model_id, word):
        database.delete_trigger_word(model_id, word)
        self.win.statusBar().showMessage(i18n.t("status_trigger_deleted").format(word=word), 2000)
        model_data = database.get_model_by_id(model_id)
        trigger_words = database.get_trigger_words(model_id)
        if model_data:
            self.win.detail_panel.set_model(model_data, trigger_words)

    @Slot(int, str)
    def on_model_image_changed(self, model_id, file_path):
        dest_dir = os.path.abspath(database.SAVED_IMAGES_DIR)
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_folder_error_title"), i18n.t("msg_folder_error_text").format(error=e), QMessageBox.Ok)
            return

        ext = os.path.splitext(file_path)[1].lower()
        timestamp = int(time.time())
        dest_path = os.path.join(dest_dir, f"model_{model_id}_{timestamp}{ext}")
        
        try:
            shutil.copy2(file_path, dest_path)
            
            old_model = database.get_model_by_id(model_id)
            if old_model and old_model.get('image_path'):
                old_path = old_model['image_path']
                if os.path.exists(old_path) and old_path != dest_path:
                    try:
                        os.remove(old_path)
                    except Exception as clean_err:
                        print(f"Error removing old image file {old_path}: {clean_err}")

            database.update_model_image(model_id, dest_path)
            self.win.statusBar().showMessage(i18n.t("status_model_img_updated"), 3000)
            
            model_data = database.get_model_by_id(model_id)
            trigger_words = database.get_trigger_words(model_id)
            if model_data:
                self.win.detail_panel.set_model(model_data, trigger_words)
            
            self.win.library_view.update_card_image(model_id, dest_path)
        except OSError as e:
            QMessageBox.critical(
                self.win, i18n.t("msg_copy_error_title"), 
                i18n.t("msg_copy_error_text").format(error=e),
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.critical(self.win, i18n.t("msg_copy_error_title"), i18n.t("msg_copy_error_text").format(error=e), QMessageBox.Ok)

    @Slot(str)
    def on_scan_library(self, library_name):
        if library_name in ("Lora Modelleri", "Lora Models"):
            dir_path = database.get_setting("lora_path", "")
        elif library_name in ("Checkpoint Modelleri", "Checkpoint Models"):
            dir_path = database.get_setting("ckpt_path", "")
        else:
            QMessageBox.warning(self.win, i18n.t("msg_copy_error_title"), i18n.t("msg_unknown_lib_text").format(name=library_name), QMessageBox.Ok)
            return

        if not dir_path or not os.path.exists(dir_path):
            QMessageBox.warning(
                self.win, i18n.t("msg_path_not_specified_title"), 
                i18n.t("msg_path_not_specified_text").format(name=library_name), 
                QMessageBox.Ok
            )
            self.on_settings_requested()
            return

        self.progress_dialog = QProgressDialog(i18n.t("msg_progress_scanning"), i18n.t("msg_progress_cancel"), 0, 0, self.win)
        self.progress_dialog.setWindowTitle(i18n.t("msg_progress_title"))
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumWidth(400)
        self.progress_dialog.canceled.connect(self.cancel_scan)
        self.progress_dialog.show()

        self.scan_thread = ModelScanner(dir_path, library_name)
        self.scan_thread.progress_signal.connect(self.on_scan_progress)
        self.scan_thread.finished_signal.connect(self.on_scan_finished)
        self.scan_thread.start()

    def on_scan_progress(self, filename):
        if self.progress_dialog:
            self.progress_dialog.setLabelText(i18n.t("msg_scanning_file").format(file=filename))

    def on_scan_finished(self, count):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
            
        self.refresh_libraries() # Refresh counts in sidebar
        
        self.win.show_toast(
            i18n.t("toast_scan_completed").format(count=count), 
            "success"
        )
        
        if self.active_library:
            self.on_library_selected(self.active_library)

        self.scan_thread = None

    def cancel_scan(self):
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.requestInterruption()
            self.win.statusBar().showMessage(i18n.t("status_cancelling_scan"), 3000)

    @Slot(int, bool)
    def on_favorite_toggled(self, model_id, is_favorite):
        database.toggle_model_favorite(model_id, is_favorite)
        self.win.library_view.update_card_favorite(model_id, is_favorite)
            
        if self.win.detail_panel.isVisible() and self.win.detail_panel.model_data and self.win.detail_panel.model_data['id'] == model_id:
            self.win.detail_panel.model_data['is_favorite'] = 1 if is_favorite else 0
            
        self.win.statusBar().showMessage(i18n.t("status_fav_updated"), 2000)

    @Slot(int, str)
    def on_add_tag(self, model_id, tag_name):
        if database.add_model_tag(model_id, tag_name):
            self.win.statusBar().showMessage(i18n.t("status_tag_added").format(tag_name=tag_name), 2000)
            self.win.show_toast(i18n.t("status_tag_added").format(tag_name=tag_name), "success")
            self.refresh_active_model_details(model_id)

    @Slot(int, str)
    def on_delete_tag(self, model_id, tag_name):
        if database.delete_model_tag(model_id, tag_name):
            self.win.statusBar().showMessage(i18n.t("status_tag_removed").format(tag_name=tag_name), 2000)
            self.win.show_toast(i18n.t("status_tag_removed").format(tag_name=tag_name), "info")
            self.refresh_active_model_details(model_id)

    @Slot(list)
    def on_bulk_add_tag(self, model_ids):
        if not model_ids:
            return
        tag_name, ok = QInputDialog.getText(
            self.win, i18n.t("bulk_add_tag_title"), i18n.t("bulk_add_tag_label")
        )
        if ok and tag_name.strip():
            tag = tag_name.strip()
            for m_id in model_ids:
                database.add_model_tag(m_id, tag)
            self.win.show_toast(i18n.t("bulk_tag_done").format(count=len(model_ids), tag=tag), "success")
            if self.active_library:
                self.win.library_view.models_data = database.get_models_in_library(self.active_library, show_hidden=self.incognito_active)
                self.win.library_view.apply_filters()
            if self.win.detail_panel.isVisible() and self.win.detail_panel.model_data and self.win.detail_panel.model_data['id'] in model_ids:
                self.refresh_active_model_details(self.win.detail_panel.model_data['id'])

    @Slot(list)
    def on_bulk_remove_tag(self, model_ids):
        if not model_ids:
            return
        tag_name, ok = QInputDialog.getText(
            self.win, i18n.t("bulk_remove_tag_title"), i18n.t("bulk_remove_tag_label")
        )
        if ok and tag_name.strip():
            tag = tag_name.strip()
            for m_id in model_ids:
                database.delete_model_tag(m_id, tag)
            self.win.show_toast(i18n.t("bulk_tag_removed").format(count=len(model_ids), tag=tag), "info")
            if self.active_library:
                self.win.library_view.models_data = database.get_models_in_library(self.active_library, show_hidden=self.incognito_active)
                self.win.library_view.apply_filters()
            if self.win.detail_panel.isVisible() and self.win.detail_panel.model_data and self.win.detail_panel.model_data['id'] in model_ids:
                self.refresh_active_model_details(self.win.detail_panel.model_data['id'])

    @Slot(list, bool)
    def on_bulk_favorite(self, model_ids, is_favorite):
        if not model_ids:
            return
        for m_id in model_ids:
            database.toggle_model_favorite(m_id, is_favorite)
            self.win.library_view.update_card_favorite(m_id, is_favorite)
        self.win.show_toast(i18n.t("bulk_fav_done").format(count=len(model_ids)), "success")
        if self.active_library:
            self.win.library_view.models_data = database.get_models_in_library(self.active_library, show_hidden=self.incognito_active)
            self.win.library_view.apply_filters()

    @Slot(list)
    def on_bulk_delete(self, model_ids):
        if not model_ids:
            return
        count = len(model_ids)
        if database.delete_models(model_ids):
            self.win.show_toast(i18n.t("bulk_delete_models_done").format(count=count), "info")
            if self.win.detail_panel.isVisible() and self.win.detail_panel.model_data and self.win.detail_panel.model_data.get('id') in model_ids:
                self.win.hide_detail_panel()
            if self.active_library:
                self.win.library_view.clear_selection()
                self.win.library_view.models_data = database.get_models_in_library(self.active_library, show_hidden=self.incognito_active)
                self.win.library_view.apply_filters()
            self.refresh_libraries()

    @Slot(int)
    def on_detail_delete_model(self, model_id):
        self.on_bulk_delete([model_id])

    def refresh_active_model_details(self, model_id):
        fresh_model_data = database.get_model_by_id(model_id)
        trigger_words = database.get_trigger_words(model_id)
        if fresh_model_data:
            self.win.detail_panel.set_model(fresh_model_data, trigger_words)
            if self.active_library:
                self.win.library_view.models_data = database.get_models_in_library(self.active_library, show_hidden=self.incognito_active)
                
            self.win.library_view.on_local_search_changed(self.win.library_view.local_search.text())

    def toggle_incognito_mode(self):
        self.incognito_active = not self.incognito_active
        # Update UI indicators
        self.win.sidebar.set_incognito_active(self.incognito_active)
        self.win.incognito_active = self.incognito_active
        # Refresh sidebar counts & lists
        self.refresh_libraries()
        self.refresh_notes()
        
        current_index = self.win.center_stack.currentIndex()
        if current_index == 0:
            self.win.show_welcome()
        elif current_index == 1 and self.active_library:
            self.on_library_selected(self.active_library)
        elif current_index == 4 and self.active_workflow_library:
            self.on_workflow_library_selected(self.active_workflow_library)
        elif current_index in [2, 3]:
            if getattr(self, 'showing_trash', False):
                self.on_trash_requested()
            else:
                self.on_all_notes_requested()

        self.win.statusBar().showMessage(i18n.t("status_incognito_on") if self.incognito_active else i18n.t("status_incognito_off"), 2000)

    @Slot(object)
    def on_model_hide(self, model_data):
        model_id = model_data['id'] if isinstance(model_data, dict) else model_data
        name = model_data.get('name', '') if isinstance(model_data, dict) else f"#{model_id}"
        database.set_model_hidden(model_id, True)
        self.win.statusBar().showMessage(i18n.t("status_model_hidden").format(name=name), 2000)
        self.refresh_libraries()
        if self.active_library:
            self.on_library_selected(self.active_library)
        if not self.incognito_active:
            self.win.hide_detail_panel()
        elif self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "MODEL" and self.win.detail_panel.model_data and self.win.detail_panel.model_data['id'] == model_id:
            self.refresh_active_model_details(model_id)

    @Slot(object)
    def on_model_unhide(self, model_data):
        model_id = model_data['id'] if isinstance(model_data, dict) else model_data
        name = model_data.get('name', '') if isinstance(model_data, dict) else f"#{model_id}"
        database.set_model_hidden(model_id, False)
        self.win.statusBar().showMessage(i18n.t("status_model_unhidden").format(name=name), 2000)
        self.refresh_libraries()
        if self.active_library:
            self.on_library_selected(self.active_library)
        if self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "MODEL" and self.win.detail_panel.model_data and self.win.detail_panel.model_data['id'] == model_id:
            self.refresh_active_model_details(model_id)

    @Slot(object)
    def on_workflow_hide(self, workflow_data):
        workflow_id = workflow_data['id'] if isinstance(workflow_data, dict) else workflow_data
        name = workflow_data.get('name', '') if isinstance(workflow_data, dict) else f"#{workflow_id}"
        database.set_workflow_hidden(workflow_id, True)
        self.win.statusBar().showMessage(i18n.t("status_wf_hidden").format(name=name), 2000)
        self.refresh_libraries()
        if self.active_workflow_library:
            self.on_workflow_library_selected(self.active_workflow_library)
        if not self.incognito_active:
            self.win.hide_detail_panel()
        elif self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "WORKFLOW" and self.win.detail_panel.workflow_data and self.win.detail_panel.workflow_data['id'] == workflow_id:
            self.on_workflow_clicked({'id': workflow_id})

    @Slot(object)
    def on_workflow_unhide(self, workflow_data):
        workflow_id = workflow_data['id'] if isinstance(workflow_data, dict) else workflow_data
        name = workflow_data.get('name', '') if isinstance(workflow_data, dict) else f"#{workflow_id}"
        database.set_workflow_hidden(workflow_id, False)
        self.win.statusBar().showMessage(i18n.t("status_wf_unhidden").format(name=name), 2000)
        self.refresh_libraries()
        if self.active_workflow_library:
            self.on_workflow_library_selected(self.active_workflow_library)
        if self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "WORKFLOW" and self.win.detail_panel.workflow_data and self.win.detail_panel.workflow_data['id'] == workflow_id:
            self.on_workflow_clicked({'id': workflow_id})

    @Slot(object)
    def on_note_hide(self, note_data):
        note_id = note_data['id'] if isinstance(note_data, dict) else note_data
        title = note_data.get('title', '') if isinstance(note_data, dict) else f"#{note_id}"
        database.set_note_hidden(note_id, True)
        self.win.statusBar().showMessage(i18n.t("status_note_hidden").format(title=title), 2000)
        self.refresh_notes()
        if not self.incognito_active:
            self.win.hide_detail_panel()
        elif self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "NOTE" and self.win.detail_panel.note_data and self.win.detail_panel.note_data['id'] == note_id:
            self.open_note_in_drawer(note_id)

    @Slot(object)
    def on_note_unhide(self, note_data):
        note_id = note_data['id'] if isinstance(note_data, dict) else note_data
        title = note_data.get('title', '') if isinstance(note_data, dict) else f"#{note_id}"
        database.set_note_hidden(note_id, False)
        self.win.statusBar().showMessage(i18n.t("status_note_unhidden").format(title=title), 2000)
        self.refresh_notes()
        if self.win.detail_panel.isVisible() and self.win.detail_panel.mode == "NOTE" and self.win.detail_panel.note_data and self.win.detail_panel.note_data['id'] == note_id:
            self.open_note_in_drawer(note_id)

def main():
    app = QApplication(sys.argv)
    database.initialize_db()
    win = MainWindow()
    controller = AppController(win)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
