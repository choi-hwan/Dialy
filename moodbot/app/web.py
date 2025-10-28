# app/web.py
from __future__ import annotations  # ← 파일 맨 첫 줄

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status, Cookie, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import EmailStr

from .auth import create_access_token, decode_access_token
from typing import Optional as Opt
from .models import DiaryEntry
from .service import DiaryService, get_diary_service
from .user_db import UserStorage, get_user_storage


templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

web_router = APIRouter()


def serialize(entry: DiaryEntry) -> dict:
    return {
        "id": entry.id,
        "text": entry.text,
        "summary": entry.summary,
        "sentiment": entry.sentiment,
        "tags": entry.tags,
        "comfort_message": entry.comfort_message,  # AI 코멘트 추가
        "conversations": entry.conversations,  # 대화 목록 추가
        "created_at": entry.created_at,
    }


def get_user_id_from_cookie(request: Request) -> Opt[int]:
    """쿠키에서 사용자 ID 가져오기"""
    token = request.cookies.get("access_token")
    if not token:
        print("DEBUG: No access_token cookie found")
        print(f"DEBUG: Available cookies: {list(request.cookies.keys())}")
        return None
    print(f"DEBUG: Token found: {token[:50]}...")
    payload = decode_access_token(token)
    if not payload:
        print("DEBUG: Failed to decode token")
        print(f"DEBUG: Token value: {token}")
        # Try to decode manually to see the error
        try:
            from jose import jwt, JWTError
            from .auth import SECRET_KEY, ALGORITHM
            test_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            print(f"DEBUG: Manual decode succeeded: {test_payload}")
        except JWTError as e:
            print(f"DEBUG: Manual decode error: {e}")
        return None
    # sub는 문자열로 저장되므로 정수로 변환
    user_id_str = payload.get("sub")
    if not user_id_str:
        print("DEBUG: No 'sub' in payload")
        return None
    try:
        user_id = int(user_id_str)
        print(f"DEBUG: User ID from cookie: {user_id}")
        return user_id
    except (ValueError, TypeError) as e:
        print(f"DEBUG: Failed to convert user_id to int: {e}")
        return None


@web_router.get("/", response_class=HTMLResponse)
async def index(
    request: Request, service: DiaryService = Depends(get_diary_service)
) -> HTMLResponse:
    user_id = get_user_id_from_cookie(request)
    print(f"DEBUG [index]: user_id={user_id}")
    entries = [serialize(entry) for entry in service.list_entries(user_id=user_id)[:5]]
    print(f"DEBUG [index]: Found {len(entries)} entries for user_id={user_id}")
    stats = service.sentiment_counts(user_id=user_id)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "entries": entries,
            "stats": stats,
        },
    )


@web_router.get("/entries", response_class=HTMLResponse)
async def entries_page(
    request: Request, service: DiaryService = Depends(get_diary_service)
) -> HTMLResponse:
    user_id = get_user_id_from_cookie(request)
    print(f"DEBUG [entries_page]: user_id={user_id}")
    entries = [serialize(entry) for entry in service.list_entries(user_id=user_id)]
    print(f"DEBUG [entries_page]: Found {len(entries)} entries for user_id={user_id}")
    for entry in entries[:3]:  # Log first 3 entries
        print(f"DEBUG [entries_page]: Entry {entry['id']} belongs to user_id (from entry data): N/A")
    return templates.TemplateResponse(
        "entries.html",
        {
            "request": request,
            "entries": entries,
        },
    )


@web_router.get("/stats", response_class=HTMLResponse)
async def stats_page(
    request: Request, service: DiaryService = Depends(get_diary_service)
) -> HTMLResponse:
    user_id = get_user_id_from_cookie(request)
    sentiment_counts = service.sentiment_counts(user_id=user_id)
    emotion_distribution = service.emotion_distribution(user_id=user_id)
    all_entries = service.list_entries(user_id=user_id)
    total_entries = len(all_entries)

    # 최근 7개 일기 데이터 (시간순)
    recent_entries = all_entries[:7]
    timeline_data = []
    for entry in reversed(recent_entries):  # 오래된 것부터 표시
        # sentiment가 중립이면 0점으로 설정
        if entry.sentiment.label == "중립":
            primary_score = 0.0
        else:
            # primary_emotion에 해당하는 점수 가져오기
            emotion_mapping = {
                "행복": entry.emotion_scores.happiness,
                "슬픔": entry.emotion_scores.sadness,
                "분노": entry.emotion_scores.anger,
                "불안": entry.emotion_scores.anxiety,
                "평온": entry.emotion_scores.calmness,
                "흥분": entry.emotion_scores.excitement,
            }
            raw_score = emotion_mapping.get(entry.primary_emotion, 0)

            # 감정을 양수/음수로 변환 (-1.0 ~ 1.0)
            # 긍정 감정: 양수 (+), 부정 감정: 음수 (-)
            if entry.primary_emotion in ["행복", "평온", "흥분"]:
                primary_score = raw_score  # 0.0 ~ 1.0 유지
            else:  # 슬픔, 분노, 불안
                primary_score = -raw_score  # -1.0 ~ 0.0

        timeline_data.append({
            "date": entry.created_at.strftime("%m/%d %H:%M"),
            "sentiment": entry.sentiment.label,
            "primary_emotion": entry.primary_emotion,
            "primary_score": primary_score,
        })

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "sentiment_counts": sentiment_counts,
            "emotion_distribution": emotion_distribution,
            "total_entries": total_entries,
            "timeline_data": timeline_data,
        },
    )


