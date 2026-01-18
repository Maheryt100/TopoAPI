"""
FastAPI TopoManager - Version Complète
Tous les champs métier disponibles avec validation stricte
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.sql import func, text
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import hashlib
import json
import jwt
import bcrypt
import os

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/Odoc2")
JWT_SECRET = os.getenv("JWT_SECRET", "3xM4y3NCphtC8qMg9ec5rqO2FLdTpb4g5ro241H2Qk9uqq+2jES1gIa+DE0U9AyldwY/tcq8P/O/NGcboApL5A==")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# SQLAlchemy
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI App
app = FastAPI(title="TopoManager API", version="2.0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Modeles SQLAlchemy
class TopoUser(Base):
    __tablename__ = "topo_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default='operator')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingDemandeur(Base):
    __tablename__ = "topo_staging_demandeurs"
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), default='topo')
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'))
    topo_user_name = Column(String(100))
    numero_ouverture = Column(String(50), nullable=False)
    target_district_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default='PENDING')
    error_reason = Column(Text)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(BigInteger)
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    files = relationship("TopoStagingFile", back_populates="demandeur", cascade="all, delete-orphan")

class TopoStagingPropriete(Base):
    __tablename__ = "topo_staging_proprietes"
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), default='topo')
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'))
    topo_user_name = Column(String(100))
    numero_ouverture = Column(String(50), nullable=False)
    target_district_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default='PENDING')
    error_reason = Column(Text)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(BigInteger)
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    files = relationship("TopoStagingFile", back_populates="propriete", cascade="all, delete-orphan")

class TopoStagingFile(Base):
    __tablename__ = "topo_staging_files"
    id = Column(Integer, primary_key=True)
    numero_ouverture = Column(String(50), nullable=False)
    target_district_id = Column(Integer, nullable=False)
    demandeur_id = Column(BigInteger, ForeignKey('topo_staging_demandeurs.id', ondelete='CASCADE'))
    propriete_id = Column(BigInteger, ForeignKey('topo_staging_proprietes.id', ondelete='CASCADE'))
    cin = Column(String(50))
    lot = Column(String(50))
    category = Column(String(50))
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    demandeur = relationship("TopoStagingDemandeur", back_populates="files")
    propriete = relationship("TopoStagingPropriete", back_populates="files")

Base.metadata.create_all(bind=engine)

# Schemas Pydantic
class LoginRequest(BaseModel):
    username: str
    password: str

class ImportResponse(BaseModel):
    success: bool
    import_id: int
    batch_id: str
    entity_type: str
    files_uploaded: int = 0

# Utilitaires
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_token(identifier: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    payload = {"sub": identifier, "role": role, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("sub")
    except:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TopoUser:
    identifier = decode_token(credentials.credentials)
    if not identifier:
        raise HTTPException(status_code=401, detail="Token invalide")
    
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
        raise HTTPException(status_code=401, detail="Utilisateur introuvable ou inactif")
    
    return user

async def save_file(file: UploadFile, entity_type: str, entity_id: int) -> dict:
    upload_dir = UPLOAD_DIR / entity_type / str(entity_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_hash = hashlib.md5(file.filename.encode()).hexdigest()[:8]
    extension = Path(file.filename).suffix
    stored_name = f"{timestamp}_{file_hash}{extension}"
    file_path = upload_dir / stored_name
    
    contents = await file.read()
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    return {
        'original_name': file.filename,
        'stored_name': stored_name,
        'file_size': len(contents),
        'mime_type': file.content_type or 'application/octet-stream'
    }

def validate_enum(value: Optional[str], valid_values: List[str], field_name: str):
    if value is None:
        return None
    if value not in valid_values:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} invalide. Valeurs acceptees: {', '.join(valid_values)}"
        )
    return value

def validate_date_iso(value: Optional[str], field_name: str):
    if value is None:
        return None
    try:
        date.fromisoformat(value)
        return value
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} doit etre au format ISO (YYYY-MM-DD)"
        )

# ROUTES - AUTHENTIFICATION
@app.post("/api/v1/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(TopoUser).filter(TopoUser.username == data.username).first()
    
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte desactive")
    
    token = create_token(user.email, user.role)
    
    return {
        "access_token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        }
    }

@app.get("/api/v1/auth/me")
async def get_me(user: TopoUser = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role
    }

# ROUTES - CREATION DEMANDEUR (VERSION COMPLETE)
@app.post("/api/v1/demandeurs/", status_code=201, response_model=ImportResponse)
async def create_demandeur(
    # Champs obligatoires
    numero_ouverture: str = Form(..., description="Numero d'ouverture du dossier"),
    target_district_id: int = Form(..., description="ID du district cible"),
    
    # Identite
    cin: Optional[str] = Form(None, description="Numero CIN"),
    titre_demandeur: Optional[str] = Form(None, description="Titre (Monsieur/Madame/Mademoiselle)"),
    nom_demandeur: Optional[str] = Form(None, description="Nom de famille"),
    prenom_demandeur: Optional[str] = Form(None, description="Prenom"),
    date_naissance: Optional[str] = Form(None, description="Date de naissance (YYYY-MM-DD)"),
    lieu_naissance: Optional[str] = Form(None, description="Lieu de naissance"),
    sexe: Optional[str] = Form(None, description="Sexe (Homme/Femme)"),
    occupation: Optional[str] = Form(None, description="Profession"),
    
    # Filiation
    nom_pere: Optional[str] = Form(None, description="Nom du pere"),
    nom_mere: Optional[str] = Form(None, description="Nom de la mere"),
    
    # CIN
    date_delivrance: Optional[str] = Form(None, description="Date de delivrance CIN (YYYY-MM-DD)"),
    lieu_delivrance: Optional[str] = Form(None, description="Lieu de delivrance CIN"),
    date_delivrance_duplicata: Optional[str] = Form(None, description="Date delivrance duplicata (YYYY-MM-DD)"),
    lieu_delivrance_duplicata: Optional[str] = Form(None, description="Lieu delivrance duplicata"),
    
    # Contact
    domiciliation: Optional[str] = Form(None, description="Adresse"),
    telephone: Optional[str] = Form(None, description="Numero de telephone"),
    nationalite: Optional[str] = Form("Malagasy", description="Nationalite"),
    
    # Situation familiale
    situation_familiale: Optional[str] = Form(None, description="Situation familiale"),
    regime_matrimoniale: Optional[str] = Form(None, description="Regime matrimonial"),
    date_mariage: Optional[str] = Form(None, description="Date de mariage (YYYY-MM-DD)"),
    lieu_mariage: Optional[str] = Form(None, description="Lieu de mariage"),
    marie_a: Optional[str] = Form(None, description="Marie(e) a"),
    
    # Fichiers
    files: List[UploadFile] = File(default=[]),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creer un import DEMANDEUR avec tous les champs"""
    
    # Validation enums
    TITRES = ["Monsieur", "Madame", "Mademoiselle"]
    SEXES = ["Homme", "Femme"]
    SITUATIONS = ["Non specifiee", "Celibataire", "Marie(e)", "Veuf/Veuve", "Divorce(e)"]
    REGIMES = ["Non specifie", "Zara-Mira", "Kitay telo an-dalana", "Separations des biens"]
    
    titre_valid = validate_enum(titre_demandeur, TITRES, "titre_demandeur")
    sexe_valid = validate_enum(sexe, SEXES, "sexe")
    situation_valid = validate_enum(situation_familiale, SITUATIONS, "situation_familiale")
    regime_valid = validate_enum(regime_matrimoniale, REGIMES, "regime_matrimoniale")
    
    # Validation dates
    date_naissance_valid = validate_date_iso(date_naissance, "date_naissance")
    date_delivrance_valid = validate_date_iso(date_delivrance, "date_delivrance")
    date_delivrance_duplicata_valid = validate_date_iso(date_delivrance_duplicata, "date_delivrance_duplicata")
    date_mariage_valid = validate_date_iso(date_mariage, "date_mariage")
    
    # Construction payload avec null explicite
    payload = {
        "cin": cin.strip() if cin and cin.strip() else None,
        "titre_demandeur": titre_valid,
        "nom_demandeur": nom_demandeur.strip() if nom_demandeur and nom_demandeur.strip() else None,
        "prenom_demandeur": prenom_demandeur.strip() if prenom_demandeur and prenom_demandeur.strip() else None,
        "date_naissance": date_naissance_valid,
        "lieu_naissance": lieu_naissance.strip() if lieu_naissance and lieu_naissance.strip() else None,
        "sexe": sexe_valid,
        "occupation": occupation.strip() if occupation and occupation.strip() else None,
        "nom_pere": nom_pere.strip() if nom_pere and nom_pere.strip() else None,
        "nom_mere": nom_mere.strip() if nom_mere and nom_mere.strip() else None,
        "date_delivrance": date_delivrance_valid,
        "lieu_delivrance": lieu_delivrance.strip() if lieu_delivrance and lieu_delivrance.strip() else None,
        "date_delivrance_duplicata": date_delivrance_duplicata_valid,
        "lieu_delivrance_duplicata": lieu_delivrance_duplicata.strip() if lieu_delivrance_duplicata and lieu_delivrance_duplicata.strip() else None,
        "domiciliation": domiciliation.strip() if domiciliation and domiciliation.strip() else None,
        "telephone": telephone.strip() if telephone and telephone.strip() else None,
        "nationalite": nationalite.strip() if nationalite and nationalite.strip() else "Malagasy",
        "situation_familiale": situation_valid,
        "regime_matrimoniale": regime_valid,
        "date_mariage": date_mariage_valid,
        "lieu_mariage": lieu_mariage.strip() if lieu_mariage and lieu_mariage.strip() else None,
        "marie_a": marie_a.strip() if marie_a and marie_a.strip() else None
    }
    
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    staging = TopoStagingDemandeur(
        source='topo',
        topo_user_id=user.id,
        topo_user_name=user.full_name,
        numero_ouverture=numero_ouverture,
        target_district_id=target_district_id,
        payload=payload,
        checksum=checksum,
        status='PENDING'
    )
    
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    # Sauvegarde fichiers
    files_saved = []
    for file in files:
        try:
            file_info = await save_file(file, 'demandeurs', staging.id)
            staging_file = TopoStagingFile(
                demandeur_id=staging.id,
                numero_ouverture=numero_ouverture,
                target_district_id=target_district_id,
                cin=cin.strip() if cin and cin.strip() else None,
                original_name=file_info['original_name'],
                stored_name=file_info['stored_name'],
                file_size=file_info['file_size'],
                mime_type=file_info['mime_type'],
                category='cin'
            )
            db.add(staging_file)
            files_saved.append(file_info)
        except Exception as e:
            print(f"Erreur fichier: {e}")
    
    db.commit()
    
    return ImportResponse(
        success=True,
        import_id=staging.id,
        batch_id=str(staging.batch_id),
        entity_type="demandeur",
        files_uploaded=len(files_saved)
    )

