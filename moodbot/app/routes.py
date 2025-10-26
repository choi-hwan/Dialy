from __future__ import annotations

from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from .models import DiaryEntry
from .schemas import (
    ConversationSchema,
    DiaryEntryCreate,
    DiaryEntryResponse,
    DiaryEntryUpdate,
    EmotionScoresSchema,
    EntriesResponse,
    ReplyToAIRequest,
    ReplyToAIResponse,
    SentimentSchema,
    StatsResponse,
)
from .service import get_diary_service
from .schemas import DiaryRequest, DiaryResponse
from .ai_service import get_ai_service
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .service import DiaryService


router = APIRouter()
api_router = APIRouter(tags=["entries"])


def serialize_entry(entry: DiaryEntry, comfort_message: str = None) -> DiaryEntryResponse:
    """DiaryEntry 모델을 DiaryEntryResponse 스키마로 변환"""
    # comfort_message가 None이면 entry에서 가져오기
    if comfort_message is None:
        comfort_message = entry.comfort_message

    return DiaryEntryResponse(
        id=entry.id,
        text=entry.text,
        summary=entry.summary,
        sentiment=SentimentSchema(
            label=entry.sentiment.label,
            score=entry.sentiment.score,
        ),
        emotion_scores=EmotionScoresSchema(
            happiness=entry.emotion_scores.happiness,
            sadness=entry.emotion_scores.sadness,
            anger=entry.emotion_scores.anger,
            anxiety=entry.emotion_scores.anxiety,
            calmness=entry.emotion_scores.calmness,
            excitement=entry.emotion_scores.excitement,
        ),
        primary_emotion=entry.primary_emotion,
        tags=list(entry.tags),
        comfort_message=comfort_message,
        conversations=[
            ConversationSchema(
                role=conv.role,
                message=conv.message,
                timestamp=conv.timestamp
            )
            for conv in entry.conversations
        ],
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@api_router.post("/entries", response_model=DiaryEntryResponse, status_code=201)
async def create_entry(
    payload: DiaryEntryCreate, service: DiaryService = Depends(get_diary_service)
) -> DiaryEntryResponse:

    entry, comfort_message = await service.create_entry(payload.text)
    return serialize_entry(entry, comfort_message)


@api_router.get("/entries", response_model=EntriesResponse)
async def list_entries(
    service: DiaryService = Depends(get_diary_service),
) -> EntriesResponse:

    entries = [serialize_entry(entry) for entry in service.list_entries()]
    return EntriesResponse(entries=entries)


@api_router.get("/entries/{entry_id}", response_model=DiaryEntryResponse)
async def get_entry(
    entry_id: int, service: DiaryService = Depends(get_diary_service)
) -> DiaryEntryResponse:

    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없습니다.")
    return serialize_entry(entry)


@api_router.put("/entries/{entry_id}", response_model=DiaryEntryResponse)
async def update_entry(
    entry_id: int,
    payload: DiaryEntryUpdate,
    service: DiaryService = Depends(get_diary_service),
) -> DiaryEntryResponse:

    if payload.text is None:
        raise HTTPException(status_code=400, detail="수정할 내용이 없습니다.")

    updated_entry = await service.update_entry(entry_id, payload.text)
    if updated_entry is None:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없습니다.")

    return serialize_entry(updated_entry)


@api_router.delete("/entries/{entry_id}", status_code=204, response_model=None)
async def delete_entry(
    entry_id: int, service: DiaryService = Depends(get_diary_service)
) -> None:

    success = service.delete_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없습니다.")


@api_router.post("/entries/{entry_id}/reply", response_model=ReplyToAIResponse)
async def reply_to_ai(
    entry_id: int,
    payload: ReplyToAIRequest,
    service: DiaryService = Depends(get_diary_service),
) -> ReplyToAIResponse:

    result = await service.reply_to_ai(entry_id, payload.message)
    if result is None:
        raise HTTPException(status_code=404, detail="일기를 찾을 수 없습니다.")

    ai_response, conversations = result
    return ReplyToAIResponse(
        ai_response=ai_response,
        conversations=[
            ConversationSchema(
                role=conv.role,
                message=conv.message,
                timestamp=conv.timestamp
            )
            for conv in conversations
        ]
    )


@api_router.get("/stats", response_model=StatsResponse)
async def stats(service: DiaryService = Depends(get_diary_service)) -> StatsResponse:

    sentiment_counts = service.sentiment_counts()
    entries = service.list_entries()
    emotion_dist = service.emotion_distribution()

    return StatsResponse(
        total_entries=len(entries),
        sentiment_counts=sentiment_counts,
        emotion_distribution=emotion_dist,
    )

@router.post("/ai/diary")
async def generate_diary_reply(request: Request):
    try:
        ct = request.headers.get("content-type", "")
        if "application/json" in ct:
            data = await request.json()
            diary_text = (data or {}).get("text")
        else:
            # form, multipart 등
            form = await request.form()
            diary_text = form.get("text")

        if not diary_text or not diary_text.strip():
            raise HTTPException(status_code=400, detail="text가 비어 있습니다.")

        ai_svc = get_ai_service()
        result = await ai_svc.analyze_diary(diary_text.strip())
        return {"result": result}

    except httpx.HTTPStatusError as e:
        # HF 401/503 등 자세히 넘겨주기
        raise HTTPException(status_code=502, detail=f"HuggingFace API error: {e.response.status_code} {e.response.text[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"server error: {e}")