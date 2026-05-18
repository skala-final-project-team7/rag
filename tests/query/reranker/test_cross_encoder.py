"""CrossEncoderRerankerImpl 어댑터 검증 (feature9-B-1).

sentence-transformers 미설치 환경에서는 importorskip로 우회한다. 모델 다운로드(약
130 MB)를 피하기 위해 단위 테스트에서는 ``CrossEncoder`` 를 모방하는 stub을 직접
주입한다. 내부 ``_sigmoid`` 헬퍼의 수치 안정성도 함께 검증한다.
"""

import math
from typing import Any

import pytest

# sentence-transformers는 무거운 의존성(embedding extra) — 미설치 환경에서는 스킵.
pytest.importorskip("sentence_transformers")
pytest.importorskip("numpy")

from app.query.reranker.cross_encoder import CrossEncoderRerankerImpl, _sigmoid  # noqa: E402


class _StubCrossEncoder:
    """sentence-transformers CrossEncoder를 모방한 stub — 실 모델 다운로드 회피."""

    def __init__(self, raw_score_per_pair: float = 0.0) -> None:
        self._raw_score_per_pair = raw_score_per_pair
        self.captured_pairs: list[tuple[str, str]] = []
        self.last_batch_size: int | None = None

    def predict(
        self,
        pairs: list[tuple[str, str]],
        *,
        batch_size: int = 32,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> Any:
        import numpy as np  # 지연 import — pytest.importorskip 통과 후 안전

        self.captured_pairs.extend(pairs)
        self.last_batch_size = batch_size
        return np.full(len(pairs), self._raw_score_per_pair, dtype=np.float32)


def _make_reranker(stub: _StubCrossEncoder, *, batch_size: int = 32) -> CrossEncoderRerankerImpl:
    reranker = CrossEncoderRerankerImpl.__new__(CrossEncoderRerankerImpl)
    reranker._model = stub  # type: ignore[attr-defined]
    reranker._batch_size = batch_size  # type: ignore[attr-defined]
    return reranker


# --- score: 입력 변환 ---


def test_score_constructs_query_passage_pairs() -> None:
    stub = _StubCrossEncoder()
    reranker = _make_reranker(stub)
    reranker.score("EKS 노드 장애 대응", ["passage A", "passage B"])
    assert stub.captured_pairs == [
        ("EKS 노드 장애 대응", "passage A"),
        ("EKS 노드 장애 대응", "passage B"),
    ]


def test_score_passes_configured_batch_size() -> None:
    stub = _StubCrossEncoder()
    reranker = _make_reranker(stub, batch_size=8)
    reranker.score("query", ["a", "b", "c"])
    assert stub.last_batch_size == 8


def test_score_empty_passages_returns_empty_without_calling_model() -> None:
    stub = _StubCrossEncoder()
    reranker = _make_reranker(stub)
    assert reranker.score("any query", []) == []
    assert stub.captured_pairs == []


def test_score_applies_sigmoid_to_raw_logits() -> None:
    # raw logit 0.0 → Sigmoid 0.5
    stub = _StubCrossEncoder(raw_score_per_pair=0.0)
    reranker = _make_reranker(stub)
    [score] = reranker.score("query", ["passage"])
    assert math.isclose(score, 0.5, rel_tol=1e-6)


def test_score_high_logit_maps_close_to_one() -> None:
    stub = _StubCrossEncoder(raw_score_per_pair=10.0)
    reranker = _make_reranker(stub)
    [score] = reranker.score("query", ["passage"])
    assert score > 0.999


def test_score_low_logit_maps_close_to_zero() -> None:
    stub = _StubCrossEncoder(raw_score_per_pair=-10.0)
    reranker = _make_reranker(stub)
    [score] = reranker.score("query", ["passage"])
    assert score < 0.001


# --- _sigmoid 수치 안정성 ---


def test_sigmoid_zero_returns_half() -> None:
    assert math.isclose(_sigmoid(0.0), 0.5, rel_tol=1e-9)


def test_sigmoid_large_positive_does_not_overflow() -> None:
    # exp(-large)이 underflow돼도 1.0에 수렴해야 함
    assert math.isclose(_sigmoid(1000.0), 1.0)
    assert _sigmoid(1000.0) <= 1.0


def test_sigmoid_large_negative_does_not_overflow() -> None:
    # exp(large)이 underflow돼도 0.0에 수렴해야 함
    assert math.isclose(_sigmoid(-1000.0), 0.0, abs_tol=1e-9)
    assert _sigmoid(-1000.0) >= 0.0


def test_sigmoid_monotonic_increasing() -> None:
    values = [_sigmoid(value) for value in (-5.0, -1.0, 0.0, 1.0, 5.0)]
    for prev, curr in zip(values[:-1], values[1:], strict=True):
        assert prev < curr
