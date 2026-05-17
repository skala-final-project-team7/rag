# Code Review — feat/#1/rag-pipeline-skeleton (2026-05-17)

리뷰 범위: `app/adapters/`, `app/ingestion/`(chunker·embedding·vector_store), `app/query/`(acl·history·search·rerank·verifier·formatter), `app/schemas/`, `app/config.py`, 대응 `tests/`, `samples/`·`examples/demo_data_layer.py`.
제외(의도된 미구현 — working-log 명시): `app/api/`, `app/pipeline/`, `app/llm/`, `app/query/generator.py`, `app/query/router.py`, `app/ingestion/document_analyzer.py`, `AtlassianSourceAdapter`, feature4-B·5-B·6·9-B·10(Agent)·11(통합), `history_manager_agent/**`(vendored).

---

## 1. 요약

기획서 v2.1.6·설계서 v0.2.2의 결정론적 핵심 로직(스키마 19종 메타·ACL Pre-filter·@enforce_acl·청킹 2단계 하이브리드·본문 6유형·docx/xlsx 첨부·임베딩 입력/payload·RRF/Pool 가중/Top-K/저신뢰 임계·1단계 규칙 검증·응답 포맷터)이 설계와 거의 1:1로 옮겨졌고, 262개 테스트로 회귀가 보호되어 있다. 책임 경계가 깨끗하고(어댑터/스키마/Pipeline/Storage 분리), 표준 주석 블록·결정론 헬퍼·멱등성 키가 컨벤션을 준수한다. 보안 관점에서 ACL 우회를 시스템 단(@enforce_acl)에서 막는 구조가 잘 잡혔고 JWT 서명 미검증은 BFF 책임으로 의도되어 docstring에 명시되어 있다. P0 즉시 결함은 없으며, P1로는 (a) `Settings.samples_dir` ↔ 어댑터 기본값 어긋남, (b) `_is_valid_acl_filter`의 절(clause) 구조 미검증, (c) xlsx 단일 행/축소 한계 그룹의 임베딩 입력 한계 가드 부재, (d) `Attachment.download_url`의 의미 이중성(로컬 경로 vs HTTP URL) 정도가 있다.

---

## 2. 설계 정합성

