"""Embedding similarity + SIMILARITY_MODE wiring. Uses a fake concept encoder: no model download needed."""
import numpy as np
import pytest

from app.ai import embeddings
from app.ai.embeddings import Embedder, embedding_similarity, set_embedder
from app.ai.overlap import _text_similarity, detect_overlaps, score_pair

CONCEPTS = [{"fee", "fees", "refund", "refunding", "returned", "money"}, {"salary", "wages", "paid", "payment"},
            {"lab", "labs", "unsafe", "equipment"}]
P1 = "Students report that the institution has not returned their fees."
P2 = "A complaint alleges an unresolved delay in refunding student fees."
UNRELATED = "Faculty wages have not been paid for three months."


def fake_encode(texts):
    out = np.zeros((len(texts), len(CONCEPTS)), dtype="float32")
    for i, t in enumerate(texts):
        words = {w.strip(".,").lower() for w in t.split()}
        for j, group in enumerate(CONCEPTS):
            out[i, j] = len(words & group)
    return out


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.delenv("SIMILARITY_MODE", raising=False)
    set_embedder(None)
    yield
    set_embedder(None)


def case(i, bureau, text):
    return {"id": i, "case_no": f"N{i}", "institution_id": 1, "bureau": bureau, "category": "fee refund",
            "status": "PENDING", "summary": text, "received_on": "2026-01-01"}


def test_default_mode_is_tfidf_and_never_loads_a_model(monkeypatch):
    called = []
    set_embedder(Embedder(lambda t: called.append(t) or fake_encode(t)))
    _text_similarity(P1, P2)
    assert called == []


def test_embedding_similarity_scores_paraphrase_high_and_unrelated_zero():
    emb = Embedder(fake_encode)
    assert embedding_similarity(P1, P2, emb) > 0.9
    assert embedding_similarity(P1, UNRELATED, emb) == 0.0


def test_hybrid_mode_recovers_paraphrase_that_tfidf_misses(monkeypatch):
    tfidf_only = _text_similarity(P1, P2)
    set_embedder(Embedder(fake_encode))
    monkeypatch.setenv("SIMILARITY_MODE", "hybrid")
    hybrid = _text_similarity(P1, P2)
    assert hybrid > tfidf_only and hybrid > 0.9
    assert _text_similarity(P1, UNRELATED) < 0.3


def test_hybrid_flags_paraphrased_pair_as_tier_b(monkeypatch):
    cases = [case(1, "RB", P1), case(2, "PGRC", P2)]
    set_embedder(Embedder(fake_encode))
    monkeypatch.setenv("SIMILARITY_MODE", "hybrid")
    result = score_pair(cases[0], cases[1])
    assert "HIGH_TEXT_SIMILARITY" in result["reasons"]
    assert any(f.tier == "B" for f in detect_overlaps(cases))


def test_falls_back_to_tfidf_when_no_model_available(monkeypatch):
    monkeypatch.setenv("SIMILARITY_MODE", "embedding")
    monkeypatch.setattr(embeddings, "get_embedder", lambda: None)
    monkeypatch.setattr("app.ai.overlap.embedding_similarity", lambda a, b, e=None: None)
    assert 0.0 <= _text_similarity(P1, P2) <= 1.0     # no exception, TF-IDF value


def test_embedder_encodes_each_unique_text_once():
    calls = []
    emb = Embedder(lambda t: calls.append(list(t)) or fake_encode(t))
    emb.encode([P1, P2, P1]); emb.encode([P1, P2])
    assert calls == [[P1, P2]]


def test_invalid_mode_falls_back_to_tfidf(monkeypatch):
    monkeypatch.setenv("SIMILARITY_MODE", "banana")
    assert embeddings.similarity_mode() == "tfidf"
