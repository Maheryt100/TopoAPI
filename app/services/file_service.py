#   """app/services/file_service.py
"""
Service de gestion des fichiers uploadés
"""
from fastapi import UploadFile
from pathlib import Path
import hashlib
from datetime import datetime
from app.core.config import get_settings

settings = get_settings()

class FileService:
    
    @staticmethod
    async def save_file(file: UploadFile, entity_type: str, entity_id: int) -> dict:
        """
        Sauvegarder un fichier uploadé
        """
        upload_dir = Path(settings.upload_dir) / entity_type / str(entity_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_hash = hashlib.md5(file.filename.encode()).hexdigest()[:8]
        extension = Path(file.filename).suffix
        stored_name = f"{timestamp}_{file_hash}{extension}"
        file_path = upload_dir / stored_name
        
        contents = await file.read()
        
        with open(file_path, 'wb') as f:
            f.write(contents)
        
        return {
            'original_name': file.filename,
            'stored_name': stored_name,
            'file_size': len(contents),
            'mime_type': file.content_type or 'application/octet-stream',
            'file_path': str(file_path)
        }
    
    @staticmethod
    def get_file_path(entity_type: str, entity_id: int, stored_name: str) -> Path:
        """Récupérer le chemin d'un fichier"""
        return Path(settings.upload_dir) / entity_type / str(entity_id) / stored_name