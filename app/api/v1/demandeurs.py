"""Routes demandeurs avec validateurs centralisés et documentation Swagger complète"""
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
    # Champs obligatoires
    numero_ouverture: str = Form(
        ...,
        description="Numéro d'ouverture du dossier",
        example="2024-001",
        min_length=1,
        max_length=50
    ),
    
    # Informations d'identité
    cin: Optional[str] = Form(
        None,
        description="Numéro CIN à 12 chiffres (obligatoire si nouveau demandeur)",
        example="123456789012",
        min_length=12,
        max_length=12,
        pattern="^[0-9]{12}$"
    ),
    
    titre_demandeur: Optional[str] = Form(
        None,
        description=f"Titre du demandeur. Valeurs possibles : {', '.join(VALID_TITRES)}",
        example="Monsieur"
    ),
    
    nom_demandeur: Optional[str] = Form(
        None,
        description="Nom de famille du demandeur",
        example="RAKOTO",
        max_length=40
    ),
    
    prenom_demandeur: Optional[str] = Form(
        None,
        description="Prénom(s) du demandeur",
        example="Jean Claude",
        max_length=50
    ),
    
    # Informations de naissance
    date_naissance: Optional[str] = Form(
        None,
        description="Date de naissance au format YYYY-MM-DD (doit avoir au moins 18 ans)",
        example="1990-01-15",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    lieu_naissance: Optional[str] = Form(
        None,
        description="Lieu de naissance",
        example="Antananarivo",
        max_length=100
    ),
    
    sexe: Optional[str] = Form(
        None,
        description=f"Sexe du demandeur. Valeurs possibles : {', '.join(VALID_SEXES)}",
        example="Homme"
    ),
    
    occupation: Optional[str] = Form(
        None,
        description="Profession ou occupation",
        example="Enseignant",
        max_length=100
    ),
    
    # Filiation
    nom_pere: Optional[str] = Form(
        None,
        description="Nom complet du père",
        example="RAKOTO Albert",
        max_length=100
    ),
    
    nom_mere: Optional[str] = Form(
        None,
        description="Nom complet de la mère",
        example="RASOA Marie",
        max_length=100
    ),
    
    # Informations CIN
    date_delivrance: Optional[str] = Form(
        None,
        description="Date de délivrance du CIN au format YYYY-MM-DD",
        example="2010-05-20",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    lieu_delivrance: Optional[str] = Form(
        None,
        description="Lieu de délivrance du CIN",
        example="Antananarivo",
        max_length=100
    ),
    
    date_delivrance_duplicata: Optional[str] = Form(
        None,
        description="Date de délivrance du duplicata CIN au format YYYY-MM-DD (si applicable)",
        example="2020-03-10",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    lieu_delivrance_duplicata: Optional[str] = Form(
        None,
        description="Lieu de délivrance du duplicata CIN (si applicable)",
        example="Antsirabe",
        max_length=100
    ),
    
    # Contact et domiciliation
    domiciliation: Optional[str] = Form(
        None,
        description="Adresse complète de domiciliation",
        example="Lot II A 25 Bis Ambohijanaka, Antananarivo",
        max_length=255
    ),
    
    telephone: Optional[str] = Form(
        None,
        description="Numéro de téléphone (format local ou international)",
        example="034 12 345 67",
        max_length=20
    ),
    
    nationalite: Optional[str] = Form(
        "Malagasy",
        description="Nationalité du demandeur (par défaut : Malagasy)",
        example="Malagasy",
        max_length=50
    ),
    
    # Situation familiale
    situation_familiale: Optional[str] = Form(
        "Non specifiee",
        description=f"Situation familiale. Valeurs possibles : {', '.join(VALID_SITUATIONS)}. Par défaut : Non specifiee",
        example="Celibataire"
    ),
    
    regime_matrimoniale: Optional[str] = Form(
        "Non specifie",
        description=f"Régime matrimonial. Valeurs possibles : {', '.join(VALID_REGIMES)}. Par défaut : Non specifie",
        example="Separations des biens"
    ),
    
    date_mariage: Optional[str] = Form(
        None,
        description="Date de mariage au format YYYY-MM-DD (si marié)",
        example="2015-06-12",
        pattern="^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
    ),
    
    lieu_mariage: Optional[str] = Form(
        None,
        description="Lieu de célébration du mariage (si marié)",
        example="Antsirabe",
        max_length=100
    ),
    
    marie_a: Optional[str] = Form(
        None,
        description="Nom complet du conjoint (si marié)",
        example="RANDRIA Sophie",
        max_length=100
    ),
    
    # Dépendances
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ## Créer un nouveau demandeur en staging
    
    Cette endpoint permet de créer un demandeur et de le placer en file d'attente (staging) 
    pour validation avant insertion définitive dans la base de données.
    
    ### Validations automatiques :
    - **Champs énumérés** : Vérification des valeurs autorisées pour titre, sexe, situation familiale, régime matrimonial
    - **Dates** : Validation du format YYYY-MM-DD et cohérence des dates
    - **CIN** : Format 12 chiffres obligatoire
    - **Âge** : Le demandeur doit avoir au moins 18 ans (date_naissance)
    
    ### Valeurs par défaut :
    - `nationalite` : "Malagasy"
    - `situation_familiale` : "Non specifiee"
    - `regime_matrimoniale` : "Non specifie"
    
    ### Réponse :
    Retourne un objet `ImportResponse` contenant :
    - `success` : Statut de l'opération
    - `import_id` : ID du record en staging
    - `batch_id` : ID du lot d'import
    - `entity_type` : Type d'entité ("demandeur")
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