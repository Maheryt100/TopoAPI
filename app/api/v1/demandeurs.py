# """app/api/v1/demandeurs.py
"""
Routes pour les imports DEMANDEUR - Avec champs Form individuels
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import hashlib
import json

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingDemandeur, TopoStagingFile
from app.schemas import ImportResponse
from app.api.v1.auth import get_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/demandeurs", tags=["Demandeurs"])

@router.post("/", status_code=201, response_model=ImportResponse)
async def create_demandeur(
    # Champs obligatoires
    target_dossier_id: int = Form(..., description="ID du dossier cible"),
    target_district_id: int = Form(..., description="ID du district cible"),
    
    # Champs identité (optionnels)
    cin: Optional[str] = Form(None, description="Numéro CIN"),
    titre_demandeur: Optional[str] = Form(None, description="Titre (Monsieur, Madame, etc.)"),
    nom_demandeur: Optional[str] = Form(None, description="Nom de famille"),
    prenom_demandeur: Optional[str] = Form(None, description="Prénom"),
    date_naissance: Optional[date] = Form(None, description="Date de naissance (YYYY-MM-DD)"),
    lieu_naissance: Optional[str] = Form(None, description="Lieu de naissance"),
    sexe: Optional[str] = Form(None, description="Sexe (M/F)"),
    occupation: Optional[str] = Form(None, description="Profession"),
    
    # Champs filiation (optionnels)
    nom_pere: Optional[str] = Form(None, description="Nom du père"),
    nom_mere: Optional[str] = Form(None, description="Nom de la mère"),
    
    # Champs CIN (optionnels)
    date_delivrance: Optional[date] = Form(None, description="Date de délivrance CIN"),
    lieu_delivrance: Optional[str] = Form(None, description="Lieu de délivrance CIN"),
    date_delivrance_duplicata: Optional[date] = Form(None, description="Date délivrance duplicata"),
    lieu_delivrance_duplicata: Optional[str] = Form(None, description="Lieu délivrance duplicata"),
    
    # Champs contact (optionnels)
    domiciliation: Optional[str] = Form(None, description="Adresse"),
    telephone: Optional[str] = Form(None, description="Numéro de téléphone"),
    nationalite: Optional[str] = Form(None, description="Nationalité"),
    
    # Champs situation familiale (optionnels)
    situation_familiale: Optional[str] = Form(None, description="Situation familiale"),
    regime_matrimoniale: Optional[str] = Form(None, description="Régime matrimonial"),
    date_mariage: Optional[date] = Form(None, description="Date de mariage"),
    lieu_mariage: Optional[str] = Form(None, description="Lieu de mariage"),
    marie_a: Optional[str] = Form(None, description="Marié(e) à"),
    
    # Fichiers joints (optionnels)
    files: List[UploadFile] = File(default=[]),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Créer un import DEMANDEUR avec champs individuels
    Seuls target_dossier_id et target_district_id sont obligatoires
    """
    
    # Construire le payload JSON à partir des champs
    payload = {}
    
    # Ajouter seulement les champs non-None et non-vides
    if cin and cin.strip(): payload['cin'] = cin.strip()
    if titre_demandeur and titre_demandeur.strip(): payload['titre_demandeur'] = titre_demandeur.strip()
    if nom_demandeur and nom_demandeur.strip(): payload['nom_demandeur'] = nom_demandeur.strip()
    if prenom_demandeur and prenom_demandeur.strip(): payload['prenom_demandeur'] = prenom_demandeur.strip()
    if date_naissance: payload['date_naissance'] = date_naissance.isoformat()
    if lieu_naissance and lieu_naissance.strip(): payload['lieu_naissance'] = lieu_naissance.strip()
    if sexe and sexe.strip(): payload['sexe'] = sexe.strip()
    if occupation and occupation.strip(): payload['occupation'] = occupation.strip()
    if nom_pere and nom_pere.strip(): payload['nom_pere'] = nom_pere.strip()
    if nom_mere and nom_mere.strip(): payload['nom_mere'] = nom_mere.strip()
    if date_delivrance: payload['date_delivrance'] = date_delivrance.isoformat()
    if lieu_delivrance and lieu_delivrance.strip(): payload['lieu_delivrance'] = lieu_delivrance.strip()
    if date_delivrance_duplicata: payload['date_delivrance_duplicata'] = date_delivrance_duplicata.isoformat()
    if lieu_delivrance_duplicata and lieu_delivrance_duplicata.strip(): payload['lieu_delivrance_duplicata'] = lieu_delivrance_duplicata.strip()
    if domiciliation and domiciliation.strip(): payload['domiciliation'] = domiciliation.strip()
    if telephone and telephone.strip(): payload['telephone'] = telephone.strip()
    if nationalite and nationalite.strip(): payload['nationalite'] = nationalite.strip()
    if situation_familiale and situation_familiale.strip(): payload['situation_familiale'] = situation_familiale.strip()
    if regime_matrimoniale and regime_matrimoniale.strip(): payload['regime_matrimoniale'] = regime_matrimoniale.strip()
    if date_mariage: payload['date_mariage'] = date_mariage.isoformat()
    if lieu_mariage and lieu_mariage.strip(): payload['lieu_mariage'] = lieu_mariage.strip()
    if marie_a and marie_a.strip(): payload['marie_a'] = marie_a.strip()
    
    # Calculer checksum
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    # Créer l'import staging
    staging = TopoStagingDemandeur(
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
                file_info = await FileService.save_file(file, 'demandeurs', staging.id)
                
                staging_file = TopoStagingFile(
                    demandeur_id=staging.id,
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
        entity_type="demandeur",
        files_uploaded=len(files_saved)
    )

@router.get("/{staging_id}")
def get_demandeur_staging(
    staging_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer un import demandeur par ID"""
    staging = db.query(TopoStagingDemandeur).filter(
        TopoStagingDemandeur.id == staging_id
    ).first()
    
    if not staging:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    files = db.query(TopoStagingFile).filter(
        TopoStagingFile.demandeur_id == staging_id
    ).all()
    
    return {
        "success": True,
        "import": {
            "id": staging.id,
            "batch_id": str(staging.batch_id),
            "entity_type": "demandeur",
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