"""Configuration centralisée avec validations"""
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache
from typing import List, Union

class Settings(BaseSettings):
    app_name: str = "TopoManager API"
    app_version: str = "1.0.0"
    
    # Base de données
    database_url: str = Field(..., min_length=10)
    
    # Sécurité JWT
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8
    
    # Serveur
    fastapi_port: int = 8000
    
    # IMPORTANT: accepter str ou list pour éviter l'erreur JSON
    cors_origins: Union[str, List[str]] = "*"
    
    # Upload fichiers
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024
    
    # IMPORTANT: accepter str ou list
    allowed_extensions: Union[str, List[str]] = ".pdf,.jpg,.jpeg,.png,.doc,.docx"
    
    # Auto-création utilisateurs
    auto_create_users: bool = False
    
    # IMPORTANT: accepter str ou list
    allowed_email_domains: Union[str, List[str]] = "topomanager.mg,geodoc.mg"
    
    # Configuration Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore les variables non définies
    )
    
    @field_validator('jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Valide et nettoie la clé JWT"""
        # Nettoyer les doubles déclarations
        if v.startswith('JWT_SECRET='):
            v = v.replace('JWT_SECRET=', '', 1)
        
        v = v.strip()
        
        if v == "changeme" or len(v) < 32:
            raise ValueError(
                "JWT_SECRET doit être une clé forte (32+ caractères)"
            )
        return v
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v) -> List[str]:
        """Parse les origines CORS - ACCEPTE STRING OU LIST"""
        if v is None or v == "":
            return ["*"]
        
        # Si c'est déjà une liste, la retourner
        if isinstance(v, list):
            return v
        
        # Si c'est une string
        if isinstance(v, str):
            v = v.strip()
            if v == "*":
                return ["*"]
            # Séparer par virgules
            origins = [x.strip() for x in v.split(',') if x.strip()]
            return origins if origins else ["*"]
        
        return ["*"]
    
    @field_validator('allowed_extensions', mode='before')
    @classmethod
    def parse_extensions(cls, v) -> List[str]:
        """Parse les extensions - ACCEPTE STRING OU LIST"""
        default = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
        
        if v is None or v == "":
            return default
        
        if isinstance(v, list):
            return [ext.lower() for ext in v]
        
        if isinstance(v, str):
            exts = [x.strip().lower() for x in v.split(',') if x.strip()]
            return exts if exts else default
        
        return default
    
    @field_validator('allowed_email_domains', mode='before')
    @classmethod
    def parse_domains(cls, v) -> List[str]:
        """Parse les domaines - ACCEPTE STRING OU LIST"""
        default = ["topomanager.mg", "geodoc.mg"]
        
        if v is None or v == "":
            return default
        
        if isinstance(v, list):
            return [d.lower() for d in v]
        
        if isinstance(v, str):
            domains = [x.strip().lower() for x in v.split(',') if x.strip()]
            return domains if domains else default
        
        return default

@lru_cache()
def get_settings() -> Settings:
    """Retourne l'instance singleton des paramètres"""
    return Settings()