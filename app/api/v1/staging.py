"""app/api/v1/staging.py
Routes pour la lecture et validation du staging - Version SIMPLIFIÉE
✅ Affichage unifié: demandeurs + propriétés + fichiers orphelins
✅ Suppression target_district_id
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingDemandeur, TopoStagingPropriete, TopoStagingFile
from app.api.v1.auth import get_current_user

router = APIRouter(tags=["Imports"])

@router.get("/")
def list_imports(
    status: Optional[str] = "PENDING",
    entity_type: Optional[str] = None,  # demandeur, propriete, fichier
    numero_ouverture: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste tous les imports en staging avec enrichissement des données
    ✅ NOUVEAU: Inclut les fichiers orphelins comme type 'fichier'
    
    Query params:
    - status: PENDING, VALIDATED, REJECTED
    - entity_type: demandeur, propriete, fichier
    - numero_ouverture: Filtrer par numéro de dossier
    
    GET /api/imports?status=PENDING
    GET /api/imports?numero_ouverture=D2024-001
    GET /api/imports?entity_type=fichier
    """
    
    results = []
    
    # ========================================
    # RÉCUPÉRER DEMANDEURS
    # ========================================
    
    if not entity_type or entity_type == 'demandeur':
        query_dem = db.query(TopoStagingDemandeur)
        
        if status:
            query_dem = query_dem.filter(TopoStagingDemandeur.status == status.upper())
        if numero_ouverture:
            query_dem = query_dem.filter(TopoStagingDemandeur.numero_ouverture == numero_ouverture)
        
        demandeurs = query_dem.order_by(TopoStagingDemandeur.created_at.desc()).all()
        
        for d in demandeurs:
            files_count = db.query(TopoStagingFile).filter(
                TopoStagingFile.demandeur_id == d.id
            ).count()
            
            results.append({
                "id": d.id,
                "entity_type": "demandeur",
                "batch_id": str(d.batch_id),
                "status": d.status.lower(),
                "numero_ouverture": d.numero_ouverture,
                "topo_user_name": d.topo_user_name,
                "import_date": d.created_at.isoformat(),
                "files_count": files_count,
                "raw_data": d.payload,
                
                # Métadonnées pour le frontend
                "dossier_nom": f"Dossier {d.numero_ouverture}",
                "rejection_reason": d.error_reason,
                "processed_at": d.validated_at.isoformat() if d.validated_at else None,
                
                # Aperçu données
                "preview": {
                    "nom": d.payload.get('nom_demandeur'),
                    "prenom": d.payload.get('prenom_demandeur'),
                    "cin": d.payload.get('cin')
                }
            })
    
    # ========================================
    # RÉCUPÉRER PROPRIÉTÉS
    # ========================================
    
    if not entity_type or entity_type == 'propriete':
        query_prop = db.query(TopoStagingPropriete)
        
        if status:
            query_prop = query_prop.filter(TopoStagingPropriete.status == status.upper())
        if numero_ouverture:
            query_prop = query_prop.filter(TopoStagingPropriete.numero_ouverture == numero_ouverture)
        
        proprietes = query_prop.order_by(TopoStagingPropriete.created_at.desc()).all()
        
        for p in proprietes:
            files_count = db.query(TopoStagingFile).filter(
                TopoStagingFile.propriete_id == p.id
            ).count()
            
            results.append({
                "id": p.id,
                "entity_type": "propriete",
                "batch_id": str(p.batch_id),
                "status": p.status.lower(),
                "numero_ouverture": p.numero_ouverture,
                "topo_user_name": p.topo_user_name,
                "import_date": p.created_at.isoformat(),
                "files_count": files_count,
                "raw_data": p.payload,
                
                "dossier_nom": f"Dossier {p.numero_ouverture}",
                "rejection_reason": p.error_reason,
                "processed_at": p.validated_at.isoformat() if p.validated_at else None,
                
                # Aperçu données
                "preview": {
                    "lot": p.payload.get('lot'),
                    "titre": p.payload.get('titre'),
                    "contenance": p.payload.get('contenance')
                }
            })
    
    # ========================================
    # ✅ NOUVEAU: RÉCUPÉRER FICHIERS ORPHELINS
    # ========================================
    
    if not entity_type or entity_type == 'fichier':
        # Fichiers sans demandeur ni propriété = fichiers du dossier global
        query_files = db.query(TopoStagingFile).filter(
            and_(
                TopoStagingFile.demandeur_id == None,
                TopoStagingFile.propriete_id == None
            )
        )
        
        if numero_ouverture:
            query_files = query_files.filter(TopoStagingFile.numero_ouverture == numero_ouverture)
        
        # Grouper par numero_ouverture pour créer un "import fichier"
        fichiers_groupes = {}
        
        for file in query_files.order_by(TopoStagingFile.uploaded_at.desc()).all():
            key = file.numero_ouverture
            
            if key not in fichiers_groupes:
                fichiers_groupes[key] = {
                    "files": [],
                    "first_upload": file.uploaded_at
                }
            
            fichiers_groupes[key]["files"].append({
                "id": file.id,
                "name": file.original_name,
                "size": file.file_size,
                "mime_type": file.mime_type,
                "category": file.category
            })
        
        # Créer un "import virtuel" pour chaque groupe de fichiers
        for numero, data in fichiers_groupes.items():
            results.append({
                "id": f"files_{numero}",  # ID virtuel
                "entity_type": "fichier",
                "batch_id": f"files_{numero}",
                "status": "pending",  # Les fichiers orphelins sont toujours pending
                "numero_ouverture": numero,
                "topo_user_name": "Import fichiers",
                "import_date": data["first_upload"].isoformat(),
                "files_count": len(data["files"]),
                "raw_data": {},
                
                "dossier_nom": f"Dossier {numero}",
                "rejection_reason": None,
                "processed_at": None,
                
                # Liste des fichiers
                "preview": {
                    "files": data["files"]
                }
            })
    
    # ========================================
    # TRIER ET PAGINER
    # ========================================
    
    results.sort(key=lambda x: x['import_date'], reverse=True)
    
    total = len(results)
    results = results[offset:offset + limit]
    
    # ========================================
    # CALCULER STATS
    # ========================================
    
    stats = {
        "total": total,
        "pending": len([r for r in results if r['status'] == 'pending']),
        "validated": len([r for r in results if r['status'] == 'validated']),
        "rejected": len([r for r in results if r['status'] == 'rejected']),
        "with_warnings": 0
    }
    
    return {
        "data": results,
        "total": total,
        "stats": stats,
        "filters": {
            "status": status,
            "entity_type": entity_type,
            "numero_ouverture": numero_ouverture
        }
    }

