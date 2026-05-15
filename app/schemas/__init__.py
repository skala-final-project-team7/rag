"""app.schemas — 계층 간 데이터 계약 [Pipeline].

파이프라인 단계 간에 dict를 그대로 전달하지 않고 Pydantic 모델로 정의한다.

계획 모듈:
- page_object.py   PageObject, Attachment (Ingestion 입력, 백엔드와 동결 — 설계서 §7.1)
- chunk.py         Chunk, ChunkMetadata (메타데이터 공통 13 + 첨부 5 + token_count)
- rag_state.py     RagState (Query LangGraph 노드 상태), IngestionState (Ingestion 노드 상태)
- response.py      QueryResponse, Source, Verification (API 응답 — docs/api-spec.md)
- enums.py         DocType(6종), AttachmentType, Intent(4종), SourceType, VerificationStatus
"""
