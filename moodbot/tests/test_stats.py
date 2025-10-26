"""
통계 API 테스트
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestStats:
    """통계 조회 테스트"""

    def test_stats_empty(self, client: TestClient, test_user: dict):
        """일기가 없을 때 통계 조회"""
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert data["total_entries"] == 0
        assert "sentiment_counts" in data
        assert "긍정" in data["sentiment_counts"]
        assert "중립" in data["sentiment_counts"]
        assert "부정" in data["sentiment_counts"]
        assert "emotion_distribution" in data

    def test_stats_with_entries(self, client: TestClient, test_user: dict, mock_ai_service):
        """일기가 있을 때 통계 조회"""
        # 로그인
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        # 여러 일기 작성
        diary_texts = [
            "오늘은 정말 행복한 하루였다!",
            "오늘은 그냥 평범한 날이었어.",
            "오늘은 너무 힘들고 슬펐다."
        ]

        for text in diary_texts:
            response = client.post(
                "/api/entries",
                json={"text": text}
            )
            assert response.status_code == 201

        # 통계 조회
        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 3
        assert "sentiment_counts" in data
        assert "emotion_distribution" in data

        # 감정 분포 확인
        emotion_dist = data["emotion_distribution"]
        assert "happiness" in emotion_dist
        assert "sadness" in emotion_dist
        assert "anger" in emotion_dist
        assert "anxiety" in emotion_dist
        assert "calmness" in emotion_dist
        assert "excitement" in emotion_dist

        # 모든 감정 점수가 0-1 범위인지 확인
        for emotion, score in emotion_dist.items():
            assert 0 <= score <= 1

    def test_stats_sentiment_counts(self, client: TestClient, test_user: dict, mock_ai_service):
        """감정 레이블 카운트 검증"""
        # 로그인
        client.post(
            "/api/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )

        # 일기 작성 (mock_ai_service는 항상 긍정 반환)
        for i in range(5):
            client.post(
                "/api/entries",
                json={"text": f"테스트 일기 {i+1}"}
            )

        response = client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        # 감정 레이블이 모두 존재하는지 확인
        sentiment_counts = data["sentiment_counts"]
        assert "긍정" in sentiment_counts
        assert "중립" in sentiment_counts
        assert "부정" in sentiment_counts

        # 총합이 전체 일기 수와 일치하는지 확인
        total_sentiment = sum(sentiment_counts.values())
        assert total_sentiment == data["total_entries"]