# ROUTES - CREATION PROPRIETE (VERSION COMPLETE)
@app.post("/api/v1/proprietes/", status_code=201, response_model=ImportResponse)
async def create_propriete(
    # Champs obligatoires
    numero_ouverture: str = Form(..., description="Numero d'ouverture du dossier"),
    target_district_id: int = Form(..., description="ID du district cible"),
    
    # Identification
    lot: Optional[str] = Form(None, description="Numero de lot"),
    titre: Optional[str] = Form(None, description="Titre"),
    contenance: Optional[int] = Form(None, description="Contenance (m2)"),
    proprietaire: Optional[str] = Form(None, description="Nom du proprietaire"),
    
    # Liens
    propriete_mere: Optional[str] = Form(None, description="Propriete mere"),
    titre_mere: Optional[str] = Form(None, description="Titre mere"),
    
    # Caracteristiques
    charge: Optional[str] = Form(None, description="Charges"),
    situation: Optional[str] = Form(None, description="Situation geographique"),
    nature: Optional[str] = Form(None, description="Nature du terrain (Urbaine/Suburbaine/Rurale)"),
    vocation: Optional[str] = Form(None, description="Vocation du terrain"),
    
    # Administratif
    numero_FN: Optional[str] = Form(None, description="Numero FN"),
    numero_requisition: Optional[str] = Form(None, description="Numero de requisition"),
    type_operation: Optional[str] = Form(None, description="Type d'operation (Morcellement/Immatriculation)"),
    
    # Dates
    date_requisition: Optional[str] = Form(None, description="Date de requisition (YYYY-MM-DD)"),
    date_depot_1: Optional[str] = Form(None, description="Date de depot 1 (YYYY-MM-DD)"),
    date_depot_2: Optional[str] = Form(None, description="Date de depot 2 (YYYY-MM-DD)"),
    date_approbation_acte: Optional[str] = Form(None, description="Date d'approbation de l'acte (YYYY-MM-DD)"),
    
    # Inscription et depot
    dep_vol_inscription: Optional[str] = Form(None, description="Depot vol inscription"),
    numero_dep_vol_inscription: Optional[str] = Form(None, description="Numero depot vol inscription"),
    dep_vol_requisition: Optional[str] = Form(None, description="Depot vol requisition"),
    numero_dep_vol_requisition: Optional[str] = Form(None, description="Numero depot vol requisition"),
    
    # Fichiers
    files: List[UploadFile] = File(default=[]),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creer un import PROPRIETE avec tous les champs"""
    
    # Validation enums
    CHARGES = ["Voie(s) publique(e)", "Voie(s) d'acces", "Servitude(s)", "Aucune"]
    NATURES = ["Urbaine", "Suburbaine", "Rurale"]
    VOCATIONS = ["Edilitaire", "Agricole", "Forestiere", "Touristique"]
    OPERATIONS = ["Morcellement", "Immatriculation"]
    
    charge_valid = validate_enum(charge, CHARGES, "charge")
    nature_valid = validate_enum(nature, NATURES, "nature")
    vocation_valid = validate_enum(vocation, VOCATIONS, "vocation")
    type_operation_valid = validate_enum(type_operation, OPERATIONS, "type_operation")
    
    # Validation dates
    date_requisition_valid = validate_date_iso(date_requisition, "date_requisition")
    date_depot_1_valid = validate_date_iso(date_depot_1, "date_depot_1")
    date_depot_2_valid = validate_date_iso(date_depot_2, "date_depot_2")
    date_approbation_acte_valid = validate_date_iso(date_approbation_acte, "date_approbation_acte")
    
    # Construction payload avec null explicite
    payload = {
        "lot": lot.strip() if lot and lot.strip() else None,
        "titre": titre.strip() if titre and titre.strip() else None,
        "contenance": contenance,
        "proprietaire": proprietaire.strip() if proprietaire and proprietaire.strip() else None,
        "propriete_mere": propriete_mere.strip() if propriete_mere and propriete_mere.strip() else None,
        "titre_mere": titre_mere.strip() if titre_mere and titre_mere.strip() else None,
        "charge": charge_valid,
        "situation": situation.strip() if situation and situation.strip() else None,
        "nature": nature_valid,
        "vocation": vocation_valid,
        "numero_FN": numero_FN.strip() if numero_FN and numero_FN.strip() else None,
        "numero_requisition": numero_requisition.strip() if numero_requisition and numero_requisition.strip() else None,
        "type_operation": type_operation_valid,
        "date_requisition": date_requisition_valid,
        "date_depot_1": date_depot_1_valid,
        "date_depot_2": date_depot_2_valid,
        "date_approbation_acte": date_approbation_acte_valid,
        "dep_vol_inscription": dep_vol_inscription.strip() if dep_vol_inscription and dep_vol_inscription.strip() else None,
        "numero_dep_vol_inscription": numero_dep_vol_inscription.strip() if numero_dep_vol_inscription and numero_dep_vol_inscription.strip() else None,
        "dep_vol_requisition": dep_vol_requisition.strip() if dep_vol_requisition and dep_vol_requisition.strip() else None,
        "numero_dep_vol_requisition": numero_dep_vol_requisition.strip() if numero_dep_vol_requisition and numero_dep_vol_requisition.strip() else None
    }
    
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    staging = TopoStagingPropriete(
        source='topo',
        topo_user_id=user.id,
        topo_user_name=user.full_name,
        numero_ouverture=numero_ouverture,
        target_district_id=target_district_id,
        payload=payload,
        checksum=checksum,
        status='PENDING'
    )
    
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    # Sauvegarde fichiers
    files_saved = []
    for file in files:
        try:
            file_info = await save_file(file, 'proprietes', staging.id)
            staging_file = TopoStagingFile(
                propriete_id=staging.id,
                numero_ouverture=numero_ouverture,
                target_district_id=target_district_id,
                lot=lot.strip() if lot and lot.strip() else None,
                original_name=file_info['original_name'],
                stored_name=file_info['stored_name'],
                file_size=file_info['file_size'],
                mime_type=file_info['mime_type'],
                category='plan'
            )
            db.add(staging_file)
            files_saved.append(file_info)
        except Exception as e:
            print(f"Erreur fichier: {e}")
    
    db.commit()
    
    return ImportResponse(
        success=True,
        import_id=staging.id,
        batch_id=str(staging.batch_id),
        entity_type="propriete",
        files_uploaded=len(files_saved)
    )

# ROUTES - IMPORTS (LECTURE)
@app.get("/api/imports/")
async def list_imports(
    status: Optional[str] = "PENDING",
    entity_type: Optional[str] = None,
    district_id: Optional[int] = None,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = []
    
    if not entity_type or entity_type == 'demandeur':
        query = db.query(TopoStagingDemandeur)
        if status:
            query = query.filter(TopoStagingDemandeur.status == status.upper())
        if district_id:
            query = query.filter(TopoStagingDemandeur.target_district_id == district_id)
        
        for d in query.order_by(TopoStagingDemandeur.created_at.desc()).all():
            files_count = db.query(TopoStagingFile).filter(TopoStagingFile.demandeur_id == d.id).count()
            results.append({
                "id": d.id,
                "entity_type": "demandeur",
                "batch_id": str(d.batch_id),
                "status": d.status.lower(),
                "numero_ouverture": d.numero_ouverture,
                "district_id": d.target_district_id,
                "topo_user_name": d.topo_user_name,
                "import_date": d.created_at.isoformat(),
                "files_count": files_count,
                "raw_data": d.payload,
                "is_archived": d.status == 'ARCHIVED',
                "can_import": d.status in ['PENDING', 'ARCHIVED'],
                "has_errors": bool(d.error_reason),
                "error_summary": d.error_reason,
                "rejection_reason": d.rejection_reason or d.error_reason,
                "processed_at": d.validated_at.isoformat() if d.validated_at else None
            })
    
    if not entity_type or entity_type == 'propriete':
        query = db.query(TopoStagingPropriete)
        if status:
            query = query.filter(TopoStagingPropriete.status == status.upper())
        if district_id:
            query = query.filter(TopoStagingPropriete.target_district_id == district_id)
        
        for p in query.order_by(TopoStagingPropriete.created_at.desc()).all():
            files_count = db.query(TopoStagingFile).filter(TopoStagingFile.propriete_id == p.id).count()
            results.append({
                "id": p.id,
                "entity_type": "propriete",
                "batch_id": str(p.batch_id),
                "status": p.status.lower(),
                "numero_ouverture": p.numero_ouverture,
                "district_id": p.target_district_id,
                "topo_user_name": p.topo_user_name,
                "import_date": p.created_at.isoformat(),
                "files_count": files_count,
                "raw_data": p.payload,
                "is_archived": p.status == 'ARCHIVED',
                "can_import": p.status in ['PENDING', 'ARCHIVED'],
                "has_errors": bool(p.error_reason),
                "error_summary": p.error_reason,
                "rejection_reason": p.rejection_reason or p.error_reason,
                "processed_at": p.validated_at.isoformat() if p.validated_at else None
            })
    
    results.sort(key=lambda x: x['import_date'], reverse=True)
    
    stats = {
        "total": len(results),
        "pending": len([r for r in results if r['status'] == 'pending']),
        "archived": len([r for r in results if r['status'] == 'archived']),
        "validated": len([r for r in results if r['status'] == 'validated']),
        "rejected": len([r for r in results if r['status'] == 'rejected'])
    }
    
    return {
        "data": results,
        "stats": stats,
        "filters": {"status": status, "entity_type": entity_type, "district_id": district_id}
    }

@app.get("/api/imports/{import_id}")
async def get_import(
    import_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == import_id).first()
    
    if staging:
        files = db.query(TopoStagingFile).filter(TopoStagingFile.demandeur_id == import_id).all()
        return {
            "import": {
                "id": staging.id,
                "batch_id": str(staging.batch_id),
                "entity_type": "demandeur",
                "raw_data": staging.payload,
                "status": staging.status.lower(),
                "numero_ouverture": staging.numero_ouverture,
                "district_id": staging.target_district_id,
                "topo_user_name": staging.topo_user_name,
                "import_date": staging.created_at.isoformat(),
                "rejection_reason": staging.rejection_reason or staging.error_reason,
                "processed_at": staging.validated_at.isoformat() if staging.validated_at else None
            },
            "files": [{"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type, "category": f.category or "autre"} for f in files]
        }
    
    staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == import_id).first()
    
    if staging:
        files = db.query(TopoStagingFile).filter(TopoStagingFile.propriete_id == import_id).all()
        return {
            "import": {
                "id": staging.id,
                "batch_id": str(staging.batch_id),
                "entity_type": "propriete",
                "raw_data": staging.payload,
                "status": staging.status.lower(),
                "numero_ouverture": staging.numero_ouverture,
                "district_id": staging.target_district_id,
                "topo_user_name": staging.topo_user_name,
                "import_date": staging.created_at.isoformat(),
                "rejection_reason": staging.rejection_reason or staging.error_reason,
                "processed_at": staging.validated_at.isoformat() if staging.validated_at else None
            },
            "files": [{"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type, "category": f.category or "autre"} for f in files]
        }
    
    raise HTTPException(status_code=404, detail="Import introuvable")

# ROUTES - ACTIONS SUR IMPORTS
@app.put("/api/imports/{import_id}/status")
async def update_status(
    import_id: int,
    action: str = Form(...),
    archived_note: Optional[str] = Form(None),
    rejection_reason: Optional[str] = Form(None),
    user_email: Optional[str] = Form(None),
    user_name: Optional[str] = Form(None),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == import_id).first()
    
    if not staging:
        staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == import_id).first()
    
    if not staging:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    now = datetime.now(timezone.utc)
    email = user_email or user.email
    
    if action == 'validate':
        staging.status = 'VALIDATED'
        staging.validated_at = now
        staging.validated_by = user.id
    elif action == 'reject':
        if not rejection_reason:
            raise HTTPException(status_code=400, detail="Motif de rejet requis")
        staging.status = 'REJECTED'
        staging.rejection_reason = rejection_reason
        staging.rejected_at = now
        staging.rejected_by_email = email
        staging.validated_at = now
        staging.validated_by = user.id
    elif action == 'archive':
        staging.status = 'ARCHIVED'
        staging.archived_at = now
        staging.archived_by_email = email
        if archived_note:
            staging.archived_note = archived_note
    elif action == 'unarchive':
        staging.status = 'PENDING'
        staging.archived_at = None
        staging.archived_by_email = None
        staging.archived_note = None
    else:
        raise HTTPException(status_code=400, detail="Action invalide")
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Import {action}",
        "import_id": import_id,
        "new_status": staging.status.lower()
    }

# ROUTES - FICHIERS
@app.get("/api/v1/files/{file_id}")
async def download_file(
    file_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    if file.demandeur_id:
        entity_type = 'demandeurs'
        entity_id = file.demandeur_id
    elif file.propriete_id:
        entity_type = 'proprietes'
        entity_id = file.propriete_id
    else:
        entity_type = 'dossiers'
        entity_id = f"{file.target_district_id}_{file.numero_ouverture}"
    
    file_path = UPLOAD_DIR / entity_type / str(entity_id) / file.stored_name
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier physique introuvable")
    
    return FileResponse(
        path=str(file_path),
        filename=file.original_name,
        media_type=file.mime_type
    )

@app.post("/api/v1/files/upload", status_code=201)
async def upload_files_independent(
    numero_ouverture: str = Form(...),
    target_district_id: int = Form(...),
    cin: Optional[str] = Form(None),
    lot: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    CATEGORIES = ["cin", "plan", "titre", "requisition", "autre"]
    category_valid = validate_enum(category, CATEGORIES, "category") if category else "autre"
    
    demandeur_id = None
    propriete_id = None
    
    if cin and cin.strip():
        demandeur = db.query(TopoStagingDemandeur).filter(
            TopoStagingDemandeur.numero_ouverture == numero_ouverture,
            TopoStagingDemandeur.target_district_id == target_district_id,
            TopoStagingDemandeur.payload['cin'].astext == cin.strip()
        ).first()
        if demandeur:
            demandeur_id = demandeur.id
    
    if lot and lot.strip():
        propriete = db.query(TopoStagingPropriete).filter(
            TopoStagingPropriete.numero_ouverture == numero_ouverture,
            TopoStagingPropriete.target_district_id == target_district_id,
            TopoStagingPropriete.payload['lot'].astext == lot.strip()
        ).first()
        if propriete:
            propriete_id = propriete.id
    
    files_saved = []
    
    for file in files:
        try:
            if demandeur_id:
                entity_type = 'demandeurs'
                entity_id = demandeur_id
            elif propriete_id:
                entity_type = 'proprietes'
                entity_id = propriete_id
            else:
                entity_type = 'dossiers'
                entity_id = f"{target_district_id}_{numero_ouverture}"
            
            file_info = await save_file(file, entity_type, entity_id)
            
            staging_file = TopoStagingFile(
                numero_ouverture=numero_ouverture,
                target_district_id=target_district_id,
                demandeur_id=demandeur_id,
                propriete_id=propriete_id,
                cin=cin.strip() if cin and cin.strip() else None,
                lot=lot.strip() if lot and lot.strip() else None,
                original_name=file_info['original_name'],
                stored_name=file_info['stored_name'],
                file_size=file_info['file_size'],
                mime_type=file_info['mime_type'],
                category=category_valid
            )
            
            db.add(staging_file)
            files_saved.append({
                "filename": file_info['original_name'],
                "size": file_info['file_size'],
                "category": category_valid,
                "associated_to": "demandeur" if demandeur_id else ("propriete" if propriete_id else "dossier")
            })
            
        except Exception as e:
            print(f"Erreur fichier {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur upload: {str(e)}")
    
    db.commit()
    
    return {
        "success": True,
        "files_uploaded": len(files_saved),
        "files": files_saved,
        "dossier": {"numero_ouverture": numero_ouverture, "district_id": target_district_id},
        "associations": {"demandeur_found": demandeur_id is not None, "propriete_found": propriete_id is not None}
    }

# ROUTES - UTILITAIRES
@app.get("/")
def root():
    return {"app": "TopoManager API", "version": "2.0.2", "status": "healthy", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/stats")
async def get_stats(user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    total_dem = db.query(TopoStagingDemandeur).count()
    pending_dem = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.status == 'PENDING').count()
    total_prop = db.query(TopoStagingPropriete).count()
    pending_prop = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.status == 'PENDING').count()
    
    return {
        "total_imports": total_dem + total_prop,
        "pending": pending_dem + pending_prop,
        "demandeurs": total_dem,
        "proprietes": total_prop
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)