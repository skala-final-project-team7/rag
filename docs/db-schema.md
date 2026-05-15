# DB Schema (Draft)

> **상태: 초안.** RAG Pipeline 관점에서 사용하는 데이터 구조의 초안이다.
> 실제 컬렉션·필드·인덱스는 Ingestion / Chunking / Embedding 작업의 Plan 확정 시 함께 갱신한다.
> 스키마 변경 시 이 문서를 함께 수정한다(루트 `CLAUDE.md` 규칙).

이 문서는 RAG Pipeline이 사용하는 MongoDB와 Vector DB(Qdrant) 데이터 구조를 정의한다.
사용자/대화/피드백 등 MySQL 정형 데이터는 Backend 담당 영역이며 `docs/architecture.md`를 참고한다.

---

## 1. MongoDB

문서 중심 데이터를 저장한다. (`docs/architecture.md` 6.2 참고)

### 1.1 `documents` — Confluence 원본 문서

| 필드 | 타입 | 설명 |
|---|---|---|
| `_id` | ObjectId | 문서 PK |
| `page_id` | string | Confluence Page ID |
| `space_id` | string | Confluence Space ID |
| `title` | string | 문서 제목 |
| `body` | string | 원본 본문 (HTML/Storage format) |
| `version` | int | Confluence 버전 번호 |
| `acl` | object | 접근 제어: `allowed_groups`, `allowed_users` |
| `updated_at` | datetime | 원본 최종 수정일 |
| `ingested_at` | datetime | 수집 시각 |

- 인덱스: `page_id`(unique), `space_id`, `updated_at`

### 1.2 `chunks` — 청킹 결과

| 필드 | 타입 | 설명 |
|---|---|---|
| `_id` | ObjectId | 청크 PK |
| `document_id` | ObjectId | `documents._id` 참조 |
| `page_id` | string | 출처 Page ID |
| `space_id` | string | 출처 Space ID |
| `chunk_index` | int | 문서 내 청크 순번 |
| `content` | string | 청크 텍스트 |
| `token_count` | int | 청크 토큰 수 |
| `acl` | object | 문서 ACL 복제본 (검색 시 권한 필터용) |
| `created_at` | datetime | 청킹 시각 |

- 인덱스: `document_id`, `page_id`, (`document_id`, `chunk_index`)

### 1.3 `ingestion_jobs` — 수집/동기화 작업 상태

| 필드 | 타입 | 설명 |
|---|---|---|
| `_id` | ObjectId | 작업 PK |
| `type` | string | `ingestion` / `sync` |
| `target` | object | 대상 Space/Page 정보 |
| `status` | string | `pending` / `running` / `done` / `failed` |
| `error` | string | 실패 원인 (실패 시) |
| `created_at` / `updated_at` | datetime | 생성/갱신 시각 |

---

## 2. Vector DB (Qdrant)

청크 임베딩 벡터와 검색 메타데이터를 저장한다. (`docs/architecture.md` 6.3 참고)

### 2.1 Collection: `chunk_embeddings`

| 항목 | 값 / 설명 |
|---|---|
| Vector size | 임베딩 모델 차원 (Plan 확정 시 기입) |
| Distance | Cosine |

Payload 필드:

| 필드 | 타입 | 설명 |
|---|---|---|
| `chunk_id` | string | MongoDB `chunks._id` |
| `document_id` | string | MongoDB `documents._id` |
| `page_id` | string | 출처 Page ID |
| `space_id` | string | 출처 Space ID |
| `allowed_groups` | string[] | ACL pre-filtering 용 |
| `allowed_users` | string[] | ACL pre-filtering 용 |
| `updated_at` | datetime | 출처 문서 최종 수정일 |
| `source_url` | string | 출처 링크 (Citation 표시용) |

- 검색 시 `allowed_groups` / `allowed_users` 기준 ACL pre-filtering을 **반드시** 적용한다.
- 출처 표시를 위해 `source_url`, `page_id`는 항상 payload에 포함한다.

---

## 3. 변경 규칙

- 컬렉션·필드·인덱스 변경 시 이 문서를 함께 수정한다.
- 임베딩 모델/차원 변경은 `chunk_embeddings` 재생성을 동반하므로 Plan에 영향 범위를 명시한다.
- ACL 관련 필드는 권한 필터링 정확도와 직결되므로 임의로 제거하지 않는다.
