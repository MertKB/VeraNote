# VeraNote Core Architecture & Development Rules

## 1. Domain & Tech Stack
- **Target Application:** VeraNote (Desktop application for general note-taking + ComfyUI models, LoRAs, workflows, and metadata tracking).
- **Core Stack:** Python 3.10+, PySide6 (Qt for Python), SQLite (`sqlite3`), Pillow (`PIL`).
- **Core Objectives:** User-friendliness, modular customizability, high performance with low memory footprint.

## 2. Strict Performance Directives
- **Zero GUI Thread Blocking:**
  - File system operations, recursive directory scanning, hashing, and metadata parsing MUST run in background threads (`QThread` or `QRunnable` via `QThreadPool`).
  - Communicate between background workers and the UI strictly via Qt Signals & Slots.
- **Image & Memory Optimization:**
  - Never load full-resolution images into model cards or list views. Always generate and cache downscaled thumbnails (`QPixmap.scaled` with `Qt.SmoothTransformation`).
  - Implement lazy loading and chunked responsive rendering instead of instantiating hundreds of heavy synchronous `QWidget` instances inside scroll areas.
- **Database & Queries:**
  - Ensure indexed lookups for model names, hashes, tags, and trigger words in `database.py`.
  - Batch database writes using transactions (`connection.commit()` after batch operations, not per single row insertion).

## 3. ComfyUI & Metadata Standards
- **PNG Chunk Handling:**
  - Accurately read both `prompt` and `workflow` text chunks from ComfyUI-generated PNG files using Pillow's `image.text` or chunk readers.
  - Fail gracefully if chunks are missing, compressed, or malformed without crashing the UI.
- **Model Card Integrity:**
  - Maintain clear relationships between models (checkpoints, LoRAs, embeddings) and their trigger words, base architecture (SD1.5, SDXL, Flux, etc.), and sample generation prompts.

## 4. UX & Customization Guidelines
- **Modern & Responsive UI:**
  - Centralize styling in clean QSS / stylesheet files (`ui/styles.py`). Do not hardcode ad-hoc inline colors across disparate widgets.
  - Support drag-and-drop: Dropping a ComfyUI PNG onto the window must immediately parse and preview workflow/prompt data.
  - Provide immediate visual feedback for async background tasks (subtle progress bars, status bar updates, toast notifications).
  - Responsive screen resolution adaptations (Viewport Clamping, Proportional, Smart Free, Absolute) for smooth FHD/2K transitions.
- **Error Handling & Resilience:**
  - Wrap file read/write operations in safe try-except blocks.
  - Never alter, overwrite, or delete original ComfyUI model weights or output images without explicit user confirmation.
