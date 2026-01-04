# """app/main.py
"""
FastAPI - Point d'entrée principal
Application de staging pour TopoManager
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi import Depends, HTTPException
from pathlib import Path

from app.core.config import get_settings
from app.core.database import Base, engine
from app.api.v1 import auth, demandeurs, proprietes, staging
from app.services.file_service import FileService
from app.models.staging import TopoStagingFile
from app.core.database import get_db
from sqlalchemy.orm import Session

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    API de staging pour TopoManager - Gestion des imports terrain
    
    ## Workflow
    1. Se connecter avec /api/v1/auth/login
    2. Créer des imports (demandeurs ou propriétés)
    3. GeODOC lit les imports via /api/v1/staging
    4. GeODOC valide et crée les entités définitives
    
    ## Notes
    - Tous les champs sont optionnels (sauf IDs de cible)
    - Les fichiers joints sont optionnels
    - JWT partagé avec GeODOC (même clé secrète)
    """
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(exist_ok=True)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(demandeurs.router, prefix="/api/v1")
app.include_router(proprietes.router, prefix="/api/v1")
app.include_router(staging.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "healthy", "version": settings.app_version}

@app.get("/api/v1/files/{file_id}")
def download_file(
    file_id: int,
    user = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Télécharger un fichier du staging"""
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    entity_type = 'demandeurs' if file.demandeur_id else 'proprietes'
    entity_id = file.demandeur_id or file.propriete_id
    
    file_path = FileService.get_file_path(entity_type, entity_id, file.stored_name)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier physique introuvable")
    
    return FileResponse(
        path=str(file_path),
        filename=file.original_name,
        media_type=file.mime_type
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.fastapi_port)