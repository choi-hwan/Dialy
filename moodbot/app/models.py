from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class Sentiment:
    label: str
    score: float


@dataclass
class EmotionScores:
    """6가지 감정 점수 (0-10)"""
    happiness: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    anxiety: float = 0.0
    calmness: float = 0.0
    excitement: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "행복": self.happiness,
            "슬픔": self.sadness,
            "분노": self.anger,
            "불안": self.anxiety,
            "평온": self.calmness,
            "흥분": self.excitement,
        }


@dataclass
class User:
    """사용자 정보"""
    id: int
    username: str
    email: str
    hashed_password: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Conversation:
    """사용자와 AI 간의 대화 메시지"""
    role: str  # "user" 또는 "assistant"
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiaryEntry:
    id: int
    text: str
    summary: str
    sentiment: Sentiment
    emotion_scores: EmotionScores
    primary_emotion: str
    user_id: int = 1  # 일기 작성자 ID (기본값 1)
    comfort_message: str = ""  # AI의 대화형 응답
    tags: List[str] = field(default_factory=list)
    conversations: List[Conversation] = field(default_factory=list)  # AI와의 대화 목록
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

