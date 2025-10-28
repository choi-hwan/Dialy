# Python 3.10 베이스 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치 (moodbot 디렉토리에서)
COPY moodbot/requirements.txt /app/

# PyTorch CPU 버전 설치 (GPU 버전이 필요한 경우 수정 필요)
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# 나머지 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (moodbot 디렉토리만)
COPY moodbot/ /app/

# 데이터베이스 디렉토리 생성
RUN mkdir -p /app/data

# 포트 노출
EXPOSE 8000

# 빌드 인자로 환경변수 받기
ARG HF_TOKEN
ARG HF_MODEL_ID=skt/A.X-3.1-Light
ARG HF_MAX_TOKENS=512
ARG HF_TEMPERATURE=0.7
ARG HF_TIMEOUT=30
ARG ENV=dev

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface
ENV HF_TOKEN=${HF_TOKEN}
ENV HF_MODEL_ID=${HF_MODEL_ID}
ENV HF_MAX_TOKENS=${HF_MAX_TOKENS}
ENV HF_TEMPERATURE=${HF_TEMPERATURE}
ENV HF_TIMEOUT=${HF_TIMEOUT}
ENV ENV=${ENV}

# 헬스체크 추가
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Uvicorn으로 FastAPI 실행 (Shell 형식으로 환경변수 지원)
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
