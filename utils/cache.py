# utils/cache.py
import os
import hashlib
from collections import OrderedDict
import threading
from PySide6.QtCore import QThreadPool, QSize, Qt
from PySide6.QtGui import QImage, QImageReader

THUMB_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".veranote_data", "thumbnails")
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)

# Dedicated bounded thread pool (max 2 concurrent decoders) to prevent parallel 2K/4K PNG heap spikes
THUMB_THREAD_POOL = QThreadPool()
THUMB_THREAD_POOL.setMaxThreadCount(2)


def load_or_create_thumbnail_qimage(image_path: str, target_w: int, target_h: int) -> QImage:
    """
    Loads a pre-scaled thumbnail from disk cache (~15-30KB) if available, avoiding
    decoding 2K/4K ComfyUI PNGs (95MB+) into RAM on every launch.
    """
    if not image_path or not os.path.exists(image_path):
        return QImage()
    try:
        st = os.stat(image_path)
        key_raw = f"{os.path.abspath(image_path)}|{int(st.st_mtime)}|{st.st_size}|{target_w}x{target_h}"
        digest = hashlib.md5(key_raw.encode("utf-8", errors="ignore")).hexdigest()
        cache_file = os.path.join(THUMB_CACHE_DIR, f"{digest}.png")
        if os.path.exists(cache_file):
            cached_img = QImage(cache_file)
            if not cached_img.isNull():
                return cached_img
    except Exception:
        cache_file = None

    cropped = None
    try:
        reader = QImageReader(image_path)
        reader.setAutoTransform(True)
        orig_size = reader.size()
        if orig_size.isValid() and orig_size.width() > 0 and orig_size.height() > 0:
            scale = max(target_w / orig_size.width(), target_h / orig_size.height())
            scaled_w = max(target_w, int(orig_size.width() * scale))
            scaled_h = max(target_h, int(orig_size.height() * scale))
            reader.setScaledSize(QSize(scaled_w, scaled_h))
            img = reader.read()
            if not img.isNull():
                cropped = img.copy(0, 0, target_w, target_h)
        if cropped is None:
            image = QImage(image_path)
            if not image.isNull():
                scaled = image.scaled(
                    target_w, target_h,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                cropped = scaled.copy(0, 0, target_w, target_h)
        if cropped is not None and not cropped.isNull() and cache_file:
            try:
                cropped.save(cache_file, "PNG")
            except Exception:
                pass
        return cropped if cropped is not None else QImage()
    except Exception:
        return QImage()

class QPixmapLRUCache:
    """Thread-safe Least-Recently-Used (LRU) Cache with item count and memory boundaries."""
    
    def __init__(self, max_size=350, max_bytes=180 * 1024 * 1024):
        """
        :param max_size: Maximum number of preview pixmaps to keep in RAM.
        :param max_bytes: Maximum estimated memory footprint in bytes (default 180MB).
        """
        self.max_size = max_size
        self.max_bytes = max_bytes
        self.cache = OrderedDict()
        self.lock = threading.RLock()
        self._approx_bytes = 0

    def _estimate_pixmap_bytes(self, pixmap):
        """Estimate the uncompressed in-memory pixel buffer size of a QPixmap."""
        if not pixmap or pixmap.isNull():
            return 0
        w = pixmap.width()
        h = pixmap.height()
        depth = pixmap.depth()
        bytes_per_pixel = max(1, depth // 8) if depth > 0 else 4
        return w * h * bytes_per_pixel

    def __getitem__(self, key):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            raise KeyError(key)

    def __setitem__(self, key, value):
        if not key or value is None:
            return
        with self.lock:
            if key in self.cache:
                old_val = self.cache[key]
                self._approx_bytes -= self._estimate_pixmap_bytes(old_val)
                self.cache.move_to_end(key)

            new_bytes = self._estimate_pixmap_bytes(value)
            self.cache[key] = value
            self._approx_bytes += new_bytes

            # Evict if count limit or memory limit exceeded
            while self.cache and (len(self.cache) > self.max_size or (self._approx_bytes > self.max_bytes and len(self.cache) > 1)):
                popped_key, popped_val = self.cache.popitem(last=False)
                self._approx_bytes -= self._estimate_pixmap_bytes(popped_val)
            
            if self._approx_bytes < 0:
                self._approx_bytes = 0

    def __delitem__(self, key):
        with self.lock:
            if key in self.cache:
                val = self.cache.pop(key)
                self._approx_bytes -= self._estimate_pixmap_bytes(val)
                if self._approx_bytes < 0:
                    self._approx_bytes = 0
            else:
                raise KeyError(key)

    def __contains__(self, key):
        with self.lock:
            return key in self.cache

    def __len__(self):
        with self.lock:
            return len(self.cache)

    def get(self, key, default=None):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return default

    def pop(self, key, default=None):
        with self.lock:
            if key in self.cache:
                val = self.cache.pop(key)
                self._approx_bytes -= self._estimate_pixmap_bytes(val)
                if self._approx_bytes < 0:
                    self._approx_bytes = 0
                return val
            return default

    def clear(self):
        with self.lock:
            self.cache.clear()
            self._approx_bytes = 0

    def current_memory_usage(self):
        """Return current approximate memory usage in bytes."""
        with self.lock:
            return self._approx_bytes

# Global shared LRU thumbnail cache with max 120 entries and ~24MB RAM limit
THUMBNAIL_CACHE = QPixmapLRUCache(max_size=120, max_bytes=24 * 1024 * 1024)

def resolve_image_path(path: str) -> str:
    """Helper to resolve relative image paths against SAVED_IMAGES_DIR if needed."""
    import database
    return database.resolve_image_path(path)
