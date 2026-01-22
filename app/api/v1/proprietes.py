"""Routes proprietes"""
# app/api/v1/proprietes.py
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date
import hashlib
import json

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingPropriete
from app.schemas import ImportResponse
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/proprietes", tags=["Proprietes"])

VALID_CHARGES = ["Voie(s) publique(e)", "Voie(s) d'acces", "Servitude(s)", "Aucune"]
VALID_NATURES = ["Urbaine", "Suburbaine", "Rurale"]
VALID_VOCATIONS = ["Edilitaire", "Agricole", "Forestiere", "Touristique"]
VALID_TYPES = ["Morcellement", "Immatriculation"]

def validate_enum(value: Optional[str], valid_values: list, field_name: str):
    if value and value not in valid_values:
        raise HTTPException(422, f"{field_name} invalide. Valeurs: {', '.join(valid_values)}")
    return value

def validate_date(value: Optional[str], field_name: str):
    if value:
        try:
            date.fromisoformat(value)
        except:
            raise HTTPException(422, f"{field_name} format: YYYY-MM-DD")
    return value

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
    validate_enum(charge, VALID_CHARGES, "charge")
    validate_enum(nature, VALID_NATURES, "nature")
    validate_enum(vocation, VALID_VOCATIONS, "vocation")
    validate_enum(type_operation, VALID_TYPES, "type_operation")
    
    validate_date(date_requisition, "date_requisition")
    validate_date(date_depot_1, "date_depot_1")
    validate_date(date_depot_2, "date_depot_2")
    validate_date(date_approbation_acte, "date_approbation_acte")
    
    payload = {}
    fields = {
        'lot': lot, 'titre': titre, 'contenance': contenance, 'proprietaire': proprietaire,
        'propriete_mere': propriete_mere, 'titre_mere': titre_mere, 'charge': charge,
        'situation': situation, 'nature': nature, 'vocation': vocation,
        'numero_FN': numero_FN, 'numero_requisition': numero_requisition,
        'type_operation': type_operation, 'date_requisition': date_requisition,
        'date_depot_1': date_depot_1, 'date_depot_2': date_depot_2,
        'date_approbation_acte': date_approbation_acte, 'dep_vol_inscription': dep_vol_inscription,
        'numero_dep_vol_inscription': numero_dep_vol_inscription,
        'dep_vol_requisition': dep_vol_requisition,
        'numero_dep_vol_requisition': numero_dep_vol_requisition
    }
    
    for key, value in fields.items():
        if value is not None:
            if isinstance(value, str) and value.strip():
                payload[key] = value.strip()
            elif not isinstance(value, str):
                payload[key] = value
    
    staging = TopoStagingPropriete(
        source='topo',
        topo_user_id=user.id,
        topo_user_name=user.full_name,
        numero_ouverture=numero_ouverture,
        payload=payload,
        checksum=hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(),
        status='PENDING'
    )
    
    db.add(staging)
    db.commit()
    db.refresh(staging)
    
    return ImportResponse(
        success=True,
        import_id=staging.id,
        batch_id=str(staging.batch_id),
        entity_type="propriete"
    )