| 심각도 | 항목 | 위치 | 설명 | 권고 |
|---|---|---|---|---|
| P1 | `Settings.samples_dir`가 어댑터 인자로 흐르지 않음 | `app/config.py:34` ↔ `app/adapters/json_fixture.py:80` | `Settings.samples_dir="samples"`가 정의되어 있으나 `JsonFixtureSourceAdapter.__init__`가 `Settings`를 참조하지 않고 자체 기본값을 둠. 두 값이 어긋나면 발견하기 어렵다. | 어댑터 팩토리(`build_source_adapter`)를 별도로 두고 그 안에서 `get_settings().samples_dir`를 주입하거나, `Settings`에서 해당 필드를 제거. |
| P1 | `_is_valid_acl_filter`가 `should` 절 내부 구조를 검증하지 않음 | `app/query/acl.py:125-134` | `acl_filter={"should":[{}]}` 또는 `should=[{"foo":"bar"}]`처럼 의미 없는 값을 넘겨도 통과한다. ACL 우회 위험은 낮으나 잘못된 호출을 빠르게 잡지 못한다. | 각 절이 dict이고 `key`/`match` 키를 갖는지(또는 `build_acl_filter`가 생성한 형태와 동치인지) 추가 검사. |
| P1 | `Attachment.download_url`의 의미 이중성 | `app/adapters/json_fixture.py:160` (`str(self.samples_dir / "attachments" / filename)`) vs `docs/db-schema.md §1.2` (출처 카드 URL) | JSON 픽스처 어댑터는 로컬 파일 시스템 경로를, 운영 어댑터는 HTTP URL을 동일 필드에 채울 예정. `chunker/attachment.py`는 `attachment.download_url`을 `python-docx`·`openpyxl`에 직접 전달하지만, 응답 포맷터의 `Source.download_url`은 사용자에게 노출된다. 두 의미가 같은 필드를 공유하면 운영 전환 시 사용자에게 로컬 경로가 누출되거나 청커가 URL을 파일로 열다 실패할 수 있다. | (a) `Attachment`에 `local_path: Optional[str]`을 분리 추가하거나, (b) 어댑터 단에서 다운로드 → 임시 경로 추출 → `download_url`은 항상 사용자 노출용 URL로 유지하도록 인터페이스를 분리. 설계서 §3.3.B의 "텍스트 추출은 어댑터 책임" 분기와도 정합. |
| P2 | xlsx 청킹이 `apply_size_rules`를 적용하지 않음 — 단일 행/축소 한계(10행) 그룹이 800토큰을 초과할 수 있음 | `app/ingestion/chunker/attachment.py:425-428`, working-log 2026-05-15 "클러스터 메트릭 시트는 단일 행이 ~163토큰" | 행 그룹 분할이 크기 처리를 겸한다는 가정인데, 단일 행이 800을 넘는 경우는 처리 단계가 더 없다. e5-large 권장 입력(512~1024) 안에 들지만 임계 근처에서 임베딩 품질 저하 위험. | `_group_sheet_rows`에 `count_tokens(text) > MAX_TOKENS && len(rows)==1`인 경우 `OVERSIZE_ATOMIC` 상태로 기록하거나(`feature6` jobs 헬퍼와 연동), text를 max_tokens 슬라이딩 윈도우로 추가 분할. 현재는 묵묵히 통과. |
| P2 | `verifier.py`의 부분 문자열 매칭 — false positive/negative 여지 | `app/query/verifier.py:130-132` (`token.lower() in cited_text.lower()`) | "32"가 청크에 "320"으로 들어있어도 grounded로 판정. 반대로 한국어 조사가 붙으면 token에 잡히지 않아 누락. PoC 휴리스틱임은 모듈 docstring·NOTE에 명시되어 있다. | 워드 경계(`\b{token}\b`) 적용 또는 Mecab 도입을 품질 튜닝 단계에서 진행. 즉시 결함은 아님. |
| P2 | `chunk_page`/`chunk_attachment`가 `is_acl_missing` 가드를 두지 않음 | `app/ingestion/chunker/body.py:217-229`, `attachment.py:397-436` | `app/CLAUDE.md` §3 "ACL 정보가 전혀 없는 PageObject·청크는 색인하지 않는다 (`INVALID_ACL`)"는 graph 조립 단계의 책임이지만(`feature6`), 안전망이 없다. 청커가 graph 외부에서 호출되면 ACL 없는 청크가 생긴다. | feature6 그래프 조립 시 명시적 가드를 두는 것이 정공법이고, 청커 단에 보조 가드를 둘지는 결정 필요. 결정 사항으로 `docs/ai/working-log.md`에 명시 권장. |
| P2 | `_NUMBER` 정규식 — 2자리 숫자가 `[0-9]{2,}`로만 잡힘 | `app/query/verifier.py:36` | `"32"`는 두 번째 분기 `[0-9]{2,}`로 매칭되나, `"5"` 같은 한자리는 매칭되지 않는다. 한자리 수치(예: `Top-5`, 단위 `1` 등)는 검증 대상이 아님 — 의도된 단순화이나 docstring에 한자리 미커버를 명시해두면 후속 정밀화 시 혼동을 줄임. | NOTE 보강. |
| P2 | `_looks_like_header`가 datetime을 헤더로 오인 가능 | `app/ingestion/chunker/attachment.py:206-211` | `_cell_to_str`이 datetime을 isoformat 문자열로 미리 변환하므로 첫 행의 datetime 셀이 모두 비수치 텍스트로 보여 헤더로 판정될 수 있다. 픽스처 4건에서는 발생하지 않으나 실데이터에서 일어날 수 있는 휴리스틱 한계. | 헤더 판정 시 raw value(`workbook ... values_only=True`로 받은 원본)로 isinstance 검사. |

