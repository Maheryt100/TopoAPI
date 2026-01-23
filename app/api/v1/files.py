"""Routes fichiers avec validations renforcées"""
# app/api/v1/files.py
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import hashlib

from app.core.database import get_db
from app.core.config import get_settings
from app.models.staging import TopoUser, TopoStagingFile
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/files", tags=["Files"])
settings = get_settings()

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True)

VALID_CATEGORIES = ["cin", "plan", "titre", "requisition", "autre"]

async def save_file(file: UploadFile, numero_ouverture: str) -> dict:
    """
    Sauvegarde un fichier uploadé avec validations
    
    Args:
        file: Fichier uploadé
        numero_ouverture: Numéro de dossier
        
    Returns:
        Dictionnaire avec métadonnées du fichier
        
    Raises:
        HTTPException: Si validation échoue
    """
    # Création du répertoire de destination
    upload_dir = UPLOAD_DIR / "dossiers" / numero_ouverture
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Lecture et validation de la taille
    contents = await file.read()
    if len(contents) > settings.max_file_size:
        max_mb = settings.max_file_size / 1024 / 1024
        raise HTTPException(
            413, 
            f"Fichier trop volumineux: {len(contents)/1024/1024:.2f}MB (max {max_mb}MB)"
        )
    
    # Validation de l'extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            415, 
            f"Type de fichier non autorisé: {file_ext}. "
            f"Extensions acceptées: {', '.join(settings.allowed_extensions)}"
        )
    
    # Génération du nom de fichier unique
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_hash = hashlib.md5(file.filename.encode()).hexdigest()[:8]
    stored_name = f"{timestamp}_{file_hash}{file_ext}"
    
    # Sauvegarde du fichier
    file_path = upload_dir / stored_name
    try:
        file_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(500, f"Erreur sauvegarde fichier: {str(e)}")
    
    return {
        'original_name': file.filename,
        'stored_name': stored_name,
        'file_size': len(contents),
        'mime_type': file.content_type or 'application/octet-stream'
    }

@router.post("/upload", status_code=201)
async def upload_files(
    numero_ouverture: str = Form(...),
    category: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload de fichiers avec transaction atomique
    
    En cas d'erreur, tous les fichiers uploadés sont supprimés
    """
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(
            422, 
            f"Catégorie invalide. Valeurs acceptées: {', '.join(VALID_CATEGORIES)}"
        )
    
    cat = category or "autre"
    saved = []
    saved_paths = []
    
    try:
        # Upload de tous les fichiers
        for file in files:
            info = await save_file(file, numero_ouverture)
            
            # Ajout en base
            db.add(TopoStagingFile(
                numero_ouverture=numero_ouverture,
                category=cat,
                **info
            ))
            
            saved.append({
                "filename": info['original_name'],
                "size": info['file_size'],
                "category": cat
            })
            
            saved_paths.append(
                UPLOAD_DIR / "dossiers" / numero_ouverture / info['stored_name']
            )
        
        # Commit atomique
        db.commit()
        
    except HTTPException:
        # Propagation des erreurs de validation
        db.rollback()
        cleanup_files(saved_paths)
        raise
        
    except Exception as e:
        # Rollback et nettoyage en cas d'erreur
        db.rollback()
        cleanup_files(saved_paths)
        raise HTTPException(500, f"Erreur lors de l'upload: {str(e)}")
    
    return {
        "success": True,
        "files_uploaded": len(saved),
        "files": saved,
        "dossier": {"numero_ouverture": numero_ouverture}
    }

def cleanup_files(paths: List[Path]):
    """Supprime les fichiers temporaires en cas d'erreur"""
    for path in paths:
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass  # Ignore les erreurs de nettoyage