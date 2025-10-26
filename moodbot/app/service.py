from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .ai_service import AIAnalysisService, get_ai_service
from .database import DiaryStorage, get_storage
from .models import Conversation, DiaryEntry, EmotionScores, Sentiment


class DiaryService:
    """일기 작성 및 AI 분석을 담당하는 서비스 레이어"""

    def __init__(
        self,
        storage: DiaryStorage,
        ai_service: AIAnalysisService,
    ) -> None:
        self.storage = storage
        self.ai_service = ai_service

    async def create_entry(self, text: str, user_id: int = 1) -> Tuple[DiaryEntry, str]:
        """
        일기 작성 + AI 분석
        Returns: (생성된 일기 엔트리, comfort_message)
        """
        # AI 분석
        analysis = await self.ai_service.analyze_diary(text)

        entry = self.storage.create_entry(
            text=text,
            summary=analysis["summary"],
            sentiment=Sentiment(**analysis["sentiment"]),
            emotion_scores=EmotionScores(**analysis["emotion_scores"]),
            primary_emotion=analysis["primary_emotion"],
            comfort_message=analysis["comfort_message"],
            tags=analysis["tags"],
            user_id=user_id,
        )

        # 초기 대화: AI의 comfort_message 추가
        if analysis["comfort_message"]:
            initial_conversation = Conversation(
                role="assistant",
                message=analysis["comfort_message"],
                timestamp=datetime.now(timezone.utc)
            )
            entry.conversations.append(initial_conversation)
            # DB에 대화 저장
            self.storage.update_conversations(
                entry.id,
                entry.conversations,
                datetime.now(timezone.utc)
            )

        return entry, analysis["comfort_message"]

    def get_entry(self, entry_id: int, user_id: Optional[int] = None) -> Optional[DiaryEntry]:
        """특정 일기 조회"""
        return self.storage.get_entry(entry_id, user_id=user_id)

    def list_entries(self, user_id: Optional[int] = None) -> List[DiaryEntry]:
        """모든 일기 목록 (최신순)"""
        return self.storage.list_entries(user_id=user_id)

    async def update_entry(self, entry_id: int, text: str) -> Optional[DiaryEntry]:
        """
        일기 수정 + AI 재분석
        """
        entry = self.storage.get_entry(entry_id)
        if entry is None:
            return None

        # AI 재분석
        analysis = await self.ai_service.analyze_diary(text)

        return self.storage.update_entry(
            entry_id,
            text=text,
            summary=analysis["summary"],
            sentiment=Sentiment(**analysis["sentiment"]),
            emotion_scores=EmotionScores(**analysis["emotion_scores"]),
            primary_emotion=analysis["primary_emotion"],
            tags=analysis["tags"],
        )

    def delete_entry(self, entry_id: int) -> bool:
        """일기 삭제"""
        return self.storage.delete_entry(entry_id)

    async def reply_to_ai(
        self, entry_id: int, user_message: str
    ) -> Optional[Tuple[str, List[Conversation]]]:
        """
        AI 코멘트에 대한 사용자 응답
        Returns: (AI 응답, 전체 대화 목록) 또는 None
        """
        entry = self.storage.get_entry(entry_id)
        if entry is None:
            return None

        # 사용자 메시지를 대화 목록에 추가
        user_conv = Conversation(
            role="user",
            message=user_message,
            timestamp=datetime.now(timezone.utc),
        )
        entry.conversations.append(user_conv)

        # 대화 히스토리를 dict 형태로 변환
        conversation_history = [
            {"role": conv.role, "message": conv.message}
            for conv in entry.conversations
        ]

        # AI 응답 생성
        ai_response = await self.ai_service.generate_followup_response(
            entry.text, conversation_history, user_message
        )

        # AI 응답을 대화 목록에 추가
        ai_conv = Conversation(
            role="assistant",
            message=ai_response,
            timestamp=datetime.now(timezone.utc),
        )
        entry.conversations.append(ai_conv)

        # 대화 목록 저장
        self.storage.update_conversations(
            entry_id, entry.conversations, datetime.now(timezone.utc)
        )

        return ai_response, entry.conversations

    def sentiment_counts(self, user_id: Optional[int] = None) -> dict:
        """감정 레이블별 개수 집계"""
        entries = self.storage.list_entries(user_id=user_id)
        counts = {"긍정": 0, "중립": 0, "부정": 0}
        for entry in entries:
            label = entry.sentiment.label
            if label in counts:
                counts[label] += 1
        return counts

    def emotion_distribution(self, user_id: Optional[int] = None) -> dict:
        """감정별 평균 점수"""
        entries = self.storage.list_entries(user_id=user_id)
        if not entries:
            return {
                "happiness": 0.0,
                "sadness": 0.0,
                "anger": 0.0,
                "anxiety": 0.0,
                "calmness": 0.0,
                "excitement": 0.0,
            }

        total = len(entries)
        sums = {
            "happiness": 0.0,
            "sadness": 0.0,
            "anger": 0.0,
            "anxiety": 0.0,
            "calmness": 0.0,
            "excitement": 0.0,
        }

        for entry in entries:
            sums["happiness"] += entry.emotion_scores.happiness
            sums["sadness"] += entry.emotion_scores.sadness
            sums["anger"] += entry.emotion_scores.anger
            sums["anxiety"] += entry.emotion_scores.anxiety
            sums["calmness"] += entry.emotion_scores.calmness
            sums["excitement"] += entry.emotion_scores.excitement

        return {k: round(v / total, 2) for k, v in sums.items()}


# DI (FastAPI Depends에서 사용)
_service_singleton: DiaryService | None = None


def get_diary_service() -> DiaryService:
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = DiaryService(
            storage=get_storage(),
            ai_service=get_ai_service(),
        )
    return _service_singleton
