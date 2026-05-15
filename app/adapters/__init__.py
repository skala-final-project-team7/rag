"""app.adapters — Document Source Adapter [Pipeline 경계].

RAG 파이프라인이 데이터 공급원에 직접 결합하지 않도록 하는 추상 인터페이스.
PoC는 MongoDB mock 어댑터, 운영 전환 시 ConfluenceSourceAdapter로 교체한다.
전환 시 바뀌는 것은 어댑터 1개 클래스 + config의 source.type 1줄뿐이다.

외부 호출(Confluence REST/OAuth, 첨부 다운로드·텍스트 추출)은 백엔드 책임이다.
본 패키지는 표준 PageObject를 반환하는 인터페이스 계약만 정의·구현한다.

계획 모듈:
- base.py    DocumentSourceAdapter 추상 인터페이스
             fetch_pages() / list_active_ids() / watch_changes()
- mongo.py   MongoSourceAdapter — PoC: rag_mock.pages / rag_mock.attachments 읽기
"""
