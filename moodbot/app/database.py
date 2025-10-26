from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Iterable, List, Optional

from .models import Conversation, DiaryEntry, EmotionScores, Sentiment


class DiaryStorage:
    """SQLite-based persistent storage for diary entries."""

    def __init__(self, db_path: str = "diary.db") -> None:
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """데이터베이스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS diary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    sentiment_label TEXT NOT NULL,
                    sentiment_score REAL NOT NULL,
                    emotion_happiness REAL NOT NULL,
                    emotion_sadness REAL NOT NULL,
                    emotion_anger REAL NOT NULL,
                    emotion_anxiety REAL NOT NULL,
                    emotion_calmness REAL NOT NULL,
                    emotion_excitement REAL NOT NULL,
                    primary_emotion TEXT NOT NULL,
                    comfort_message TEXT DEFAULT '',
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # 기존 테이블에 comfort_message 컬럼 추가 (존재하지 않을 경우)
            try:
                conn.execute("ALTER TABLE diary_entries ADD COLUMN comfort_message TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                # 컬럼이 이미 존재하면 무시
                pass

            # 기존 테이블에 conversations 컬럼 추가 (존재하지 않을 경우)
            try:
                conn.execute("ALTER TABLE diary_entries ADD COLUMN conversations TEXT DEFAULT '[]'")
            except sqlite3.OperationalError:
                # 컬럼이 이미 존재하면 무시
                pass

            # 기존 테이블에 user_id 컬럼 추가 (존재하지 않을 경우)
            try:
                conn.execute("ALTER TABLE diary_entries ADD COLUMN user_id INTEGER DEFAULT 1")
            except sqlite3.OperationalError:
                # 컬럼이 이미 존재하면 무시
                pass
            conn.commit()

    def _row_to_entry(self, row: tuple) -> DiaryEntry:
        """데이터베이스 행을 DiaryEntry 객체로 변환"""
        # 현재 스키마: id, text, summary, sentiment_label, sentiment_score,
        # emotion_happiness, emotion_sadness, emotion_anger, emotion_anxiety, emotion_calmness, emotion_excitement,
        # primary_emotion, comfort_message, tags, created_at, updated_at, conversations, user_id

        # conversations 파싱 (인덱스 16)
        conversations = []
        if len(row) > 16 and row[16]:
            try:
                conversations_data = json.loads(row[16])
                conversations = [
                    Conversation(
                        role=conv["role"],
                        message=conv["message"],
                        timestamp=datetime.fromisoformat(conv["timestamp"])
                    )
                    for conv in conversations_data
                ]
            except (json.JSONDecodeError, KeyError, TypeError):
                conversations = []

        # user_id 파싱 (인덱스 17)
        user_id = row[17] if len(row) > 17 and row[17] is not None else 1

        # sentiment label 정리 (공백 제거 및 영어->한국어 변환)
        sentiment_label = (row[3] or "중립").strip()
        label_mapping = {
            "positive": "긍정",
            "negative": "부정",
            "neutral": "중립",
        }
        sentiment_label = label_mapping.get(sentiment_label.lower(), sentiment_label)
        if sentiment_label not in ["긍정", "중립", "부정"]:
            sentiment_label = "중립"

        return DiaryEntry(
            id=row[0],
            text=row[1],
            summary=row[2],
            sentiment=Sentiment(label=sentiment_label, score=row[4]),
            emotion_scores=EmotionScores(
                happiness=row[5],
                sadness=row[6],
                anger=row[7],
                anxiety=row[8],
                calmness=row[9],
                excitement=row[10],
            ),
            primary_emotion=row[11],
            user_id=user_id,
            comfort_message=row[12] if len(row) > 12 else "",
            tags=json.loads(row[13]) if len(row) > 13 else [],
            conversations=conversations,
            created_at=datetime.fromisoformat(row[14]) if len(row) > 14 else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(row[15]) if len(row) > 15 else datetime.now(timezone.utc),
        )

    def add(self, entry: DiaryEntry) -> DiaryEntry:
        # conversations를 JSON으로 직렬화
        conversations_json = json.dumps([
            {
                "role": conv.role,
                "message": conv.message,
                "timestamp": conv.timestamp.isoformat()
            }
            for conv in entry.conversations
        ], ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO diary_entries (
                    text, summary, sentiment_label, sentiment_score,
                    emotion_happiness, emotion_sadness, emotion_anger,
                    emotion_anxiety, emotion_calmness, emotion_excitement,
                    primary_emotion, comfort_message, tags, created_at, updated_at, conversations, user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.text,
                    entry.summary,
                    entry.sentiment.label,
                    entry.sentiment.score,
                    entry.emotion_scores.happiness,
                    entry.emotion_scores.sadness,
                    entry.emotion_scores.anger,
                    entry.emotion_scores.anxiety,
                    entry.emotion_scores.calmness,
                    entry.emotion_scores.excitement,
                    entry.primary_emotion,
                    entry.comfort_message,
                    json.dumps(entry.tags, ensure_ascii=False),
                    entry.created_at.isoformat(),
                    entry.updated_at.isoformat(),
                    conversations_json,
                    entry.user_id,
                ),
            )
            conn.commit()
            entry.id = cursor.lastrowid
        return entry

    def create_entry(
        self,
        *,
        text: str,
        summary: str,
        sentiment: Sentiment,
        emotion_scores: EmotionScores,
        primary_emotion: str,
        comfort_message: str = "",
        tags: List[str],
        user_id: int = 1,  # 기본값 1 (기존 호환성)
    ) -> DiaryEntry:
        """새로운 일기 항목 생성"""
        print(f"DEBUG [DB create_entry]: Creating entry with user_id={user_id}")
        entry = DiaryEntry(
            id=0,  # Will be set by database
            text=text,
            summary=summary,
            sentiment=sentiment,
            emotion_scores=emotion_scores,
            primary_emotion=primary_emotion,
            user_id=user_id,
            comfort_message=comfort_message,
            tags=tags,
        )
        created_entry = self.add(entry)
        print(f"DEBUG [DB create_entry]: Created entry id={created_entry.id} with user_id={created_entry.user_id}")
        return created_entry

    def get_entry(self, entry_id: int, user_id: Optional[int] = None) -> Optional[DiaryEntry]:
        """ID로 일기 조회"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM diary_entries WHERE id = ? AND user_id = ?", (entry_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM diary_entries WHERE id = ?", (entry_id,)
                )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_entry(row)

    def update_entry(
        self,
        entry_id: int,
        *,
        text: str,
        summary: str,
        sentiment: Sentiment,
        emotion_scores: EmotionScores,
        primary_emotion: str,
        tags: List[str],
    ) -> Optional[DiaryEntry]:
        """일기 수정"""
        entry = self.get_entry(entry_id)
        if entry is None:
            return None

        updated_at = datetime.now(timezone.utc)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE diary_entries SET
                    text = ?, summary = ?, sentiment_label = ?, sentiment_score = ?,
                    emotion_happiness = ?, emotion_sadness = ?, emotion_anger = ?,
                    emotion_anxiety = ?, emotion_calmness = ?, emotion_excitement = ?,
                    primary_emotion = ?, tags = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    text,
                    summary,
                    sentiment.label,
                    sentiment.score,
                    emotion_scores.happiness,
                    emotion_scores.sadness,
                    emotion_scores.anger,
                    emotion_scores.anxiety,
                    emotion_scores.calmness,
                    emotion_scores.excitement,
                    primary_emotion,
                    json.dumps(tags, ensure_ascii=False),
                    updated_at.isoformat(),
                    entry_id,
                ),
            )
            conn.commit()

        return self.get_entry(entry_id)

    def update_conversations(
        self, entry_id: int, conversations: List[Conversation], updated_at: datetime
    ) -> bool:
        """대화 목록 업데이트"""
        conversations_json = json.dumps([
            {
                "role": conv.role,
                "message": conv.message,
                "timestamp": conv.timestamp.isoformat()
            }
            for conv in conversations
        ], ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE diary_entries SET
                    conversations = ?, updated_at = ?
                WHERE id = ?
                """,
                (conversations_json, updated_at.isoformat(), entry_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_entry(self, entry_id: int) -> bool:
        """일기 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM diary_entries WHERE id = ?", (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def list_entries(self, user_id: Optional[int] = None) -> List[DiaryEntry]:
        """모든 일기 목록 (최신순)"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id is not None:
                print(f"DEBUG [DB list_entries]: Querying with user_id={user_id}")
                cursor = conn.execute(
                    "SELECT * FROM diary_entries WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
                )
            else:
                print(f"DEBUG [DB list_entries]: Querying WITHOUT user_id filter")
                cursor = conn.execute(
                    "SELECT * FROM diary_entries ORDER BY created_at DESC"
                )
            rows = cursor.fetchall()
            print(f"DEBUG [DB list_entries]: Found {len(rows)} rows")
            if rows:
                # Log first row's user_id
                print(f"DEBUG [DB list_entries]: First row user_id={rows[0][17] if len(rows[0]) > 17 else 'N/A'}")
            entries = [self._row_to_entry(row) for row in rows]
            return entries

    def all(self) -> Iterable[DiaryEntry]:
        """모든 일기 반환"""
        return self.list_entries()


storage = DiaryStorage()


def get_storage() -> DiaryStorage:
    return storage
