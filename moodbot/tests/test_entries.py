"""
일기 API 테스트
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestCreateEntry:
    """일기 작성 테스트"""

    def test_create_entry_success(self, client: TestClient, test_user: dict, mock_ai_service):
        """정상적인 일기 작성"""
        # 로그인
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.post(
            "/api/entries",
            json={"text": "오늘은 정말 행복한 하루였다!"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "오늘은 정말 행복한 하루였다!"
        assert "summary" in data
        assert "sentiment" in data
        assert data["sentiment"]["label"] in ["긍정", "중립", "부정"]
        assert 0 <= data["sentiment"]["score"] <= 1
        assert "emotion_scores" in data
        assert "primary_emotion" in data
        assert "tags" in data
        assert isinstance(data["tags"], list)
        assert "comfort_message" in data
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_entry_empty_text(self, client: TestClient, test_user: dict):
        """빈 텍스트로 일기 작성 시도"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.post(
            "/api/entries",
            json={"text": ""}
        )

        assert response.status_code == 422  # Validation Error

    def test_create_entry_missing_text(self, client: TestClient, test_user: dict):
        """텍스트 필드 누락"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.post(
            "/api/entries",
            json={}
        )

        assert response.status_code == 422  # Validation Error


class TestListEntries:
    """일기 목록 조회 테스트"""

    def test_list_entries_empty(self, client: TestClient, test_user: dict, mock_ai_service):
        """일기가 없을 때 목록 조회"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.get("/api/entries")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert isinstance(data["entries"], list)

    def test_list_entries_with_data(self, client: TestClient, test_user: dict, mock_ai_service):
        """일기가 있을 때 목록 조회"""
        # 로그인
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        # 일기 3개 작성
        for i in range(3):
            client.post(
                "/api/entries",
                json={"text": f"테스트 일기 {i+1}"}
            )

        response = client.get("/api/entries")

        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert len(data["entries"]) == 3


class TestGetEntry:
    """일기 상세 조회 테스트"""

    def test_get_entry_success(self, client: TestClient, sample_diary_entry: dict):
        """정상적인 일기 조회"""
        entry_id = sample_diary_entry["id"]

        response = client.get(f"/api/entries/{entry_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert "text" in data
        assert "summary" in data
        assert "sentiment" in data
        assert "emotion_scores" in data

    def test_get_entry_not_found(self, client: TestClient, test_user: dict):
        """존재하지 않는 일기 조회"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.get("/api/entries/99999")

        assert response.status_code == 404
        assert "일기를 찾을 수 없습니다" in response.json()["detail"]


class TestUpdateEntry:
    """일기 수정 테스트"""

    def test_update_entry_success(self, client: TestClient, sample_diary_entry: dict, mock_ai_service):
        """정상적인 일기 수정"""
        entry_id = sample_diary_entry["id"]

        response = client.put(
            f"/api/entries/{entry_id}",
            json={"text": "수정된 일기 내용입니다."}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == entry_id
        assert data["text"] == "수정된 일기 내용입니다."
        # AI 재분석이 수행되어야 함
        assert "summary" in data
        assert "sentiment" in data

    def test_update_entry_not_found(self, client: TestClient, test_user: dict):
        """존재하지 않는 일기 수정"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.put(
            "/api/entries/99999",
            json={"text": "수정된 내용"}
        )

        assert response.status_code == 404

    def test_update_entry_empty_text(self, client: TestClient, sample_diary_entry: dict):
        """빈 텍스트로 수정 시도"""
        entry_id = sample_diary_entry["id"]

        response = client.put(
            f"/api/entries/{entry_id}",
            json={"text": None}
        )

        assert response.status_code == 400
        assert "수정할 내용이 없습니다" in response.json()["detail"]


class TestDeleteEntry:
    """일기 삭제 테스트"""

    def test_delete_entry_success(self, client: TestClient, sample_diary_entry: dict):
        """정상적인 일기 삭제"""
        entry_id = sample_diary_entry["id"]

        response = client.delete(f"/api/entries/{entry_id}")

        assert response.status_code == 204

        # 삭제 확인
        get_response = client.get(f"/api/entries/{entry_id}")
        assert get_response.status_code == 404

    def test_delete_entry_not_found(self, client: TestClient, test_user: dict):
        """존재하지 않는 일기 삭제"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.delete("/api/entries/99999")

        assert response.status_code == 404


class TestReplyToAI:
    """AI 대화 테스트"""

    def test_reply_to_ai_success(self, client: TestClient, sample_diary_entry: dict, mock_ai_service):
        """정상적인 AI 대화"""
        entry_id = sample_diary_entry["id"]

        response = client.post(
            f"/api/entries/{entry_id}/reply",
            json={"message": "고마워요!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
        assert len(data["conversations"]) >= 2  # user + assistant

        # 대화 내용 확인
        conversations = data["conversations"]
        assert conversations[-2]["role"] == "user"
        assert conversations[-2]["message"] == "고마워요!"
        assert conversations[-1]["role"] == "assistant"
        assert "timestamp" in conversations[-1]

    def test_reply_to_ai_not_found(self, client: TestClient, test_user: dict):
        """존재하지 않는 일기에 대화 시도"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.post(
            "/api/entries/99999/reply",
            json={"message": "안녕하세요"}
        )

        assert response.status_code == 404

    def test_reply_to_ai_empty_message(self, client: TestClient, sample_diary_entry: dict):
        """빈 메시지로 대화 시도"""
        entry_id = sample_diary_entry["id"]

        response = client.post(
            f"/api/entries/{entry_id}/reply",
            json={"message": ""}
        )

        assert response.status_code == 422  # Validation Error
