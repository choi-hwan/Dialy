"""
일기 작성 엔드포인트와 AI 파이프라인 테스트
"""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestEntryCreationPipeline:
    """일기 작성 및 AI 분석 파이프라인 테스트"""

    def test_create_entry_api_success(self, client: TestClient, mock_ai_service):

        diary_text = "오늘은 정말 행복한 하루였어요. 친구들과 즐거운 시간을 보냈어요."

        response = client.post(
            "/api/entries",
            json={"text": diary_text}
        )

        # 1. HTTP 상태 확인
        assert response.status_code == 201

        # 2. 응답 데이터 검증
        data = response.json()

        # 기본 필드 확인
        assert "id" in data
        assert data["text"] == diary_text
        assert "summary" in data
        assert len(data["summary"]) > 0

        # 3. AI 분석 결과 검증 - sentiment
        assert "sentiment" in data
        assert data["sentiment"]["label"] in ["긍정", "중립", "부정"]
        assert 0 <= data["sentiment"]["score"] <= 1

        # 4. AI 분석 결과 검증 - emotion_scores
        assert "emotion_scores" in data
        emotion_scores = data["emotion_scores"]
        assert "happiness" in emotion_scores
        assert "sadness" in emotion_scores
        assert "anger" in emotion_scores
        assert "anxiety" in emotion_scores
        assert "calmness" in emotion_scores
        assert "excitement" in emotion_scores

        # 모든 감정 점수가 0~1 범위인지 확인
        for score in emotion_scores.values():
            assert 0 <= score <= 1

        # 5. primary_emotion 확인
        assert data["primary_emotion"] in ["행복", "슬픔", "분노", "불안", "평온", "흥분"]

        # 6. comfort_message 확인
        assert "comfort_message" in data
        assert len(data["comfort_message"]) > 0

        # 7. tags 확인
        assert "tags" in data
        assert isinstance(data["tags"], list)

        # 8. 타임스탬프 확인
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_entry_api_empty_text(self, client: TestClient):
        """
        POST /api/entries - 빈 텍스트로 일기 작성 시 에러
        """
        response = client.post(
            "/api/entries",
            json={"text": ""}
        )

        # 빈 텍스트는 에러 발생 (422 Unprocessable Entity)
        assert response.status_code in [400, 422]

    def test_create_entry_api_missing_field(self, client: TestClient):
        """
        POST /api/entries - text 필드 누락 시 에러
        """
        response = client.post(
            "/api/entries",
            json={}
        )

        # 필수 필드 누락 에러
        assert response.status_code == 422

    def test_pipeline_ai_analysis_integration(self, client: TestClient, mock_ai_service):

        diary_text = "시험에서 좋은 성적을 받아서 기분이 좋아요!"

        # 1. 일기 작성
        create_response = client.post(
            "/api/entries",
            json={"text": diary_text}
        )
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # 2. 작성된 일기 조회
        get_response = client.get(f"/api/entries/{entry_id}")
        assert get_response.status_code == 200

        # 3. 저장된 분석 결과 확인
        entry_data = get_response.json()
        assert entry_data["text"] == diary_text
        assert entry_data["sentiment"]["label"] in ["긍정", "중립", "부정"]
        assert entry_data["primary_emotion"] in ["행복", "슬픔", "분노", "불안", "평온", "흥분"]
        assert "comfort_message" in entry_data
        assert len(entry_data["comfort_message"]) > 0

    def test_pipeline_multiple_entries(self, client: TestClient, mock_ai_service):
        
        entries_text = [
            "오늘은 행복한 날이었어요.",
            "내일은 더 좋을 거예요.",
            "새로운 도전을 시작했습니다."
        ]

        created_ids = []

        # 여러 일기 작성
        for text in entries_text:
            response = client.post(
                "/api/entries",
                json={"text": text}
            )
            assert response.status_code == 201
            created_ids.append(response.json()["id"])

        # 모든 일기가 개별적으로 저장되었는지 확인
        assert len(created_ids) == len(entries_text)
        assert len(set(created_ids)) == len(entries_text)  # 중복 없음

    def test_pipeline_conversations_initialization(self, client: TestClient, mock_ai_service):
        
        response = client.post(
            "/api/entries",
            json={"text": "새로운 일기를 작성합니다."}
        )

        assert response.status_code == 201
        data = response.json()

        # conversations 필드 확인
        assert "conversations" in data
        conversations = data["conversations"]

        # 초기에는 AI의 첫 메시지만 있어야 함
        assert len(conversations) == 1
        assert conversations[0]["role"] == "assistant"
        assert conversations[0]["message"] == data["comfort_message"]

    def test_pipeline_data_persistence(self, client: TestClient, mock_ai_service):
      
        diary_text = "데이터 영속성 테스트"

        # 1. 일기 작성
        create_response = client.post(
            "/api/entries",
            json={"text": diary_text}
        )
        entry_id = create_response.json()["id"]

        # 2. 일기 목록에서 확인
        list_response = client.get("/api/entries")
        assert list_response.status_code == 200

        entries = list_response.json()["entries"]
        found = False
        for entry in entries:
            if entry["id"] == entry_id:
                found = True
                assert entry["text"] == diary_text
                break

        assert found, "작성한 일기가 목록에 없습니다"
