"""청킹 2단계 하이브리드 규칙 — split_oversized / merge_undersized / apply_size_rules.

chunking-strategy.md §3·§5: 1차 분할(body.py 담당) 결과에 2차 재분할(800토큰 초과 →
100토큰 오버랩)과 하한선 병합(200토큰 미만)을 적용. 원자성 유지 유형은 제외.
"""

from app.ingestion.chunker.base import (
    ChunkDraft,
    apply_size_rules,
    merge_undersized,
    split_oversized,
)
from app.ingestion.chunker.tokenizer import count_tokens


def test_split_oversized_keeps_short_text() -> None:
    text = "짧은 문장 하나"
    assert split_oversized(text, max_tokens=100, overlap_tokens=10) == [text]


def test_split_oversized_splits_long_text() -> None:
    # 10줄, 각 줄 약 4토큰 → 약 40토큰. max=12면 여러 윈도우로 분할
    text = "\n".join(f"라인 번호 {i}" for i in range(10))
    windows = split_oversized(text, max_tokens=12, overlap_tokens=4)
    assert len(windows) > 1
    # 각 윈도우는 max_tokens 이하 (단일 단위 예외 제외)
    for window in windows:
        assert count_tokens(window) <= 12
    # 전체 라인이 누락 없이 포함된다
    joined = "\n".join(windows)
    for i in range(10):
        assert f"라인 번호 {i}" in joined


def test_split_oversized_has_overlap() -> None:
    text = "\n".join(f"문장{i}" for i in range(12))
    windows = split_oversized(text, max_tokens=6, overlap_tokens=2)
    # 인접 윈도우는 겹치는 라인을 공유한다
    assert len(windows) >= 2
    first_lines = set(windows[0].split("\n"))
    second_lines = set(windows[1].split("\n"))
    assert first_lines & second_lines


def test_merge_undersized_merges_small_adjacent() -> None:
    drafts = [
        ChunkDraft(text="가 " * 250, section_header="A"),  # 큰 비원자 청크 (prev)
        ChunkDraft(text="짧음", section_header="B"),  # < 200 토큰 → 직전과 병합
    ]
    merged = merge_undersized(drafts, min_tokens=200)
    assert len(merged) == 1
    assert "짧음" in merged[0].text


def test_merge_undersized_keeps_atomic() -> None:
    drafts = [
        ChunkDraft(text="가 " * 250, section_header="A"),
        ChunkDraft(text="짧은 원자 청크", section_header="B", is_atomic=True),
    ]
    merged = merge_undersized(drafts, min_tokens=200)
    # 원자성 청크는 작아도 병합되지 않는다
    assert len(merged) == 2


def test_apply_size_rules_combines_split_and_merge() -> None:
    # 약 8토큰 × 250줄 = 2000토큰 → 기본 임계(800) 초과로 2차 재분할 발생
    big_text = "\n".join(f"항목 번호 {i} 입니다" for i in range(250))
    drafts = [
        ChunkDraft(text=big_text, section_header="big"),
        ChunkDraft(text="adr 원자 청크", section_header="adr", is_atomic=True),
    ]
    result = apply_size_rules(drafts)
    # 큰 비원자 청크는 여러 조각으로 분할, 원자 청크는 그대로 유지
    assert len([d for d in result if d.section_header == "big"]) >= 2
    assert any(d.is_atomic and d.section_header == "adr" for d in result)


def test_chunk_draft_defaults() -> None:
    draft = ChunkDraft(text="본문", section_header="섹션")
    assert draft.is_atomic is False
