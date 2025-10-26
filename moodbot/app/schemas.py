from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional, Sequence

from pydantic import BaseModel, EmailStr, Field, validator


SentimentLabel = Literal["긍정", "중립", "부정"]


# 인증 관련 스키마

class UserCreate(BaseModel):
    """회원가입 요청"""
    username: str = Field(..., min_length=3, max_length=50, description="사용자 이름")
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., min_length=6, description="비밀번호")


class UserLogin(BaseModel):
    """로그인 요청"""
    username: str = Field(..., description="사용자 이름")
    password: str = Field(..., description="비밀번호")


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: int
    username: str
    email: str
    created_at: datetime


class Token(BaseModel):
    """JWT 토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============ 일기 관련 스키마 ============


class SentimentSchema(BaseModel):
    label: SentimentLabel
    score: float = Field(ge=0.0, le=1.0)


class EmotionScoresSchema(BaseModel):
    """6가지 감정 점수"""
    happiness: float = Field(ge=0.0, le=10.0, description="행복")
    sadness: float = Field(ge=0.0, le=10.0, description="슬픔")
    anger: float = Field(ge=0.0, le=10.0, description="분노")
    anxiety: float = Field(ge=0.0, le=10.0, description="불안")
    calmness: float = Field(ge=0.0, le=10.0, description="평온")
    excitement: float = Field(ge=0.0, le=10.0, description="흥분")


class DiaryEntryCreate(BaseModel):
    """일기 작성 요청"""
    text: str = Field(..., min_length=1, description="일기 내용")


class DiaryEntryUpdate(BaseModel):
    """일기 수정 요청"""
    text: Optional[str] = Field(None, min_length=1, description="일기 내용")


class ConversationSchema(BaseModel):
    """사용자와 AI 간의 대화"""
    role: str = Field(..., description="user 또는 assistant")
    message: str = Field(..., description="메시지 내용")
    timestamp: datetime


class DiaryEntryResponse(BaseModel):
    """일기 응답"""
    id: int
    text: str
    summary: str
    sentiment: SentimentSchema
    emotion_scores: EmotionScoresSchema
    primary_emotion: str
    tags: Sequence[str]
    comfort_message: Optional[str] = Field(None, description="위로 메시지")
    conversations: Sequence[ConversationSchema] = Field(default_factory=list, description="AI와의 대화 목록")
    created_at: datetime
    updated_at: datetime


class EntriesResponse(BaseModel):
    """일기 목록 응답"""
    entries: Sequence[DiaryEntryResponse]


class ReplyToAIRequest(BaseModel):
    """AI 코멘트에 대한 사용자 응답"""
    message: str = Field(..., min_length=1, description="사용자의 응답 메시지")


class ReplyToAIResponse(BaseModel):
    """AI의 답변"""
    ai_response: str = Field(..., description="AI의 답변")
    conversations: Sequence[ConversationSchema] = Field(..., description="업데이트된 대화 목록")


class StatsResponse(BaseModel):
    """통계 응답"""
    total_entries: int
    sentiment_counts: dict[SentimentLabel, int]
    emotion_distribution: Dict[str, float]

    @validator("sentiment_counts")
    def ensure_labels(cls, value: dict[SentimentLabel, int]) -> dict[SentimentLabel, int]:
        for label in ("긍정", "중립", "부정"):
            value.setdefault(label, 0)
        return value
    
    

class DiaryRequest(BaseModel):
    text: str = Field(..., description="사용자의 다이어리 원문 텍스트")

class DiaryResponse(BaseModel):
    result: str = Field(..., description="모델이 생성한 답변")