# """app/api/v1/proprietes.py
"""
Routes pour les imports PROPRIÉTÉ - Version 2.0
Utilisation de numero_ouverture + validation stricte
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import hashlib
import json

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingPropriete, TopoStagingFile
from app.schemas import ImportResponse, Charge, Nature, Vocation, TypeOperation
from app.api.v1.auth import get_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/proprietes", tags=["Propriétés"])

# ========================================
# VALIDATEURS ENUM (réutilisés)
# ========================================

def validate_enum(value: Optional[str], enum_class, field_name: str):
    """Valide qu'une valeur correspond à un enum"""
    if value is None:
        return None
    try:
        return enum_class(value).value
    except ValueError:
        valid_values = [e.value for e in enum_class]
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} invalide. Valeurs acceptées: {', '.join(valid_values)}"
        )

def validate_date_iso(value: Optional[str], field_name: str):
    """Valide qu'une date est au format ISO"""
    if value is None:
        return None
    try:
        date.fromisoformat(value)
        return value
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"{field_name} doit être au format ISO (YYYY-MM-DD)"
        )

# ========================================
# ROUTES
# ========================================

@router.post("/", status_code=201, response_model=ImportResponse)
async def create_propriete(
    # ✅ Champs obligatoires MODIFIÉS
    numero_ouverture: str = Form(..., description="Numéro d'ouverture du dossier"),
    target_district_id: int = Form(..., description="ID du district cible"),
    
    # Champs propriété (tous optionnels avec validation)
    lot: Optional[str] = Form(None, description="Numéro de lot"),
    titre: Optional[str] = Form(None, description="Titre"),
    contenance: Optional[int] = Form(None, description="Contenance (m²)"),
    proprietaire: Optional[str] = Form(None, description="Nom du propriétaire"),
    
    propriete_mere: Optional[str] = Form(None, description="Propriété mère"),
    titre_mere: Optional[str] = Form(None, description="Titre mère"),
    
    charge: Optional[str] = Form(None, description="Charges"),
    situation: Optional[str] = Form(None, description="Situation géographique"),
    nature: Optional[str] = Form(None, description="Nature du terrain (Urbaine/Suburbaine/Rurale)"),
    vocation: Optional[str] = Form(None, description="Vocation du terrain"),
    
    # Champs administratifs
    numero_FN: Optional[str] = Form(None, description="Numéro FN"),
    numero_requisition: Optional[str] = Form(None, description="Numéro de réquisition"),
    type_operation: Optional[str] = Form(None, description="Type d'opération (Morcellement/Immatriculation)"),
    
    # Dates
    date_requisition: Optional[str] = Form(None, description="Date de réquisition (YYYY-MM-DD)"),
    date_depot_1: Optional[str] = Form(None, description="Date de dépôt 1 (YYYY-MM-DD)"),
    date_depot_2: Optional[str] = Form(None, description="Date de dépôt 2 (YYYY-MM-DD)"),
    date_approbation_acte: Optional[str] = Form(None, description="Date d'approbation de l'acte (YYYY-MM-DD)"),
    
    # Inscription et dépôt
    dep_vol_inscription: Optional[str] = Form(None, description="Dépôt vol inscription"),
    numero_dep_vol_inscription: Optional[str] = Form(None, description="Numéro dépôt vol inscription"),
    dep_vol_requisition: Optional[str] = Form(None, description="Dépôt vol réquisition"),
    numero_dep_vol_requisition: Optional[str] = Form(None, description="Numéro dépôt vol réquisition"),
    
    # Fichiers joints (optionnels)
    files: List[UploadFile] = File(default=[]),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Créer un import PROPRIÉTÉ
    ✅ Validation stricte des enums
    ✅ Utilisation de numero_ouverture
    """
    
    # ========================================
    # VALIDATION DES ENUMS
    # ========================================
    
    charge_valid = validate_enum(charge, Charge, "charge")
    nature_valid = validate_enum(nature, Nature, "nature")
    vocation_valid = validate_enum(vocation, Vocation, "vocation")
    type_operation_valid = validate_enum(type_operation, TypeOperation, "type_operation")
    
    # ========================================
    # VALIDATION DES DATES
    # ========================================
    
    date_requisition_valid = validate_date_iso(date_requisition, "date_requisition")
    date_depot_1_valid = validate_date_iso(date_depot_1, "date_depot_1")
    date_depot_2_valid = validate_date_iso(date_depot_2, "date_depot_2")
    date_approbation_acte_valid = validate_date_iso(date_approbation_acte, "date_approbation_acte")
    
    # ========================================
    # CONSTRUCTION PAYLOAD
    # ========================================
    
    payload = {}
    
    # Ajouter seulement les champs non-None et non-vides
    if lot and lot.strip(): 
        payload['lot'] = lot.strip()
    if titre and titre.strip(): 
        payload['titre'] = titre.strip()
    if contenance is not None: 
        payload['contenance'] = contenance
    if proprietaire and proprietaire.strip(): 
        payload['proprietaire'] = proprietaire.strip()
    if propriete_mere and propriete_mere.strip(): 
        payload['propriete_mere'] = propriete_mere.strip()
    if titre_mere and titre_mere.strip(): 
        payload['titre_mere'] = titre_mere.strip()
    if charge_valid: 
        payload['charge'] = charge_valid
    if situation and situation.strip(): 
        payload['situation'] = situation.strip()
    if nature_valid: 
        payload['nature'] = nature_valid
    if vocation_valid: 
        payload['vocation'] = vocation_valid
    if numero_FN and numero_FN.strip(): 
        payload['numero_FN'] = numero_FN.strip()
    if numero_requisition and numero_requisition.strip(): 
        payload['numero_requisition'] = numero_requisition.strip()
    if type_operation_valid: 
        payload['type_operation'] = type_operation_valid
    if date_requisition_valid: 
        payload['date_requisition'] = date_requisition_valid
    if date_depot_1_valid: 
        payload['date_depot_1'] = date_depot_1_valid
    if date_depot_2_valid: 
        payload['date_depot_2'] = date_depot_2_valid
    # if date_approbation_acte_valid: 
    #     payload['date_approbation_acte'] = date_approbation_acte_valid
    if dep_vol_inscription and dep_vol_inscription.strip(): 
        payload['dep_vol_inscription'] = dep_vol_inscription.strip()
    if numero_dep_vol_inscription and numero_dep_vol_inscription.strip(): 
        payload['numero_dep_vol_inscription'] = numero_dep_vol_inscription.strip()
    if dep_vol_requisition and dep_vol_requisition.strip(): 
        payload['dep_vol_requisition'] = dep_vol_requisition.strip()
    if numero_dep_vol_requisition and numero_dep_vol_requisition.strip(): 
        payload['numero_dep_vol_requisition'] = numero_dep_vol_requisition.strip()
    
    # Calculer checksum
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    # ========================================
    # CRÉER L'IMPORT STAGING
    # ========================================
    
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
    
    # ========================================
    # SAUVEGARDER LES FICHIERS
    # ========================================
    
    files_saved = []
    if files and len(files) > 0:
        for file in files:
            try:
                file_info = await FileService.save_file(file, 'proprietes', staging.id)
                
                # Nouveau modèle de fichier avec numero_ouverture
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
                print(f"Erreur fichier {file.filename}: {e}")
    
    db.commit()
    
    return ImportResponse(
        success=True,
        import_id=staging.id,
        batch_id=str(staging.batch_id),
        entity_type="propriete",
        files_uploaded=len(files_saved)
    )

@router.get("/{staging_id}")
def get_propriete_staging(
    staging_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer un import propriété par ID"""
    staging = db.query(TopoStagingPropriete).filter(
        TopoStagingPropriete.id == staging_id
    ).first()
    
    if not staging:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    files = db.query(TopoStagingFile).filter(
        TopoStagingFile.propriete_id == staging_id
    ).all()
    
    return {
        "success": True,
        "import": {
            "id": staging.id,
            "batch_id": str(staging.batch_id),
            "entity_type": "propriete",
            "payload": staging.payload,
            "status": staging.status,
            "numero_ouverture": staging.numero_ouverture,
            "target_district_id": staging.target_district_id,
            "topo_user_name": staging.topo_user_name,
            "created_at": staging.created_at.isoformat(),
            "error_reason": staging.error_reason
        },
        "files": [
            {
                "id": f.id,
                "name": f.original_name,
                "size": f.file_size,
                "mime_type": f.mime_type,
                "category": f.category,
                "lot": f.lot,
                "download_url": f"/api/v1/files/{f.id}"
            }
            for f in files
        ]
    }