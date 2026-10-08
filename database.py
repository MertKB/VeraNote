# Vera Note - AI Model & Workflow Manager
# Copyright (C) 2026 Vera Note Contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# database.py
import os
import sqlite3
import shutil
import contextlib
import threading
import zipfile
import time

# Thread-local storage for persistent per-thread SQLite connections
_thread_local = threading.local()

# Hidden private data directory relative to AppData/Home
db_dir = os.path.join(os.path.expanduser("~"), ".veranote_data")
os.makedirs(db_dir, exist_ok=True)
DB_NAME = os.path.join(db_dir, "veranote.db")

SAVED_IMAGES_DIR = os.path.join(db_dir, "saved_images")
os.makedirs(SAVED_IMAGES_DIR, exist_ok=True)

SAVED_WORKFLOWS_DIR = os.path.join(db_dir, "saved_workflows")
os.makedirs(SAVED_WORKFLOWS_DIR, exist_ok=True)

def resolve_image_path(path: str) -> str:
    """Resolve image path handling absolute paths, legacy folder names, and relative paths."""
    if not path:
        return ""
    if os.path.exists(path):
        return os.path.abspath(path)
    
    base = os.path.basename(path)
    if not base:
        return ""
        
    # Check SAVED_IMAGES_DIR (~/.veranote_data/saved_images/)
    p_saved = os.path.join(SAVED_IMAGES_DIR, base)
    if os.path.exists(p_saved):
        return os.path.abspath(p_saved)
        
    # Check root images directory
    module_dir = os.path.dirname(os.path.abspath(__file__))
    p_local = os.path.join(module_dir, "images", base)
    if os.path.exists(p_local):
        return os.path.abspath(p_local)
        
    p_cwd = os.path.join(os.getcwd(), "images", base)
    if os.path.exists(p_cwd):
        return os.path.abspath(p_cwd)
        
    return ""

# Automatic migration of existing database from legacy app data directories
for legacy_dir_name in [".veranote_legacy_data"]:
    legacy_db_dir = os.path.join(os.path.expanduser("~"), legacy_dir_name)
    legacy_db_file = os.path.join(legacy_db_dir, "veranote_legacy.db")
    if os.path.exists(legacy_db_file) and not os.path.exists(DB_NAME):
        try:
            shutil.copy2(legacy_db_file, DB_NAME)
            legacy_images = os.path.join(legacy_db_dir, "saved_images")
            if os.path.exists(legacy_images):
                for f in os.listdir(legacy_images):
                    src = os.path.join(legacy_images, f)
                    dst = os.path.join(SAVED_IMAGES_DIR, f)
                    if not os.path.exists(dst) and os.path.isfile(src):
                        shutil.copy2(src, dst)
        except Exception as e:
            print(f"Migration error from {legacy_dir_name}: {e}")

# Automatic migration of existing database from workspace root (fallback)
for legacy_name in ["veranote_old.db"]:
    legacy_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), legacy_name)
    if os.path.exists(legacy_db_path):
        if not os.path.exists(DB_NAME):
            try:
                shutil.copy2(legacy_db_path, DB_NAME)
            except Exception as e:
                print(f"Migration error from workspace root: {e}")
        try:
            os.remove(legacy_db_path)
        except Exception:
            pass

def get_db_connection():
    """Get or create a thread-local SQLite connection with optimized PRAGMAs."""
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_NAME, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        _thread_local.conn = conn
    return conn

