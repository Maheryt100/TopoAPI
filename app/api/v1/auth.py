# app/api/v1/auth.py
"""
Routes d'authentification
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_token, decode_token, hash_password
from app.models.staging import TopoUser
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentification"])

# Définir get_current_user EN PREMIER (avant les routes qui l'utilisent)
def get_current_user(
    credentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
) -> TopoUser:
    """Dependency pour récupérer l'utilisateur authentifié"""
    identifier = decode_token(credentials.credentials)
    
    if not identifier:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = db.query(TopoUser).filter(
        (TopoUser.username == identifier) | (TopoUser.email == identifier)
    ).first()
    
    if not user and '@' in identifier:
        # Création auto pour utilisateurs GeODOC
        user = TopoUser(
            username=identifier.split('@')[0],
            email=identifier,
            full_name=identifier.split('@')[0].replace('.', ' ').title(),
            hashed_password=hash_password(f"auto_{identifier}"),
            role="operator",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Compte désactivé")
    
    return user


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Connexion avec username/password"""
    user = db.query(TopoUser).filter(TopoUser.username == data.username).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    
    token = create_token(user.email, user.role)
    
    return LoginResponse(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    )


@router.get("/me")
def get_current_user_info(user: TopoUser = Depends(get_current_user)):
    """Informations utilisateur connecté"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }