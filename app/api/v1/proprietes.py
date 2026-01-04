# """app/api/v1/proprietes.py
"""
Routes pour les imports PROPRIÉTÉ - Avec champs Form individuels
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import hashlib
import json

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingPropriete, TopoStagingFile
from app.schemas import ImportResponse
from app.api.v1.auth import get_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/proprietes", tags=["Propriétés"])

@router.post("/", status_code=201, response_model=ImportResponse)
async def create_propriete(
    # Champs obligatoires
    target_dossier_id: int = Form(..., description="ID du dossier cible"),
    target_district_id: int = Form(..., description="ID du district cible"),
    
    # Champs propriété (tous optionnels)
    lot: Optional[str] = Form(None, description="Numéro de lot"),
    nature: Optional[str] = Form(None, description="Nature du terrain"),
    type_operation: Optional[str] = Form(None, description="Type d'opération"),
    propriete_mere: Optional[str] = Form(None, description="Propriété mère"),
    titre_mere: Optional[str] = Form(None, description="Titre mère"),
    titre: Optional[str] = Form(None, description="Titre"),
    proprietaire: Optional[str] = Form(None, description="Nom du propriétaire"),
    contenance: Optional[int] = Form(None, description="Contenance (m²)"),
    charge: Optional[str] = Form(None, description="Charges"),
    situation: Optional[str] = Form(None, description="Situation géographique"),
    vocation: Optional[str] = Form(None, description="Vocation du terrain"),
    
    # Champs administratifs
    numero_FN: Optional[str] = Form(None, description="Numéro FN"),
    numero_requisition: Optional[str] = Form(None, description="Numéro de réquisition"),
    date_requisition: Optional[date] = Form(None, description="Date de réquisition"),
    dep_vol_requisition: Optional[str] = Form(None, description="Dépôt vol réquisition"),
    numero_dep_vol_requisition: Optional[str] = Form(None, description="Numéro dépôt vol réquisition"),
    
    # Dates de dépôt
    date_depot_1: Optional[date] = Form(None, description="Date de dépôt 1"),
    date_depot_2: Optional[date] = Form(None, description="Date de dépôt 2"),
    date_approbation_acte: Optional[date] = Form(None, description="Date d'approbation de l'acte"),
    
    # Inscription et dépôt
    dep_vol_inscription: Optional[str] = Form(None, description="Dépôt vol inscription"),
    numero_dep_vol_inscription: Optional[str] = Form(None, description="Numéro dépôt vol inscription"),
    dep_vol: Optional[str] = Form(None, description="Dépôt vol"),
    numero_dep_vol: Optional[str] = Form(None, description="Numéro dépôt vol"),
    
    # Fichiers joints (optionnels)
    files: List[UploadFile] = File(default=[]),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Créer un import PROPRIÉTÉ avec champs individuels
    Seuls target_dossier_id et target_district_id sont obligatoires
    """
    
    # Construire le payload JSON à partir des champs
    payload = {}
    
    # Ajouter seulement les champs non-None et non-vides
    if lot and lot.strip(): payload['lot'] = lot.strip()
    if nature and nature.strip(): payload['nature'] = nature.strip()
    if type_operation and type_operation.strip(): payload['type_operation'] = type_operation.strip()
    if propriete_mere and propriete_mere.strip(): payload['propriete_mere'] = propriete_mere.strip()
    if titre_mere and titre_mere.strip(): payload['titre_mere'] = titre_mere.strip()
    if titre and titre.strip(): payload['titre'] = titre.strip()
    if proprietaire and proprietaire.strip(): payload['proprietaire'] = proprietaire.strip()
    if contenance is not None: payload['contenance'] = contenance
    if charge and charge.strip(): payload['charge'] = charge.strip()
    if situation and situation.strip(): payload['situation'] = situation.strip()
    if vocation and vocation.strip(): payload['vocation'] = vocation.strip()
    if numero_FN and numero_FN.strip(): payload['numero_FN'] = numero_FN.strip()
    if numero_requisition and numero_requisition.strip(): payload['numero_requisition'] = numero_requisition.strip()
    if date_requisition: payload['date_requisition'] = date_requisition.isoformat()
    if dep_vol_requisition and dep_vol_requisition.strip(): payload['dep_vol_requisition'] = dep_vol_requisition.strip()
    if numero_dep_vol_requisition and numero_dep_vol_requisition.strip(): payload['numero_dep_vol_requisition'] = numero_dep_vol_requisition.strip()
    if date_depot_1: payload['date_depot_1'] = date_depot_1.isoformat()
    if date_depot_2: payload['date_depot_2'] = date_depot_2.isoformat()
    if date_approbation_acte: payload['date_approbation_acte'] = date_approbation_acte.isoformat()
    if dep_vol_inscription and dep_vol_inscription.strip(): payload['dep_vol_inscription'] = dep_vol_inscription.strip()
    if numero_dep_vol_inscription and numero_dep_vol_inscription.strip(): payload['numero_dep_vol_inscription'] = numero_dep_vol_inscription.strip()
    if dep_vol and dep_vol.strip(): payload['dep_vol'] = dep_vol.strip()
    if numero_dep_vol and numero_dep_vol.strip(): payload['numero_dep_vol'] = numero_dep_vol.strip()
    
    # Calculer checksum
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    # Créer l'import staging
    staging = TopoStagingPropriete(
        source='topo',
        topo_user_id=user.id,
        topo_user_name=user.full_name,
        target_dossier_id=target_dossier_id,
        target_district_id=target_district_id,
        payload=payload,
        checksum=checksum,
        status='PENDING'
    )
    
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    # Sauvegarder les fichiers
    files_saved = []
    if files and len(files) > 0:
        for file in files:
            try:
                file_info = await FileService.save_file(file, 'proprietes', staging.id)
                
                staging_file = TopoStagingFile(
                    propriete_id=staging.id,
                    original_name=file_info['original_name'],
                    stored_name=file_info['stored_name'],
                    file_size=file_info['file_size'],
                    mime_type=file_info['mime_type']
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
        from fastapi import HTTPException
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
            "target_dossier_id": staging.target_dossier_id,
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
                "download_url": f"/api/v1/files/{f.id}"
            }
            for f in files
        ]
    }