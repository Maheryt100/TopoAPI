"""Routes demandeurs avec validateurs centralisés"""
# app/api/v1/demandeurs.py
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import hashlib
import json

from app.core.database import get_db
from app.core.validators import validate_enum, validate_date, clean_payload
from app.models.staging import TopoUser, TopoStagingDemandeur
from app.schemas import ImportResponse
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/demandeurs", tags=["Demandeurs"])

# Constantes de validation
VALID_TITRES = ["Monsieur", "Madame", "Mademoiselle"]
VALID_SEXES = ["Homme", "Femme"]
VALID_SITUATIONS = ["Non specifiee", "Celibataire", "Marie(e)", "Veuf/Veuve", "Divorce(e)"]
VALID_REGIMES = ["Non specifie", "Zara-Mira", "Kitay telo an-dalana", "Separations des biens"]

@router.post("/", status_code=201, response_model=ImportResponse)
async def create_demandeur(
    numero_ouverture: str = Form(...),
    cin: Optional[str] = Form(None),
    titre_demandeur: Optional[str] = Form(None),
    nom_demandeur: Optional[str] = Form(None),
    prenom_demandeur: Optional[str] = Form(None),
    date_naissance: Optional[str] = Form(None),
    lieu_naissance: Optional[str] = Form(None),
    sexe: Optional[str] = Form(None),
    occupation: Optional[str] = Form(None),
    nom_pere: Optional[str] = Form(None),
    nom_mere: Optional[str] = Form(None),
    date_delivrance: Optional[str] = Form(None),
    lieu_delivrance: Optional[str] = Form(None),
    date_delivrance_duplicata: Optional[str] = Form(None),
    lieu_delivrance_duplicata: Optional[str] = Form(None),
    domiciliation: Optional[str] = Form(None),
    telephone: Optional[str] = Form(None),
    nationalite: Optional[str] = Form("Malagasy"),
    situation_familiale: Optional[str] = Form(None),
    regime_matrimoniale: Optional[str] = Form(None),
    date_mariage: Optional[str] = Form(None),
    lieu_mariage: Optional[str] = Form(None),
    marie_a: Optional[str] = Form(None),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau demandeur en staging
    
    Valide les champs enum et dates avant insertion
    """
    # Validations enum
    validate_enum(titre_demandeur, VALID_TITRES, "titre_demandeur")
    validate_enum(sexe, VALID_SEXES, "sexe")
    validate_enum(situation_familiale, VALID_SITUATIONS, "situation_familiale")
    validate_enum(regime_matrimoniale, VALID_REGIMES, "regime_matrimoniale")
    
    # Validations dates
    validate_date(date_naissance, "date_naissance")
    validate_date(date_delivrance, "date_delivrance")
    validate_date(date_delivrance_duplicata, "date_delivrance_duplicata")
    validate_date(date_mariage, "date_mariage")
    
    # Construction du payload propre
    fields = {
        'cin': cin, 
        'titre_demandeur': titre_demandeur, 
        'nom_demandeur': nom_demandeur,
        'prenom_demandeur': prenom_demandeur, 
        'date_naissance': date_naissance,
        'lieu_naissance': lieu_naissance, 
        'sexe': sexe, 
        'occupation': occupation,
        'nom_pere': nom_pere, 
        'nom_mere': nom_mere, 
        'date_delivrance': date_delivrance,
        'lieu_delivrance': lieu_delivrance, 
        'date_delivrance_duplicata': date_delivrance_duplicata,
        'lieu_delivrance_duplicata': lieu_delivrance_duplicata, 
        'domiciliation': domiciliation,
        'telephone': telephone, 
        'nationalite': nationalite, 
        'situation_familiale': situation_familiale,
        'regime_matrimoniale': regime_matrimoniale, 
        'date_mariage': date_mariage,
        'lieu_mariage': lieu_mariage, 
        'marie_a': marie_a
    }
    
    payload = clean_payload(fields)
    
    # Création du staging record
    staging = TopoStagingDemandeur(
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
        entity_type="demandeur"
    )