설계서·기획서 항목 정합성 확인 결과(어긋남 없음):

- ACL 필터 should-OR 구조(`acl.py:117-122`) = `docs/db-schema.md §1.4` / 설계서 §4.2.1
- Qdrant payload 19필드(`vector_store.py:49-71`) = `docs/db-schema.md §1.2`
- Pool 이름·인덱스 키워드/datetime = `docs/db-schema.md §1.3`(설계서 §3.6.2)
- 청크 메타 19종(`chunker/metadata.py`, `chunker/attachment.py:347-394`) = `docs/chunking-strategy.md §6`
- RRF k=60·Top-20·Top-5·5위<0.30 축소·최고<0.20 저신뢰 = 설계서 §4.5·§8
- 응답 포맷터 분기(`formatter.py:82-93`) = `docs/api-spec.md` 표준 분기 응답
- DocType 6 / AttachmentType 4 / Intent 4 / VerificationStatus 3 / IngestionStatus 예외 코드 9 = `docs/chunking-strategy.md §4·§5·§8`, 설계서 §4.4·§4.7
- `make_chunk_id` SHA1(page_id+chunk_index+attachment_id), 결정론·임의 UUID 미사용 = `docs/chunking-strategy.md §6.1`
- 첨부 청크 `doc_type` 자리에 `attachment_type` 값 부착(`attachment.py:382`) = `docs/db-schema.md §1.2` 주석 "첨부는 `attachment_type` 값"

---

## 3. 코드 품질 (모듈별)

### `app/schemas/`

- 좋은 점: `StrEnum`으로 JSON 직렬화·Qdrant 비교 자연스러움. `make_chunk_id` 결정론 보장. `PageObject.is_acl_missing` 식별자가 응집 있게 page_object.py에 위치. `RagState`가 노드 시그니처 계약을 단일 모델로 응집. `HistoryDecision` 분리로 agent 출력의 비파괴 매핑을 보장.
- 개선점: `ChunkMetadata.doc_type`이 `str`이라 본문은 `DocType` 값, 첨부는 `AttachmentType` 값을 같은 칸에 담는 다형성. 의도는 알지만 정적 타입 검사가 약해진다. `Union[DocType, AttachmentType]` 또는 `Literal[...]`로 강제하면 잘못된 값 주입을 컴파일 시 잡을 수 있다. 또한 `last_modified`가 timezone-aware인지 검증하는 validator가 없어, 후속 단계에서 비교 시 `naive vs aware` 충돌 가능 — pydantic validator 추가 권장(P2).

### `app/adapters/`

- 좋은 점: 추상 인터페이스(`DocumentSourceAdapter`)와 PoC 어댑터 분리. `parse_atlassian_datetime`의 콜론 없는 오프셋 정규화가 명시되어 있고 단위 테스트가 양쪽 케이스를 모두 다룬다(`tests/adapters/test_json_fixture.py:53-62`).
- 개선점: `_synthesize_acl`이 `allowed_groups=["space:{space_key}"]`만 반환 — 결정한 ACL 모델(`allowed_groups`/`allowed_users`)이지만 실 입도(granularity)는 스페이스 단위와 동일. 이건 working-log·current-plan에 "교체 지점"으로 명시되어 있어 의도된 미완. 다만 JWT의 `groups`에 `space:CLOUD` 형태 prefix를 BFF가 채워줘야 매칭 — 이 prefix 컨벤션이 어디에도 동결되지 않았으므로 `docs/api-spec.md` 또는 별도 ADR로 남기는 것이 안전(P2).

### `app/ingestion/chunker/`

