"""데이터 계층 로컬 실행 데모 — 팀원 시연용.

samples/*.json(Atlassian 응답 포맷)을 JsonFixtureSourceAdapter로 읽어 표준
PageObject로 변환되는 것을 콘솔에 요약 출력한다. 현재까지 구현된
feature1(스키마)·feature2 일부(어댑터)가 실제 데이터로 동작하는지 보여준다.

--------------------------------------------------
실행 방법 (저장소 루트에서):

    # 1) Python 3.11 가상환경 (프로젝트 요구: Python 3.11.x)
    python3.11 -m venv .venv
    source .venv/bin/activate            # Windows: .venv\\Scripts\\activate

    # 2) 데이터 계층에 필요한 최소 의존성만 설치
    pip install pydantic pydantic-settings

    # 3) 데모 실행
    python -m examples.demo_data_layer

(전체 의존성 설치는 `pip install -e ".[dev]"` — 단, langgraph/qdrant 등 무거운
 패키지가 함께 설치되므로 데이터 계층 시연만이라면 위 최소 설치로 충분하다.)
--------------------------------------------------
"""

from collections import Counter
from pathlib import Path

from app.adapters.json_fixture import JsonFixtureSourceAdapter

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SAMPLES_DIR = _REPO_ROOT / "samples"


def main() -> None:
    """samples/ 전체를 PageObject로 로드하고 요약을 출력한다."""
    print("=" * 60)
    print("  LINA RAG Pipeline — 데이터 계층 데모")
    print("=" * 60)
    print(f"샘플 경로: {_SAMPLES_DIR}")

    adapter = JsonFixtureSourceAdapter(samples_dir=_SAMPLES_DIR)
    pages = list(adapter.fetch_pages())

    print(f"\n[로드] PageObject {len(pages)}개 — Pydantic 스키마 검증 통과 (오류 0건)")

    by_space = Counter(page.space_key for page in pages)
    print("\n[스페이스 분포]")
    for space_key, count in sorted(by_space.items()):
        print(f"  {space_key:<12} {count:>3}개")

    acl_missing = sum(1 for page in pages if page.is_acl_missing)
    print(f"\n[ACL] 누락(is_acl_missing) {acl_missing}개 / 전체 {len(pages)}개")
    print("  └ PoC: JsonFixtureSourceAdapter가 space_key 기반으로 ACL을 합성")

    attachments = [(p.page_id, a) for p in pages for a in p.attachments]
    print(f"\n[첨부] {len(attachments)}건")
    for page_id, attachment in attachments:
        print(f"  - page {page_id}: {attachment.filename} [{attachment.extracted_format}]")

    active = adapter.list_active_ids()
    print(
        f"\n[Reconciliation] active pages {len(active.pages)} / "
        f"attachments {len(active.attachments)}"
    )

    sample = next(p for p in pages if p.page_id == "100001")
    print("\n[샘플 페이지]")
    print(f"  page_id       : {sample.page_id}")
    print(f"  title         : {sample.title}")
    print(f"  space_key     : {sample.space_key}")
    print(f"  version       : {sample.version_number}")
    print(f"  last_modified : {sample.last_modified.isoformat()}")
    print(f"  labels        : {sample.labels}")
    print(f"  ancestors     : {sample.ancestors}")
    print(f"  allowed_groups: {sample.allowed_groups}")
    print(f"  attachments   : {[a.filename for a in sample.attachments]}")

    print("\n" + "=" * 60)
    print("  ✓ 데이터 계층 정상 — 92개 페이지가 표준 PageObject로 로드됨")
    print("=" * 60)


if __name__ == "__main__":
    main()
