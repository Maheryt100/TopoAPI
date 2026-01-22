"""Routes authentification"""
# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_token, decode_token, hash_password
from app.models.staging import TopoUser
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()

def get_current_user(credentials = Depends(security), db: Session = Depends(get_db)) -> TopoUser:
    identifier = decode_token(credentials.credentials)
    if not identifier:
        raise HTTPException(401, "Token invalide")
    
    user = db.query(TopoUser).filter(
        (TopoUser.username == identifier) | (TopoUser.email == identifier)
    ).first()
    
    if not user and '@' in identifier:
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
    
    if not user or not user.is_active:
        raise HTTPException(401, "Utilisateur introuvable ou desactive")
    
    return user

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(TopoUser).filter(TopoUser.username == data.username).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Identifiants incorrects")
    
    if not user.is_active:
        raise HTTPException(403, "Compte desactive")
    
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
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }