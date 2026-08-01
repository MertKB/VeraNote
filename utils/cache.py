# utils/cache.py
from collections import OrderedDict

class QPixmapLRUCache:
    """Least-Recently-Used (LRU) Cache wrapper with maximum capacity to prevent RAM bloat."""
    def __init__(self, max_size=150):
        self.max_size = max_size
        self.cache = OrderedDict()

    def __getitem__(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

    def __contains__(self, key):
        return key in self.cache

    def get(self, key, default=None):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return default

    def clear(self):
        self.cache.clear()

# Global shared LRU thumbnail cache with max 150 entries
THUMBNAIL_CACHE = QPixmapLRUCache(max_size=150)
