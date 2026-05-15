"""골격 스모크 테스트.

실제 파이프라인 테스트는 docs/ai/workflow.md의 '테스트 우선' 절차에 따라
feature 단위로 추가한다. 이 파일은 패키지 import 가능 여부만 확인한다.
"""


def test_app_package_is_importable() -> None:
    import app

    assert app is not None
