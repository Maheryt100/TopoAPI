"""app/schemas/__init__.py
Schemas Pydantic avec validation stricte des enums
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import date
from enum import Enum

# ENUMS STRICTS

class TitreDemandeur(str, Enum):
    MONSIEUR = "Monsieur"
    MADAME = "Madame"
    MADEMOISELLE = "Mademoiselle"

class Sexe(str, Enum):
    HOMME = "Homme"
    FEMME = "Femme"

class SituationFamiliale(str, Enum):
    NON_SPECIFIEE = "Non specifiee"
    CELIBATAIRE = "Celibataire"
    MARIE = "Marie(e)"
    VEUF = "Veuf/Veuve"
    DIVORCE = "Divorce(e)"

class RegimeMatrimonial(str, Enum):
    NON_SPECIFIE = "Non specifie"
    ZARA_MIRA = "Zara-Mira"
    KITAY_TELO = "Kitay telo an-dalana"
    SEPARATION = "Separations des biens"

class Charge(str, Enum):
    VOIE_PUBLIQUE = "Voie(s) publique(e)"
    VOIE_ACCES = "Voie(s) d'acces"
    SERVITUDE = "Servitude(s)"
    AUCUNE = "Aucune"

class Nature(str, Enum):
    URBAINE = "Urbaine"
    SUBURBAINE = "Suburbaine"
    RURALE = "Rurale"

class Vocation(str, Enum):
    EDILITAIRE = "Edilitaire"
    AGRICOLE = "Agricole"
    FORESTIERE = "Forestiere"
    TOURISTIQUE = "Touristique"

class TypeOperation(str, Enum):
    MORCELLEMENT = "Morcellement"
    IMMATRICULATION = "Immatriculation"

class FileCategory(str, Enum):
    CIN = "cin"
    PLAN = "plan"
    TITRE = "titre"
    REQUISITION = "requisition"
    AUTRE = "autre"

# AUTH

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user: dict

# DEMANDEUR

class DemandeurCreate(BaseModel):
    """Creation demandeur - tous champs optionnels sauf numero_ouverture"""
    numero_ouverture: str = Field(..., description="Numero d'ouverture du dossier")
    
    titre_demandeur: Optional[TitreDemandeur] = None
    nom_demandeur: Optional[str] = None
    prenom_demandeur: Optional[str] = None
    date_naissance: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    lieu_naissance: Optional[str] = None
    sexe: Optional[Sexe] = None
    occupation: Optional[str] = None
    
    nom_pere: Optional[str] = None
    nom_mere: Optional[str] = None
    
    cin: Optional[str] = None
    date_delivrance: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    lieu_delivrance: Optional[str] = None
    date_delivrance_duplicata: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    lieu_delivrance_duplicata: Optional[str] = None
    
    domiciliation: Optional[str] = None
    telephone: Optional[str] = None
    nationalite: Optional[str] = "Malagasy"
    
    situation_familiale: Optional[SituationFamiliale] = None
    regime_matrimoniale: Optional[RegimeMatrimonial] = None
    date_mariage: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    lieu_mariage: Optional[str] = None
    marie_a: Optional[str] = None
    
    @field_validator('date_naissance', 'date_delivrance', 'date_delivrance_duplicata', 'date_mariage')
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('Date must be in ISO format YYYY-MM-DD')

# PROPRIETE

class ProprieteCreate(BaseModel):
    """Creation propriete - tous champs optionnels sauf numero_ouverture"""
    numero_ouverture: str = Field(..., description="Numero d'ouverture du dossier")
    
    lot: Optional[str] = None
    titre: Optional[str] = None
    contenance: Optional[int] = Field(None, description="Contenance en m²")
    proprietaire: Optional[str] = None
    
    propriete_mere: Optional[str] = None
    titre_mere: Optional[str] = None
    
    charge: Optional[Charge] = None
    situation: Optional[str] = None
    nature: Optional[Nature] = None
    vocation: Optional[Vocation] = None
    
    numero_FN: Optional[str] = None
    numero_requisition: Optional[str] = None
    type_operation: Optional[TypeOperation] = None
    
    date_requisition: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    date_depot_1: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    date_depot_2: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    date_approbation_acte: Optional[str] = Field(None, description="Format ISO: YYYY-MM-DD")
    
    dep_vol_inscription: Optional[str] = None
    numero_dep_vol_inscription: Optional[str] = None
    dep_vol_requisition: Optional[str] = None
    numero_dep_vol_requisition: Optional[str] = None
    
    @field_validator('date_requisition', 'date_depot_1', 'date_depot_2', 'date_approbation_acte')
    @classmethod
    def validate_date_format(cls, v):
        if v is None:
            return v
        try:
            date.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError('Date must be in ISO format YYYY-MM-DD')

# FILES

class FileUploadRequest(BaseModel):
    """Upload fichiers - associe au dossier uniquement"""
    numero_ouverture: str = Field(..., description="Numero d'ouverture du dossier")
    category: Optional[FileCategory] = Field(None, description="Categorie du fichier")

# RESPONSES

class ImportResponse(BaseModel):
    success: bool
    import_id: int
    batch_id: str
    entity_type: str
    
class StagingListItem(BaseModel):
    id: int
    entity_type: str
    batch_id: str
    status: str
    numero_ouverture: str
    topo_user_name: str
    created_at: str
    files_count: int
    payload: dict