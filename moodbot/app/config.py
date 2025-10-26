"""
애플리케이션 설정 관리
환경 변수를 로드하고 관리합니다.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# .env 파일 로드 (프로젝트 루트에서)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """애플리케이션 설정"""

    def __init__(self):
        # HuggingFace 설정
        self.HUGGINGFACE_TOKEN: Optional[str] = os.getenv("HUGGINGFACE_TOKEN")
        self.HUGGINGFACE_MODEL: str = os.getenv(
            "HUGGINGFACE_MODEL", "JaeJiMin/daily_hug"
        )

        # 애플리케이션 설정
        self.DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

        # 토큰 유효성 검사
        if self.HUGGINGFACE_TOKEN and self.HUGGINGFACE_TOKEN.startswith("hf_YOUR_TOKEN"):
            print("⚠️  경고: .env 파일에 실제 HuggingFace 토큰을 설정해주세요!")
            print("   토큰은 https://huggingface.co/settings/tokens 에서 발급받을 수 있습니다.")
            self.HUGGINGFACE_TOKEN = None

    def is_huggingface_configured(self) -> bool:
        """HuggingFace 토큰이 올바르게 설정되었는지 확인"""
        return self.HUGGINGFACE_TOKEN is not None and len(self.HUGGINGFACE_TOKEN) > 0


# 싱글톤 인스턴스
settings = Settings()
