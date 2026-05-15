"""app.ingestion — Ingestion 파이프라인.

표준 PageObject를 검색 가능한 벡터로 변환해 Qdrant Multi-Pool에 적재한다.
처리 결과는 MongoDB ingestion_jobs 컬렉션에 단계별 상태로 기록한다.

단계 및 분류 (docs/rag-pipeline-design.md §5):
- document_analyzer.py  문서 분석기 [Agent]     스페이스별 1회 doc_type 판별 → MySQL 캐싱
- attachment_analyzer.py 첨부 파일 분석기 [Pipeline] mime/확장자 판별·텍스트 유효성 검증·메타 상속
- chunker/              Adaptive Chunker [Pipeline]  본문 6유형 + 첨부 3유형 청킹 (하위 패키지)
- embedding.py          Dual Embedding [Pipeline]  Dense(e5-large 1024d) + Sparse(BM25)
- vector_store.py       Multi-Pool Vector Store [Storage]  Qdrant title/content/label pool upsert
- sync.py               삭제 동기화 [Pipeline]  Reconciliation 중심 3중 전략 (고스트 데이터 방지)
- jobs.py               ingestion_jobs 상태 기록 헬퍼
"""
