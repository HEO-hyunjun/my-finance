from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "My Finance"
    DEBUG: bool = True

    # Database (로컬 개발: 3307, Docker 내부: 3306)
    DATABASE_URL: str = "mysql+asyncmy://myfinance:myfinance@localhost:3307/myfinance?charset=utf8mb4"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # External APIs
    SERPAPI_KEY: str = ""
    ENCRYPTION_KEY: str = ""

    # 검색 프로바이더: "serpapi" | "firecrawl"
    # 뉴스/웹 검색에 사용할 프로바이더 선택 (금융 시세는 항상 yfinance 사용)
    SEARCH_PROVIDER: str = "serpapi"
    FIRECRAWL_API_KEY: str = ""
    FIRECRAWL_BASE_URL: str = ""  # self-hosted Firecrawl (예: http://firecrawl:3002)

    # SerpAPI 무료 플랜 최적화
    SERPAPI_DAILY_LIMIT: int = 5
    SERPAPI_MONTHLY_LIMIT: int = 95
    NEWS_CACHE_TTL: int = 43200       # 뉴스 캐시 12시간
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

    # 뉴스 LLM - 기사 요약/클러스터링
    NEWS_LLM_MODEL: str = ""
    NEWS_LLM_MAX_TOKENS: int = 1024
    NEWS_LLM_TEMPERATURE: float = 0.3

    # AI 인사이트 - 대시보드 AI 위젯
    INSIGHT_MODEL: str = ""
    INSIGHT_MAX_TOKENS: int = 512
    INSIGHT_TEMPERATURE: float = 0.5

    @property
    def chatbot_model(self) -> str:
        return self.CHATBOT_MODEL or self.LITELLM_MODEL

    @property
    def news_llm_model(self) -> str:
        return self.NEWS_LLM_MODEL or self.LITELLM_MODEL

    @property
    def insight_model(self) -> str:
        return self.INSIGHT_MODEL or self.LITELLM_MODEL

    model_config = {
        "env_file": (".env", "../.env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
