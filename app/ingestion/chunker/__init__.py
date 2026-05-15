"""app.ingestion.chunker — Adaptive Chunker [Pipeline].

doc_type / attachment_type 분기에 따라 본문·첨부 텍스트를 청크로 분할한다.
2단계 하이브리드: 1차 논리 단위 분할 → 2차 800토큰 재분할(100토큰 오버랩) → 200토큰 하한선 병합.
원자성 유지 유형(FAQ Q&A·ADR·회의록 안건·트러블슈팅 케이스)은 2차 분할·하한선 병합에서 제외한다.
상세 규칙: docs/chunking-strategy.md.

구현 상태:
- tokenizer.py        count_tokens — 토큰 카운터 (PoC 휴리스틱) [feature3-A 완료]
- storage_format.py   clean_storage_format — Storage Format(HTML) 전처리 [feature3-A 완료]
- base.py             ChunkDraft / split_oversized / merge_undersized / apply_size_rules
                      — 2단계 하이브리드 분할 공통 로직 [feature3-A 완료]
- body.py             본문 6유형 1차 분할 [feature3-B 예정]
- metadata.py         청크 메타데이터 19종 부착 [feature3-B 예정]
"""

from app.ingestion.chunker.base import (
    MAX_TOKENS,
    MIN_TOKENS,
    OVERLAP_TOKENS,
    ChunkDraft,
    apply_size_rules,
    merge_undersized,
    split_oversized,
)
from app.ingestion.chunker.storage_format import clean_storage_format
from app.ingestion.chunker.tokenizer import count_tokens

__all__ = [
    "MAX_TOKENS",
    "MIN_TOKENS",
    "OVERLAP_TOKENS",
    "ChunkDraft",
    "apply_size_rules",
    "clean_storage_format",
    "count_tokens",
    "merge_undersized",
    "split_oversized",
]
