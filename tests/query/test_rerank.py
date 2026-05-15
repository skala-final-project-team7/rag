"""Cross-Encoder 재순위화 선정 로직 검증 (feature9-A) — rag-pipeline-design.md §6 4.5, §8.

select_reranked: Top-5 선정, 5위 < 0.30 시 Top-3 축소, 최고 < 0.20 시 저신뢰 분기.
"""

from app.query.rerank import RerankResult, select_reranked


def test_select_reranked_keeps_top_5() -> None:
    scored = {f"c{i}": 0.9 - i * 0.05 for i in range(8)}  # c0..c7 내림차순
    result = select_reranked(scored)
    assert isinstance(result, RerankResult)
    # 8개 중 Top-5 (5위 점수 0.70 ≥ 0.30 → 축소 없음)
    assert [item for item, _ in result.top] == ["c0", "c1", "c2", "c3", "c4"]
    assert result.is_low_confidence is False


def test_select_reranked_narrows_to_top_3_when_fifth_is_low() -> None:
    # 5위 점수가 0.30 미만이면 Top-3로 축소한다
    scored = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.25, "e": 0.20}
    result = select_reranked(scored)
    assert [item for item, _ in result.top] == ["a", "b", "c"]
    assert result.is_low_confidence is False


def test_select_reranked_keeps_top_5_when_fifth_at_threshold() -> None:
    # 5위 점수가 정확히 0.30이면 축소하지 않는다 (< 0.30 만 축소)
    scored = {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.5, "e": 0.30}
    result = select_reranked(scored)
    assert len(result.top) == 5


def test_select_reranked_low_confidence_when_best_below_threshold() -> None:
    # 최고 점수가 0.20 미만이면 저신뢰 분기
    scored = {"a": 0.19, "b": 0.1, "c": 0.05}
    result = select_reranked(scored)
    assert result.is_low_confidence is True
    assert [item for item, _ in result.top] == ["a", "b", "c"]


def test_select_reranked_empty_is_low_confidence() -> None:
    result = select_reranked({})
    assert result.top == []
    assert result.is_low_confidence is True


def test_select_reranked_tie_break_is_deterministic() -> None:
    # 동점은 item 오름차순으로 결정론 정렬
    result = select_reranked({"b": 0.5, "a": 0.5, "c": 0.5})
    assert [item for item, _ in result.top] == ["a", "b", "c"]
