"""
사용자 데이터베이스 관리
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .auth import get_password_hash, verify_password
from .models import User


class UserStorage:
    """SQLite 기반 사용자 저장소"""

    def __init__(self, db_path: str = "diary.db") -> None:
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """사용자 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # diary_entries 테이블에 user_id 컬럼 추가 (존재하지 않을 경우)
            try:
                conn.execute("ALTER TABLE diary_entries ADD COLUMN user_id INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                # 컬럼이 이미 존재하면 무시
                pass

            conn.commit()

    def create_user(self, username: str, email: str, password: str) -> User:
        """새 사용자 생성"""
        hashed_password = get_password_hash(password)
        created_at = datetime.now(timezone.utc)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, hashed_password, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, email, hashed_password, created_at.isoformat()),
            )
            conn.commit()
            user_id = cursor.lastrowid

        return User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=created_at,
        )

    def get_user_by_username(self, username: str) -> Optional[User]:
        """사용자 이름으로 사용자 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                created_at=datetime.fromisoformat(row[4]),
            )

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()

            if row is None:
                return None

            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                created_at=datetime.fromisoformat(row[4]),
            )

    def get_user_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()

            if row is None:
                return None

            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                hashed_password=row[3],
                created_at=datetime.fromisoformat(row[4]),
            )

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user = self.get_user_by_username(username)
        if user is None:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user


# 싱글톤 인스턴스
_user_storage: UserStorage | None = None


def get_user_storage() -> UserStorage:
    """사용자 저장소 인스턴스 반환"""
    global _user_storage
    if _user_storage is None:
        _user_storage = UserStorage()
    return _user_storage
