# MoodBot Docker 배포 가이드

## 사전 준비

1. Docker 및 Docker Compose 설치 확인
```bash
docker --version
docker-compose --version
```

2. `.env` 파일 설정
```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 HF_TOKEN 설정
nano .env
```

## 빌드 및 실행

### 방법 1: Docker Compose 사용 (권장)

```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose up -d --build

# 로그 확인
docker-compose logs -f

# 상태 확인
docker-compose ps

# 중지
docker-compose down

# 중지 + 볼륨 삭제 (데이터베이스 초기화)
docker-compose down -v
```

### 방법 2: Docker 직접 사용

```bash
# 이미지 빌드
docker build -t moodbot:latest .

# 컨테이너 실행
docker run -d \
  --name moodbot \
  -p 8000:8000 \
  -e HF_TOKEN=your_token_here \
  -v $(pwd)/diary.db:/app/diary.db \
  -v moodbot-cache:/app/.cache/huggingface \
  moodbot:latest

# 로그 확인
docker logs -f moodbot

# 중지
docker stop moodbot

# 삭제
docker rm moodbot
```

## 접속

컨테이너 실행 후 브라우저에서 다음 URL로 접속:
- http://localhost:8000

## 헬스체크

```bash
curl http://localhost:8000/health
```

## 주의사항

### 메모리 요구사항
- 최소: 2GB RAM
- 권장: 4GB RAM 이상
- AI 모델 로딩 시 약 2-3GB 메모리 사용

### GPU 사용 (선택사항)

GPU를 사용하려면 Dockerfile을 수정하세요:

```dockerfile
# PyTorch GPU 버전으로 변경
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

docker-compose.yml에 GPU 설정 추가:

```yaml
services:
  moodbot:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### 데이터 백업

```bash
# 데이터베이스 백업
docker cp moodbot:/app/diary.db ./diary.db.backup

# 복원
docker cp ./diary.db.backup moodbot:/app/diary.db
```

## 트러블슈팅

### 컨테이너가 시작되지 않는 경우
```bash
# 로그 확인
docker-compose logs moodbot

# 컨테이너 내부 접속
docker exec -it moodbot bash
```

### 모델 다운로드 실패
- HF_TOKEN이 올바르게 설정되었는지 확인
- 인터넷 연결 확인
- Hugging Face 계정이 모델 접근 권한이 있는지 확인

### 메모리 부족 오류
- docker-compose.yml에서 메모리 제한 증가
- 더 작은 모델 사용 고려

## 환경 변수

| 변수명 | 기본값 | 설명 |
|--------|--------|------|
| HF_TOKEN | - | Hugging Face API 토큰 (필수) |
| HF_MODEL_ID | JaeJiMin/daily_hug | 사용할 모델 ID |
| HF_MAX_TOKENS | 512 | 최대 생성 토큰 수 |
| HF_TEMPERATURE | 0.7 | 생성 온도 (0.0-2.0) |
| ENV | prod | 환경 (dev/prod) |

## 프로덕션 배포 시 권장사항

1. **리버스 프록시 사용** (Nginx, Traefik 등)
2. **HTTPS 설정**
3. **로그 로테이션 설정**
4. **정기 백업 자동화**
5. **모니터링 도구 연동** (Prometheus, Grafana 등)
