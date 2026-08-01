# Vera Note - AI Model & Workflow Manager
# Copyright (C) 2026 Vera Note Contributors
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# scanner.py
import os
from PySide6.QtCore import QThread, Signal
import database

class ModelScanner(QThread):
    progress_signal = Signal(str) # Filename currently being indexed
    finished_signal = Signal(int) # Number of models scanned

    def __init__(self, directory_path, library_name, parent=None):
        super().__init__(parent)
        self.directory_path = os.path.abspath(directory_path) if directory_path else ""
        self.library_name = library_name

    def run(self):
        if not self.directory_path or not os.path.exists(self.directory_path):
            self.finished_signal.emit(0)
            return

        library_id = database.get_library_id(self.library_name)
        if not library_id:
            self.finished_signal.emit(0)
            return

        scanned_count = 0
        batch = []
        
        # Walk through directory
        for root, dirs, files in os.walk(self.directory_path):
            for file in files:
                if self.isInterruptionRequested():
                    if batch:
                        database.register_models_batch(batch)
                    self.finished_signal.emit(scanned_count)
                    return
                
                # Scan safetensors and checkpoints
                if file.endswith(('.safetensors', '.ckpt')):
                    file_path = os.path.join(root, file)
                    self.progress_signal.emit(file)
                    
                    # Store empty/dummy hash since we are offline and need instant response
                    file_hash = ""
                    
                    # Register to database in batch (name defaults to filename without extension)
                    name = os.path.splitext(file)[0]
                    batch.append((library_id, name, file_path, file_hash))
                    scanned_count += 1
                    
                    # Insert in batches of 100 to reduce transaction and IO locking overhead
                    if len(batch) >= 100:
                        database.register_models_batch(batch)
                        batch = []

        # Write remaining models in batch
        if batch:
            database.register_models_batch(batch)

        self.finished_signal.emit(scanned_count)
