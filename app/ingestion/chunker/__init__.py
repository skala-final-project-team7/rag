"""app.ingestion.chunker — Adaptive Chunker [Pipeline].

doc_type / attachment_type 분기에 따라 본문·첨부 텍스트를 청크로 분할한다.
2단계 하이브리드: 1차 논리 단위 분할 → 2차 800토큰 재분할(100토큰 오버랩) → 200토큰 하한선 병합.
원자성 유지 유형(FAQ Q&A·ADR·회의록 안건·트러블슈팅 케이스)은 2차 분할·하한선 병합에서 제외한다.
상세 규칙: docs/chunking-strategy.md.

계획 모듈:
- base.py           청킹 공통 인터페이스 + 2차 재분할 / 하한선 병합 / chunk_id 결정론 계산
- storage_format.py Confluence Storage Format(HTML) 공통 전처리 (매크로·코드블록·표·이미지 정규화)
- body.py           본문 6유형 분할 (incident / operation / faq / meeting / adr / troubleshoot)
- attachment.py     첨부 3유형 분할 (pdf / docx / xlsx·csv) — Excel/CSV 자연어 직렬화 포함
- metadata.py       청크 메타데이터 19종 부착 + 무결성 규칙
- tokenizer.py      임베딩 토큰 카운팅 (SentencePiece, 800/200 임계 판단)
"""
