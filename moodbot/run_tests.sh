#!/bin/bash
# 테스트 실행 스크립트

set -e

echo "==================================="
echo "MoodBot 테스트 실행"
echo "==================================="

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 의존성 확인
echo -e "${BLUE}📦 테스트 의존성 확인 중...${NC}"
if ! python -m pytest --version > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  pytest가 설치되지 않았습니다. 설치 중...${NC}"
    pip install -r requirements-test.txt
fi

# 옵션 파싱
case "${1:-all}" in
    all)
        echo -e "${BLUE}🧪 모든 테스트 실행 중...${NC}"
        pytest -v --cov=app --cov-report=html --cov-report=term-missing
        ;;

    fast)
        echo -e "${BLUE}⚡ 빠른 테스트만 실행 중...${NC}"
        pytest -v -m "not slow"
        ;;

    auth)
        echo -e "${BLUE}🔐 인증 테스트 실행 중...${NC}"
        pytest -v tests/test_auth.py
        ;;

    api)
        echo -e "${BLUE}🌐 API 테스트 실행 중...${NC}"
        pytest -v tests/test_auth.py tests/test_entries.py tests/test_stats.py
        ;;

    web)
        echo -e "${BLUE}🖥️  웹 UI 테스트 실행 중...${NC}"
        pytest -v tests/test_web.py
        ;;

    models)
        echo -e "${BLUE}📊 모델 테스트 실행 중...${NC}"
        pytest -v tests/test_models.py
        ;;

    coverage)
        echo -e "${BLUE}📈 커버리지 리포트 생성 중...${NC}"
        pytest --cov=app --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}✅ HTML 리포트가 생성되었습니다: htmlcov/index.html${NC}"
        ;;

    *)
        echo "사용법: $0 [all|fast|auth|api|web|models|coverage]"
        echo ""
        echo "옵션:"
        echo "  all      - 모든 테스트 실행 (기본값)"
        echo "  fast     - 빠른 테스트만 실행 (느린 테스트 제외)"
        echo "  auth     - 인증 테스트만 실행"
        echo "  api      - API 테스트만 실행"
        echo "  web      - 웹 UI 테스트만 실행"
        echo "  models   - 모델 테스트만 실행"
        echo "  coverage - 커버리지 리포트 생성"
        exit 1
        ;;
esac

echo -e "${GREEN}✅ 테스트 완료!${NC}"
