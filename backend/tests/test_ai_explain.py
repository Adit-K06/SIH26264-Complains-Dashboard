"""RAG retrieval + LLM/template explanation. Uses fake LLM callables: no network, no API key."""
import pytest

from app.ai.embeddings import set_embedder
from app.ai.explain import (build_explain_prompt, explain_overlap, redact, retrieve_similar, summarize_complaint,
                            template_explanation)

A = {"id": 1, "bureau": "RB", "category": "fee refund", "status": "PENDING", "received_on": "2026-01-01",
     "summary": "Students say fees were not returned. Call 9876543210 or mail x@y.com", "complainant_ref": "SECRET-REF"}
B = {"id": 2, "bureau": "PGRC", "category": "fee refund", "status": "PENDING", "received_on": "2026-01-10",
     "summary": "Delay in refunding student fees."}
SCORED = {"score": 0.62, "reasons": ["SAME_CATEGORY", "WITHIN_30_DAYS", "DIFFERENT_BUREAU"]}


@pytest.fixture(autouse=True)
def no_llm_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SIMILARITY_MODE", raising=False)
    set_embedder(None)


def test_redact_removes_phone_and_email():
    out = redact("call +91 98765 43210 or a.b@college.edu now")
    assert "98765" not in out and "@" not in out and "[phone]" in out and "[email]" in out


def test_prompt_never_contains_complainant_ref_or_contact_details():
    prompt = build_explain_prompt(A, B, SCORED, [])
    assert "SECRET-REF" not in prompt and "9876543210" not in prompt and "x@y.com" not in prompt
    assert "untrusted" in prompt


def test_template_used_when_no_llm_available():
    result = explain_overlap(A, B, SCORED)
    assert result["method"] == "TEMPLATE" and result["advisory"] is True
    assert "same category" in result["explanation"] and "not proof" in result["explanation"]


def test_llm_output_is_used_and_labelled():
    result = explain_overlap(A, B, SCORED, llm=lambda prompt: "Both mention unreturned fees.")
    assert result["method"] == "LLM" and result["explanation"] == "Both mention unreturned fees."
    assert result["sources"] == [1, 2]


def test_llm_failure_falls_back_to_template():
    def boom(prompt): raise RuntimeError("rate limited")
    assert explain_overlap(A, B, SCORED, llm=boom)["method"] == "TEMPLATE"


def test_empty_llm_reply_falls_back_to_template():
    assert explain_overlap(A, B, SCORED, llm=lambda p: "   ")["method"] == "TEMPLATE"


def test_retrieve_similar_ranks_relevant_case_first_and_excludes_ids():
    corpus = [{"id": 1, "summary": "fees not returned to students"},
              {"id": 3, "summary": "refund of student fees delayed by months"},
              {"id": 4, "summary": "laboratory equipment is unsafe"}]
    hits = retrieve_similar("student fees refund delay", corpus, k=2, exclude_ids={1})
    assert [h["id"] for h in hits][0] == 3 and 1 not in [h["id"] for h in hits]
    assert all(0 <= h["retrieval_score"] <= 1 for h in hits)


def test_retrieve_similar_handles_empty_inputs():
    assert retrieve_similar("", [{"id": 1, "summary": "x"}]) == []
    assert retrieve_similar("fees", []) == []


def test_precedents_are_added_to_sources_and_prompt():
    prec = [{"id": 9, "bureau": "FINANCE", "summary": "earlier fee refund complaint"}]
    seen = {}
    result = explain_overlap(A, B, SCORED, prec, llm=lambda p: seen.setdefault("p", p) and "ok")
    assert 9 in result["sources"] and "earlier fee refund complaint" in seen["p"]


def test_summarize_extractive_fallback_and_llm_path():
    text = "First sentence. Second sentence. Third sentence."
    assert summarize_complaint(text)["summary"] == "First sentence. Second sentence." and summarize_complaint(text)["method"] == "EXTRACTIVE"
    assert summarize_complaint(text, llm=lambda p: "Short.")["method"] == "LLM"
    assert summarize_complaint("")["summary"] == ""


def test_template_with_no_reasons():
    assert "manual review" in template_explanation({"score": 0.41, "reasons": []})
