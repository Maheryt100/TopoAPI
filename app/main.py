"""
FastAPI TopoManager app/main.py
"""
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger, and_
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.sql import func, text
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
import hashlib, json, jwt, bcrypt, os
from dotenv import load_dotenv

load_dotenv()

# CONFIG
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/Odoc2")
JWT_SECRET = os.getenv("JWT_SECRET")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODELS
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
    numero_ouverture = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingPropriete(Base):
    __tablename__ = "topo_staging_proprietes"
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), default='topo')
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'))
    topo_user_name = Column(String(100))
    numero_ouverture = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingFile(Base):
    __tablename__ = "topo_staging_files"
    id = Column(Integer, primary_key=True)
    numero_ouverture = Column(String(50), nullable=False, index=True)
    category = Column(String(50))
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(bind=engine)

# SCHEMAS
class LoginRequest(BaseModel):
    username: str
    password: str

class ImportResponse(BaseModel):
    success: bool
    import_id: int
    batch_id: str
    entity_type: str

# APP
app = FastAPI(title="TopoManager API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
security = HTTPBearer()

# UTILS
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def create_token(identifier: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": identifier, "role": role, "exp": expire, "iat": datetime.now(timezone.utc)}, JWT_SECRET, "HS256")

def decode_token(token: str) -> Optional[str]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"]).get("sub")
    except:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> TopoUser:
    identifier = decode_token(credentials.credentials)
    if not identifier:
        raise HTTPException(401, "Token invalide")
    user = db.query(TopoUser).filter((TopoUser.username == identifier) | (TopoUser.email == identifier)).first()
    if not user and '@' in identifier:
        user = TopoUser(username=identifier.split('@')[0], email=identifier, full_name=identifier.split('@')[0].replace('.', ' ').title(),
                       hashed_password=hash_password(f"auto_{identifier}"), role="operator", is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    if not user or not user.is_active:
        raise HTTPException(401, "Utilisateur introuvable")
    return user

async def save_file(file: UploadFile, numero_ouverture: str) -> dict:
    upload_dir = UPLOAD_DIR / "dossiers" / numero_ouverture
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stored_name = f"{timestamp}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}{Path(file.filename).suffix}"
    contents = await file.read()
    (upload_dir / stored_name).write_bytes(contents)
    return {'original_name': file.filename, 'stored_name': stored_name, 'file_size': len(contents), 'mime_type': file.content_type or 'application/octet-stream'}

def validate_enum(v: Optional[str], vals: List[str], name: str):
    if v is None:
        return None
    if v not in vals:
        raise HTTPException(422, f"{name} invalide. Valeurs: {', '.join(vals)}")
    return v

def validate_date(v: Optional[str], name: str):
    if v is None:
        return None
    try:
        date.fromisoformat(v)
        return v
    except:
        raise HTTPException(422, f"{name} format: YYYY-MM-DD")

# AUTH
@app.post("/api/v1/auth/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(TopoUser).filter(TopoUser.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Identifiants incorrects")
    if not user.is_active:
        raise HTTPException(403, "Compte desactive")
    return {"access_token": create_token(user.email, user.role), "user": {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role}}

@app.get("/api/v1/auth/me")
async def get_me(user: TopoUser = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "email": user.email, "full_name": user.full_name, "role": user.role}

# DEMANDEURS
@app.post("/api/v1/demandeurs/", status_code=201, response_model=ImportResponse)
async def create_demandeur(
    numero_ouverture: str = Form(..., description="Numero d'ouverture du dossier"),
    cin: Optional[str] = Form(None, description="Numero CIN"),
    titre_demandeur: Optional[str] = Form(None, description="Titre - Valeurs: Monsieur, Madame, Mademoiselle"),
    nom_demandeur: Optional[str] = Form(None, description="Nom de famille"),
    prenom_demandeur: Optional[str] = Form(None, description="Prenom"),
    date_naissance: Optional[str] = Form(None, description="Date naissance - Format: YYYY-MM-DD"),
    lieu_naissance: Optional[str] = Form(None, description="Lieu de naissance"),
    sexe: Optional[str] = Form(None, description="Sexe - Valeurs: Homme, Femme"),
    occupation: Optional[str] = Form(None, description="Profession"),
    nom_pere: Optional[str] = Form(None, description="Nom du pere"),
    nom_mere: Optional[str] = Form(None, description="Nom de la mere"),
    date_delivrance: Optional[str] = Form(None, description="Date delivrance CIN - Format: YYYY-MM-DD"),
    lieu_delivrance: Optional[str] = Form(None, description="Lieu delivrance CIN"),
    date_delivrance_duplicata: Optional[str] = Form(None, description="Date duplicata - Format: YYYY-MM-DD"),
    lieu_delivrance_duplicata: Optional[str] = Form(None, description="Lieu duplicata"),
    domiciliation: Optional[str] = Form(None, description="Adresse"),
    telephone: Optional[str] = Form(None, description="Telephone"),
    nationalite: Optional[str] = Form("Malagasy", description="Nationalite"),
    situation_familiale: Optional[str] = Form(None, description="Situation - Valeurs: Non specifiee, Celibataire, Marie(e), Veuf/Veuve, Divorce(e)"),
    regime_matrimoniale: Optional[str] = Form(None, description="Regime - Valeurs: Non specifie, Zara-Mira, Kitay telo an-dalana, Separations des biens"),
    date_mariage: Optional[str] = Form(None, description="Date mariage - Format: YYYY-MM-DD"),
    lieu_mariage: Optional[str] = Form(None, description="Lieu mariage"),
    marie_a: Optional[str] = Form(None, description="Marie(e) a"),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    titre_v = validate_enum(titre_demandeur, ["Monsieur", "Madame", "Mademoiselle"], "titre_demandeur")
    sexe_v = validate_enum(sexe, ["Homme", "Femme"], "sexe")
    situation_v = validate_enum(situation_familiale, ["Non specifiee", "Celibataire", "Marie(e)", "Veuf/Veuve", "Divorce(e)"], "situation_familiale")
    regime_v = validate_enum(regime_matrimoniale, ["Non specifie", "Zara-Mira", "Kitay telo an-dalana", "Separations des biens"], "regime_matrimoniale")
    dn = validate_date(date_naissance, "date_naissance")
    dd = validate_date(date_delivrance, "date_delivrance")
    ddd = validate_date(date_delivrance_duplicata, "date_delivrance_duplicata")
    dm = validate_date(date_mariage, "date_mariage")
    
    payload = {
        "cin": cin.strip() if cin and cin.strip() else None,
        "titre_demandeur": titre_v,
        "nom_demandeur": nom_demandeur.strip() if nom_demandeur and nom_demandeur.strip() else None,
        "prenom_demandeur": prenom_demandeur.strip() if prenom_demandeur and prenom_demandeur.strip() else None,
        "date_naissance": dn,
        "lieu_naissance": lieu_naissance.strip() if lieu_naissance and lieu_naissance.strip() else None,
        "sexe": sexe_v,
        "occupation": occupation.strip() if occupation and occupation.strip() else None,
        "nom_pere": nom_pere.strip() if nom_pere and nom_pere.strip() else None,
        "nom_mere": nom_mere.strip() if nom_mere and nom_mere.strip() else None,
        "date_delivrance": dd,
        "lieu_delivrance": lieu_delivrance.strip() if lieu_delivrance and lieu_delivrance.strip() else None,
        "date_delivrance_duplicata": ddd,
        "lieu_delivrance_duplicata": lieu_delivrance_duplicata.strip() if lieu_delivrance_duplicata and lieu_delivrance_duplicata.strip() else None,
        "domiciliation": domiciliation.strip() if domiciliation and domiciliation.strip() else None,
        "telephone": telephone.strip() if telephone and telephone.strip() else None,
        "nationalite": nationalite.strip() if nationalite and nationalite.strip() else "Malagasy",
        "situation_familiale": situation_v,
        "regime_matrimoniale": regime_v,
        "date_mariage": dm,
        "lieu_mariage": lieu_mariage.strip() if lieu_mariage and lieu_mariage.strip() else None,
        "marie_a": marie_a.strip() if marie_a and marie_a.strip() else None
    }
    
    staging = TopoStagingDemandeur(source='topo', topo_user_id=user.id, topo_user_name=user.full_name,
                                   numero_ouverture=numero_ouverture, payload=payload,
                                   checksum=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), status='PENDING')
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    return ImportResponse(success=True, import_id=staging.id, batch_id=str(staging.batch_id), entity_type="demandeur")

# PROPRIETES
@app.post("/api/v1/proprietes/", status_code=201, response_model=ImportResponse)
async def create_propriete(
    numero_ouverture: str = Form(..., description="Numero d'ouverture du dossier"),
    lot: Optional[str] = Form(None, description="Numero de lot"),
    titre: Optional[str] = Form(None, description="Titre"),
    contenance: Optional[int] = Form(None, description="Contenance en m²"),
    proprietaire: Optional[str] = Form(None, description="Nom proprietaire"),
    propriete_mere: Optional[str] = Form(None, description="Propriete mere"),
    titre_mere: Optional[str] = Form(None, description="Titre mere"),
    charge: Optional[str] = Form(None, description="Charges - Valeurs: Voie(s) publique(e), Voie(s) d'acces, Servitude(s), Aucune"),
    situation: Optional[str] = Form(None, description="Situation geographique"),
    nature: Optional[str] = Form(None, description="Nature - Valeurs: Urbaine, Suburbaine, Rurale"),
    vocation: Optional[str] = Form(None, description="Vocation - Valeurs: Edilitaire, Agricole, Forestiere, Touristique"),
    numero_FN: Optional[str] = Form(None, description="Numero FN"),
    numero_requisition: Optional[str] = Form(None, description="Numero requisition"),
    type_operation: Optional[str] = Form(None, description="Type - Valeurs: Morcellement, Immatriculation"),
    date_requisition: Optional[str] = Form(None, description="Date requisition - Format: YYYY-MM-DD"),
    date_depot_1: Optional[str] = Form(None, description="Date depot 1 - Format: YYYY-MM-DD"),
    date_depot_2: Optional[str] = Form(None, description="Date depot 2 - Format: YYYY-MM-DD"),
    date_approbation_acte: Optional[str] = Form(None, description="Date approbation - Format: YYYY-MM-DD"),
    dep_vol_inscription: Optional[str] = Form(None, description="Depot vol inscription"),
    numero_dep_vol_inscription: Optional[str] = Form(None, description="Numero depot vol inscription"),
    dep_vol_requisition: Optional[str] = Form(None, description="Depot vol requisition"),
    numero_dep_vol_requisition: Optional[str] = Form(None, description="Numero depot vol requisition"),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    charge_v = validate_enum(charge, ["Voie(s) publique(e)", "Voie(s) d'acces", "Servitude(s)", "Aucune"], "charge")
    nature_v = validate_enum(nature, ["Urbaine", "Suburbaine", "Rurale"], "nature")
    vocation_v = validate_enum(vocation, ["Edilitaire", "Agricole", "Forestiere", "Touristique"], "vocation")
    type_v = validate_enum(type_operation, ["Morcellement", "Immatriculation"], "type_operation")
    dr = validate_date(date_requisition, "date_requisition")
    dd1 = validate_date(date_depot_1, "date_depot_1")
    dd2 = validate_date(date_depot_2, "date_depot_2")
    daa = validate_date(date_approbation_acte, "date_approbation_acte")
    
    payload = {
        "lot": lot.strip() if lot and lot.strip() else None,
        "titre": titre.strip() if titre and titre.strip() else None,
        "contenance": contenance,
        "proprietaire": proprietaire.strip() if proprietaire and proprietaire.strip() else None,
        "propriete_mere": propriete_mere.strip() if propriete_mere and propriete_mere.strip() else None,
        "titre_mere": titre_mere.strip() if titre_mere and titre_mere.strip() else None,
        "charge": charge_v,
        "situation": situation.strip() if situation and situation.strip() else None,
        "nature": nature_v,
        "vocation": vocation_v,
        "numero_FN": numero_FN.strip() if numero_FN and numero_FN.strip() else None,
        "numero_requisition": numero_requisition.strip() if numero_requisition and numero_requisition.strip() else None,
        "type_operation": type_v,
        "date_requisition": dr,
        "date_depot_1": dd1,
        "date_depot_2": dd2,
        "date_approbation_acte": daa,
        "dep_vol_inscription": dep_vol_inscription.strip() if dep_vol_inscription and dep_vol_inscription.strip() else None,
        "numero_dep_vol_inscription": numero_dep_vol_inscription.strip() if numero_dep_vol_inscription and numero_dep_vol_inscription.strip() else None,
        "dep_vol_requisition": dep_vol_requisition.strip() if dep_vol_requisition and dep_vol_requisition.strip() else None,
        "numero_dep_vol_requisition": numero_dep_vol_requisition.strip() if numero_dep_vol_requisition and numero_dep_vol_requisition.strip() else None
    }
    
    staging = TopoStagingPropriete(source='topo', topo_user_id=user.id, topo_user_name=user.full_name,
                                   numero_ouverture=numero_ouverture, payload=payload,
                                   checksum=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), status='PENDING')
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    return ImportResponse(success=True, import_id=staging.id, batch_id=str(staging.batch_id), entity_type="propriete")

# UPLOAD FICHIERS
@app.post("/api/v1/files/upload", status_code=201)
async def upload_files(
    numero_ouverture: str = Form(...),
    category: Optional[str] = Form(None, description="Categorie - Valeurs: cin, plan, titre, requisition, autre"),
    files: List[UploadFile] = File(...),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cat = validate_enum(category, ["cin", "plan", "titre", "requisition", "autre"], "category") or "autre"
    
    saved = []
    for file in files:
        try:
            info = await save_file(file, numero_ouverture)
            db.add(TopoStagingFile(numero_ouverture=numero_ouverture, **info, category=cat))
            saved.append({"filename": info['original_name'], "size": info['file_size'], "category": cat})
        except Exception as e:
            raise HTTPException(500, f"Erreur: {e}")
    
    db.commit()
    return {"success": True, "files_uploaded": len(saved), "files": saved, "dossier": {"numero_ouverture": numero_ouverture}}

# LISTE IMPORTS
@app.get("/api/imports/")
async def list_imports(status: Optional[str] = "PENDING", entity_type: Optional[str] = None, numero_ouverture: Optional[str] = None,
                      user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    results = []
    
    if not entity_type or entity_type == 'demandeur':
        q = db.query(TopoStagingDemandeur)
        if status:
            q = q.filter(TopoStagingDemandeur.status == status.upper())
        if numero_ouverture:
            q = q.filter(TopoStagingDemandeur.numero_ouverture == numero_ouverture)
        
        for d in q.order_by(TopoStagingDemandeur.created_at.desc()).all():
            fc = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == d.numero_ouverture).count()
            results.append({"id": d.id, "entity_type": "demandeur", "batch_id": str(d.batch_id), "status": d.status.lower(),
                          "numero_ouverture": d.numero_ouverture, "topo_user_name": d.topo_user_name, "import_date": d.created_at.isoformat(),
                          "files_count": fc, "raw_data": d.payload, "is_archived": d.status == 'ARCHIVED', "can_import": d.status in ['PENDING', 'ARCHIVED'],
                          "has_errors": bool(d.error_reason), "error_summary": d.error_reason, "rejection_reason": d.rejection_reason or d.error_reason,
                          "processed_at": d.rejected_at.isoformat() if d.rejected_at else None})
    
    if not entity_type or entity_type == 'propriete':
        q = db.query(TopoStagingPropriete)
        if status:
            q = q.filter(TopoStagingPropriete.status == status.upper())
        if numero_ouverture:
            q = q.filter(TopoStagingPropriete.numero_ouverture == numero_ouverture)
        
        for p in q.order_by(TopoStagingPropriete.created_at.desc()).all():
            fc = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == p.numero_ouverture).count()
            results.append({"id": p.id, "entity_type": "propriete", "batch_id": str(p.batch_id), "status": p.status.lower(),
                          "numero_ouverture": p.numero_ouverture, "topo_user_name": p.topo_user_name, "import_date": p.created_at.isoformat(),
                          "files_count": fc, "raw_data": p.payload, "is_archived": p.status == 'ARCHIVED', "can_import": p.status in ['PENDING', 'ARCHIVED'],
                          "has_errors": bool(p.error_reason), "error_summary": p.error_reason, "rejection_reason": p.rejection_reason or p.error_reason,
                          "processed_at": p.rejected_at.isoformat() if p.rejected_at else None})
    
    if not entity_type or entity_type == 'fichier':
        q = db.query(TopoStagingFile)
        if numero_ouverture:
            q = q.filter(TopoStagingFile.numero_ouverture == numero_ouverture)
        
        grouped = {}
        for f in q.order_by(TopoStagingFile.uploaded_at.desc()).all():
            key = f.numero_ouverture
            if key not in grouped:
                grouped[key] = {"files": [], "first_upload": f.uploaded_at}
            grouped[key]["files"].append({"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type, "category": f.category})
        
        for num, data in grouped.items():
            results.append({"id": f"files_{num}", "entity_type": "fichier", "batch_id": f"files_{num}", "status": "pending",
                          "numero_ouverture": num, "topo_user_name": "Import fichiers", "import_date": data["first_upload"].isoformat(),
                          "files_count": len(data["files"]), "raw_data": {}, "is_archived": False, "can_import": True,
                          "has_errors": False, "error_summary": None, "rejection_reason": None, "processed_at": None,
                          "preview": {"files": data["files"]}})
    
    results.sort(key=lambda x: x['import_date'], reverse=True)
    stats = {"total": len(results), "pending": len([r for r in results if r['status'] == 'pending']),
            "archived": len([r for r in results if r['status'] == 'archived']), "rejected": len([r for r in results if r['status'] == 'rejected'])}
    
    return {"data": results, "stats": stats, "filters": {"status": status, "entity_type": entity_type, "numero_ouverture": numero_ouverture}}

# DETAIL IMPORT
@app.get("/api/imports/{import_id}")
async def get_import(import_id: str, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Récupérer détail d'un import
    ✅ CORRIGÉ: Validation stricte entity_type
    """
    
    # ========================================
    # CAS 1: Import fichiers virtuel
    # ========================================
    if str(import_id).startswith("files_"):
        num = str(import_id).replace("files_", "")
        files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == num).all()
        if not files:
            raise HTTPException(404, "Import introuvable")
        
        return {
            "import": {
                "id": import_id,
                "batch_id": import_id,
                "entity_type": "fichier",  # ✅ Type explicite
                "raw_data": {},
                "status": "pending",
                "numero_ouverture": num,
                "topo_user_name": "Import fichiers",
                "import_date": files[0].uploaded_at.isoformat(),
                "rejection_reason": None,
                "processed_at": None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    # ========================================
    # CAS 2: Import demandeur
    # ========================================
    staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == int(import_id)).first()
    if staging:
        files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == staging.numero_ouverture).all()
        
        # ✅ CORRECTION: entity_type explicite et garanti
        return {
            "import": {
                "id": staging.id,
                "batch_id": str(staging.batch_id),
                "entity_type": "demandeur",  # ✅ Type GARANTI
                "raw_data": staging.payload,
                "status": staging.status.lower(),
                "numero_ouverture": staging.numero_ouverture,
                "topo_user_name": staging.topo_user_name,
                "import_date": staging.created_at.isoformat(),
                "rejection_reason": staging.rejection_reason or staging.error_reason,
                "processed_at": staging.rejected_at.isoformat() if staging.rejected_at else None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    # ========================================
    # CAS 3: Import propriété
    # ========================================
    staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == int(import_id)).first()
    if staging:
        files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == staging.numero_ouverture).all()
        
        # ✅ CORRECTION: entity_type explicite et garanti
        return {
            "import": {
                "id": staging.id,
                "batch_id": str(staging.batch_id),
                "entity_type": "propriete",  # ✅ Type GARANTI
                "raw_data": staging.payload,
                "status": staging.status.lower(),
                "numero_ouverture": staging.numero_ouverture,
                "topo_user_name": staging.topo_user_name,
                "import_date": staging.created_at.isoformat(),
                "rejection_reason": staging.rejection_reason or staging.error_reason,
                "processed_at": staging.rejected_at.isoformat() if staging.rejected_at else None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    raise HTTPException(404, "Import introuvable")

# ACTIONS IMPORT
@app.put("/api/imports/{import_id}/action")
async def import_action(import_id: str, action: str = Form(...), archived_note: Optional[str] = Form(None),
                       rejection_reason: Optional[str] = Form(None), user_email: Optional[str] = Form(None),
                       user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if str(import_id).startswith("files_"):
        return {"success": True, "message": "Import fichiers pret", "import_id": import_id, "new_status": "pending"}
    
    staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == int(import_id)).first()
    if not staging:
        staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == int(import_id)).first()
    if not staging:
        raise HTTPException(404, "Import introuvable")
    
    now = datetime.now(timezone.utc)
    email = user_email or user.email
    
    if action == 'reject':
        if not rejection_reason:
            raise HTTPException(400, "Motif requis")
        staging.status, staging.rejection_reason, staging.rejected_at, staging.rejected_by_email = 'REJECTED', rejection_reason, now, email
    elif action == 'archive':
        staging.status, staging.archived_at, staging.archived_by_email = 'ARCHIVED', now, email
        if archived_note:
            staging.archived_note = archived_note
    elif action == 'unarchive':
        staging.status, staging.archived_at, staging.archived_by_email, staging.archived_note = 'PENDING', None, None, None
    else:
        raise HTTPException(400, "Action invalide: reject, archive, unarchive")
    
    db.commit()
    return {"success": True, "message": f"Import {action}", "import_id": import_id, "new_status": staging.status.lower()}

# FICHIERS
@app.get("/api/v1/files/{file_id}")
async def download_file(file_id: int, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    if not file:
        raise HTTPException(404, "Fichier introuvable")
    
    path = UPLOAD_DIR / "dossiers" / file.numero_ouverture / file.stored_name
    
    if not path.exists():
        raise HTTPException(404, "Fichier physique introuvable")
    
    return FileResponse(path=str(path), filename=file.original_name, media_type=file.mime_type)

@app.get("/api/v1/files/dossier/{numero_ouverture}")
def list_files(numero_ouverture: str, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == numero_ouverture).all()
    return {"success": True, "dossier": {"numero_ouverture": numero_ouverture}, "total_files": len(files),
           "files": [{"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type,
                     "category": f.category, "uploaded_at": f.uploaded_at.isoformat(),
                     "download_url": f"/api/v1/files/{f.id}"} for f in files]}

@app.delete("/api/v1/files/{file_id}")
def delete_file(file_id: int, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    if not file:
        raise HTTPException(404, "Fichier introuvable")
    
    try:
        path = UPLOAD_DIR / "dossiers" / file.numero_ouverture / file.stored_name
        if path.exists():
            path.unlink()
    except Exception as e:
        print(f"Erreur suppression: {e}")
    
    db.delete(file)
    db.commit()
    return {"success": True, "message": "Fichier supprime"}

@app.delete("/api/imports/{import_id}/files")
def cleanup_files(import_id: str, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if str(import_id).startswith("files_"):
        num = str(import_id).replace("files_", "")
        cnt = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == num).delete()
    else:
        staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == int(import_id)).first()
        if not staging:
            staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == int(import_id)).first()
        if not staging:
            raise HTTPException(404, "Import introuvable")
        cnt = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == staging.numero_ouverture).delete()
    
    db.commit()
    return {"success": True, "message": "Fichiers nettoyes", "files_deleted": cnt}

# GET DEMANDEUR/PROPRIETE
@app.get("/api/v1/demandeurs/{staging_id}")
def get_demandeur(staging_id: int, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    staging = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.id == staging_id).first()
    if not staging:
        raise HTTPException(404, "Import introuvable")
    files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == staging.numero_ouverture).all()
    return {"success": True, "import": {"id": staging.id, "batch_id": str(staging.batch_id), "entity_type": "demandeur",
                                       "payload": staging.payload, "status": staging.status, "numero_ouverture": staging.numero_ouverture,
                                       "topo_user_name": staging.topo_user_name, "created_at": staging.created_at.isoformat(),
                                       "error_reason": staging.error_reason},
           "files": [{"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type,
                     "category": f.category, "download_url": f"/api/v1/files/{f.id}"} for f in files]}

@app.get("/api/v1/proprietes/{staging_id}")
def get_propriete(staging_id: int, user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    staging = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.id == staging_id).first()
    if not staging:
        raise HTTPException(404, "Import introuvable")
    files = db.query(TopoStagingFile).filter(TopoStagingFile.numero_ouverture == staging.numero_ouverture).all()
    return {"success": True, "import": {"id": staging.id, "batch_id": str(staging.batch_id), "entity_type": "propriete",
                                       "payload": staging.payload, "status": staging.status, "numero_ouverture": staging.numero_ouverture,
                                       "topo_user_name": staging.topo_user_name, "created_at": staging.created_at.isoformat(),
                                       "error_reason": staging.error_reason},
           "files": [{"id": f.id, "name": f.original_name, "size": f.file_size, "mime_type": f.mime_type,
                     "category": f.category, "download_url": f"/api/v1/files/{f.id}"} for f in files]}

# UTILS
@app.get("/")
def root():
    return {"app": "TopoManager API", "version": "2.1.0", "status": "healthy", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/stats")
async def stats(user: TopoUser = Depends(get_current_user), db: Session = Depends(get_db)):
    td = db.query(TopoStagingDemandeur).count()
    pd = db.query(TopoStagingDemandeur).filter(TopoStagingDemandeur.status == 'PENDING').count()
    tp = db.query(TopoStagingPropriete).count()
    pp = db.query(TopoStagingPropriete).filter(TopoStagingPropriete.status == 'PENDING').count()
    return {"total_imports": td + tp, "pending": pd + pp, "demandeurs": td, "proprietes": tp}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)