def close_db_connection():
    """Close the active thread-local connection if present."""
    conn = getattr(_thread_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _thread_local.conn = None

@contextlib.contextmanager
def get_connection():
    """Return a context manager yielding the persistent thread-local connection within a transaction."""
    conn = get_db_connection()
    try:
        with conn:
            yield conn
    except sqlite3.OperationalError as e:
        # If connection was lost or corrupted, reset thread local connection
        if "closed" in str(e).lower() or "disk i/o error" in str(e).lower():
            try:
                conn.close()
            except Exception:
                pass
            _thread_local.conn = None
        raise

def initialize_db():
    """Create tables if they don't exist and pre-populate default libraries."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)

        # Notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT,
                image_path TEXT,
                display_mode TEXT DEFAULT 'WITH_IMAGE',
                is_favorite INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                is_pinned_corkboard INTEGER DEFAULT 0,
                color_hex TEXT DEFAULT '#FEF08A',
                corkboard_x INTEGER DEFAULT 0,
                corkboard_y INTEGER DEFAULT 0,
                corkboard_w INTEGER DEFAULT 200,
                corkboard_h INTEGER DEFAULT 180,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Libraries
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS libraries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                type TEXT DEFAULT 'MODEL'
            );
        """)

        # Workflows (ComfyUI Workflow repository)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                description TEXT,
                image_path TEXT,
                notes TEXT,
                is_hidden INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(library_id) REFERENCES libraries(id) ON DELETE CASCADE
            );
        """)

        # Models
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                library_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT,
                image_path TEXT,
                notes TEXT,
                description TEXT,
                is_favorite INTEGER DEFAULT 0,
                is_hidden INTEGER DEFAULT 0,
                base_architecture TEXT,
                embedding BLOB,
                FOREIGN KEY(library_id) REFERENCES libraries(id) ON DELETE CASCADE
            );
        """)

        # Trigger Words
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trigger_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE,
                UNIQUE(model_id, word)
            );
        """)

        # Tags
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
        """)

        # Model Tags (Many-to-Many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_tags (
                model_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL,
                FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                UNIQUE(model_id, tag_id)
            );
        """)

        # Note Models (Many-to-Many for notes-models association)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_models (
                note_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE,
                FOREIGN KEY(model_id) REFERENCES models(id) ON DELETE CASCADE,
                UNIQUE(note_id, model_id)
            );
        """)

        # Daily Notes (Ajanda / Günlük Notlar)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_notes (
                date TEXT PRIMARY KEY,
                content TEXT DEFAULT '',
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Tasks (Ajanda Görevleri)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                is_completed INTEGER DEFAULT 0,
                due_date TEXT,
                priority INTEGER DEFAULT 1,
                daily_note_date TEXT,
                note_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                FOREIGN KEY (daily_note_date) REFERENCES daily_notes(date) ON DELETE CASCADE,
                FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE SET NULL
            );
        """)

        # Recurring Routines (Ajanda Tekrarlayan Rutinler / Şablonlar)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_routines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                frequency TEXT DEFAULT 'daily',
                priority INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()

        # Migrate libraries table if type column is missing
        try:
            cursor.execute("PRAGMA table_info(libraries);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'type' not in columns:
                cursor.execute("ALTER TABLE libraries ADD COLUMN type TEXT DEFAULT 'MODEL';")
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error migrating libraries table: {e}")

        # Migrate notes table if columns are missing (RUN BEFORE INDEX CREATION!)
        try:
            cursor.execute("PRAGMA table_info(notes);")
            columns = [row['name'] for row in cursor.fetchall()]
            
            if 'image_path' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN image_path TEXT;")
            if 'display_mode' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN display_mode TEXT DEFAULT 'WITH_IMAGE';")
            if 'is_favorite' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_favorite INTEGER DEFAULT 0;")
            if 'created_at' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
            if 'is_deleted' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_deleted INTEGER DEFAULT 0;")
            if 'is_pinned_corkboard' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_pinned_corkboard INTEGER DEFAULT 0;")
            if 'color_hex' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN color_hex TEXT DEFAULT '#FEF08A';")
            if 'corkboard_x' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN corkboard_x INTEGER DEFAULT 0;")
            if 'corkboard_y' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN corkboard_y INTEGER DEFAULT 0;")
            if 'corkboard_w' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN corkboard_w INTEGER DEFAULT 200;")
            if 'corkboard_h' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN corkboard_h INTEGER DEFAULT 180;")
            if 'embedding' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN embedding BLOB;")
                
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error migrating database (notes table): {e}")

        # Add is_favorite column to models if it doesn't exist (migration for existing db)
        try:
            cursor.execute("SELECT is_favorite FROM models LIMIT 1;")
        except sqlite3.OperationalError:
            try:
                cursor.execute("ALTER TABLE models ADD COLUMN is_favorite INTEGER DEFAULT 0;")
                conn.commit()
            except sqlite3.Error as e:
                print(f"Error migrating database (adding is_favorite to models): {e}")

        # Migrate is_hidden columns
        try:
            cursor.execute("PRAGMA table_info(notes);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'is_hidden' not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_hidden INTEGER DEFAULT 0;")
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error migrating notes table (is_hidden): {e}")

        try:
            cursor.execute("PRAGMA table_info(workflows);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'is_hidden' not in columns:
                cursor.execute("ALTER TABLE workflows ADD COLUMN is_hidden INTEGER DEFAULT 0;")
            if 'title' not in columns:
                cursor.execute("ALTER TABLE workflows ADD COLUMN title TEXT;")
            if 'workflow_json' not in columns:
                cursor.execute("ALTER TABLE workflows ADD COLUMN workflow_json TEXT;")
            if 'is_favorite' not in columns:
                cursor.execute("ALTER TABLE workflows ADD COLUMN is_favorite INTEGER DEFAULT 0;")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error migrating workflows table (columns): {e}")

        try:
            cursor.execute("PRAGMA table_info(models);")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'is_hidden' not in columns:
                cursor.execute("ALTER TABLE models ADD COLUMN is_hidden INTEGER DEFAULT 0;")
            if 'base_architecture' not in columns:
                cursor.execute("ALTER TABLE models ADD COLUMN base_architecture TEXT;")
            if 'embedding' not in columns:
                cursor.execute("ALTER TABLE models ADD COLUMN embedding BLOB;")
            conn.commit()

            # Auto backfill base_architecture for existing models if empty
            cursor.execute("SELECT id, name, file_path FROM models WHERE base_architecture IS NULL OR base_architecture = '';")
            rows = cursor.fetchall()
            if rows:
                from utils.png_parser import detect_base_architecture
                updates = []
                for r in rows:
                    arch = detect_base_architecture([r['name'], r['file_path']])
                    if arch:
                        updates.append((arch, r['id']))
                if updates:
                    cursor.executemany("UPDATE models SET base_architecture = ? WHERE id = ?;", updates)
                    conn.commit()
        except sqlite3.Error as e:
            print(f"Error migrating models table: {e}")

        # CREATE INDEXES FOR OPTIMIZED QUERY SPEED
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_library_id ON models(library_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_library_id ON workflows(library_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trigger_words_model_id ON trigger_words(model_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_tags_model_id ON model_tags(model_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_model_tags_tag_id ON model_tags(tag_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_is_favorite ON notes(is_favorite);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_models_note_id ON note_models(note_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_note_models_model_id ON note_models(model_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_is_favorite ON workflows(is_favorite);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_fav_hidden ON models(is_favorite, is_hidden);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_models_lib_hidden ON models(library_id, is_hidden);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_pinned_hidden ON notes(is_pinned_corkboard, is_hidden);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflows_lib_hidden ON workflows(library_id, is_hidden);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_daily_date ON tasks(daily_note_date);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(is_completed);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_routines_active ON recurring_routines(is_active);")

        conn.commit()

        # Insert default libraries and settings if not exists
        try:
            cursor.execute("INSERT OR IGNORE INTO libraries (name, type) VALUES ('Lora Modelleri', 'MODEL');")
            cursor.execute("INSERT OR IGNORE INTO libraries (name, type) VALUES ('Checkpoint Modelleri', 'MODEL');")
            # Force update in case they existed without type
            cursor.execute("UPDATE libraries SET type = 'MODEL' WHERE name IN ('Lora Modelleri', 'Checkpoint Modelleri');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_save_enabled', '1');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('auto_save_interval', '1.5');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('comfyui_enabled', '1');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('theme', 'Koyu Gece');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('lang', 'en');")
            cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('custom_theme_colors', '{\"bg_main\":\"#131314\",\"bg_card\":\"#1E1F20\",\"accent_color\":\"#1A73E8\"}');")
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error seeding libraries or settings: {e}")

# --- CRUD METHODS ---

# Settings
def get_setting(key, default=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cursor.fetchone()
        return row['value'] if row else default

def set_setting(key, value):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, str(value)))
        conn.commit()

# Notes
def save_note(note_id, title, content, image_path=None, display_mode='WITH_IMAGE', is_favorite=0, is_deleted=0, color_hex=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if note_id is None:
            c_hex = color_hex if color_hex is not None else 'default'
            cursor.execute("""
                INSERT INTO notes (title, content, image_path, display_mode, is_favorite, is_deleted, color_hex) 
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (title, content, image_path, display_mode, is_favorite, is_deleted, c_hex))
            note_id = cursor.lastrowid
        else:
            if color_hex is not None:
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, content = ?, image_path = ?, display_mode = ?, is_favorite = ?, is_deleted = ?, color_hex = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?;
                """, (title, content, image_path, display_mode, is_favorite, is_deleted, color_hex, note_id))
            else:
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, content = ?, image_path = ?, display_mode = ?, is_favorite = ?, is_deleted = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?;
                """, (title, content, image_path, display_mode, is_favorite, is_deleted, note_id))
        conn.commit()
        return note_id

def update_note_color(note_id, color_hex):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET color_hex = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (color_hex, note_id))
        conn.commit()

