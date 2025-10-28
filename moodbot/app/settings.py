# app/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # ==== Hugging Face ====
    hf_token: str = Field(default="", validation_alias="HF_TOKEN")
    hf_model_id: str = Field("skt/A.X-3.1-Light", validation_alias="HF_MODEL_ID")
    hf_timeout: int = Field(30, validation_alias="HF_TIMEOUT")
    hf_max_tokens: int = Field(512, validation_alias="HF_MAX_TOKENS")
    hf_temperature: float = Field(0.7, validation_alias="HF_TEMPERATURE")

    # ==== CORS 설정 ====
    cors_origins: List[str] = Field(
        default=["*"],
        validation_alias="CORS_ORIGINS",
        description="허용할 오리진 목록 (쉼표로 구분)"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        validation_alias="CORS_ALLOW_CREDENTIALS"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"],
        validation_alias="CORS_ALLOW_METHODS"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        validation_alias="CORS_ALLOW_HEADERS"
    )
    cors_expose_headers: List[str] = Field(
        default=[],
        validation_alias="CORS_EXPOSE_HEADERS"
    )
    cors_max_age: int = Field(
        default=600,
        validation_alias="CORS_MAX_AGE",
        description="Preflight 요청 캐시 시간(초)"
    )

    # 공통
    env: str = Field("dev", validation_alias="ENV")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env") if (BASE_DIR / ".env").exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def check_hf_token(self):
        # Railway 등 클라우드 환경에서는 환경변수로 설정됨
        # 빌드 시점에는 비어있을 수 있으므로 경고만 출력
        if not self.hf_token:
            print("WARNING: HF_TOKEN is empty. Please set it in environment variables.")
        return self

    @model_validator(mode="after")
    def parse_cors_origins(self):
        """CORS_ORIGINS가 문자열로 들어온 경우 리스트로 변환"""
        if isinstance(self.cors_origins, str):
            # 쉼표로 구분된 문자열을 리스트로 변환
            self.cors_origins = [
                origin.strip()
                for origin in self.cors_origins.split(",")
                if origin.strip()
            ]
        return self


settings = Settings()