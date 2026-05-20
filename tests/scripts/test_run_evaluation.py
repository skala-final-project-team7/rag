"""scripts/run_evaluation.py — ROUGE-L / BERTScore helper 회귀 (feature17b).

라이브러리 의존성 (rouge-score / bert-score) 은 monkeypatch 로 sentinel 응답으로
대체해 evaluation extras 미설치 환경에서도 회귀 가능. helper 함수의 평균 산출
로직과 옵션 미설치 시 ImportError 분기를 검증한다.
"""

from __future__ import annotations

import sys
import types

import pytest


def test_compute_rouge_l_f1_avg_with_fake_scorer(monkeypatch: pytest.MonkeyPatch) -> None:
    """rouge_scorer.RougeScorer mock 으로 평균 산출 회귀."""

    class _FakeScore:
        def __init__(self, fmeasure: float) -> None:
            self.fmeasure = fmeasure

    class _FakeScorer:
        def __init__(self, types: list[str], use_stemmer: bool) -> None:
            self.types = types
            self.use_stemmer = use_stemmer

        def score(self, ref: str, pred: str) -> dict:
            # ref / pred 의 길이 차이로 F1 을 단순 매핑 (회귀 검증용 deterministic).
            common = min(len(ref), len(pred))
            return {"rougeL": _FakeScore(common / max(len(ref), len(pred), 1))}

    rouge_module = types.ModuleType("rouge_score")
    rouge_scorer_module = types.ModuleType("rouge_score.rouge_scorer")
    rouge_scorer_module.RougeScorer = _FakeScorer  # type: ignore[attr-defined]
    rouge_module.rouge_scorer = rouge_scorer_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rouge_score", rouge_module)
    monkeypatch.setitem(sys.modules, "rouge_score.rouge_scorer", rouge_scorer_module)

    from scripts.run_evaluation import _compute_rouge_l_f1_avg

    avg = _compute_rouge_l_f1_avg(
        predictions=["abc", "abcdef"],
        references=["abcd", "abcdef"],
    )
    # (3/4 + 6/6) / 2 = (0.75 + 1.0) / 2 = 0.875
    assert avg == pytest.approx(0.875)


def test_compute_rouge_l_f1_avg_raises_without_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rouge-score 미설치 시 ImportError + 안내 메시지."""
    # rouge_score 모듈을 sys.modules 에서 제거 → import 실패 유도.
    monkeypatch.setitem(sys.modules, "rouge_score", None)  # type: ignore[arg-type]
    from scripts.run_evaluation import _compute_rouge_l_f1_avg

    with pytest.raises(ImportError, match="evaluation"):
        _compute_rouge_l_f1_avg(["pred"], ["ref"])


def test_compute_bert_score_f1_avg_with_fake_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bert_score.score mock 으로 평균 산출 회귀."""

    def _fake_score(preds: list[str], refs: list[str], lang: str, verbose: bool) -> tuple:
        # 단순 deterministic F1 — 길이 매칭 비율.
        assert lang == "ko"
        scores = [
            min(len(p), len(r)) / max(len(p), len(r), 1) for p, r in zip(preds, refs, strict=True)
        ]
        # bert_score 는 (P, R, F1) tuple 반환. F1 만 사용.
        return scores, scores, _FakeTensor(scores)

    class _FakeTensor:
        def __init__(self, values: list[float]) -> None:
            self._values = values

        def tolist(self) -> list[float]:
            return self._values

    bert_module = types.ModuleType("bert_score")
    bert_module.score = _fake_score  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "bert_score", bert_module)

    from scripts.run_evaluation import _compute_bert_score_f1_avg

    avg = _compute_bert_score_f1_avg(
        predictions=["abc", "abcdef"],
        references=["abcd", "abcdef"],
    )
    assert avg == pytest.approx(0.875)


