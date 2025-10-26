"""
pytest 설정 및 공통 픽스처
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.database import DiaryStorage
from app.user_db import UserStorage


@pytest.fixture(scope="function")
def test_db_path() -> Generator[str, None, None]:
    """테스트용 임시 데이터베이스 경로"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # 테스트 후 삭제
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def diary_storage(test_db_path: str) -> DiaryStorage:
    """테스트용 DiaryStorage 인스턴스"""
    storage = DiaryStorage(db_path=test_db_path)
    return storage


@pytest.fixture(scope="function")
def user_storage(test_db_path: str) -> UserStorage:
    """테스트용 UserStorage 인스턴스"""
    storage = UserStorage(db_path=test_db_path)
    return storage


@pytest.fixture(scope="function")
def client(test_db_path: str, monkeypatch) -> TestClient:
    """테스트용 FastAPI 클라이언트"""
    # 테스트용 DB 경로로 변경
    def mock_create_app():
        # DiaryStorage와 UserStorage가 test_db_path를 사용하도록 설정
        DiaryStorage._instances = {}
        UserStorage._instances = {}

        app = create_app()

        # 테스트용 DB 경로 설정
        from app.database import DiaryStorage as DS
        from app.user_db import UserStorage as US

        DS._instances[test_db_path] = DS(db_path=test_db_path)
        US._instances[test_db_path] = US(db_path=test_db_path)

        return app

    app = mock_create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(user_storage: UserStorage) -> dict:
    """테스트용 사용자 생성"""
    user = user_storage.create_user(
        username="testuser",
        email="test@example.com",
        password="password123"
    )
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password": "password123"  # 원본 비밀번호 저장
    }


@pytest.fixture
def auth_headers(client: TestClient, test_user: dict) -> dict:
    """인증 헤더 생성"""
    response = client.post(
        "/api/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_ai_service(monkeypatch):
    """AI 서비스 모킹 (실제 모델 로드 방지)"""
    from app import ai_service

    class MockAIService:
        async def analyze_diary(self, diary_text: str) -> dict:
            """모의 일기 분석"""
            return {
                "summary": "테스트 일기 요약",
                "sentiment": {"label": "긍정", "score": 0.8},
                "emotion_scores": {
                    "happiness": 0.8,
                    "sadness": 0.1,
                    "anger": 0.0,
                    "anxiety": 0.1,
                    "calmness": 0.5,
                    "excitement": 0.6
                },
                "primary_emotion": "행복",
                "comfort_message": "좋은 하루 보내셨네요! 계속 행복한 일들이 가득하길 바랍니다.",
                "tags": ["테스트", "행복"]
            }

        async def generate_followup_response(
            self,
            diary_text: str,
            conversation_history: list,
            user_message: str
        ) -> str:
            """모의 대화 응답"""
            return "감사합니다. 언제든 이야기 나눠요!"

    mock_service = MockAIService()
    monkeypatch.setattr(ai_service, "ai_service", mock_service)
    return mock_service


@pytest.fixture
def sample_diary_entry(client: TestClient, test_user: dict, mock_ai_service) -> dict:
    """샘플 일기 엔트리 생성"""
    # 먼저 로그인
    login_response = client.post(
        "/api/auth/login",
        json={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )

    # 일기 작성
    response = client.post(
        "/api/entries",
        json={"text": "오늘은 정말 좋은 하루였다!"}
    )
    assert response.status_code == 201
    return response.json()
