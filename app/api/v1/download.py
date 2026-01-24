"""Routes de téléchargement sécurisées pour TopoFlux"""
# app/api/v1/download.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pathlib import Path
import zipfile
import io
import logging

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import decode_token
from app.models.staging import TopoStagingFile

# Configuration
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

router = APIRouter(prefix="/download", tags=["Download"])
security = HTTPBearer()
settings = get_settings()

UPLOAD_DIR = Path(settings.upload_dir)


# ============================================
# AUTHENTIFICATION JWT
# ============================================
def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """
    Vérifie le token JWT envoyé par Laravel
    
    Le token est envoyé dans le header Authorization: Bearer {token}
    
    Returns:
        dict: Informations de l'utilisateur (identifier, payload)
    """
    token = credentials.credentials
    
    # Décoder le token
    identifier = decode_token(token)
    
    if not identifier:
        logger.error("❌ Token JWT invalide ou expiré")
        raise HTTPException(401, "Token invalide ou expiré")
    
    logger.info(f"✅ Token valide - Utilisateur: {identifier}")
    
    return {
        "identifier": identifier,
        "token_valid": True
    }


# ============================================
# TÉLÉCHARGEMENT FICHIER INDIVIDUEL
# ============================================
@router.get("/file/{file_id}")
async def download_file(
    file_id: int,
    auth: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Télécharge un fichier individuel
    
    **Authentification:**
    - Header: `Authorization: Bearer {jwt_token}`
    
    **Sécurité:**
    - Token JWT validé
    - Vérification existence fichier en BDD
    - Vérification existence fichier physique
    
    **Exemple d'appel depuis Laravel:**
    ```php
    $response = Http::withHeaders([
        'Authorization' => "Bearer {$jwtToken}"
    ])->get("{$fastApiUrl}/api/v1/download/file/{$fileId}");
    ```
    """
    logger.info(f"📥 Téléchargement fichier #{file_id}")
    logger.info(f"👤 Utilisateur: {auth['identifier']}")
    
    # 1. Récupérer le fichier en base
    file = db.query(TopoStagingFile).filter(TopoStagingFile.id == file_id).first()
    
    if not file:
        logger.error(f"❌ Fichier #{file_id} introuvable en base")
        raise HTTPException(404, "Fichier introuvable")
    
    # 2. Construire le chemin physique
    file_path = UPLOAD_DIR / "dossiers" / file.numero_ouverture / file.stored_name
    
    logger.info(f"📂 Chemin: {file_path}")
    
    # 3. Vérifier l'existence du fichier physique
    if not file_path.exists():
        logger.error(f"❌ Fichier physique introuvable: {file_path}")
        raise HTTPException(404, "Fichier physique introuvable sur le serveur")
    
    if not file_path.is_file():
        logger.error(f"❌ Chemin invalide (pas un fichier): {file_path}")
        raise HTTPException(500, "Le chemin ne pointe pas vers un fichier valide")
    
    logger.info(f"✅ Envoi fichier: {file.original_name} ({file.file_size} bytes)")
    
    # 4. Retourner le fichier avec les bons headers
    return FileResponse(
        path=str(file_path),
        filename=file.original_name,
        media_type=file.mime_type or "application/octet-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ============================================
# TÉLÉCHARGEMENT ZIP DOSSIER COMPLET
# ============================================
@router.get("/files/{numero_ouverture}/zip")
async def download_files_zip(
    numero_ouverture: str,
    auth: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Télécharge tous les fichiers d'un dossier en ZIP
    
    **Authentification:** Identique à download_file
    
    **Process:**
    1. Récupère tous les fichiers du dossier
    2. Crée un ZIP en mémoire
    3. Retourne le ZIP au client
    """
    logger.info(f"📦 Téléchargement ZIP dossier {numero_ouverture}")
    logger.info(f"👤 Utilisateur: {auth['identifier']}")
    
    # 1. Récupérer tous les fichiers du dossier
    files = db.query(TopoStagingFile).filter(
        TopoStagingFile.numero_ouverture == numero_ouverture
    ).all()
    
    if not files:
        logger.error(f"❌ Aucun fichier pour dossier {numero_ouverture}")
        raise HTTPException(404, f"Aucun fichier trouvé pour le dossier {numero_ouverture}")
    
    # 2. Créer le ZIP en mémoire
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        added_count = 0
        missing_files = []
        
        for file in files:
            file_path = UPLOAD_DIR / "dossiers" / file.numero_ouverture / file.stored_name
            
            if file_path.exists() and file_path.is_file():
                # Ajouter le fichier au ZIP avec son nom original
                zip_file.write(file_path, file.original_name)
                added_count += 1
                logger.info(f"  ✅ Ajouté: {file.original_name}")
            else:
                missing_files.append(file.original_name)
                logger.warning(f"  ⚠️ Fichier manquant: {file.original_name}")
    
    # 3. Vérifier qu'on a au moins 1 fichier
    if added_count == 0:
        logger.error(f"❌ Aucun fichier physique pour {numero_ouverture}")
        if missing_files:
            raise HTTPException(
                404, 
                f"Aucun fichier physique trouvé. Fichiers manquants: {', '.join(missing_files)}"
            )
        raise HTTPException(404, "Aucun fichier physique trouvé")
    
    logger.info(f"✅ ZIP créé: {added_count} fichier(s), {len(missing_files)} manquant(s)")
    
    # 4. Préparer le buffer pour le téléchargement
    zip_buffer.seek(0)
    zip_filename = f"dossier_{numero_ouverture}_fichiers.zip"
    
    # 5. Retourner le ZIP
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ============================================
# INFO FICHIERS (pour debug)
# ============================================
@router.get("/files/{numero_ouverture}/info")
async def get_files_info(
    numero_ouverture: str,
    auth: dict = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Informations sur les fichiers d'un dossier (pour debug)
    
    Retourne la liste des fichiers avec leur statut de disponibilité
    """
    files = db.query(TopoStagingFile).filter(
        TopoStagingFile.numero_ouverture == numero_ouverture
    ).all()
    
    if not files:
        raise HTTPException(404, f"Aucun fichier trouvé pour le dossier {numero_ouverture}")
    
    files_info = []
    total_size = 0
    available_count = 0
    
    for file in files:
        file_path = UPLOAD_DIR / "dossiers" / file.numero_ouverture / file.stored_name
        exists = file_path.exists() and file_path.is_file()
        
        if exists:
            available_count += 1
            total_size += file.file_size
        
        files_info.append({
            "id": file.id,
            "original_name": file.original_name,
            "stored_name": file.stored_name,
            "size": file.file_size,
            "category": file.category,
            "uploaded_at": file.uploaded_at.isoformat(),
            "available": exists,
            "physical_path": str(file_path) if exists else None,
            "download_url": f"/api/v1/download/file/{file.id}" if exists else None
        })
    
    return {
        "numero_ouverture": numero_ouverture,
        "total_files": len(files),
        "available_files": available_count,
        "missing_files": len(files) - available_count,
        "total_size": total_size,
        "files": files_info,
        "zip_download_url": f"/api/v1/download/files/{numero_ouverture}/zip" if available_count > 0 else None
    }


# ============================================
# HEALTH CHECK
# ============================================
@router.get("/health")
async def health_check():
    """
    Vérifie que le service de téléchargement fonctionne
    """
    upload_dir_exists = UPLOAD_DIR.exists()
    dossiers_dir_exists = (UPLOAD_DIR / "dossiers").exists()
    
    return {
        "status": "healthy" if upload_dir_exists else "degraded",
        "upload_dir": str(UPLOAD_DIR),
        "upload_dir_exists": upload_dir_exists,
        "dossiers_dir_exists": dossiers_dir_exists,
        "message": "Service de téléchargement opérationnel" if upload_dir_exists else "Répertoire uploads introuvable"
    }