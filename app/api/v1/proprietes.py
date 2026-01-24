"""Routes propriétés avec validateurs centralisés et documentation Swagger complète"""
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
    # Champs obligatoires
    numero_ouverture: str = Form(
        ...,
        description="Numéro d'ouverture du dossier",
        example="2024-001",
        min_length=1,
        max_length=50
    ),
    
    # Informations du lot
    lot: Optional[str] = Form(
        None,
        description="Numéro du lot de propriété",
        example="LOT-123-A",
        max_length=15
    ),
    
    titre: Optional[str] = Form(
        None,
        description="Numéro de titre foncier",
        example="TF-45678",
        max_length=50
    ),
    
    contenance: Optional[int] = Form(
        None,
        description="Superficie de la propriété en m² (doit être > 0)",
        example=500,
        gt=0
    ),
    
    proprietaire: Optional[str] = Form(
        None,
        description="Nom complet du propriétaire actuel",
        example="RAKOTO Jean",
        max_length=100
    ),
    
    # Informations de filiation
    propriete_mere: Optional[str] = Form(
        None,
        description="Référence de la propriété mère (pour les morcelements)",
        example="PM-2023-045",
        max_length=50
    ),
    
    titre_mere: Optional[str] = Form(
        None,
        description="Numéro de titre foncier de la propriété mère",
        example="TF-12345",
        max_length=50
    ),
    
    # Caractéristiques de la propriété
    charge: Optional[str] = Form(
        None,
        description=f"Charges grevant la propriété. Valeurs possibles : {', '.join(VALID_CHARGES)}",
        example="Voie(s) d'acces"
    ),
    
    situation: Optional[str] = Form(
        None,
        description="Description de la localisation géographique de la propriété",
        example="Quartier Ambohijanaka, Commune Urbaine d'Antananarivo",
        max_length=500
    ),
    
    nature: Optional[str] = Form(
        None,
        description=f"Nature de la propriété. Valeurs possibles : {', '.join(VALID_NATURES)}",
        example="Urbaine"
    ),
    
    vocation: Optional[str] = Form(
        None,
        description=f"Vocation de la propriété. Valeurs possibles : {', '.join(VALID_VOCATIONS)}",
        example="Edilitaire"
    ),
    
    # Références administratives
    numero_FN: Optional[str] = Form(
        None,
        description="Numéro de la Fiche Notariale",
        example="FN-2024-0123",
        max_length=30
    ),
    
    numero_requisition: Optional[str] = Form(
        None,
        description="Numéro de la réquisition d'immatriculation",
        example="REQ-2024-456",
        max_length=50
    ),
    
    type_operation: Optional[str] = Form(
        None,
        description=f"Type d'opération foncière. Valeurs possibles : {', '.join(VALID_TYPES)}",
        example="Morcellement"
    ),
    
    # Dates importantes
    date_requisition: Optional[str] = Form(
        None,
        description="Date de la réquisition au format YYYY-MM-DD",
        example="2024-01-15",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    date_depot_1: Optional[str] = Form(
        None,
        description="Date du premier dépôt au format YYYY-MM-DD",
        example="2024-02-01",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    date_depot_2: Optional[str] = Form(
        None,
        description="Date du second dépôt au format YYYY-MM-DD (si applicable)",
        example="2024-02-15",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    date_approbation_acte: Optional[str] = Form(
        None,
        description="Date d'approbation de l'acte au format YYYY-MM-DD (doit être >= date_requisition)",
        example="2024-03-10",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    # Dépôt/Volume - Inscription
    dep_vol_inscription: Optional[str] = Form(
        None,
        description="Référence Dépôt/Volume pour l'inscription",
        example="DV-2024-INS",
        max_length=50
    ),
    
    numero_dep_vol_inscription: Optional[str] = Form(
        None,
        description="Numéro du Dépôt/Volume pour l'inscription",
        example="0123",
        max_length=50
    ),
    
    # Dépôt/Volume - Réquisition
    dep_vol_requisition: Optional[str] = Form(
        None,
        description="Référence Dépôt/Volume pour la réquisition",
        example="DV-2024-REQ",
        max_length=50
    ),
    
    numero_dep_vol_requisition: Optional[str] = Form(
        None,
        description="Numéro du Dépôt/Volume pour la réquisition",
        example="0456",
        max_length=50
    ),
    
    # Dépendances
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## Créer une nouvelle propriété en staging
    
    Cette endpoint permet de créer une propriété et de la placer en file d'attente (staging) 
    pour validation avant insertion définitive dans la base de données.
    
    ### Validations automatiques :
    - **Champs énumérés** : Vérification des valeurs autorisées pour charge, nature, vocation, type_operation
    - **Dates** : Validation du format YYYY-MM-DD et cohérence des dates
    - **Contenance** : Doit être un nombre positif (> 0)
    - **Cohérence** : La date_approbation_acte doit être >= date_requisition
    
    ### Types d'opération :
    - **Morcellement** : Division d'une propriété mère en plusieurs lots
    - **Immatriculation** : Création d'un nouveau titre foncier
    
    ### Natures et vocations :
    - **Urbaine** : En zone urbaine (généralement vocation Edilitaire)
    - **Suburbaine** : En zone périurbaine
    - **Rurale** : En zone rurale (vocations Agricole, Forestiere, Touristique)
    
    ### Réponse :
    Retourne un objet `ImportResponse` contenant :
    - `success` : Statut de l'opération
    - `import_id` : ID du record en staging
    - `batch_id` : ID du lot d'import
    - `entity_type` : Type d'entité ("propriete")
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