- 좋은 점: 2단계 하이브리드 분할(split_oversized → merge_undersized)의 봉인 로직과 회귀 테스트(`test_merge_undersized_seals_chunk_at_min_tokens`)가 명료. 본문 6유형 분기 함수(`_split_*`)가 단일 책임. xlsx 자연어 직렬화 형식이 설계서 §3.4.5·기획서 §6.6의 "컬럼명 매 행 부착" 의도와 일치. `clean_storage_format`이 code 매크로 내부 `<env>` 등이 태그로 파싱되어 사라지는 문제를 플레이스홀더 보호로 막은 부분이 견고.
- 개선점:
  - `_split_long_unit`(base.py:44-60): 단일 단어가 max_tokens를 넘는 경우(예: 매우 긴 URL) — 현재는 그 단어 1개를 그대로 한 윈도우로 둔다. 임베딩 입력 한계 우려는 P2 항목과 동일 맥락.
  - `chunker/body.py:_split_by_question_lines`: 두 번째 이상의 '?' 줄이 첫 번째 '?' 줄과 같은 라인에 나오는 답을 흡수해 한 청크에 정답+다음 질문이 함께 들어갈 수 있다. 픽스처에선 영향 없으나 실 FAQ에선 빈도 있는 패턴. 보조 분할(다음 '?' 발견 시 그 줄 직전까지를 답으로 자르기) 검토.
  - `attachment.py:_chunk_xlsx`: `data_only=True`로 수식 결과만 읽는데, 일부 통계 시트는 수식 캐시가 없으면 None만 잡힌다. `workbook.save()`가 수식 캐시를 채우지 않은 외부 xlsx에서 발생 — 픽스처에서는 영향 없음.
  - `attachment.py:_iter_block_items`의 `# type: ignore[attr-defined]`는 python-docx 내부 API 접근. 라이브러리 메이저 업그레이드 시 깨질 수 있으니 호환성 테스트 한 줄 추가 또는 변경 시 영향 받는 함수임을 docstring에 명시 권장.

### `app/ingestion/embedding.py` / `vector_store.py`

- 좋은 점: `version_number`가 `ChunkMetadata`에 없는 사정을 부모 PageObject에서 별도 인자로 받는 식으로 깨끗하게 처리(설계서·db-schema 정합). `pool_embedding_texts`가 첨부 청크에 `attachment_filename`을 title_pool 입력으로 쓰는 분기 명확. `should_skip_embedding`이 단일 진리값 함수로 멱등성 의도를 명확히 표현.
- 개선점: `build_point_payload`의 `text_preview` 슬라이싱이 코드포인트 기준(`chunk.text[:200]`). 한국어는 글자/코드포인트 매핑이 1:1이라 문제 없지만, 이모지/결합 문자가 들어가면 마지막 글자가 잘릴 수 있다. PoC 단계에서는 무해. 또한 `metadata.last_modified.isoformat()`을 호출하는데 datetime이 None일 일은 없으나(필수 필드), Optional 타이밍이 다시 들어오면 NoneError. validator 추가로 보강 가능.

### `app/query/`

- 좋은 점:
  - `acl.py`가 데코레이션 시점(`acl_filter` 파라미터 존재 강제)·호출 시점(필터 유효성) 양쪽을 모두 검사 — 우회 불가 구조 명확. `inspect.signature(func)`을 데코레이터 정의 시 한 번만 계산해 호출 오버헤드 최소화.
  - `search.py`/`rerank.py`가 외부 의존성 없는 순수 함수. 동점 결정론 정렬로 회귀 보호 가능.
  - `verifier.py`/`formatter.py`가 단일 책임. `format_response`가 차단·저신뢰 우선순위를 한 줄 비교로 표현(`is_low_confidence = is_blocked or _is_low_confidence(sources)`)해 가독성 좋음.
  - `history.py` 어댑터가 vendored 패키지 무수정 보존 원칙을 지키면서 RagState ↔ agent 스키마를 비파괴 매핑(`query` 원문 유지, `needs_search` 기본값 유지) — current-plan feature8의 매핑 원칙과 정합.
