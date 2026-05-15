"""app.adapters — Document Source Adapter [Pipeline 경계].

RAG 파이프라인이 데이터 공급원에 직접 결합하지 않도록 하는 추상 인터페이스.
공급원이 무엇이든 동일한 표준 PageObject 스트림을 반환하도록 강제하며,
공급원 전환 시 어댑터 1개 클래스 + config의 source.type 1줄만 바뀐다.

백엔드(BFF)가 아직 없어, PoC에서는 본 저장소가 Atlassian REST API를 직접 호출한다.
OAuth 인증·access_token 관리는 Authorization Server(Spring) 책임이며, 본 저장소는
발급된 access_token·cloudid를 전달받아 사용한다. 상세: docs/atlassian-api.md.

계획 모듈:
- base.py          DocumentSourceAdapter 추상 인터페이스
                   fetch_pages() / list_active_ids() / watch_changes()
- json_fixture.py  JsonFixtureSourceAdapter — samples/*.json 읽기 (로컬 개발·테스트용)
- atlassian.py     AtlassianSourceAdapter — atlassian-python-api로 Confluence REST 직접 호출
                   (DATA-01 페이지 목록 / DATA-02 CQL 델타 싱크 / DATA-03 Space 목록)
"""
