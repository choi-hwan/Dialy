"""
인증 관련 API 라우터
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from .auth import create_access_token
from .schemas import Token, UserCreate, UserLogin, UserResponse
from .user_db import UserStorage, get_user_storage

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate, user_storage: UserStorage = Depends(get_user_storage)
) -> Token:
 
    # 중복 확인
    existing_user = user_storage.get_user_by_username(user_data.username)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 사용자 이름입니다.",
        )

    existing_email = user_storage.get_user_by_email(user_data.email)
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다.",
        )

    # 사용자 생성
    user = user_storage.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
    )

    # JWT 토큰 생성 (sub는 문자열이어야 함)
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

    return Token(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )


@auth_router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin, user_storage: UserStorage = Depends(get_user_storage)
) -> Token:
    """
    로그인

    - **username**: 사용자 이름
    - **password**: 비밀번호
    """
    user = user_storage.authenticate_user(login_data.username, login_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자 이름 또는 비밀번호가 올바르지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWT 토큰 생성 (sub는 문자열이어야 함)
    access_token = create_access_token(data={"sub": str(user.id), "username": user.username})

    return Token(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )
