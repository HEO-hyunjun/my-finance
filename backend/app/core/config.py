from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "My Finance"
    DEBUG: bool = True

    # Database (로컬 개발: 5433, Docker 내부: 5432)
    DATABASE_URL: str = "postgresql+asyncpg://myfinance:myfinance@localhost:5433/myfinance"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Timezone (IANA name)
    TIMEZONE: str = "Asia/Seoul"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # External APIs
    ENCRYPTION_KEY: str = ""

    # 검색 프로바이더: "tavily" | "serpapi" | "firecrawl"
    SEARCH_PROVIDER: str = "tavily"
    TAVILY_API_KEY: str = ""
    SERPAPI_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""
    FIRECRAWL_BASE_URL: str = ""

    # 검색 캐시
    WEB_SEARCH_CACHE_TTL: int = 7200  # 웹 검색 캐시 2시간

    # LLM API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # LLM 글로벌 기본값 (개별 설정이 없으면 이 값 사용)
    LITELLM_MODEL: str = "gpt-4o-mini"

    # 챗봇 (Deep Agent) - 대화형 재무 상담
    CHATBOT_MODEL: str = ""
    CHATBOT_MAX_TOKENS: int = 2048
    CHATBOT_TEMPERATURE: float = 0.7
    CHATBOT_MAX_HISTORY: int = 20

    # AI 인사이트 - 대시보드 AI 위젯
    INSIGHT_MODEL: str = ""
    INSIGHT_MAX_TOKENS: int = 4096
    INSIGHT_TEMPERATURE: float = 0.5

    @property
    def chatbot_model(self) -> str:
        return self.CHATBOT_MODEL or self.LITELLM_MODEL

    @property
    def insight_model(self) -> str:
        return self.INSIGHT_MODEL or self.LITELLM_MODEL

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
