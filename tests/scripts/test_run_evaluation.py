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
