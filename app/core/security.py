# """app/core/security.py
"""
Sécurité : JWT + Hash passwords
Compatible avec Laravel (même clé JWT)
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

def verify_password(plain: str, hashed: str) -> bool:
    """Vérifier un mot de passe (compatible Laravel bcrypt)"""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def hash_password(password: str) -> str:
    """Hasher un mot de passe"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_token(identifier: str, role: str) -> str:
    """
    Créer un JWT compatible Laravel
    identifier = email ou username
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    
    payload = {
        "sub": identifier,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "iss": "TopoManager"
    }
    
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> Optional[str]:
    """
    Décoder un JWT (venant de Laravel ou créé par FastAPI)
    Retourne l'identifiant utilisateur (sub)
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None