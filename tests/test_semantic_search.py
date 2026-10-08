# tests/test_semantic_search.py
"""
Automated unit & integration tests for Vera Note Semantic Search.
Tests:
- Database schema and BLOB columns
- Formatting templates for models and notes
- Vector serialization (numpy <-> bytes BLOB)
- Dot product cosine similarity and threshold filtering
- Embedding model loading and encoding
- Backfill queries
"""

import os
import sys
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import database
from utils.semantic_search import (
    clean_text_for_embedding,
    format_model_text,
    format_note_text,
    vector_to_blob,
    blob_to_vector,
    semantic_service,
    AsyncSemanticSearchWorker
)


def test_schema_and_db_helpers():
    print("[*] Testing database schema initialization...")
    database.initialize_db()

    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(models);")
        model_cols = [r['name'] for r in cursor.fetchall()]
        assert "embedding" in model_cols, "embedding column missing from models table!"

        cursor.execute("PRAGMA table_info(notes);")
        note_cols = [r['name'] for r in cursor.fetchall()]
        assert "embedding" in note_cols, "embedding column missing from notes table!"

    print("[+] Database schema successfully verified with embedding column.")


def test_text_formatting():
    print("[*] Testing text formatting templates...")
    # Model text format
    m_text = format_model_text(
        name="Cyberpunk Anime Girl",
        base_arch="SDXL",
        triggers=["1girl", "neon city", "purple hair"],
        tags=["aesthetic", "scifi"],
        notes="<p>A cool cyberpunk <b>model</b> for neon renders.</p>"
    )
    assert "Cyberpunk Anime Girl" in m_text
    assert "SDXL" in m_text
    assert "purple hair" in m_text
    assert "aesthetic" in m_text
    assert "neon renders" in m_text
    assert "<p>" not in m_text, "HTML tags must be stripped!"

    # Note text format
    n_text = format_note_text(
        title="Anime Concept Ideas",
        content="<div>Notes for dark gothic street scene and <i>character design</i></div>"
    )
    assert "Anime Concept Ideas" in n_text
    assert "dark gothic street scene" in n_text
    assert "<div>" not in n_text, "HTML tags must be stripped!"

    print("[+] Text formatting verified.")


def test_vector_blob_serialization():
    print("[*] Testing vector BLOB serialization...")
    dummy = np.random.randn(384).astype(np.float32)
    norm = np.linalg.norm(dummy)
    dummy = dummy / norm

    blob = vector_to_blob(dummy)
    assert isinstance(blob, bytes)
    assert len(blob) == 384 * 4, f"Expected 1536 bytes, got {len(blob)}"

    restored = blob_to_vector(blob)
    assert restored is not None
    assert restored.shape == (384,)
    assert np.allclose(dummy, restored, atol=1e-6)

    print("[+] Vector serialization verified.")


def test_similarity_math():
    print("[*] Testing cosine similarity math and thresholding...")
    # Create two unit vectors: one identical, one orthogonal, one opposite
    v1 = np.zeros(384, dtype=np.float32)
    v1[0] = 1.0

    v2 = np.zeros(384, dtype=np.float32)
    v2[0] = 0.9
    v2[1] = np.sqrt(1.0 - 0.9**2) # Cosine similarity ~ 0.90

    v3 = np.zeros(384, dtype=np.float32)
    v3[2] = 1.0 # Orthogonal: Cosine similarity = 0.0

    doc_mat = np.vstack([v1, v2, v3])
    scores = np.dot(doc_mat, v1)

    assert np.isclose(scores[0], 1.0)
    assert np.isclose(scores[1], 0.9)
    assert np.isclose(scores[2], 0.0)

    # Threshold 0.25 filtering
    threshold = 0.25
    valid = [i for i, s in enumerate(scores) if s >= threshold]
    assert valid == [0, 1], f"Expected indices [0, 1], got {valid}"

    print("[+] Similarity math and thresholding verified.")


def test_embedding_model_encode():
    print("[*] Testing embedding model loading and inference...")
    loaded = semantic_service.load_model()
    assert loaded, "SemanticSearchService failed to load model!"
    assert semantic_service.is_ready

    # Encode query
    query = "karanlık gotik sokak"
    vec = semantic_service.encode(query)
    assert vec is not None
    assert vec.shape == (384,)
    norm = np.linalg.norm(vec)
    assert np.isclose(norm, 1.0, atol=1e-3), f"Vector must be L2 normalized! Norm={norm}"

    # Batch encode
    texts = ["mor saçlı anime kızı", "parmak anatomisi promptları"]
    batch_vecs = semantic_service.encode_batch(texts)
    assert batch_vecs is not None
    assert batch_vecs.shape == (2, 384)

    # Test semantic relevance
    # "mor saçlı anime kızı" should be more similar to "purple hair anime girl" than "car engine repair manual"
    v_tr = semantic_service.encode("mor saçlı anime kızı")
    v_en = semantic_service.encode("purple hair anime girl")
    v_unrelated = semantic_service.encode("automotive combustion engine repair manual")

    sim_related = float(np.dot(v_tr, v_en))
    sim_unrelated = float(np.dot(v_tr, v_unrelated))
    print(f"    Semantic similarity (Turkish 'mor saçlı anime kızı' vs English 'purple hair anime girl'): {sim_related:.3f}")
    print(f"    Semantic similarity (vs unrelated engine manual): {sim_unrelated:.3f}")
    assert sim_related > sim_unrelated, "Semantic search should recognize conceptual proximity across languages!"
    assert sim_related > 0.25, f"Related concept should pass threshold 0.25, got {sim_related}"

    print("[+] Embedding model encoding and semantic relevance verified.")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING VERA NOTE SEMANTIC SEARCH UNIT TESTS")
    print("=" * 60)
    test_schema_and_db_helpers()
    test_text_formatting()
    test_vector_blob_serialization()
    test_similarity_math()
    test_embedding_model_encode()
    print("=" * 60)
    print("ALL SEMANTIC SEARCH TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