@router.get("/{import_id}")
def get_import_detail(
    import_id: str,  # Peut être int ou "files_{numero}"
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer UN import par ID avec tous ses fichiers
    ✅ NOUVEAU: Gère aussi les imports de fichiers virtuels
    
    GET /api/imports/123
    GET /api/imports/files_D2024-001
    """
    
    # ========================================
    # CAS 1: Import fichiers virtuel
    # ========================================
    
    if str(import_id).startswith("files_"):
        numero_ouverture = str(import_id).replace("files_", "")
        
        files = db.query(TopoStagingFile).filter(
            and_(
                TopoStagingFile.numero_ouverture == numero_ouverture,
                TopoStagingFile.demandeur_id == None,
                TopoStagingFile.propriete_id == None
            )
        ).all()
        
        if not files:
            raise HTTPException(status_code=404, detail="Import fichiers introuvable")
        
        return {
            "import": {
                "id": import_id,
                "batch_id": import_id,
                "entity_type": "fichier",
                "raw_data": {},
                "status": "pending",
                "numero_ouverture": numero_ouverture,
                "topo_user_name": "Import fichiers",
                "import_date": files[0].uploaded_at.isoformat(),
                "rejection_reason": None,
                "processed_at": None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    # ========================================
    # CAS 2: Import demandeur
    # ========================================
    
    staging_dem = db.query(TopoStagingDemandeur).filter(
        TopoStagingDemandeur.id == int(import_id)
    ).first()
    
    if staging_dem:
        files = db.query(TopoStagingFile).filter(
            TopoStagingFile.demandeur_id == int(import_id)
        ).all()
        
        return {
            "import": {
                "id": staging_dem.id,
                "batch_id": str(staging_dem.batch_id),
                "entity_type": "demandeur",
                "raw_data": staging_dem.payload,
                "status": staging_dem.status.lower(),
                "numero_ouverture": staging_dem.numero_ouverture,
                "topo_user_name": staging_dem.topo_user_name,
                "import_date": staging_dem.created_at.isoformat(),
                "rejection_reason": staging_dem.error_reason,
                "processed_at": staging_dem.validated_at.isoformat() if staging_dem.validated_at else None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "cin": f.cin,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    # ========================================
    # CAS 3: Import propriété
    # ========================================
    
    staging_prop = db.query(TopoStagingPropriete).filter(
        TopoStagingPropriete.id == int(import_id)
    ).first()
    
    if staging_prop:
        files = db.query(TopoStagingFile).filter(
            TopoStagingFile.propriete_id == int(import_id)
        ).all()
        
        return {
            "import": {
                "id": staging_prop.id,
                "batch_id": str(staging_prop.batch_id),
                "entity_type": "propriete",
                "raw_data": staging_prop.payload,
                "status": staging_prop.status.lower(),
                "numero_ouverture": staging_prop.numero_ouverture,
                "topo_user_name": staging_prop.topo_user_name,
                "import_date": staging_prop.created_at.isoformat(),
                "rejection_reason": staging_prop.error_reason,
                "processed_at": staging_prop.validated_at.isoformat() if staging_prop.validated_at else None
            },
            "files": [
                {
                    "id": f.id,
                    "name": f.original_name,
                    "size": f.file_size,
                    "mime_type": f.mime_type,
                    "category": f.category,
                    "lot": f.lot,
                    "download_url": f"/api/v1/files/{f.id}"
                }
                for f in files
            ]
        }
    
    raise HTTPException(status_code=404, detail="Import introuvable")

@router.put("/{import_id}/validate")
def validate_import(
    import_id: str,
    action: str,
    rejection_reason: Optional[str] = None,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Valider ou rejeter un import
    ✅ NOUVEAU: Gère aussi les imports fichiers virtuels
    
    PUT /api/imports/123/validate?action=validate
    PUT /api/imports/files_D2024-001/validate?action=validate
    """
    
    if action not in ['validate', 'reject']:
        raise HTTPException(status_code=400, detail="Action doit être 'validate' ou 'reject'")
    
    # ========================================
    # CAS 1: Import fichiers virtuel
    # ========================================
    
    if str(import_id).startswith("files_"):
        # Pour les fichiers, on ne fait rien ici
        # La validation se fait dans Laravel lors de l'import
        return {
            "success": True,
            "message": "Import fichiers prêt à être importé",
            "import_id": import_id,
            "new_status": "pending"
        }
    
    # ========================================
    # CAS 2 & 3: Import demandeur/propriété
    # ========================================
    
    staging = db.query(TopoStagingDemandeur).filter(
        TopoStagingDemandeur.id == int(import_id)
    ).first()
    
    if not staging:
        staging = db.query(TopoStagingPropriete).filter(
            TopoStagingPropriete.id == int(import_id)
        ).first()
    
    if not staging:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    if action == 'validate':
        staging.status = 'VALIDATED'
        staging.validated_at = datetime.now()
        staging.validated_by = user.id
    elif action == 'reject':
        if not rejection_reason:
            raise HTTPException(status_code=400, detail="Motif de rejet requis")
        staging.status = 'REJECTED'
        staging.error_reason = rejection_reason
        staging.validated_at = datetime.now()
        staging.validated_by = user.id
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Import {action}",
        "import_id": import_id,
        "new_status": staging.status.lower()
    }

@router.delete("/{import_id}/files")
def cleanup_import_files(
    import_id: str,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Nettoyer les fichiers d'un import
    ✅ NOUVEAU: Gère aussi les imports fichiers virtuels
    
    DELETE /api/imports/123/files
    DELETE /api/imports/files_D2024-001/files
    """
    
    if str(import_id).startswith("files_"):
        numero_ouverture = str(import_id).replace("files_", "")
        deleted_count = db.query(TopoStagingFile).filter(
            and_(
                TopoStagingFile.numero_ouverture == numero_ouverture,
                TopoStagingFile.demandeur_id == None,
                TopoStagingFile.propriete_id == None
            )
        ).delete()
    else:
        deleted_count = db.query(TopoStagingFile).filter(
            or_(
                TopoStagingFile.demandeur_id == int(import_id),
                TopoStagingFile.propriete_id == int(import_id)
            )
        ).delete()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Fichiers nettoyés",
        "files_deleted": deleted_count
    }