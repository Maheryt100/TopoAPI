"""Configuration centralisee"""
# app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "TopoManager API"
    app_version: str = "2.0.0"
    
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    
    fastapi_port: int = 8000
    cors_origins: list = ["*"]
    
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()