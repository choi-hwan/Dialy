#!/bin/bash

# MoodBot 서버 실행 스크립트

echo "Starting MoodBot server..."

# .env 파일 확인
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# 가상환경 활성화 (있는 경우)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 서버 실행
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000

