"""
데이터 모델 및 서비스 레이어 테스트
"""
from __future__ import annotations

from datetime import datetime

import pytest

from app.models import Conversation, DiaryEntry, EmotionScores, Sentiment, User


class TestModels:
    """데이터 모델 테스트"""

    def test_sentiment_model(self):
        """Sentiment 모델 생성"""
        sentiment = Sentiment(label="긍정", score=0.8)

        assert sentiment.label == "긍정"
        assert sentiment.score == 0.8

    def test_emotion_scores_model(self):
        """EmotionScores 모델 생성"""
        scores = EmotionScores(
            happiness=0.8,
            sadness=0.1,
            anger=0.0,
            anxiety=0.2,
            calmness=0.5,
            excitement=0.6
        )

        assert scores.happiness == 0.8
        assert scores.sadness == 0.1

        # to_dict 메소드 테스트
        scores_dict = scores.to_dict()
        assert "행복" in scores_dict
        assert scores_dict["행복"] == 0.8

    def test_user_model(self):
        """User 모델 생성"""
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pw"
        )

        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert isinstance(user.created_at, datetime)

    def test_conversation_model(self):
        """Conversation 모델 생성"""
        conv = Conversation(
            role="user",
            message="안녕하세요!"
        )

        assert conv.role == "user"
        assert conv.message == "안녕하세요!"
        assert isinstance(conv.timestamp, datetime)

    def test_diary_entry_model(self):
        """DiaryEntry 모델 생성"""
        entry = DiaryEntry(
            id=1,
            text="테스트 일기",
            summary="요약",
            sentiment=Sentiment(label="긍정", score=0.8),
            emotion_scores=EmotionScores(),
            primary_emotion="행복",
            user_id=1,
            comfort_message="위로 메시지",
            tags=["태그1", "태그2"],
            conversations=[]
        )

        assert entry.id == 1
        assert entry.text == "테스트 일기"
        assert entry.sentiment.label == "긍정"
        assert entry.user_id == 1
        assert len(entry.tags) == 2
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)


class TestDiaryService:
    """DiaryService 테스트"""

    def test_create_entry(self, diary_storage, mock_ai_service):
        """일기 생성 테스트"""
        from app.service import DiaryService

        service = DiaryService(storage=diary_storage)

        # 일기 작성 (비동기 함수이므로 pytest-asyncio 필요)
        import asyncio
        entry, comfort_message = asyncio.run(
            service.create_entry("테스트 일기 내용", user_id=1)
        )

        assert entry is not None
        assert entry.text == "테스트 일기 내용"
        assert entry.user_id == 1

    def test_list_entries(self, diary_storage):
        """일기 목록 조회 테스트"""
        from app.service import DiaryService

        service = DiaryService(storage=diary_storage)

        entries = service.list_entries(user_id=1)
        assert isinstance(entries, list)

    def test_get_entry(self, diary_storage):
        """일기 조회 테스트"""
        from app.service import DiaryService

        service = DiaryService(storage=diary_storage)

        # 존재하지 않는 일기
        entry = service.get_entry(999, user_id=1)
        assert entry is None

    def test_delete_entry(self, diary_storage):
        """일기 삭제 테스트"""
        from app.service import DiaryService

        service = DiaryService(storage=diary_storage)

        # 존재하지 않는 일기 삭제
        result = service.delete_entry(999)
        assert result is False

    def test_sentiment_counts(self, diary_storage):
        """감정 통계 테스트"""
        from app.service import DiaryService

        service = DiaryService(storage=diary_storage)

        counts = service.sentiment_counts(user_id=1)
        assert isinstance(counts, dict)
        assert "긍정" in counts
        assert "중립" in counts
        assert "부정" in counts


class TestUserStorage:
    """UserStorage 테스트"""

    def test_create_user(self, user_storage):
        """사용자 생성"""
        user = user_storage.create_user(
            username="newuser",
            email="new@example.com",
            password="password123"
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.hashed_password != "password123"  # 해싱되어야 함

    def test_get_user_by_username(self, user_storage):
        """사용자 이름으로 조회"""
        # 사용자 생성
        user_storage.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        # 조회
        user = user_storage.get_user_by_username("testuser")
        assert user is not None
        assert user.username == "testuser"

        # 존재하지 않는 사용자
        user = user_storage.get_user_by_username("nonexistent")
        assert user is None

    def test_get_user_by_email(self, user_storage):
        """이메일로 조회"""
        # 사용자 생성
        user_storage.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        # 조회
        user = user_storage.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

        # 존재하지 않는 이메일
        user = user_storage.get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_authenticate_user(self, user_storage):
        """사용자 인증"""
        # 사용자 생성
        user_storage.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

        # 올바른 인증
        user = user_storage.authenticate_user("testuser", "password123")
        assert user is not None
        assert user.username == "testuser"

        # 잘못된 비밀번호
        user = user_storage.authenticate_user("testuser", "wrongpassword")
        assert user is None

        # 존재하지 않는 사용자
        user = user_storage.authenticate_user("nonexistent", "password123")
        assert user is None
