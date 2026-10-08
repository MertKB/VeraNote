# Vera Note - AI Model & Workflow Manager
# Copyright (C) 2026 Vera Note Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Local Semantic Search (Vector Search) Service for Vera Note.
Uses sentence-transformers (all-MiniLM-L6-v2) to generate 384-dimensional
float32 embeddings, stored in SQLite as raw BLOBs, and calculates fast cosine
similarity via NumPy dot product in background worker threads.
"""

import re
import time
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from PySide6.QtCore import QObject, Signal, QThread, QRunnable, QThreadPool

def ensure_ml_packages_accessible():
    """Ensure local python site-packages are accessible when running in frozen bundle."""
    import sys
    import os
    if getattr(sys, 'frozen', False):
        candidate_paths = []
        try:
            import site
            candidate_paths.extend(site.getsitepackages())
        except Exception:
            pass
        try:
            import site
            u = site.getusersitepackages()
            if u:
                candidate_paths.append(u)
        except Exception:
            pass
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            for py_ver in ("Python310", "Python311", "Python312"):
                candidate_paths.append(os.path.join(local_app, "Programs", "Python", py_ver, "lib", "site-packages"))

        for p in candidate_paths:
            if p and os.path.exists(p) and p not in sys.path:
                sys.path.append(p)

    try:
        import torch
        if not hasattr(torch, "accelerator"):
            torch.accelerator = type('AcceleratorStub', (), {
                'current_accelerator': staticmethod(lambda: None)
            })()
    except Exception:
        pass

ensure_ml_packages_accessible()

import database


def clean_text_for_embedding(text: str) -> str:
    """Strip HTML tags, URLs, and collapses extra whitespace."""
    if not text:
        return ""
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Strip HTML entities
    clean = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean)
    # Strip excessive punctuation repetitions and whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def format_model_text(name: str, base_arch: str = "", triggers: Optional[List[str]] = None,
                      tags: Optional[List[str]] = None, notes: str = "", description: str = "") -> str:
    """
    Format model metadata into a descriptive semantic string for encoding.
    Combines: model name, base architecture, trigger words, user tags, and notes/description.
    """
    parts = []
    if name:
        parts.append(f"Model: {name.strip()}")
    if base_arch:
        parts.append(f"Architecture: {base_arch.strip()}")
    if triggers:
        valid_trigs = [str(w).strip() for w in triggers if str(w).strip()]
        if valid_trigs:
            parts.append(f"Triggers: {', '.join(valid_trigs)}")
    if tags:
        valid_tags = [str(t).strip() for t in tags if str(t).strip()]
        if valid_tags:
            parts.append(f"Tags: {', '.join(valid_tags)}")
    desc = clean_text_for_embedding(notes or description or "")
    if desc:
        parts.append(f"Description: {desc}")
    return ". ".join(parts)


def format_note_text(title: str, content: str = "") -> str:
    """
    Format note metadata into a plain text string for encoding.
    Directly combines title and clean content text.
    """
    clean_title = clean_text_for_embedding(title or "")
    clean_content = clean_text_for_embedding(content or "")
    if clean_title and clean_content:
        return f"{clean_title}. {clean_content}"
    return clean_title or clean_content or ""


def vector_to_blob(vec: np.ndarray) -> bytes:
    """Serialize a 1D float32 numpy vector to raw bytes for SQLite BLOB storage."""
    return vec.astype(np.float32).tobytes()


def blob_to_vector(blob: bytes) -> Optional[np.ndarray]:
    """Deserialize SQLite BLOB back to a 1D float32 numpy vector."""
    if not blob:
        return None
    try:
        arr = np.frombuffer(blob, dtype=np.float32)
        if arr.size == 384:
            return arr
    except Exception:
        pass
    return None


class SemanticSearchService:
    """
    Singleton service managing the embedding model in memory.
    Ensures the model is loaded once and shared across background tasks.
    """
    _instance: Optional['SemanticSearchService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._is_loading = False
            cls._instance._backend = None
        return cls._instance

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def load_model(self) -> bool:
        """
        Load the sentence transformer model into memory.
        Must be called from a background thread to prevent UI freezing.
        """
        if self._model is not None:
            return True

        self._is_loading = True
        try:
            # 1. Primary backend: sentence-transformers
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._backend = "sentence_transformers"
            self._is_loading = False
            return True
        except Exception as e:
            # 2. Fallback backend: fastembed ONNX
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2")
                self._backend = "fastembed"
                self._is_loading = False
                return True
            except Exception as e2:
                self._is_loading = False
                print(f"Failed to load embedding model: ST error={e}, FastEmbed error={e2}")
                return False

    def encode(self, text: str) -> Optional[np.ndarray]:
        """Encode a single text into a normalized 384-d float32 vector."""
        if not self._model or not text.strip():
            return None

        try:
            if self._backend == "sentence_transformers":
                vec = self._model.encode(text, normalize_embeddings=True)
                return np.asarray(vec, dtype=np.float32)
            elif self._backend == "fastembed":
                embs = list(self._model.embed([text]))
                if embs:
                    vec = np.asarray(embs[0], dtype=np.float32)
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    return vec
        except Exception as e:
            print(f"Error encoding text: {e}")
        return None

    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """Encode a list of texts into normalized 384-d float32 vectors."""
        if not self._model or not texts:
            return None

        clean_texts = [t.strip() if t and t.strip() else "empty" for t in texts]
        try:
            if self._backend == "sentence_transformers":
                vecs = self._model.encode(clean_texts, normalize_embeddings=True, batch_size=32)
                return np.asarray(vecs, dtype=np.float32)
            elif self._backend == "fastembed":
                embs = list(self._model.embed(clean_texts, batch_size=32))
                mat = np.asarray(embs, dtype=np.float32)
                norms = np.linalg.norm(mat, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                return mat / norms
        except Exception as e:
            print(f"Error batch encoding texts: {e}")
        return None


# Global singleton instance
semantic_service = SemanticSearchService()


class ModelWarmupWorker(QThread):
    """Background worker to warm up / load the embedding model on startup."""
    loaded_signal = Signal(bool)

    def run(self):
        success = semantic_service.load_model()
        self.loaded_signal.emit(success)


class EmbeddingBackfillWorker(QThread):
    """
    Background worker that detects models and notes where embedding IS NULL
    and generates vectors in chunks without interrupting user flow.
    """
    progress_signal = Signal(int, int) # completed, total
    finished_signal = Signal(int)       # total completed

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        # Ensure model is ready
        if not semantic_service.is_ready:
            semantic_service.load_model()

        if not semantic_service.is_ready:
            self.finished_signal.emit(0)
            return

        total_processed = 0

        # 1. Backfill Models
        unembedded_models = database.get_unembedded_models()
        if unembedded_models:
            batch_size = 20
            for i in range(0, len(unembedded_models), batch_size):
                if self.isInterruptionRequested():
                    self.finished_signal.emit(total_processed)
                    return

                chunk = unembedded_models[i:i + batch_size]
                texts = [
                    format_model_text(
                        m.get('name', ''),
                        m.get('base_architecture', ''),
                        m.get('trigger_words', []),
                        m.get('tags', []),
                        m.get('notes', ''),
                        m.get('description', '')
                    )
                    for m in chunk
                ]
                vectors = semantic_service.encode_batch(texts)
                if vectors is not None:
                    for model_dict, vec in zip(chunk, vectors):
                        database.update_model_embedding(model_dict['id'], vector_to_blob(vec))
                        total_processed += 1
                self.progress_signal.emit(total_processed, len(unembedded_models))

        # 2. Backfill Notes
        unembedded_notes = database.get_unembedded_notes()
        if unembedded_notes:
            batch_size = 20
            for i in range(0, len(unembedded_notes), batch_size):
                if self.isInterruptionRequested():
                    self.finished_signal.emit(total_processed)
                    return

                chunk = unembedded_notes[i:i + batch_size]
                texts = [
                    format_note_text(n.get('title', ''), n.get('content', ''))
                    for n in chunk
                ]
                vectors = semantic_service.encode_batch(texts)
                if vectors is not None:
                    for note_dict, vec in zip(chunk, vectors):
                        database.update_note_embedding(note_dict['id'], vector_to_blob(vec))
                        total_processed += 1
                self.progress_signal.emit(total_processed, len(unembedded_models) + len(unembedded_notes))

        self.finished_signal.emit(total_processed)


class SingleItemEmbeddingWorker(QRunnable):
    """
    Asynchronous QRunnable for re-generating the embedding of a single note or model
    upon save or metadata update without blocking the UI thread.
    """
    def __init__(self, item_type: str, item_id: int):
        super().__init__()
        self.item_type = item_type # 'model' or 'note'
        self.item_id = item_id

    def run(self):
        if not semantic_service.is_ready:
            semantic_service.load_model()
        if not semantic_service.is_ready:
            return

        if self.item_type == 'model':
            data = database.get_model_embedding_data(self.item_id)
            if data:
                text = format_model_text(
                    data.get('name', ''),
                    data.get('base_architecture', ''),
                    data.get('trigger_words', []),
                    data.get('tags', []),
                    data.get('notes', ''),
                    data.get('description', '')
                )
                vec = semantic_service.encode(text)
                if vec is not None:
                    database.update_model_embedding(self.item_id, vector_to_blob(vec))

        elif self.item_type == 'note':
            data = database.get_note_embedding_data(self.item_id)
            if data:
                text = format_note_text(data.get('title', ''), data.get('content', ''))
                vec = semantic_service.encode(text)
                if vec is not None:
                    database.update_note_embedding(self.item_id, vector_to_blob(vec))


def enqueue_single_embedding_update(item_type: str, item_id: int):
    """Queue a single item embedding update in the global thread pool."""
    worker = SingleItemEmbeddingWorker(item_type, item_id)
    QThreadPool.globalInstance().start(worker)


class AsyncSemanticSearchWorker(QThread):
    """
    Background worker that computes cosine similarity between a user query vector
    and candidate items' embeddings.
    Emits results_ready_signal with list of (item_id, score) sorted descending by score.
    """
    results_ready_signal = Signal(str, list) # query, list of (item_id, score)

    def __init__(self, query: str, candidate_items: List[Dict[str, Any]], threshold: float = 0.25, parent=None):
        super().__init__(parent)
        self.query = query.strip()
        self.candidate_items = candidate_items
        self.threshold = threshold

    def run(self):
        if not self.query or not self.candidate_items:
            self.results_ready_signal.emit(self.query, [])
            return

        # Ensure model is ready
        if not semantic_service.is_ready:
            semantic_service.load_model()

        if not semantic_service.is_ready or self.isInterruptionRequested():
            self.results_ready_signal.emit(self.query, [])
            return

        # 1. Encode query
        query_vec = semantic_service.encode(self.query)
        if query_vec is None or self.isInterruptionRequested():
            self.results_ready_signal.emit(self.query, [])
            return

        # 2. Extract item vectors
        item_ids = []
        vectors = []
        for item in self.candidate_items:
            blob = item.get('embedding')
            if blob:
                vec = blob_to_vector(blob)
                if vec is not None:
                    item_ids.append(item['id'])
                    vectors.append(vec)

        if not vectors or self.isInterruptionRequested():
            self.results_ready_signal.emit(self.query, [])
            return

        # 3. Calculate dot product cosine similarity
        doc_matrix = np.vstack(vectors) # (N, 384)
        scores = np.dot(doc_matrix, query_vec) # (N,)

        # 4. Filter by threshold and sort
        scored_results = []
        for item_id, score in zip(item_ids, scores):
            if score >= self.threshold:
                scored_results.append((item_id, float(score)))

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x[1], reverse=True)

        if not self.isInterruptionRequested():
            self.results_ready_signal.emit(self.query, scored_results)
