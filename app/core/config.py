"""Configuration centralisée avec validations"""
# app/core/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    app_name: str = "TopoManager API"
    app_version: str = "2.0.0"
    
    # Base de données
    database_url: str = Field(..., min_length=10, description="URL de connexion PostgreSQL")
    
    # Sécurité JWT
    jwt_secret: str = Field(..., min_length=32, description="Clé secrète JWT (32+ caractères)")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    
    # Serveur
    fastapi_port: int = 8000
    cors_origins: List[str] = ["*"]
    
    # Upload fichiers
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
    
    # Auto-création utilisateurs
    auto_create_users: bool = False
    allowed_email_domains: List[str] = ["topomanager.mg", "geodoc.mg"]
    
    @validator('jwt_secret')
    def validate_jwt_secret(cls, v):
        """Valide que la clé JWT est suffisamment forte"""
        if v == "changeme" or v == "secret" or len(v) < 32:
            raise ValueError(
                "JWT_SECRET doit être une clé forte (32+ caractères). "
                "Utilisez: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        return v
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        """Parse les origines CORS depuis une chaîne ou une liste"""
        if isinstance(v, str):
            return [x.strip() for x in v.split(',') if x.strip()]
        return v
    
    @validator('allowed_extensions', pre=True)
    def parse_extensions(cls, v):
        """Parse les extensions autorisées"""
        if isinstance(v, str):
            return [x.strip().lower() for x in v.split(',') if x.strip()]
        return [ext.lower() for ext in v]
    
    @validator('allowed_email_domains', pre=True)
    def parse_domains(cls, v):
        """Parse les domaines email autorisés"""
        if isinstance(v, str):
            return [x.strip().lower() for x in v.split(',') if x.strip()]
        return [d.lower() for d in v]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""

@lru_cache()
def get_settings() -> Settings:
    """Retourne l'instance singleton des paramètres"""
    return Settings()