- 개선점:
  - `acl.py`의 `enforce_acl` 데코레이터가 docstring상 "sync/async 모두 지원"이라고 적혔으나 실제 wrapper는 `def`(sync). async 함수에 적용하면 wrapper 호출이 coroutine 객체를 그대로 반환하므로 `await wrapper(...)`는 동작하지만 데코레이터 자체가 awaitable이 되진 않는다. 동작에는 문제 없지만 표현이 오해를 일으킬 수 있으니 docstring 보강.
  - `acl.py:build_acl_filter` — `groups=[]`인 사용자가 들어오면 `allowed_groups` 절이 `match.any=[]`로 채워진다. Qdrant 동작상 빈 any는 항상 거짓이라 결과적으로 안전하지만, 빈 어레이가 어떤 백엔드에선 다르게 해석될 수 있다(예: ES `terms` 0개는 에러). Qdrant 외 backend에 포팅될 가능성 있으면 클라이언트 단에서 그 절을 빼는 식의 정규화 함수 분리(P2).
  - `formatter.py` — `_is_low_confidence`에 `sources=[]`도 저신뢰로 묶었는데, `api-spec.md`의 `RETRIEVAL_EMPTY`는 0건 일 때 LLM 미호출·표준 분기 응답으로 바로 끝나는 별도 케이스다. 통합 단계(`feature11` 그래프 조립)에서 검색 0건은 early-exit이고 포맷터까지 도달하지 않는 흐름이라는 점은 모듈 docstring에 명시되어 있어 정합. 다만 미래 보강 시 두 케이스가 한 분기로 합쳐지지 않도록 그래프 측 책임 분리를 유지 권장.

### `app/config.py`

- 좋은 점: `SecretStr`로 `openai_api_key`를 보호하고, `repr`/`str`에 평문이 노출되지 않는지 테스트로 확정.
- 개선점: `mysql_uri = "mysql+pymysql://..."`처럼 DSN을 평문 문자열로 둔 항목들은 실 운영에서 비밀번호가 포함되면 로그에 노출될 수 있다. PoC는 OK이지만 운영 전환 시 `SecretStr`로 승급하는 항목을 미리 표시해두면 좋다(NOTE 주석 정도).

---

## 4. 테스트

- 262건 통과 + samples 92페이지 통합 청킹 + 첨부 4건 통합 청킹이 회귀 보호의 단단한 백본이다. 모듈별 테스트가 docstring에 "검증 대상 + 설계서 절"을 명시해 의도가 명확.
- 픽스처 품질: `_PAGE_METADATA`(test_embedding/test_vector_store)와 `_PAGE_KWARGS`(test_chunk)가 모듈 간 일관된 스타일. `tests/query/test_acl.py:_make_jwt`로 서명 미검증 JWT를 만드는 헬퍼가 잘 분리됨.
- 놓친 케이스/보강 후보:
  - **@enforce_acl + 실제 검색 함수 통합** — async 함수에 데코레이션해 `await`로 호출하는 테스트가 없다. 데코레이터 docstring이 sync/async 모두 지원이라고 적혀 있으니 한 줄 통합 테스트 권장(P2).
  - **chunker `is_acl_missing` 경계** — `chunk_page(page_with_empty_acl)`에 대한 테스트가 없다. 현재 chunker는 가드를 두지 않으므로 청크가 생성되는데, 이 동작이 의도된 것인지(그래프 단계에서 막음) 문서로 단언하는 회귀 테스트 1건 추가 권장(P2).
  - **`@enforce_acl` 데코레이터에 `acl_filter` 키워드만 갖는 변형** — 현재 위치 인자 케이스(test_enforce_acl_accepts_positional_filter)는 있으나 `**kwargs`로 받는 함수(`**kwargs`에 acl_filter가 들어오는)에 대한 동작 검증은 없다. `signature.bind`가 처리하지만 회귀 보호 차원에서 1건 추가 권장(P2).
  - **`_split_by_question_lines` 답 흡수 케이스** — 답 줄에 또 다른 '?' 줄이 끼어든 입력(실 FAQ 패턴). 본문 6유형 테스트가 깔끔하나 이 엣지만 빠져 있음(P2).
  - **`extract_principal`이 `groups` 클레임 비-리스트일 때 거부**는 PrincipalExtractionError를 발생시키는데 해당 테스트가 명시적으로 없다. 다른 거부 케이스는 다 있으니 1건 추가 권장(P2).

