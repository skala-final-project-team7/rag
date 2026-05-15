"""app.pipeline — LangGraph 그래프 조립.

app.ingestion / app.query 의 단계별 노드를 LangGraph StateGraph로 연결한다.
각 노드는 단일 책임을 갖고, 노드 입출력 상태는 app.schemas 의 IngestionState / RagState로 통일한다.

계획 모듈:
- ingestion_graph.py  Ingestion 그래프 (문서 분석 → 첨부 분석 → 청킹 → 임베딩 → 적재)
- query_graph.py      Query 그래프 (ACL → 히스토리 → 라우터 → 검색·재순위화 → 생성 → 검증 → 포맷)
                      히스토리 관리자의 needs_search=false 시 검색 단계 스킵 분기 포함
"""
