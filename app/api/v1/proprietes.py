"""Routes propriétés avec validateurs centralisés"""
# app/api/v1/proprietes.py
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import json

from app.core.database import get_db
from app.core.validators import validate_enum, validate_date, clean_payload
from app.models.staging import TopoUser, TopoStagingPropriete
from app.schemas import ImportResponse
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/proprietes", tags=["Proprietes"])

# Constantes de validation
VALID_CHARGES = ["Voie(s) publique(e)", "Voie(s) d'acces", "Servitude(s)", "Aucune"]
VALID_NATURES = ["Urbaine", "Suburbaine", "Rurale"]
VALID_VOCATIONS = ["Edilitaire", "Agricole", "Forestiere", "Touristique"]
VALID_TYPES = ["Morcellement", "Immatriculation"]

@router.post("/", status_code=201, response_model=ImportResponse)
async def create_propriete(
    numero_ouverture: str = Form(...),
    lot: Optional[str] = Form(None),
    titre: Optional[str] = Form(None),
    contenance: Optional[int] = Form(None),
    proprietaire: Optional[str] = Form(None),
    propriete_mere: Optional[str] = Form(None),
    titre_mere: Optional[str] = Form(None),
    charge: Optional[str] = Form(None),
    situation: Optional[str] = Form(None),
    nature: Optional[str] = Form(None),
    vocation: Optional[str] = Form(None),
    numero_FN: Optional[str] = Form(None),
    numero_requisition: Optional[str] = Form(None),
    type_operation: Optional[str] = Form(None),
    date_requisition: Optional[str] = Form(None),
    date_depot_1: Optional[str] = Form(None),
    date_depot_2: Optional[str] = Form(None),
    date_approbation_acte: Optional[str] = Form(None),
    dep_vol_inscription: Optional[str] = Form(None),
    numero_dep_vol_inscription: Optional[str] = Form(None),
    dep_vol_requisition: Optional[str] = Form(None),
    numero_dep_vol_requisition: Optional[str] = Form(None),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crée une nouvelle propriété en staging
    
    Valide les champs enum et dates avant insertion
    """
    # Validations enum
    validate_enum(charge, VALID_CHARGES, "charge")
    validate_enum(nature, VALID_NATURES, "nature")
    validate_enum(vocation, VALID_VOCATIONS, "vocation")
    validate_enum(type_operation, VALID_TYPES, "type_operation")
    
    # Validations dates
    validate_date(date_requisition, "date_requisition")
    validate_date(date_depot_1, "date_depot_1")
    validate_date(date_depot_2, "date_depot_2")
    validate_date(date_approbation_acte, "date_approbation_acte")
    
    # Construction du payload propre
    fields = {
        'lot': lot, 
        'titre': titre, 
        'contenance': contenance, 
        'proprietaire': proprietaire,
        'propriete_mere': propriete_mere, 
        'titre_mere': titre_mere, 
        'charge': charge,
        'situation': situation, 
        'nature': nature, 
        'vocation': vocation,
        'numero_FN': numero_FN, 
        'numero_requisition': numero_requisition,
        'type_operation': type_operation, 
        'date_requisition': date_requisition,
        'date_depot_1': date_depot_1, 
        'date_depot_2': date_depot_2,
        'date_approbation_acte': date_approbation_acte, 
        'dep_vol_inscription': dep_vol_inscription,
        'numero_dep_vol_inscription': numero_dep_vol_inscription,
        'dep_vol_requisition': dep_vol_requisition,
        'numero_dep_vol_requisition': numero_dep_vol_requisition
    }
    
    payload = clean_payload(fields)
    
    # Création du staging record
    staging = TopoStagingPropriete(
        source='topo',
        topo_user_id=user.id,
        topo_user_name=user.full_name,
        numero_ouverture=numero_ouverture,
        payload=payload,
        checksum=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        status='PENDING'
    )
    
    try:
        db.add(staging)
        db.commit()
        db.refresh(staging)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erreur lors de la sauvegarde: {str(e)}")
    
    return ImportResponse(
        success=True,
        import_id=staging.id,
        batch_id=str(staging.batch_id),
        entity_type="propriete"
    )