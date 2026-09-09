from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "sqlite:///./cyberchain.db"
    JWT_SECRET: str = "change-me-to-a-long-random-secret-for-sih26183"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720
    ETHERSCAN_API_KEY: str = ""
    POLYGONSCAN_API_KEY: str = ""
    BSCSCAN_API_KEY: str = ""
    TRACING_MAX_HOPS: int = 5
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    RATE_LIMIT_PER_MINUTE: int = 120
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 20

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
