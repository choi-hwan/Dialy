from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth_routes import auth_router
from .database import DiaryStorage
from .routes import api_router
from .settings import settings
from .user_db import UserStorage
from .web import web_router


def create_app() -> FastAPI:
    # 데이터베이스 초기화 (moodbot 디렉토리에 저장)
    db_path = Path(__file__).parent.parent / "diary.db"
    DiaryStorage(db_path=str(db_path))
    UserStorage(db_path=str(db_path))

    app = FastAPI(
        title="MoodBot",
        version="0.1.0",
        description="AI 기반 감정 분석 일기 서비스",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS 미들웨어 추가 (환경변수로 제어)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
        expose_headers=settings.cors_expose_headers,
        max_age=settings.cors_max_age,
    )

    # CORS 설정 로깅
    print(f"CORS 설정 - Origins: {settings.cors_origins}")
    print(f"CORS 설정 - Credentials: {settings.cors_allow_credentials}")
    print(f"CORS 설정 - Methods: {settings.cors_allow_methods}")
    print(f"CORS 설정 - Headers: {settings.cors_allow_headers}")

    # 라우터 등록
    app.include_router(auth_router, prefix="/api")
    app.include_router(api_router, prefix="/api")
    app.include_router(web_router)

    # 정적 파일 서빙
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app


app = create_app()


# 헬스체크
@app.get("/health")
async def health():
    return {"ok": True}