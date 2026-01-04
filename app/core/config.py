# """app/core/config.py
"""
Configuration centralisée FastAPI
Charge les variables d'environnement et expose les settings
"""
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Application
    app_name: str = "TopoManager API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Database
    database_url: str
    
    # JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    
    # FastAPI
    fastapi_port: int = 8000
    
    # CORS
    cors_origins: list = ["*"]
    
    # Upload
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()