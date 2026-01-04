# """app/schemas/__init__.py
"""
Schémas Pydantic pour validation et sérialisation
Tous les champs sont optionnels (FastAPI accepte données partielles)
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

# Auth
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    user: dict

# Demandeur (tous optionnels sauf metadata)
class DemandeurCreate(BaseModel):
    target_dossier_id: int
    target_district_id: int
    
    # Champs demandeur (tous optionnels)
    cin: Optional[str] = None
    titre_demandeur: Optional[str] = None
    nom_demandeur: Optional[str] = None
    prenom_demandeur: Optional[str] = None
    date_naissance: Optional[date] = None
    lieu_naissance: Optional[str] = None
    sexe: Optional[str] = None
    occupation: Optional[str] = None
    nom_pere: Optional[str] = None
    nom_mere: Optional[str] = None
    date_delivrance: Optional[date] = None
    lieu_delivrance: Optional[str] = None
    date_delivrance_duplicata: Optional[date] = None
    lieu_delivrance_duplicata: Optional[str] = None
    domiciliation: Optional[str] = None
    telephone: Optional[str] = None
    nationalite: Optional[str] = "Malagasy"
    situation_familiale: Optional[str] = None
    regime_matrimoniale: Optional[str] = None
    date_mariage: Optional[date] = None
    lieu_mariage: Optional[str] = None
    marie_a: Optional[str] = None

# Propriété (tous optionnels sauf metadata)
class ProprieteCreate(BaseModel):
    target_dossier_id: int
    target_district_id: int
    
    # Champs propriété (tous optionnels)
    lot: Optional[str] = None
    nature: Optional[str] = None
    type_operation: Optional[str] = None
    propriete_mere: Optional[str] = None
    titre_mere: Optional[str] = None
    titre: Optional[str] = None
    proprietaire: Optional[str] = None
    contenance: Optional[int] = None
    charge: Optional[str] = None
    situation: Optional[str] = None
    vocation: Optional[str] = None
    numero_FN: Optional[str] = None
    numero_requisition: Optional[str] = None
    date_requisition: Optional[date] = None
    dep_vol_requisition: Optional[str] = None
    numero_dep_vol_requisition: Optional[str] = None
    date_depot_1: Optional[date] = None
    date_depot_2: Optional[date] = None
    date_approbation_acte: Optional[date] = None
    dep_vol_inscription: Optional[str] = None
    numero_dep_vol_inscription: Optional[str] = None
    dep_vol: Optional[str] = None
    numero_dep_vol: Optional[str] = None

# Réponses
class ImportResponse(BaseModel):
    success: bool
    import_id: int
    batch_id: str
    entity_type: str
    files_uploaded: int = 0
    
class StagingListItem(BaseModel):
    id: int
    entity_type: str
    batch_id: str
    status: str
    target_dossier_id: int
    target_district_id: int
    topo_user_name: str
    created_at: str
    files_count: int
    payload: dict