def test_compute_bert_score_f1_avg_raises_without_library(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """bert-score 미설치 시 ImportError + 안내 메시지."""
    monkeypatch.setitem(sys.modules, "bert_score", None)  # type: ignore[arg-type]
    from scripts.run_evaluation import _compute_bert_score_f1_avg

    with pytest.raises(ImportError, match="evaluation"):
        _compute_bert_score_f1_avg(["pred"], ["ref"])


# ---------------------------------------------------------------------------
# feature17b 정밀 매칭 회귀 (2026-05-20) — _load_page_id_to_webui_link / _precision_match
# ---------------------------------------------------------------------------


def test_load_page_id_to_webui_link_reads_confluence_and_datadog(tmp_path) -> None:
    """samples 의 두 JSON 파일에서 page_id → webui_link 매핑이 합쳐져 로드된다."""
    import json

    from scripts.run_evaluation import _load_page_id_to_webui_link

    samples_dir = tmp_path / "samples"
    samples_dir.mkdir()
    (samples_dir / "confluence_sample_data.json").write_text(
        json.dumps(
            {
                "single_page_responses": [
                    {"id": "100001", "_links": {"webui": "/display/CLOUD/A"}},
                    {"id": "100002", "_links": {"webui": "/display/CLOUD/B"}},
                ]
            }
        )
    )
    (samples_dir / "datadog_docs.json").write_text(
        json.dumps(
            {
                "single_page_responses": [
                    {"id": "dd001", "_links": {"webui": "https://docs/x"}},
                ]
            }
        )
    )

    mapping = _load_page_id_to_webui_link(samples_dir=samples_dir)
    assert mapping == {
        "100001": "/display/CLOUD/A",
        "100002": "/display/CLOUD/B",
        "dd001": "https://docs/x",
    }


def test_load_page_id_to_webui_link_returns_empty_when_samples_missing(tmp_path) -> None:
    """samples 디렉토리가 없거나 파일이 없으면 빈 dict 반환 (호출 측이 fallback)."""
    from scripts.run_evaluation import _load_page_id_to_webui_link

    mapping = _load_page_id_to_webui_link(samples_dir=tmp_path / "no_such")
    assert mapping == {}


def _fake_source(confluence_url: str):
    """Source 의 confluence_url 만 채운 가벼운 sentinel."""
    return types.SimpleNamespace(confluence_url=confluence_url)


def test_precision_match_strict_hit_via_webui_link() -> None:
    """expected_page_ids 의 webui_link 중 하나가 sources confluence_url 에 있으면 hit."""
    from scripts.run_evaluation import _precision_match

    mapping = {"100001": "/display/CLOUD/A", "100002": "/display/CLOUD/B"}
    sources = [_fake_source("/display/CLOUD/B"), _fake_source("/display/CLOUD/Z")]

    assert _precision_match(sources, {"100001", "100002"}, mapping) is True


def test_precision_match_strict_miss_when_webui_link_not_in_sources() -> None:
    """expected_page_ids 의 webui_link 가 sources 에 없으면 miss."""
    from scripts.run_evaluation import _precision_match

    mapping = {"100001": "/display/CLOUD/A"}
    sources = [_fake_source("/display/CLOUD/Z")]

    assert _precision_match(sources, {"100001"}, mapping) is False


def test_precision_match_falls_back_to_loose_when_mapping_empty() -> None:
    """samples lookup 부재 시 sources 비어 있지 않으면 hit (약식)."""
    from scripts.run_evaluation import _precision_match

    sources = [_fake_source("/whatever")]

    # mapping 자체가 비어 있음 → loose fallback.
    assert _precision_match(sources, {"100001"}, {}) is True


def test_precision_match_returns_false_when_no_expected_page_ids() -> None:
    """expected_page_ids 가 비어 있으면 항상 miss (집계 대상 제외)."""
    from scripts.run_evaluation import _precision_match

    sources = [_fake_source("/display/CLOUD/A")]
    assert _precision_match(sources, set(), {"100001": "/display/CLOUD/A"}) is False


# ---------------------------------------------------------------------------
# feature17c-9 — Pool 가중치 그리드 서치 오버라이드 파서
# ---------------------------------------------------------------------------


def test_parse_pool_weights_maps_short_keys_to_pool_names() -> None:
    """title/content/label 단축키 → title_pool/content_pool/label_pool 매핑 + float 변환."""
    from scripts.run_evaluation import _parse_pool_weights

    assert _parse_pool_weights("title:0.25,content:0.6,label:0.15") == {
        "title_pool": 0.25,
        "content_pool": 0.6,
        "label_pool": 0.15,
    }


def test_parse_pool_weights_rejects_unknown_key() -> None:
    """미지의 Pool 키는 ValueError."""
    from scripts.run_evaluation import _parse_pool_weights

    with pytest.raises(ValueError, match="미지의 Pool"):
        _parse_pool_weights("title:0.5,body:0.5,label:0.0")


def test_parse_pool_weights_requires_all_three_pools() -> None:
    """3 Pool 을 모두 명시하지 않으면 ValueError."""
    from scripts.run_evaluation import _parse_pool_weights

    with pytest.raises(ValueError, match="3 Pool"):
        _parse_pool_weights("title:0.5,content:0.5")


def test_parse_pool_weights_rejects_malformed_item() -> None:
    """':' 없는 항목은 ValueError."""
    from scripts.run_evaluation import _parse_pool_weights

    with pytest.raises(ValueError, match="잘못된 pool-weights"):
        _parse_pool_weights("title=0.5,content:0.3,label:0.2")


# ---------------------------------------------------------------------------
# feature17c-13 — 환각 측정 공정화 (_summarize_hallucination)
# ---------------------------------------------------------------------------


def _ns(*statuses: str) -> list[dict[str, str]]:
    """verification status 목록을 result 형태로 변환."""
    return [{"sentence_id": i, "status": s} for i, s in enumerate(statuses)]


def test_summarize_hallucination_separates_answerable() -> None:
    """is_answerable=false 항목의 NOT_SUPPORTED 는 answerable 지표에서 제외된다."""
    from scripts.run_evaluation import _summarize_hallucination

    results = [
        # answerable: 3문장 중 1 NOT_SUPPORTED
        {
            "is_answerable": True,
            "n_sources": 3,
            "verification": _ns("SUPPORTED", "NOT_SUPPORTED", "PASS"),
        },
        # answerable: 1문장 SUPPORTED
        {"is_answerable": True, "n_sources": 2, "verification": _ns("SUPPORTED")},
        # non-answerable: 1 NOT_SUPPORTED (올바른 거부) → answerable 집계 제외
        {"is_answerable": False, "n_sources": 0, "verification": _ns("NOT_SUPPORTED")},
    ]
    out = _summarize_hallucination(results)

    # 전체: 5문장 중 2 NOT_SUPPORTED
    assert out["verification_total"] == 5
    assert out["not_supported_count"] == 2
    assert out["not_supported_ratio"] == pytest.approx(2 / 5)
    # answerable 만: 4문장 중 1 NOT_SUPPORTED (non-answerable 1건 분리)
    assert out["verification_total_answerable"] == 4
    assert out["not_supported_count_answerable"] == 1
    assert out["not_supported_ratio_answerable"] == pytest.approx(1 / 4)
    assert out["answerable_n_items"] == 2
    assert out["non_answerable_n_items"] == 1


def test_summarize_hallucination_defaults_missing_flag_to_answerable() -> None:
    """is_answerable 미지정 항목은 answerable(True)로 집계된다."""
    from scripts.run_evaluation import _summarize_hallucination

    results = [
        {"n_sources": 1, "verification": _ns("NOT_SUPPORTED", "SUPPORTED")},
    ]
    out = _summarize_hallucination(results)

    assert out["answerable_n_items"] == 1
    assert out["non_answerable_n_items"] == 0
    assert out["verification_total_answerable"] == 2
    assert out["not_supported_count_answerable"] == 1
    # 전체와 answerable 이 동일 (모두 answerable)
    assert out["not_supported_ratio"] == out["not_supported_ratio_answerable"]


def test_summarize_hallucination_counts_non_answerable_correct_refusal() -> None:
    """non-answerable 항목 중 검색 후보 0건은 '올바른 거부'로 카운트된다."""
    from scripts.run_evaluation import _summarize_hallucination

    results = [
        # non-answerable + n_sources=0 → 올바른 거부
        {"is_answerable": False, "n_sources": 0, "verification": _ns("NOT_SUPPORTED")},
        # non-answerable + n_sources=1 → 거부 실패(답변 시도) → 카운트 안 함
        {"is_answerable": False, "n_sources": 1, "verification": _ns("NOT_SUPPORTED", "PASS")},
        # answerable → 거부 카운트 무관
        {"is_answerable": True, "n_sources": 2, "verification": _ns("SUPPORTED")},
    ]
    out = _summarize_hallucination(results)

    assert out["non_answerable_n_items"] == 2
    assert out["non_answerable_correct_refusal_n_items"] == 1


def test_summarize_hallucination_handles_empty_results() -> None:
    """결과가 없으면 비율은 None, 카운트는 0."""
    from scripts.run_evaluation import _summarize_hallucination

    out = _summarize_hallucination([])

    assert out["not_supported_ratio"] is None
    assert out["not_supported_ratio_answerable"] is None
    assert out["verification_total"] == 0
    assert out["answerable_n_items"] == 0
    assert out["non_answerable_n_items"] == 0


# ---------------------------------------------------------------------------
# feature17c-15 — 검증 진단 (--debug-verify) 순수 헬퍼
# ---------------------------------------------------------------------------


def test_classify_token_location_in_cited() -> None:
    """인용 청크에 존재하면 in_cited (1단계 false positive 후보)."""
    from scripts.run_evaluation import _classify_token_location

    assert (
        _classify_token_location(grounded_in_cited=True, grounded_in_any=True) == "in_cited"
    )


def test_classify_token_location_in_other_topk() -> None:
    """인용엔 없으나 다른 Top-K 에 있으면 in_other_topk (citation 정밀도)."""
    from scripts.run_evaluation import _classify_token_location

    assert (
        _classify_token_location(grounded_in_cited=False, grounded_in_any=True)
        == "in_other_topk"
    )


def test_classify_token_location_absent() -> None:
    """어느 Top-K 에도 없으면 absent (recall·생성 갭)."""
    from scripts.run_evaluation import _classify_token_location

    assert (
        _classify_token_location(grounded_in_cited=False, grounded_in_any=False) == "absent"
    )


def _verify_rec(
    *,
    sid: int,
    final: str,
    suspicious: bool = True,
    raw_label: str | None = None,
    locations: list[str] | None = None,
) -> dict:
    return {
        "sentence_id": sid,
        "sentence": f"sentence {sid}",
        "cited_chunks": [1],
        "checkable_tokens": [],
        "unverified_tokens": [{"token": f"t{i}", "location": loc} for i, loc in
                              enumerate(locations or [])],
        "suspicious": suspicious,
        "stage2_raw_label": raw_label,
        "stage2_score": None,
        "stage2_reason": None,
        "final_status": final,
    }


def test_summarize_debug_verify_distributions() -> None:
    """final 상태/raw label/토큰 위치 분포를 집계한다."""
    from scripts.run_evaluation import _summarize_debug_verify

    records = [
        _verify_rec(sid=1, final="PASS", suspicious=False),
        _verify_rec(sid=2, final="NOT_SUPPORTED", raw_label="low_confidence",
                    locations=["absent", "in_other_topk"]),
        _verify_rec(sid=3, final="NOT_SUPPORTED", raw_label="unsupported",
                    locations=["absent"]),
        _verify_rec(sid=4, final="SUPPORTED", raw_label="supported", locations=[]),
    ]
    out = _summarize_debug_verify(records)

    assert out["n_sentences"] == 4
    assert out["final_status_dist"] == {"PASS": 1, "NOT_SUPPORTED": 2, "SUPPORTED": 1}
    # NOT_SUPPORTED 만 raw label 집계
    assert out["not_supported_raw_label_dist"] == {"low_confidence": 1, "unsupported": 1}
    assert out["unverified_token_location_dist"] == {"absent": 2, "in_other_topk": 1}