def update_corkboard_geometry(note_id, x, y, w=None, h=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if w is not None and h is not None:
            cursor.execute(
                "UPDATE notes SET corkboard_x = ?, corkboard_y = ?, corkboard_w = ?, corkboard_h = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (int(x), int(y), int(w), int(h), note_id)
            )
        else:
            cursor.execute(
                "UPDATE notes SET corkboard_x = ?, corkboard_y = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (int(x), int(y), note_id)
            )
        conn.commit()

def update_corkboard_position(note_id, x, y):
    update_corkboard_geometry(note_id, x, y)

def delete_note(note_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
        conn.commit()

def soft_delete_note(note_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET is_deleted = 1 WHERE id = ?;", (note_id,))
        conn.commit()

def restore_note(note_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET is_deleted = 0 WHERE id = ?;", (note_id,))
        conn.commit()

def permanently_delete_note(note_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?;", (note_id,))
        conn.commit()

def empty_recycle_bin():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE is_deleted = 1;")
        conn.commit()

def get_notes(search_query=None, show_only_favs=False, sort_by="En Yeni", only_deleted=False, show_hidden=False, limit=None, offset=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM notes WHERE "
        if only_deleted:
            query += "is_deleted = 1"
        else:
            query += "is_deleted = 0"
            
        if not show_hidden:
            query += " AND is_hidden = 0"
            
        params = []
        
        if show_only_favs:
            query += " AND is_favorite = 1"
            
        if search_query:
            query += " AND (title LIKE ? OR content LIKE ?)"
            q = f"%{search_query}%"
            params.extend([q, q])
            
        # Sorting (Multilingual: TR & EN support)
        s_lower = (sort_by or "").lower().strip()
        if s_lower in ("a-z", "a to z"):
            query += " ORDER BY title ASC"
        elif s_lower in ("z-a", "z to a"):
            query += " ORDER BY title DESC"
        elif s_lower in ("en eski", "oldest"):
            query += " ORDER BY created_at ASC"
        elif s_lower in ("en son düzenlenen", "son düzenlenen", "last edited", "recently edited"):
            query += " ORDER BY updated_at DESC"
        else: # "En Yeni", "Newest"
            query += " ORDER BY created_at DESC"
            
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
            if offset is not None:
                query += " OFFSET ?"
                params.append(int(offset))
                
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

def get_note_by_id(note_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?;", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        row_dict = dict(row)
        # Fetch associated models
        cursor.execute("""
            SELECT m.id, m.name 
            FROM models m
            JOIN note_models nm ON nm.model_id = m.id
            WHERE nm.note_id = ?
            ORDER BY m.name ASC;
        """, (note_id,))
        row_dict['associated_models'] = [dict(r) for r in cursor.fetchall()]
        return row_dict

def get_libraries(search_query=None, lib_type='MODEL'):
    with get_connection() as conn:
        cursor = conn.cursor()
        if search_query:
            q = f"%{search_query}%"
            cursor.execute("SELECT name FROM libraries WHERE name LIKE ? AND type = ? ORDER BY name ASC;", (q, lib_type))
        else:
            cursor.execute("SELECT name FROM libraries WHERE type = ? ORDER BY name ASC;", (lib_type,))
        return [row['name'] for row in cursor.fetchall()]

def add_library(name):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO libraries (name) VALUES (?);", (name,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_library_id(name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM libraries WHERE name = ?;", (name,))
        row = cursor.fetchone()
        return row['id'] if row else None

# Models
def get_models_in_library(library_name, show_hidden=False, limit=None, offset=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.id, m.library_id, m.name, m.file_path, m.file_hash, m.image_path, m.notes, m.description, m.is_favorite, m.is_hidden, m.base_architecture, m.embedding,
                   (SELECT GROUP_CONCAT(t.name, ',') FROM model_tags mt JOIN tags t ON mt.tag_id = t.id WHERE mt.model_id = m.id) as tags_list,
                   (SELECT GROUP_CONCAT(tw.word, ', ') FROM trigger_words tw WHERE tw.model_id = m.id) as triggers_list
            FROM models m
            JOIN libraries l ON m.library_id = l.id
            WHERE l.name = ?
        """
        params = [library_name]
        if not show_hidden:
            query += " AND m.is_hidden = 0"
        query += " ORDER BY m.name ASC"
        
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
            if offset is not None:
                query += " OFFSET ?"
                params.append(int(offset))
                
        query += ";"
        
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            tags_str = row_dict.get('tags_list')
            row_dict['tags'] = tags_str.split(',') if tags_str else []
            trig_str = row_dict.get('triggers_list')
            row_dict['trigger_words'] = [w.strip() for w in trig_str.split(', ')] if trig_str else []
            results.append(row_dict)
        return results

def get_model_by_id(model_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.library_id, m.name, m.file_path, m.file_hash, m.image_path, m.notes, m.description, m.is_favorite, m.base_architecture, m.embedding,
                   (SELECT GROUP_CONCAT(t.name, ',') FROM model_tags mt JOIN tags t ON mt.tag_id = t.id WHERE mt.model_id = m.id) as tags_list,
                   (SELECT GROUP_CONCAT(tw.word, ', ') FROM trigger_words tw WHERE tw.model_id = m.id) as triggers_list
            FROM models m
            WHERE m.id = ?;
        """, (model_id,))
        row = cursor.fetchone()
        if not row:
            return None
        row_dict = dict(row)
        tags_str = row_dict.get('tags_list')
        row_dict['tags'] = tags_str.split(',') if tags_str else []
        trig_str = row_dict.get('triggers_list')
        row_dict['trigger_words'] = [w.strip() for w in trig_str.split(', ')] if trig_str else []
        return row_dict

def register_model(library_id, name, file_path, file_hash, base_architecture=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if isinstance(library_id, str):
            lib_row = get_library_id(library_id)
            if lib_row:
                library_id = lib_row
        if not base_architecture:
            if file_path and file_path.lower().endswith('.safetensors'):
                try:
                    from utils.safetensors_parser import detect_lora_architecture, map_architecture_to_canonical
                    det = detect_lora_architecture(file_path)
                    mapped = map_architecture_to_canonical(det)
                    if mapped:
                        base_architecture = mapped
                except Exception:
                    base_architecture = None
            if not base_architecture:
                from utils.png_parser import detect_base_architecture
                from utils.safetensors_parser import map_architecture_to_canonical
                fallback = detect_base_architecture([name, file_path])
                base_architecture = map_architecture_to_canonical(fallback) or fallback
        cursor.execute("SELECT id FROM models WHERE file_path = ?;", (file_path,))
        existing_row = cursor.fetchone()
        is_new = (existing_row is None)

        cursor.execute("""
            INSERT INTO models (library_id, name, file_path, file_hash, base_architecture) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET 
                file_hash = excluded.file_hash,
                base_architecture = CASE 
                    WHEN models.base_architecture IS NOT NULL AND models.base_architecture != '' 
                    THEN models.base_architecture 
                    ELSE excluded.base_architecture 
                END;
        """, (library_id, name, file_path, file_hash, base_architecture))
        
        inserted_id = cursor.lastrowid if is_new else existing_row['id']

        # Only extract trigger words if this is a newly inserted card!
        if is_new and inserted_id and file_path and file_path.lower().endswith('.safetensors'):
            try:
                from utils.safetensors_parser import extract_metadata_tags_and_triggers
                extracted_triggers = extract_metadata_tags_and_triggers(file_path, max_tags=15)
                for w in extracted_triggers or []:
                    cursor.execute("INSERT OR IGNORE INTO trigger_words (model_id, word) VALUES (?, ?);", (inserted_id, w))
            except Exception:
                pass

        conn.commit()
        return inserted_id

def update_model_data(model_id, name, notes, base_architecture=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if base_architecture is not None:
            cursor.execute("UPDATE models SET name = ?, notes = ?, base_architecture = ? WHERE id = ?;", (name, notes, base_architecture, model_id))
        else:
            cursor.execute("UPDATE models SET name = ?, notes = ? WHERE id = ?;", (name, notes, model_id))
        conn.commit()

def update_model_base_architecture(model_id, base_architecture):
    """Directly updates base architecture for a model in SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET base_architecture = ? WHERE id = ?;", (base_architecture, model_id))
        conn.commit()

def update_model_image(model_id, image_path):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET image_path = ? WHERE id = ?;", (image_path, model_id))
        conn.commit()

# Trigger Words
def get_trigger_words(model_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT word FROM trigger_words WHERE model_id = ? ORDER BY word ASC;", (model_id,))
        return [row['word'] for row in cursor.fetchall()]

def add_trigger_word(model_id, word):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO trigger_words (model_id, word) VALUES (?, ?);", (model_id, word))
            conn.commit()
            return True
        except sqlite3.Error:
            return False

def delete_trigger_word(model_id, word):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trigger_words WHERE model_id = ? AND word = ?;", (model_id, word))
        conn.commit()

def set_trigger_words(model_id, words_list):
    """
    Atomically updates the entire trigger words list for a model in SQLite.
    Clears existing trigger words and inserts the new list.
    """
    if not model_id:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM trigger_words WHERE model_id = ?;", (model_id,))
            seen = set()
            for word in words_list or []:
                w = str(word).strip()
                if not w or w.lower() in seen:
                    continue
                seen.add(w.lower())
                cursor.execute("INSERT OR IGNORE INTO trigger_words (model_id, word) VALUES (?, ?);", (model_id, w))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting trigger words for model {model_id}: {e}")
            return False

def add_trigger_words_batch(model_id, words_list):
    """
    Inserts multiple trigger words for a model in a single transaction without deleting existing ones.
    """
    if not model_id or not words_list:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            seen = set()
            for word in words_list or []:
                w = str(word).strip()
                if not w or w.lower() in seen:
                    continue
                seen.add(w.lower())
                cursor.execute("INSERT OR IGNORE INTO trigger_words (model_id, word) VALUES (?, ?);", (model_id, w))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding trigger words batch for model {model_id}: {e}")
            return False

def register_models_batch(models_list):
    """Insert or update multiple models in a single fast database transaction."""
    if not models_list:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Check which models are genuinely new before inserting
            new_paths = []
            for item in models_list:
                fpath = item[2]
                cursor.execute("SELECT id FROM models WHERE file_path = ?;", (fpath,))
                if not cursor.fetchone():
                    new_paths.append(fpath)

            sample = models_list[0]
            if len(sample) == 5:
                cursor.executemany("""
                    INSERT INTO models (library_id, name, file_path, file_hash, base_architecture) 
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET 
                        file_hash = excluded.file_hash,
                        base_architecture = CASE 
                            WHEN models.base_architecture IS NOT NULL AND models.base_architecture != '' 
                            THEN models.base_architecture 
                            ELSE excluded.base_architecture 
                        END;
                """, models_list)
            else:
                cursor.executemany("""
                    INSERT INTO models (library_id, name, file_path, file_hash) 
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET file_hash = excluded.file_hash;
                """, models_list)

            # Auto-extract initial trigger words ONLY for newly created cards
            if new_paths:
                from utils.safetensors_parser import extract_metadata_tags_and_triggers
                for fpath in new_paths:
                    if fpath.lower().endswith('.safetensors') and os.path.exists(fpath):
                        cursor.execute("SELECT id FROM models WHERE file_path = ?;", (fpath,))
                        row = cursor.fetchone()
                        if row:
                            mid = row['id']
                            try:
                                trigs = extract_metadata_tags_and_triggers(fpath, max_tags=15)
                                for tr in trigs or []:
                                    cursor.execute("INSERT OR IGNORE INTO trigger_words (model_id, word) VALUES (?, ?);", (mid, tr))
                            except Exception:
                                pass

            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            print(f"Error registering models batch: {e}")

def get_model_count_in_library(library_name, show_hidden=False):
    """Retrieve the total count of models in a specific library."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT COUNT(*) as cnt
            FROM models m
            JOIN libraries l ON m.library_id = l.id
            WHERE l.name = ?
        """
        if not show_hidden:
            query += " AND m.is_hidden = 0"
        query += ";"
        cursor.execute(query, (library_name,))
        row = cursor.fetchone()
        return row['cnt'] if row else 0

def get_workflow_count_in_library(library_id, show_hidden=False):
    """Retrieve total count of workflows in a specific library efficiently."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) as cnt FROM workflows WHERE library_id = ?"
        if not show_hidden:
            query += " AND is_hidden = 0"
        query += ";"
        cursor.execute(query, (library_id,))
        row = cursor.fetchone()
        return row['cnt'] if row else 0

# --- FAVORITE AND TAG CRUD FUNCTIONS ---
def toggle_model_favorite(model_id, is_fav):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET is_favorite = ? WHERE id = ?;", (1 if is_fav else 0, model_id))
        conn.commit()

def get_favorite_models(show_hidden=False, limit=None, offset=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.id, m.library_id, m.name, m.file_path, m.file_hash, m.image_path, m.notes, m.description, m.is_favorite, m.is_hidden, m.base_architecture,
                   (SELECT GROUP_CONCAT(t.name, ',') FROM model_tags mt JOIN tags t ON mt.tag_id = t.id WHERE mt.model_id = m.id) as tags_list,
                   (SELECT GROUP_CONCAT(tw.word, ', ') FROM trigger_words tw WHERE tw.model_id = m.id) as triggers_list
            FROM models m
            WHERE m.is_favorite = 1
        """
        params = []
        if not show_hidden:
            query += " AND m.is_hidden = 0"
        query += " ORDER BY m.name ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(int(limit))
            if offset is not None:
                query += " OFFSET ?"
                params.append(int(offset))
        query += ";"
        
        cursor.execute(query, params)
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            tags_str = row_dict.get('tags_list')
            row_dict['tags'] = tags_str.split(',') if tags_str else []
            trig_str = row_dict.get('triggers_list')
            row_dict['trigger_words'] = [w.strip() for w in trig_str.split(', ')] if trig_str else []
            results.append(row_dict)
        return results

def get_favorite_model_count(show_hidden=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) as cnt FROM models WHERE is_favorite = 1"
        if not show_hidden:
            query += " AND is_hidden = 0"
        query += ";"
        cursor.execute(query)
        row = cursor.fetchone()
        return row['cnt'] if row else 0

def add_model_tag(model_id, tag_name):
    tag_name = tag_name.strip()
    if not tag_name:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Insert tag if not exists
            cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?);", (tag_name,))
            # Fetch tag id
            cursor.execute("SELECT id FROM tags WHERE name = ?;", (tag_name,))
            row = cursor.fetchone()
            if row:
                tag_id = row['id']
                cursor.execute("INSERT OR IGNORE INTO model_tags (model_id, tag_id) VALUES (?, ?);", (model_id, tag_id))
                conn.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Error adding tag {tag_name} for model {model_id}: {e}")
            return False

def delete_model_tag(model_id, tag_name):
    tag_name = tag_name.strip()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM tags WHERE name = ?;", (tag_name,))
            row = cursor.fetchone()
            if row:
                tag_id = row['id']
                cursor.execute("DELETE FROM model_tags WHERE model_id = ? AND tag_id = ?;", (model_id, tag_id))
                
                # Cleanup orphan tag
                cursor.execute("SELECT COUNT(*) as cnt FROM model_tags WHERE tag_id = ?;", (tag_id,))
                cnt_row = cursor.fetchone()
                if cnt_row and cnt_row['cnt'] == 0:
                    cursor.execute("DELETE FROM tags WHERE id = ?;", (tag_id,))
                
                conn.commit()
                return True
            return False
        except sqlite3.Error as e:
            print(f"Error deleting tag {tag_name} for model {model_id}: {e}")
            return False

def set_model_tags(model_id, tags_list):
    """
    Atomically updates the entire tag list for a model in SQLite.
    Removes existing model tags, assigns new ones, and cleans up orphan tags.
    """
    if not model_id:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Clear existing model_tags for this model
            cursor.execute("DELETE FROM model_tags WHERE model_id = ?;", (model_id,))
            
            # 2. Add each tag in tags_list
            seen = set()
            for tag in tags_list or []:
                tag_name = str(tag).strip()
                if not tag_name or tag_name.lower() in seen:
                    continue
                seen.add(tag_name.lower())
                
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?);", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE name = ?;", (tag_name,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("INSERT OR IGNORE INTO model_tags (model_id, tag_id) VALUES (?, ?);", (model_id, row['id']))
            
            # 3. Clean up orphan tags
            cursor.execute("""
                DELETE FROM tags WHERE id NOT IN (SELECT DISTINCT tag_id FROM model_tags);
            """)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error setting model tags for model {model_id}: {e}")
            return False

def add_model_tags_batch(model_id, tags_list):
    """
    Inserts multiple tags for a model in a single transaction without deleting existing tags.
    """
    if not model_id or not tags_list:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            for tag in tags_list:
                tag_name = str(tag).strip()
                if not tag_name:
                    continue
                cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?);", (tag_name,))
                cursor.execute("SELECT id FROM tags WHERE name = ?;", (tag_name,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("INSERT OR IGNORE INTO model_tags (model_id, tag_id) VALUES (?, ?);", (model_id, row['id']))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding model tags batch for model {model_id}: {e}")
            return False

def delete_model(model_id):
    """Deletes a model and all its associations from VeraNote database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM model_tags WHERE model_id = ?;", (model_id,))
            cursor.execute("DELETE FROM trigger_words WHERE model_id = ?;", (model_id,))
            cursor.execute("DELETE FROM note_models WHERE model_id = ?;", (model_id,))
            cursor.execute("DELETE FROM models WHERE id = ?;", (model_id,))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error deleting model {model_id}: {e}")
            return False

def delete_models(model_ids):
    """Batch deletes multiple models and their associations from VeraNote database in a single transaction."""
    if not model_ids:
        return True
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            placeholders = ",".join("?" for _ in model_ids)
            ids_tuple = tuple(model_ids)
            cursor.execute(f"DELETE FROM model_tags WHERE model_id IN ({placeholders});", ids_tuple)
            cursor.execute(f"DELETE FROM trigger_words WHERE model_id IN ({placeholders});", ids_tuple)
            cursor.execute(f"DELETE FROM note_models WHERE model_id IN ({placeholders});", ids_tuple)
            cursor.execute(f"DELETE FROM models WHERE id IN ({placeholders});", ids_tuple)
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error bulk deleting models {model_ids}: {e}")
            return False

# --- NOTE ADDITIONAL CRUD AND RELATION FUNCTIONS ---
def toggle_note_favorite(note_id, is_fav):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET is_favorite = ? WHERE id = ?;", (1 if is_fav else 0, note_id))
        conn.commit()

def get_note_count(show_hidden=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) as cnt FROM notes WHERE is_deleted = 0"
        if not show_hidden:
            query += " AND is_hidden = 0"
        query += ";"
        cursor.execute(query)
        row = cursor.fetchone()
        return row['cnt'] if row else 0

def get_deleted_note_count(show_hidden=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) as cnt FROM notes WHERE is_deleted = 1"
        if not show_hidden:
            query += " AND is_hidden = 0"
        query += ";"
        cursor.execute(query)
        row = cursor.fetchone()
        return row['cnt'] if row else 0

def associate_note_model(note_id, model_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT OR IGNORE INTO note_models (note_id, model_id) VALUES (?, ?);", (note_id, model_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error associating note {note_id} with model {model_id}: {e}")
            return False

def dissociate_note_model(note_id, model_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM note_models WHERE note_id = ? AND model_id = ?;", (note_id, model_id))
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error dissociating note {note_id} with model {model_id}: {e}")
            return False

def get_all_models_for_association():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM models ORDER BY name ASC;")
        return [dict(row) for row in cursor.fetchall()]

associate_model_with_note = associate_note_model
dissociate_model_from_note = dissociate_note_model

# --- BACKUP & RESTORE UTILITIES ---
def export_backup_zip(target_zip_path: str) -> bool:
    """Creates a compressed .zip backup containing veranote.db, saved_images/, and saved_workflows/."""
    try:
        # Checkpoint SQLite WAL journal into main db file before archiving
        with get_connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")

        with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Add database file
            if os.path.exists(DB_NAME):
                zf.write(DB_NAME, arcname="veranote.db")
            
            # 2. Add saved_images
            if os.path.exists(SAVED_IMAGES_DIR):
                for root, dirs, files in os.walk(SAVED_IMAGES_DIR):
                    for file in files:
                        fp = os.path.join(root, file)
                        arc = os.path.relpath(fp, db_dir)
                        zf.write(fp, arcname=arc)

            # 3. Add saved_workflows
            if os.path.exists(SAVED_WORKFLOWS_DIR):
                for root, dirs, files in os.walk(SAVED_WORKFLOWS_DIR):
                    for file in files:
                        fp = os.path.join(root, file)
                        arc = os.path.relpath(fp, db_dir)
                        zf.write(fp, arcname=arc)
        return True
    except Exception as e:
        print(f"Error creating backup ZIP {target_zip_path}: {e}")
        return False

def import_backup_zip(source_zip_path: str) -> bool:
    """Restores database and images from a backup .zip, preserving a safety copy of current db."""
    if not source_zip_path or not os.path.exists(source_zip_path):
        return False

    try:
        # Close any active connection
        close_db_connection()

        # Create a timestamped backup copy of current DB if exists
        if os.path.exists(DB_NAME):
            bak_path = DB_NAME + f".{int(time.time())}.bak"
            try:
                shutil.copy2(DB_NAME, bak_path)
            except Exception:
                pass

        with zipfile.ZipFile(source_zip_path, 'r') as zf:
            for member in zf.namelist():
                # Prevent path traversal vulnerabilities
                if member.startswith("/") or ".." in member:
                    continue
                zf.extract(member, db_dir)

        # Re-initialize DB tables/migrations
        initialize_db()
        return True
    except Exception as e:
        print(f"Error restoring backup ZIP {source_zip_path}: {e}")
        return False

# --- WORKFLOW CRUD FUNCTIONS ---
def get_workflow_libraries():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM libraries WHERE type = 'WORKFLOW' ORDER BY name ASC;")
        return [dict(row) for row in cursor.fetchall()]

def add_workflow_library(name):
    name = name.strip()
    if not name:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO libraries (name, type) VALUES (?, 'WORKFLOW');", (name,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def delete_workflow_library(library_id):
    """Deletes a workflow library, all its contained workflows, and their saved files."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, image_path, file_path FROM workflows WHERE library_id = ?;", (library_id,))
        rows = cursor.fetchall()
        
        project_images_dir = os.path.abspath(SAVED_IMAGES_DIR)
        project_wf_dir = os.path.abspath(SAVED_WORKFLOWS_DIR)
        
        for r in rows:
            img_path = r['image_path']
            if img_path:
                abs_img = os.path.abspath(img_path)
                if os.path.dirname(abs_img) == project_images_dir and os.path.exists(abs_img):
                    try:
                        os.remove(abs_img)
                    except Exception as e:
                        print(f"Error cleaning workflow image {abs_img}: {e}")
            wf_file = r['file_path']
            if wf_file:
                abs_wf = os.path.abspath(wf_file)
                if os.path.dirname(abs_wf) == project_wf_dir and os.path.exists(abs_wf):
                    try:
                        os.remove(abs_wf)
                    except Exception as e:
                        print(f"Error cleaning workflow file {abs_wf}: {e}")

        cursor.execute("DELETE FROM workflows WHERE library_id = ?;", (library_id,))
        cursor.execute("DELETE FROM libraries WHERE id = ? AND type = 'WORKFLOW';", (library_id,))
        conn.commit()
        return True

def add_workflow(library_id, name, file_path, description="", image_path="", notes=""):
    import time
    import random
    import json
    
    os.makedirs(SAVED_IMAGES_DIR, exist_ok=True)
    os.makedirs(SAVED_WORKFLOWS_DIR, exist_ok=True)
    
    timestamp = int(time.time())
    rand_suffix = random.randint(1000, 9999)
    safe_name = "".join([c if c.isalnum() else "_" for c in name])
    
    dest_json_path = ""
    dest_image_path = ""
    workflow_json_content = ""
    
    # 1. Extract JSON from file_path (PNG metadata or direct JSON file)
    if file_path.lower().endswith('.png'):
        from utils.png_parser import extract_comfyui_metadata_from_png
        meta = extract_comfyui_metadata_from_png(file_path)
        workflow_dict = meta.get('workflow')
        if workflow_dict:
            workflow_json_content = json.dumps(workflow_dict, indent=2)
            dest_json_path = os.path.join(SAVED_WORKFLOWS_DIR, f"{safe_name}_{timestamp}_{rand_suffix}.json")
            try:
                with open(dest_json_path, 'w', encoding='utf-8') as f:
                    f.write(workflow_json_content)
            except Exception as e:
                print(f"Error saving local workflow json copy: {e}")
            # If the user dropped a PNG, that PNG is also the preview image!
            image_path = file_path
        if not description and meta.get('formatted_summary'):
            description = meta['formatted_summary']
    elif file_path.lower().endswith('.json'):
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    workflow_json_content = f.read()
                dest_json_path = os.path.join(SAVED_WORKFLOWS_DIR, f"{safe_name}_{timestamp}_{rand_suffix}.json")
                with open(dest_json_path, 'w', encoding='utf-8') as f:
                    f.write(workflow_json_content)
            except Exception as e:
                print(f"Error copying local workflow json file: {e}")
                dest_json_path = file_path
        else:
            dest_json_path = file_path
    else:
        # Fallback
        dest_json_path = file_path

    # 2. Copy preview image to SAVED_IMAGES_DIR
    if image_path and os.path.exists(image_path):
        ext = os.path.splitext(image_path)[1].lower()
        if not ext:
            ext = ".png"
        dest_image_path = os.path.join(SAVED_IMAGES_DIR, f"wf_{safe_name}_{timestamp}_{rand_suffix}{ext}")
        try:
            shutil.copy2(image_path, dest_image_path)
        except Exception as e:
            print(f"Error copying local workflow preview image: {e}")
            dest_image_path = image_path
            
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO workflows (library_id, name, file_path, description, image_path, notes, title, workflow_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (library_id, name, dest_json_path, description, dest_image_path, notes, name, workflow_json_content))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding workflow {name}: {e}")
            return None

def get_workflows_in_library(library_name_or_id, show_hidden=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        hidden_cond = " AND is_hidden = 0" if not show_hidden else ""
        if isinstance(library_name_or_id, int):
            cursor.execute(f"""
                SELECT id, library_id, name, file_path, description, image_path, notes, is_hidden, created_at, updated_at, title, workflow_json, is_favorite
                FROM workflows
                WHERE library_id = ?{hidden_cond}
                ORDER BY name ASC;
            """, (library_name_or_id,))
        else:
            cursor.execute(f"""
                SELECT w.id, w.library_id, w.name, w.file_path, w.description, w.image_path, w.notes, w.is_hidden, w.created_at, w.updated_at, w.title, w.workflow_json, w.is_favorite
                FROM workflows w
                JOIN libraries l ON w.library_id = l.id
                WHERE l.name = ? AND l.type = 'WORKFLOW'{hidden_cond.replace('is_hidden', 'w.is_hidden')}
                ORDER BY w.name ASC;
            """, (library_name_or_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_workflow_by_id(workflow_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, library_id, name, file_path, description, image_path, notes, is_hidden, created_at, updated_at, title, workflow_json, is_favorite
            FROM workflows
            WHERE id = ?;
        """, (workflow_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_workflow_data(workflow_id, name, description, notes):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workflows
            SET name = ?, title = ?, description = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (name, name, description, notes, workflow_id))
        conn.commit()

def update_workflow_image(workflow_id, image_path):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workflows
            SET image_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (image_path, workflow_id))
        conn.commit()

def toggle_workflow_favorite(workflow_id, is_favorite):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE workflows
            SET is_favorite = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """, (1 if is_favorite else 0, workflow_id))
        conn.commit()

def delete_workflow(workflow_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM workflows WHERE id = ?;", (workflow_id,))
        conn.commit()

def set_note_hidden(note_id, is_hidden):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET is_hidden = ? WHERE id = ?;", (1 if is_hidden else 0, note_id))
        conn.commit()

def set_model_hidden(model_id, is_hidden):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET is_hidden = ? WHERE id = ?;", (1 if is_hidden else 0, model_id))
        conn.commit()

def set_workflow_hidden(workflow_id, is_hidden):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE workflows SET is_hidden = ? WHERE id = ?;", (1 if is_hidden else 0, workflow_id))
        conn.commit()

# Corkboard & Bulk Operations
def get_corkboard_notes(show_hidden=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM notes WHERE is_deleted = 0 AND is_pinned_corkboard = 1"
        if not show_hidden:
            query += " AND is_hidden = 0"
        query += " ORDER BY updated_at DESC;"
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

# Ensure DB is initialized on module import
initialize_db()

def toggle_corkboard_pin(note_id, is_pinned=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if is_pinned is None:
            cursor.execute("SELECT is_pinned_corkboard FROM notes WHERE id = ?;", (note_id,))
            row = cursor.fetchone()
            current = row['is_pinned_corkboard'] if row else 0
            new_val = 1 if current == 0 else 0
        else:
            new_val = 1 if is_pinned else 0
        cursor.execute("UPDATE notes SET is_pinned_corkboard = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (new_val, note_id))
        conn.commit()
        return new_val

def delete_notes_bulk(note_ids, is_trash=False):
    if not note_ids:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in note_ids)
        if is_trash:
            cursor.execute(f"DELETE FROM notes WHERE id IN ({placeholders});", note_ids)
        else:
            cursor.execute(f"UPDATE notes SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders});", note_ids)
        conn.commit()

def restore_notes_bulk(note_ids):
    if not note_ids:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in note_ids)
        cursor.execute(f"UPDATE notes SET is_deleted = 0, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders});", note_ids)
        conn.commit()

def get_storage_stats():
    """Calculate storage sizes for database and asset files."""
    db_size = 0
    if os.path.exists(DB_NAME):
        try:
            db_size = os.path.getsize(DB_NAME)
        except Exception:
            pass

    assets_size = 0
    if os.path.exists(db_dir):
        try:
            for root, dirs, files in os.walk(db_dir):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath) and filepath != DB_NAME:
                        assets_size += os.path.getsize(filepath)
        except Exception:
            pass

    workspace_images = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
    if os.path.exists(workspace_images):
        try:
            for root, dirs, files in os.walk(workspace_images):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        assets_size += os.path.getsize(filepath)
        except Exception:
            pass

    def format_size(size):
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    return format_size(db_size), format_size(assets_size), format_size(db_size + assets_size)


# ==========================================
# AGENDA REPOSITORY (Faz 1 - Daily Notes & Tasks)
# ==========================================

class AgendaRepository:
    """Repository for managing daily notes and scheduled agenda tasks."""

    @staticmethod
    def get_or_create_daily_note(date_str: str) -> dict:
        """Fetch daily note for the given date (YYYY-MM-DD), or create an empty one if it doesn't exist."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_notes WHERE date = ?;", (date_str,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            
            cursor.execute("""
                INSERT INTO daily_notes (date, content, summary, created_at, updated_at)
                VALUES (?, '', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
            """, (date_str,))
            conn.commit()
            
            cursor.execute("SELECT * FROM daily_notes WHERE date = ?;", (date_str,))
            return dict(cursor.fetchone())

    @staticmethod
    def save_daily_note(date_str: str, content: str, summary: str = None) -> bool:
        """Save or update daily note content and optional summary."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_notes (date, content, summary, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    content = excluded.content,
                    summary = COALESCE(excluded.summary, daily_notes.summary),
                    updated_at = CURRENT_TIMESTAMP;
            """, (date_str, content, summary))
            conn.commit()
            return True

    @staticmethod
    def get_tasks_for_date(date_str: str) -> list:
        """Retrieve tasks matching the given due date or daily note date."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks
                WHERE due_date = ? OR daily_note_date = ?
                ORDER BY is_completed ASC, priority DESC, id ASC;
            """, (date_str, date_str))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_month_task_indicators(year: int, month: int) -> dict:
        """
        Retrieve task indicators and daily note status for all days in a given year/month.
        Returns a dict mapping date string 'YYYY-MM-DD' to:
        {'has_note': bool, 'pending_tasks': int, 'completed_tasks': int}
        """
        prefix = f"{year:04d}-{month:02d}-%"
        indicators = {}

        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Check notes with non-empty content
            cursor.execute("""
                SELECT date FROM daily_notes
                WHERE date LIKE ? AND TRIM(content) != '';
            """, (prefix,))
            for row in cursor.fetchall():
                d = row['date']
                if d not in indicators:
                    indicators[d] = {'has_note': True, 'pending_tasks': 0, 'completed_tasks': 0}
                else:
                    indicators[d]['has_note'] = True

            # 2. Check tasks due or assigned to days in this month
            cursor.execute("""
                SELECT 
                    COALESCE(due_date, daily_note_date) AS task_date,
                    is_completed,
                    COUNT(*) AS count
                FROM tasks
                WHERE (due_date LIKE ? OR daily_note_date LIKE ?)
                GROUP BY task_date, is_completed;
            """, (prefix, prefix))
            for row in cursor.fetchall():
                d = row['task_date']
                if not d:
                    continue
                if d not in indicators:
                    indicators[d] = {'has_note': False, 'pending_tasks': 0, 'completed_tasks': 0}
                if row['is_completed'] == 1:
                    indicators[d]['completed_tasks'] += row['count']
                else:
                    indicators[d]['pending_tasks'] += row['count']

        return indicators

    @staticmethod
    def get_monthly_agenda_stats(year: int, month: int) -> dict:
        """
        Calculate monthly metrics for the Agenda view:
        - total tasks & completed tasks
        - completion rate (%)
        - active note days count & ratio
        - streak (consecutive active days up to today)
        - overall productivity score
        """
        import calendar
        import datetime
        _, num_days = calendar.monthrange(year, month)
        prefix = f"{year:04d}-{month:02d}-%"

        with get_connection() as conn:
            cursor = conn.cursor()
            # 1. Total tasks & completed tasks in month
            cursor.execute("""
                SELECT 
                    COUNT(*) AS total_count,
                    COALESCE(SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END), 0) AS completed_count
                FROM tasks
                WHERE (due_date LIKE ? OR daily_note_date LIKE ?);
            """, (prefix, prefix))
            task_row = cursor.fetchone()
            total_tasks = task_row['total_count'] if task_row else 0
            completed_tasks = task_row['completed_count'] if task_row else 0

            # 2. Distinct days with non-empty notes in month
            cursor.execute("""
                SELECT COUNT(DISTINCT date) AS note_days
                FROM daily_notes
                WHERE date LIKE ? AND TRIM(content) != '';
            """, (prefix,))
            note_row = cursor.fetchone()
            active_note_days = note_row['note_days'] if note_row else 0

            # 3. Calculate streak (consecutive active days backwards from today)
            today = datetime.date.today()
            cursor.execute("""
                SELECT DISTINCT date FROM (
                    SELECT date FROM daily_notes WHERE TRIM(content) != ''
                    UNION
                    SELECT COALESCE(due_date, daily_note_date) AS date FROM tasks WHERE is_completed = 1
                ) WHERE date IS NOT NULL;
            """)
            active_dates = {row['date'] for row in cursor.fetchall()}

            streak = 0
            check_date = today
            # If today has no activity yet, streak can count backwards from yesterday
            if check_date.isoformat() not in active_dates:
                check_date = check_date - datetime.timedelta(days=1)

            while check_date.isoformat() in active_dates:
                streak += 1
                check_date = check_date - datetime.timedelta(days=1)

            completion_rate = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0
            note_ratio = int((active_note_days / num_days) * 100) if num_days > 0 else 0
            
            if total_tasks > 0:
                productivity_score = int(completion_rate * 0.7 + note_ratio * 0.3)
            elif active_note_days > 0:
                productivity_score = note_ratio
            else:
                productivity_score = 0

            return {
                "year": year,
                "month": month,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_rate": completion_rate,
                "active_note_days": active_note_days,
                "days_in_month": num_days,
                "streak_days": streak,
                "productivity_score": min(100, productivity_score),
            }

    @staticmethod
    def get_upcoming_tasks(days_ahead: int = 3) -> list:
        """
        Fetch pending (uncompleted) tasks scheduled between today and today + days_ahead.
        Returns a list of dicts ordered by date ASC, priority DESC, id ASC.
        """
        import datetime
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=days_ahead)
        today_str = today.isoformat()
        end_str = end_date.isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks
                WHERE (due_date BETWEEN ? AND ? OR daily_note_date BETWEEN ? AND ?)
                  AND is_completed = 0
                ORDER BY COALESCE(due_date, daily_note_date) ASC, priority DESC, id ASC;
            """, (today_str, end_str, today_str, end_str))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_task(title: str, description: str = None, due_date: str = None,
                 priority: int = 1, daily_note_date: str = None, note_id: int = None) -> int:
        """Add a new task to the database."""
        with get_connection() as conn:
            cursor = conn.cursor()
            if daily_note_date:
                cursor.execute("""
                    INSERT OR IGNORE INTO daily_notes (date, content, created_at, updated_at)
                    VALUES (?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """, (daily_note_date,))
            cursor.execute("""
                INSERT INTO tasks (title, description, is_completed, due_date, priority, daily_note_date, note_id, created_at)
                VALUES (?, ?, 0, ?, ?, ?, ?, CURRENT_TIMESTAMP);
            """, (title, description, due_date, priority, daily_note_date, note_id))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def delete_task(task_id: int) -> bool:
        """Delete a task by ID."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def toggle_task_completed(task_id: int, is_completed: int = None) -> int:
        """Toggle or set the completion status of a task."""
        with get_connection() as conn:
            cursor = conn.cursor()
            if is_completed is None:
                cursor.execute("SELECT is_completed FROM tasks WHERE id = ?;", (task_id,))
                row = cursor.fetchone()
                current = row['is_completed'] if row else 0
                new_status = 1 if current == 0 else 0
            else:
                new_status = 1 if is_completed else 0

            if new_status == 1:
                cursor.execute("""
                    UPDATE tasks
                    SET is_completed = 1, completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                """, (task_id,))
            else:
                cursor.execute("""
                    UPDATE tasks
                    SET is_completed = 0, completed_at = NULL
                    WHERE id = ?;
                """, (task_id,))
            conn.commit()
            return new_status

    @staticmethod
    def clear_completed_tasks(date_str: str) -> int:
        """Permanently delete all completed tasks for a specific date."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM tasks
                WHERE (due_date = ? OR daily_note_date = ?) AND is_completed = 1;
            """, (date_str, date_str))
            conn.commit()
            return cursor.rowcount

    @staticmethod
    def get_active_routines() -> list:
        """Fetch all active recurring routine templates."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM recurring_routines
                WHERE is_active = 1
                ORDER BY priority DESC, id ASC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_all_routines() -> list:
        """Fetch all recurring routine templates."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM recurring_routines
                ORDER BY is_active DESC, priority DESC, id ASC;
            """)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def add_routine(title: str, frequency: str = 'daily', priority: int = 1) -> int:
        """Add a new recurring routine template."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recurring_routines (title, frequency, priority, is_active, created_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP);
            """, (title.strip(), frequency, priority))
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def delete_routine(routine_id: int) -> bool:
        """Delete a recurring routine template."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM recurring_routines WHERE id = ?;", (routine_id,))
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def toggle_routine(routine_id: int, is_active: int = None) -> int:
        """Toggle or set active status of a recurring routine."""
        with get_connection() as conn:
            cursor = conn.cursor()
            if is_active is None:
                cursor.execute("SELECT is_active FROM recurring_routines WHERE id = ?;", (routine_id,))
                row = cursor.fetchone()
                current = row['is_active'] if row else 1
                new_status = 0 if current == 1 else 1
            else:
                new_status = 1 if is_active else 0
            cursor.execute("UPDATE recurring_routines SET is_active = ? WHERE id = ?;", (new_status, routine_id))
            conn.commit()
            return new_status

    @staticmethod
    def seed_daily_tasks_from_routines(date_str: str) -> int:
        """
        Seeds active routines into the tasks table for date_str if not already present.
        - Avoids duplicates: checks if a task with identical title already exists for that date.
        - Respects frequency: routines with frequency='weekdays' are skipped on weekends (Saturday & Sunday).
        Returns the number of new tasks created.
        """
        import datetime
        try:
            dt = datetime.date.fromisoformat(date_str)
            is_weekend = dt.weekday() >= 5  # 5: Saturday, 6: Sunday
        except Exception:
            is_weekend = False

        added_count = 0
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM recurring_routines
                WHERE is_active = 1
                ORDER BY priority DESC, id ASC;
            """)
            routines = [dict(row) for row in cursor.fetchall()]

            for routine in routines:
                # If routine is weekdays-only and today is a weekend, skip
                if routine.get('frequency') == 'weekdays' and is_weekend:
                    continue

                # Check if a task with the same title already exists for this date
                cursor.execute("""
                    SELECT id FROM tasks
                    WHERE (due_date = ? OR daily_note_date = ?) AND title = ?
                    LIMIT 1;
                """, (date_str, date_str, routine['title']))
                if cursor.fetchone():
                    continue

                # Ensure daily_notes record exists for this date to satisfy foreign key constraint
                cursor.execute("""
                    INSERT OR IGNORE INTO daily_notes (date, content, created_at, updated_at)
                    VALUES (?, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
                """, (date_str,))

                # Insert routine as a task for this day
                cursor.execute("""
                    INSERT INTO tasks (title, description, is_completed, due_date, priority, daily_note_date, created_at)
                    VALUES (?, '', 0, ?, ?, ?, CURRENT_TIMESTAMP);
                """, (routine['title'], date_str, routine['priority'], date_str))
                added_count += 1

            if added_count > 0:
                conn.commit()

        return added_count

# Convenient module-level aliases
get_or_create_daily_note = AgendaRepository.get_or_create_daily_note
save_daily_note = AgendaRepository.save_daily_note
get_tasks_for_date = AgendaRepository.get_tasks_for_date
get_month_task_indicators = AgendaRepository.get_month_task_indicators
get_monthly_agenda_stats = AgendaRepository.get_monthly_agenda_stats
get_upcoming_tasks = AgendaRepository.get_upcoming_tasks
add_task = AgendaRepository.add_task
delete_task = AgendaRepository.delete_task
toggle_task_completed = AgendaRepository.toggle_task_completed
clear_completed_tasks = AgendaRepository.clear_completed_tasks
get_active_routines = AgendaRepository.get_active_routines
get_all_routines = AgendaRepository.get_all_routines
add_routine = AgendaRepository.add_routine
delete_routine = AgendaRepository.delete_routine
toggle_routine = AgendaRepository.toggle_routine
seed_daily_tasks_from_routines = AgendaRepository.seed_daily_tasks_from_routines

# --- SEMANTIC SEARCH & VECTOR EMBEDDING HELPERS ---
def update_model_embedding(model_id: int, embedding_bytes: bytes):
    """Save raw embedding float32 bytes for a model."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET embedding = ? WHERE id = ?;", (embedding_bytes, model_id))
        conn.commit()

def update_note_embedding(note_id: int, embedding_bytes: bytes):
    """Save raw embedding float32 bytes for a note."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notes SET embedding = ? WHERE id = ?;", (embedding_bytes, note_id))
        conn.commit()

def get_unembedded_models(limit=None):
    """Fetch models where embedding IS NULL along with tags and trigger words."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = """
            SELECT m.id, m.name, m.base_architecture, m.notes, m.description,
                   (SELECT GROUP_CONCAT(t.name, ',') FROM model_tags mt JOIN tags t ON mt.tag_id = t.id WHERE mt.model_id = m.id) as tags_list,
                   (SELECT GROUP_CONCAT(tw.word, ', ') FROM trigger_words tw WHERE tw.model_id = m.id) as triggers_list
            FROM models m
            WHERE m.embedding IS NULL
            ORDER BY m.id ASC
        """
        if limit:
            query += f" LIMIT {int(limit)}"
        query += ";"
        cursor.execute(query)
        results = []
        for row in cursor.fetchall():
            row_dict = dict(row)
            tags_str = row_dict.get('tags_list')
            row_dict['tags'] = tags_str.split(',') if tags_str else []
            trig_str = row_dict.get('triggers_list')
            row_dict['trigger_words'] = [w.strip() for w in trig_str.split(', ')] if trig_str else []
            results.append(row_dict)
        return results

def get_unembedded_notes(limit=None):
    """Fetch non-deleted notes where embedding IS NULL."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT id, title, content FROM notes WHERE embedding IS NULL AND is_deleted = 0 ORDER BY id ASC"
        if limit:
            query += f" LIMIT {int(limit)}"
        query += ";"
        cursor.execute(query)
        return [dict(r) for r in cursor.fetchall()]

def get_model_embedding_data(model_id: int):
    """Fetch metadata for a single model needed to compute its embedding."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.id, m.name, m.base_architecture, m.notes, m.description,
                   (SELECT GROUP_CONCAT(t.name, ',') FROM model_tags mt JOIN tags t ON mt.tag_id = t.id WHERE mt.model_id = m.id) as tags_list,
                   (SELECT GROUP_CONCAT(tw.word, ', ') FROM trigger_words tw WHERE tw.model_id = m.id) as triggers_list
            FROM models m
            WHERE m.id = ?;
        """, (model_id,))
        row = cursor.fetchone()
        if not row:
            return None
        row_dict = dict(row)
        tags_str = row_dict.get('tags_list')
        row_dict['tags'] = tags_str.split(',') if tags_str else []
        trig_str = row_dict.get('triggers_list')
        row_dict['trigger_words'] = [w.strip() for w in trig_str.split(', ')] if trig_str else []
        return row_dict

def get_note_embedding_data(note_id: int):
    """Fetch title and content for a single note."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, content FROM notes WHERE id = ?;", (note_id,))
        row = cursor.fetchone()
        return dict(row) if row else None