@web_router.post("/entries", response_class=HTMLResponse)
async def submit_entry(
    request: Request,
    text: str = Form(...),
    service: DiaryService = Depends(get_diary_service)
) -> RedirectResponse:
    user_id = get_user_id_from_cookie(request)
    print(f"DEBUG [submit_entry]: Extracted user_id={user_id}")
    if not user_id:
        # 로그인하지 않은 경우 기본 사용자 ID 사용
        user_id = 1
        print(f"DEBUG [submit_entry]: No user_id found, using default user_id={user_id}")
    print(f"DEBUG [submit_entry]: Creating entry with user_id={user_id}, text='{text[:50]}'")
    await service.create_entry(text, user_id=user_id)
    return RedirectResponse(url="/entries", status_code=status.HTTP_303_SEE_OTHER)


@web_router.post("/entries/{entry_id}/reply", response_class=HTMLResponse)
async def reply_to_ai(
    entry_id: int,
    message: str = Form(...),
    service: DiaryService = Depends(get_diary_service)
) -> RedirectResponse:
    """AI 코멘트에 대한 사용자 응답 처리"""
    await service.reply_to_ai(entry_id, message)
    return RedirectResponse(url="/entries", status_code=status.HTTP_303_SEE_OTHER)


@web_router.post("/entries/{entry_id}/delete", response_class=HTMLResponse)
async def delete_entry_web(
    request: Request,
    entry_id: int,
    service: DiaryService = Depends(get_diary_service)
) -> RedirectResponse:
    """일기 삭제 (사용자 권한 확인 포함)"""
    user_id = get_user_id_from_cookie(request)
    print(f"DEBUG [delete_entry]: user_id={user_id}, entry_id={entry_id}")

    if not user_id:
        # 로그인하지 않은 경우
        print(f"DEBUG [delete_entry]: No user_id, redirecting to login")
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    # 해당 일기가 현재 사용자의 것인지 확인
    entry = service.get_entry(entry_id, user_id=user_id)
    if not entry:
        print(f"DEBUG [delete_entry]: Entry not found or user {user_id} doesn't own entry {entry_id}")
        # 일기가 없거나 다른 사용자의 일기인 경우
        return RedirectResponse(url="/entries?error=not_found", status_code=status.HTTP_303_SEE_OTHER)

    # 삭제 수행
    success = service.delete_entry(entry_id)
    print(f"DEBUG [delete_entry]: Delete success={success}")

    if success:
        return RedirectResponse(url="/entries?success=deleted", status_code=status.HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(url="/entries?error=delete_failed", status_code=status.HTTP_303_SEE_OTHER)


# ============ 인증 관련 웹 라우트 ============


@web_router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    """로그인 페이지"""
    error_message = None
    if request.query_params.get("error") == "invalid_credentials":
        error_message = "아이디/비밀번호 입력이 잘못되었습니다."
    return templates.TemplateResponse("login.html", {"request": request, "error": error_message})


@web_router.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    user_storage: UserStorage = Depends(get_user_storage),
) -> RedirectResponse:
    """로그인 처리"""
    user = user_storage.authenticate_user(username, password)

    if user is None:
        # 로그인 실패 - 에러 메시지와 함께 로그인 페이지로
        return RedirectResponse(
            url="/login?error=invalid_credentials", status_code=status.HTTP_303_SEE_OTHER
        )

    # JWT 토큰 생성 (sub는 문자열이어야 함)
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

    # 쿠키에 토큰 저장
    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7일
        samesite="lax",
    )

    return redirect


@web_router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    """회원가입 페이지"""
    return templates.TemplateResponse("register.html", {"request": request})


@web_router.post("/register")
async def register(
    response: Response,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    user_storage: UserStorage = Depends(get_user_storage),
) -> RedirectResponse:
    """회원가입 처리"""
    # 중복 확인
    existing_user = user_storage.get_user_by_username(username)
    if existing_user is not None:
        return RedirectResponse(
            url="/register?error=username_exists", status_code=status.HTTP_303_SEE_OTHER
        )

    existing_email = user_storage.get_user_by_email(email)
    if existing_email is not None:
        return RedirectResponse(
            url="/register?error=email_exists", status_code=status.HTTP_303_SEE_OTHER
        )

    # 사용자 생성
    user = user_storage.create_user(username=username, email=email, password=password)

    # JWT 토큰 생성 (sub는 문자열이어야 함)
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

    # 쿠키에 토큰 저장하고 홈으로 리다이렉트
    redirect = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,  # 7일
        samesite="lax",
    )

    return redirect


@web_router.get("/logout")
async def logout() -> RedirectResponse:
    """로그아웃"""
    redirect = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    redirect.delete_cookie(key="access_token")
    return redirect