---

## 5. 보안·ACL

- `@enforce_acl` 데코레이터(`app/query/acl.py:137-172`): 데코레이션 시점에 대상 함수에 `acl_filter` 파라미터가 있는지 검사(`TypeError`), 호출 시점에 그 값이 유효한지 검사(`ACLViolationError`). `signature.bind` + `apply_defaults`로 키워드/위치 인자 모두 커버. 회귀 테스트가 명시적 None·빈 dict·`should` 없는 dict·dict 아닌 값·파라미터 부재 함수 데코레이션을 모두 다룸. 우회 불가 구조 — 잘 설계됨.
- `extract_principal`: JWT 서명은 검증하지 않는다. 인증·서명·발급은 BFF(`docs/api-spec.md`)의 책임이고, working-log·docstring·`app/CLAUDE.md` §3에 일관되게 명시되어 있다. 의도된 책임 분리. `pyjwt` 미도입은 합리적 결정.
- payload 디코드 시 `binascii.Error`/`ValueError`를 모두 잡아 `PrincipalExtractionError`로 정규화 → API의 `UNAUTHORIZED` 매핑이 깔끔. `sub` 누락·`groups` 타입 오류도 동일 예외로 정규화.
- `build_acl_filter`가 입력 `groups` 리스트를 `list(groups)`로 복사 — 호출자가 원본을 변경해도 필터가 영향받지 않는다(테스트 `test_build_acl_filter_does_not_alias_groups`로 보호). 좋은 방어 코드.
- 잠재 위험(P1): `_is_valid_acl_filter`가 `should` 절의 내부 구조까지 검증하지 않음(§2 참조). 보안 우회 위험은 낮으나, ACL 모델 교체 시 잘못된 필터가 조용히 통과될 수 있어 결함 발견이 늦어진다.
- 잠재 위험(P2): `samples`의 ACL 합성(`space:{key}`) prefix 컨벤션이 BFF JWT의 `groups`와 어디에 동결되는지 문서가 없음. 운영 전환 시 매칭 실패로 검색 0건 사고 가능 — `docs/api-spec.md`에 short note 추가 권장.

---

## 6. 의도된 미구현 vs 실수 누락

### 의도된 미완 (working-log·current-plan에 명시 — 결함 아님)

- `app/api/`·`app/pipeline/`·`app/llm/`: 빈 패키지, docstring으로 책임 명시. feature11 통합·Agent 인프라 도착 후 채워질 예정.
- `app/query/generator.py`·`app/query/router.py`: Agent 담당자 영역. feature8 라우터/feature10 생성·검증 2단계가 도착하면 vendoring 또는 새 어댑터로 통합.
- `app/ingestion/document_analyzer.py`·`attachment_analyzer.py`·`sync.py`·`jobs.py`: feature6 — 본 담당자(Pipeline)/Agent 담당자 분리. 아직 미진행.
- `AtlassianSourceAdapter` (`feature2` 잔여): `access_token`/`cloudid` 전달 경로 미정 — current-plan 선행 의존성에 명시.
- feature4-B (PDF/CSV 청킹): 픽스처 미확보·`pymupdf` 미설치로 보류.
- feature5-B (실제 임베딩·Qdrant·MongoDB 클라이언트): 무거운 의존성 방향 결정 후 진행 — working-log·current-plan에 명시.
- feature9-B (검색·재순위화 노드 오케스트레이션): feature5·Cross-Encoder 모델 확보 후 진행.
- feature11 (Query 그래프 조립·FastAPI 라우트·SSE): Agent 노드 도착 후 통합.
- `space_doc_type_cache` MySQL 캐시 미구현: 문서 분석기 Agent와 연결되는 영역 — feature6.

