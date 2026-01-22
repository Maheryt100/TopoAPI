"""Routes fichiers"""
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
    upload_dir = UPLOAD_DIR / "dossiers" / numero_ouverture
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stored_name = f"{timestamp}_{hashlib.md5(file.filename.encode()).hexdigest()[:8]}{Path(file.filename).suffix}"
    
    contents = await file.read()
    (upload_dir / stored_name).write_bytes(contents)
    
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
    if category and category not in VALID_CATEGORIES:
        raise HTTPException(422, f"Categorie invalide. Valeurs: {', '.join(VALID_CATEGORIES)}")
    
    cat = category or "autre"
    saved = []
    
    for file in files:
        try:
            info = await save_file(file, numero_ouverture)
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
        except Exception as e:
            raise HTTPException(500, f"Erreur upload: {e}")
    
    db.commit()
    
    return {
        "success": True,
        "files_uploaded": len(saved),
        "files": saved,
        "dossier": {"numero_ouverture": numero_ouverture}
    }