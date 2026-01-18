"""app/api/v1/files.py
Routes pour l'upload de fichiers INDÉPENDANT
✅ Upload sans demandeur/propriété préexistant
✅ Association possible via cin/lot
✅ SIMPLIFIÉ: Seulement numero_ouverture (pas de target_district_id)
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingFile, TopoStagingDemandeur, TopoStagingPropriete
from app.schemas import FileCategory
from app.api.v1.auth import get_current_user
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])

# ========================================
# VALIDATION ENUM
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

# ========================================
# ROUTES
# ========================================

@router.post("/upload", status_code=201)
async def upload_files_independent(
    # ✅ SIMPLIFIÉ: Seulement numero_ouverture
    numero_ouverture: str = Form(..., description="Numéro d'ouverture du dossier"),
    
    # ✅ Association optionnelle
    cin: Optional[str] = Form(None, description="CIN du demandeur (pour association)"),
    lot: Optional[str] = Form(None, description="Lot de la propriété (pour association)"),
    
    # ✅ Catégorie fichier (optionnelle)
    category: Optional[str] = Form(None, description="Catégorie: cin/plan/titre/requisition/autre"),
    
    # ✅ Fichiers (obligatoires)
    files: List[UploadFile] = File(..., description="Fichiers à uploader"),
    
    # Dependencies
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de fichiers INDÉPENDANT (SIMPLIFIÉ)
    
    Cas d'usage:
    1. Upload vers dossier global: numero_ouverture seul
    2. Upload vers demandeur: numero_ouverture + cin
    3. Upload vers propriété: numero_ouverture + lot
    
    Les fichiers sont TOUJOURS liés au dossier, avec association optionnelle
    """
    
    # Validation catégorie
    category_valid = validate_enum(category, FileCategory, "category")
    
    # Recherche d'association si cin/lot fourni
    demandeur_id = None
    propriete_id = None
    
    if cin and cin.strip():
        # Chercher demandeur correspondant dans ce dossier
        demandeur = db.query(TopoStagingDemandeur).filter(
            TopoStagingDemandeur.numero_ouverture == numero_ouverture,
            TopoStagingDemandeur.payload['cin'].astext == cin.strip()
        ).first()
        
        if demandeur:
            demandeur_id = demandeur.id
    
    if lot and lot.strip():
        # Chercher propriété correspondante dans ce dossier
        propriete = db.query(TopoStagingPropriete).filter(
            TopoStagingPropriete.numero_ouverture == numero_ouverture,
            TopoStagingPropriete.payload['lot'].astext == lot.strip()
        ).first()
        
        if propriete:
            propriete_id = propriete.id
    
    # ========================================
    # SAUVEGARDER LES FICHIERS
    # ========================================
    
    files_saved = []
    
    for file in files:
        try:
            # Déterminer le dossier de stockage
            if demandeur_id:
                entity_type = 'demandeurs'
                entity_id = demandeur_id
            elif propriete_id:
                entity_type = 'proprietes'
                entity_id = propriete_id
            else:
                entity_type = 'dossiers'
                entity_id = numero_ouverture  # Utiliser numero_ouverture comme ID
            
            file_info = await FileService.save_file(file, entity_type, entity_id)
            
            # Créer l'enregistrement
            staging_file = TopoStagingFile(
                numero_ouverture=numero_ouverture,
                demandeur_id=demandeur_id,
                propriete_id=propriete_id,
                cin=cin.strip() if cin and cin.strip() else None,
                lot=lot.strip() if lot and lot.strip() else None,
                original_name=file_info['original_name'],
                stored_name=file_info['stored_name'],
                file_size=file_info['file_size'],
                mime_type=file_info['mime_type'],
                category=category_valid or 'autre'
            )
            
            db.add(staging_file)
            files_saved.append({
                "filename": file_info['original_name'],
                "size": file_info['file_size'],
                "category": category_valid or 'autre',
                "associated_to": "demandeur" if demandeur_id else ("propriete" if propriete_id else "dossier")
            })
            
        except Exception as e:
            print(f"Erreur fichier {file.filename}: {e}")
            raise HTTPException(status_code=500, detail=f"Erreur upload: {str(e)}")
    
    db.commit()
    
    return {
        "success": True,
        "files_uploaded": len(files_saved),
        "files": files_saved,
        "dossier": {
            "numero_ouverture": numero_ouverture
        },
        "associations": {
            "demandeur_found": demandeur_id is not None,
            "propriete_found": propriete_id is not None
        }
    }

@router.get("/dossier/{numero_ouverture}")
def list_files_by_dossier(
    numero_ouverture: str,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lister tous les fichiers d'un dossier
    GET /api/v1/files/dossier/D2024-001
    """
    
    files = db.query(TopoStagingFile).filter(
        TopoStagingFile.numero_ouverture == numero_ouverture
    ).all()
    
    return {
        "success": True,
        "dossier": {
            "numero_ouverture": numero_ouverture
        },
        "total_files": len(files),
        "files": [
            {
                "id": f.id,
                "name": f.original_name,
                "size": f.file_size,
                "mime_type": f.mime_type,
                "category": f.category,
                "cin": f.cin,
                "lot": f.lot,
                "uploaded_at": f.uploaded_at.isoformat(),
                "associated_to": (
                    "demandeur" if f.demandeur_id else 
                    ("propriete" if f.propriete_id else "dossier")
                ),
                "download_url": f"/api/v1/files/{f.id}"
            }
            for f in files
        ]
    }

@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Supprimer un fichier"""
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    # Supprimer le fichier physique
    try:
        entity_type = (
            'demandeurs' if file.demandeur_id else 
            ('proprietes' if file.propriete_id else 'dossiers')
        )
        entity_id = file.demandeur_id or file.propriete_id or file.numero_ouverture
        file_path = FileService.get_file_path(entity_type, entity_id, file.stored_name)
        
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        print(f"Erreur suppression physique: {e}")
    
    # Supprimer l'enregistrement
    db.delete(file)
    db.commit()
    
    return {"success": True, "message": "Fichier supprimé"}