### 실수 누락이 아니지만 문서 보강이 필요한 항목

- ACL prefix 컨벤션(`space:{key}` 또는 다른 형태)이 BFF JWT `groups`에 어떻게 들어오는지 동결되지 않음 — `docs/api-spec.md` 또는 ADR에 한 줄 명시 권장.
- xlsx의 oversize 단일 행/그룹이 `OVERSIZE_ATOMIC` 등의 상태 코드와 연동되는지 명시 안 됨 — `docs/chunking-strategy.md` §5 또는 working-log 보강.

### 실수 누락 가능성 (확인 필요)

- 없음. 코드/테스트/문서가 working-log의 진행 상황과 일치하며, 작성자 본인이 "보류"라고 적어둔 항목 외에 빠진 영역이 발견되지 않았다.

---

## 7. 우선순위별 개선 제안

### P0 (즉시 수정)

- 없음. 보안 핵심(ACL·서명 책임 분리)과 설계 정합성이 모두 충족된다.

### P1 (다음 PR — 통합 진행 전에 정리하면 비용이 작음)

1. `Settings.samples_dir` ↔ `JsonFixtureSourceAdapter` 기본값 어긋남 해소 — 어댑터 팩토리 도입 또는 Settings에서 제거 (`app/config.py:34`, `app/adapters/json_fixture.py:80`).
2. `_is_valid_acl_filter`에 `should` 절 내부 구조 검사 추가 — `[{ "key": str, "match": dict }, ...]` 형태인지 확인 (`app/query/acl.py:125-134`).
3. `Attachment.download_url` 의미 이중성 — 로컬 경로와 사용자 노출 URL을 분리(예: `local_path` 추가 또는 download_url을 URL로 통일하고 청커는 별도 다운로드 헬퍼 호출) (`app/adapters/json_fixture.py:160`, `chunker/attachment.py:175,292`).

### P2 (여유 시 / 품질 튜닝 단계)

1. xlsx 단일 행·축소 한계(10행) 그룹이 800 초과인 경우 슬라이딩 윈도우 분할 또는 `OVERSIZE_ATOMIC` 기록(`chunker/attachment.py:_group_sheet_rows`).
2. `verifier._token_grounded`/`_NUMBER`의 부분 문자열 매칭 한계 — 워드 경계·Mecab 도입(품질 튜닝 시).
3. `count_tokens`의 PoC 휴리스틱 → SentencePiece 토크나이저로 교체.
4. `chunk_page`/`chunk_attachment`에 `is_acl_missing` 가드 안전망 추가 여부 결정(graph 외부 호출 차단), 또는 working-log에 "graph가 유일한 진입점"으로 명시.
5. `_looks_like_header`의 datetime 셀 오인 보강 — raw value로 type check.
6. `@enforce_acl` 데코레이터의 async 사용 예시 통합 테스트 1건, `extract_principal`의 비-리스트 groups 케이스 테스트 1건, FAQ '?' 답 흡수 회귀 테스트 1건.
7. `ChunkMetadata.doc_type`을 `Union[DocType, AttachmentType]` 또는 `Literal`로 강제하여 정적 타입 검사 강화.
8. `Attachment.download_url`/`samples` ACL prefix 컨벤션을 `docs/api-spec.md` 또는 ADR로 동결.
9. `mysql_uri`처럼 비밀번호 포함 가능 DSN을 운영 전환 시 `SecretStr`로 승급할 항목 표시.
10. `attachment.py:_iter_block_items`의 python-docx 내부 API 접근 — 라이브러리 메이저 업그레이드 시 검증 포인트 명시.

---

> 본 리뷰는 read-only로 진행했으며, 모든 평가는 저장소 루트 `CLAUDE.md`·`app/CLAUDE.md`·`docs/` 및 첨부 기획서·설계서 텍스트와 코드의 대조에 기반합니다. 작성자 working-log에 "보류"로 명시된 항목은 결함으로 보고하지 않았습니다.
