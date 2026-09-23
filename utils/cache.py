# utils/cache.py
from collections import OrderedDict
import threading

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

# Global shared LRU thumbnail cache with max 350 entries and ~180MB RAM limit
THUMBNAIL_CACHE = QPixmapLRUCache(max_size=350, max_bytes=180 * 1024 * 1024)

def resolve_image_path(path: str) -> str:
    """Helper to resolve relative image paths against SAVED_IMAGES_DIR if needed."""
    if not path:
        return ""
    import os
    if os.path.isabs(path) and os.path.exists(path):
        return path
    import database
    rel_in_saved = os.path.join(database.SAVED_IMAGES_DIR, os.path.basename(path))
    if os.path.exists(rel_in_saved):
        return rel_in_saved
    return path
