"""Cross-Encoder 재순위화 — CrossEncoderRerankerImpl (sentence-transformers 래퍼) [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : sentence-transformers의 ``CrossEncoder`` 를 래핑해 CrossEncoderReranker
          인터페이스(`app/query/reranker/base.py`)를 구현한다. Sigmoid 활성화로 raw
          logit을 ``[0.0, 1.0]`` 점수로 변환해 ``select_reranked`` (feature9-A)의 임계값
          (NARROW 0.30 / LOW 0.20)과 정합시킨다 (`docs/rag-pipeline-design.md` §6 4.5,
          `app/CLAUDE.md` §8).
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature9-B-1 — CrossEncoderRerankerImpl
--------------------------------------------------
[호환성]
  - Python 3.11.x
  - sentence-transformers>=3.0 + torch (pyproject [embedding] extra)
  - NOTE: 본 모듈은 sentence-transformers / torch 설치를 전제로 한다. embedding extra
          미설치 환경에서는 import 단계에서 ImportError 발생 — 테스트는 base.Fake 또는
          pytest.importorskip로 우회한다.
--------------------------------------------------
"""

import math

from sentence_transformers import CrossEncoder

from app.query.reranker.base import CrossEncoderReranker


class CrossEncoderRerankerImpl(CrossEncoderReranker):
    """``cross-encoder/ms-marco-MiniLM-L-12`` 어댑터 (sentence-transformers).

    sentence-transformers ``CrossEncoder.predict`` 를 호출해 (query, passage) 쌍의 관련도
    logit을 산출한 뒤, Sigmoid를 적용해 ``[0.0, 1.0]`` 점수로 변환한다 —
    ``select_reranked`` (feature9-A)의 임계값과 정합.

    Args:
        model_name: 모델 이름. 기본값은 ms-marco-MiniLM-L-12.
        device: torch 장치(``"cpu"`` / ``"cuda"`` / ``"mps"`` 등). ``None`` 이면
            sentence-transformers가 자동 선택.
        batch_size: 추론 시 배치 크기. ms-marco-MiniLM-L-12 기준 32가 권장
            (`app/CLAUDE.md` §5.7 NOTE 정합).

    Raises:
        ImportError: sentence-transformers 미설치 시 모듈 import 단계에서 발생.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-12",
        *,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        self._model = CrossEncoder(model_name, device=device)
        self._batch_size = batch_size

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        pairs = [(query, passage) for passage in passages]
        # raw logit → Sigmoid → [0.0, 1.0]. sentence-transformers CrossEncoder는
        # apply_softmax / 별도 활성화 함수 인자를 제공하지만 raw 값을 받고 어댑터에서
        # 변환하는 게 행위 명시성이 높다. 또한 의존성 import 비용 회피 위해 sigmoid는
        # torch.nn.functional이 아니라 stdlib math로 단일 값씩 처리한다.
        raw_scores = self._model.predict(
            pairs,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [_sigmoid(float(score)) for score in raw_scores]


def _sigmoid(value: float) -> float:
    """수치적으로 안정한 Sigmoid 변환 — overflow/underflow 모두 안전.

    큰 양수 입력에서 ``math.exp(-value)`` 가 underflow되면 1.0에 수렴, 큰 음수에서
    ``math.exp(value)`` 가 underflow되면 0.0에 수렴하도록 분기.
    """
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)
