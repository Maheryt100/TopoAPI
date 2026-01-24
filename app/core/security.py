"""Sécurité JWT et mots de passe - Compatible GeODOC"""
# app/core/security.py
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from app.core.config import get_settings

settings = get_settings()

def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt"""
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def create_token(identifier: str, role: str) -> str:
    """
    Crée un token JWT pour FastAPI (utilisé par l'app mobile TopoManager)
    
    Args:
        identifier: Email de l'utilisateur
        role: Rôle de l'utilisateur
        
    Returns:
        Token JWT encodé
        
    Note:
        Ce token est différent de celui de GeODOC !
        GeODOC a son propre JwtService.php qui génère des tokens avec 'sub' = user.id
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": identifier,  # Email pour FastAPI
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.jwt_secret, settings.jwt_algorithm)

def decode_token(token: str) -> Optional[Union[str, int]]:
    """
    Décode un token JWT et retourne l'identifiant utilisateur
    
    COMPATIBLE AVEC 2 FORMATS :
    
    1. **Token FastAPI** (app mobile TopoManager) :
       ```json
       {
         "sub": "topo@gmail.com",  // Email
         "role": "operator",
         "exp": 1769213142
       }
       ```
       → Retourne l'email (str)
    
    2. **Token GeODOC** (Laravel JwtService.php) :
       ```json
       {
         "iss": "http://localhost",
         "sub": 2,  // ID utilisateur (int)
         "user": { ... },
         "exp": 1769270843
       }
       ```
       → Retourne l'ID utilisateur (int)
    
    Args:
        token: Token JWT encodé
        
    Returns:
        - Email (str) pour tokens FastAPI
        - ID utilisateur (int) pour tokens GeODOC
        - None si le token est invalide
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        
        # Extraire 'sub' (peut être un email ou un ID)
        identifier = payload.get("sub")
        
        if identifier is None:
            return None
        
        # Si c'est un nombre, le retourner tel quel (GeODOC envoie un int)
        # Si c'est une string, la retourner telle quelle (FastAPI envoie un email)
        return identifier
        
    except jwt.ExpiredSignatureError:
        # Token expiré
        return None
    except jwt.InvalidTokenError:
        # Token invalide (signature incorrecte, format incorrect, etc.)
        return None
    except Exception:
        # Toute autre erreur
        return None

def is_token_valid(token: str) -> bool:
    """
    Vérifie si un token est valide (non expiré, signature correcte)
    
    Args:
        token: Token JWT à vérifier
        
    Returns:
        True si valide, False sinon
    """
    return decode_token(token) is not None

def extract_user_data(token: str) -> Optional[dict]:
    """
    Extrait toutes les données utilisateur d'un token GeODOC
    
    Utilisé pour récupérer les infos supplémentaires dans le payload GeODOC
    (comme id_district, role, etc.)
    
    Args:
        token: Token JWT GeODOC
        
    Returns:
        Dictionnaire avec les données utilisateur ou None
        
    Example:
        ```python
        data = extract_user_data(token)
        # {
        #   "id": 2,
        #   "email": "mahery@gmail.com",
        #   "name": "Mahery Tiana",
        #   "role": "admin_district",
        #   "id_district": 7
        # }
        ```
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        
        # GeODOC stocke les infos user dans un objet 'user'
        return payload.get("user")
        
    except Exception:
        return None