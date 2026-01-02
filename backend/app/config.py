from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "K12 Asset Guardian"
    environment: str = "development"

    # Database
    # NOTE: Overridden by docker-compose or .env in production
    database_url: str = "sqlite:///./k12_asset_guardian.db"

    # Security / Auth
    jwt_secret: str = "CHANGE_ME_SUPER_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_exp_minutes: int = 480

    # Email (alerts)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "K12 Asset Guardian <no-reply@k12guardian.local>"

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
