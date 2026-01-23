"""Routes authentification avec sécurité renforcée"""
# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_token, decode_token, hash_password
from app.core.config import get_settings
from app.models.staging import TopoUser
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()
settings = get_settings()

def get_current_user(credentials = Depends(security), db: Session = Depends(get_db)) -> TopoUser:
    """
    Récupère l'utilisateur actuel depuis le token JWT
    Avec option d'auto-création pour domaines autorisés
    """
    identifier = decode_token(credentials.credentials)
    if not identifier:
        raise HTTPException(401, "Token invalide ou expiré")
    
    # Recherche utilisateur existant
    user = db.query(TopoUser).filter(
        (TopoUser.username == identifier) | (TopoUser.email == identifier)
    ).first()
    
    # Auto-création si activée et domaine autorisé
    if not user and '@' in identifier and settings.auto_create_users:
        domain = identifier.split('@')[1].lower()
        
        if domain not in settings.allowed_email_domains:
            raise HTTPException(
                403, 
                f"Domaine email non autorisé: {domain}. "
                f"Domaines acceptés: {', '.join(settings.allowed_email_domains)}"
            )
        
        # Création automatique pour domaines de confiance
        username = identifier.split('@')[0].replace('.', '_').replace('-', '_')
        full_name = identifier.split('@')[0].replace('.', ' ').replace('_', ' ').title()
        
        user = TopoUser(
            username=username,
            email=identifier,
            full_name=full_name,
            hashed_password=hash_password(f"auto_{identifier}_{settings.jwt_secret[:8]}"),
            role="operator",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    if not user:
        raise HTTPException(401, "Utilisateur introuvable")
    
    if not user.is_active:
        raise HTTPException(403, "Compte désactivé. Contactez l'administrateur")
    
    return user

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authentifie un utilisateur et retourne un token JWT
    """
    user = db.query(TopoUser).filter(TopoUser.username == data.username).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Identifiants incorrects")
    
    if not user.is_active:
        raise HTTPException(403, "Compte désactivé. Contactez l'administrateur")
    
    return LoginResponse(
        access_token=create_token(user.email, user.role),
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    )

@router.get("/me")
def get_me(user: TopoUser = Depends(get_current_user)):
    """
    Retourne les informations de l'utilisateur connecté
    """
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active
    }