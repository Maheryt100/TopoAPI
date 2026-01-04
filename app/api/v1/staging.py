# """app/api/v1/staging.py
"""
Routes pour la lecture et validation du staging
Utilisé par GeODOC pour lire les imports en attente
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingDemandeur, TopoStagingPropriete, TopoStagingFile
from app.api.v1.auth import get_current_user
from app.schemas import StagingListItem

router = APIRouter(prefix="/staging", tags=["Staging"])

@router.get("/")
def list_staging(
    status: Optional[str] = "PENDING",
    entity_type: Optional[str] = None,
    district_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lister tous les imports en staging
    Utilisé par GeODOC pour afficher les imports en attente
    """
    
    results = []
    
    # Récupérer demandeurs
    if not entity_type or entity_type == 'demandeur':
        query_dem = db.query(TopoStagingDemandeur)
        
        if status:
            query_dem = query_dem.filter(TopoStagingDemandeur.status == status)
        if district_id:
            query_dem = query_dem.filter(TopoStagingDemandeur.target_district_id == district_id)
        
        demandeurs = query_dem.order_by(TopoStagingDemandeur.created_at.desc()).all()
        
        for d in demandeurs:
            files_count = db.query(TopoStagingFile).filter(
                TopoStagingFile.demandeur_id == d.id
            ).count()
            
            results.append({
                "id": d.id,
                "entity_type": "demandeur",
                "batch_id": str(d.batch_id),
                "status": d.status,
                "target_dossier_id": d.target_dossier_id,
                "target_district_id": d.target_district_id,
                "topo_user_name": d.topo_user_name,
                "created_at": d.created_at.isoformat(),
                "files_count": files_count,
                "payload": d.payload
            })
    
    # Récupérer propriétés
    if not entity_type or entity_type == 'propriete':
        query_prop = db.query(TopoStagingPropriete)
        
        if status:
            query_prop = query_prop.filter(TopoStagingPropriete.status == status)
        if district_id:
            query_prop = query_prop.filter(TopoStagingPropriete.target_district_id == district_id)
        
        proprietes = query_prop.order_by(TopoStagingPropriete.created_at.desc()).all()
        
        for p in proprietes:
            files_count = db.query(TopoStagingFile).filter(
                TopoStagingFile.propriete_id == p.id
            ).count()
            
            results.append({
                "id": p.id,
                "entity_type": "propriete",
                "batch_id": str(p.batch_id),
                "status": p.status,
                "target_dossier_id": p.target_dossier_id,
                "target_district_id": p.target_district_id,
                "topo_user_name": p.topo_user_name,
                "created_at": p.created_at.isoformat(),
                "files_count": files_count,
                "payload": p.payload
            })
    
    # Trier par date décroissante
    results.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Pagination
    total = len(results)
    results = results[offset:offset + limit]
    
    return {
        "success": True,
        "total": total,
        "data": results
    }

@router.get("/{entity_type}/{staging_id}")
def get_staging_detail(
    entity_type: str,
    staging_id: int,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupérer les détails d'un import staging"""
    
    if entity_type == 'demandeur':
        staging = db.query(TopoStagingDemandeur).filter(
            TopoStagingDemandeur.id == staging_id
        ).first()
        files = db.query(TopoStagingFile).filter(
            TopoStagingFile.demandeur_id == staging_id
        ).all()
    elif entity_type == 'propriete':
        staging = db.query(TopoStagingPropriete).filter(
            TopoStagingPropriete.id == staging_id
        ).first()
        files = db.query(TopoStagingFile).filter(
            TopoStagingFile.propriete_id == staging_id
        ).all()
    else:
        raise HTTPException(status_code=400, detail="Type invalide")
    
    if not staging:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    return {
        "success": True,
        "import": {
            "id": staging.id,
            "batch_id": str(staging.batch_id),
            "entity_type": entity_type,
            "payload": staging.payload,
            "status": staging.status,
            "target_dossier_id": staging.target_dossier_id,
            "target_district_id": staging.target_district_id,
            "topo_user_name": staging.topo_user_name,
            "created_at": staging.created_at.isoformat(),
            "error_reason": staging.error_reason
        },
        "files": [
            {
                "id": f.id,
                "name": f.original_name,
                "size": f.file_size,
                "mime_type": f.mime_type
            }
            for f in files
        ]
    }

@router.put("/{entity_type}/{staging_id}/status")
def update_staging_status(
    entity_type: str,
    staging_id: int,
    status: str,
    error_reason: Optional[str] = None,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour le statut d'un import
    Utilisé par GeODOC après validation
    """
    
    if entity_type == 'demandeur':
        staging = db.query(TopoStagingDemandeur).filter(
            TopoStagingDemandeur.id == staging_id
        ).first()
    elif entity_type == 'propriete':
        staging = db.query(TopoStagingPropriete).filter(
            TopoStagingPropriete.id == staging_id
        ).first()
    else:
        raise HTTPException(status_code=400, detail="Type invalide")
    
    if not staging:
        raise HTTPException(status_code=404, detail="Import introuvable")
    
    staging.status = status
    if error_reason:
        staging.error_reason = error_reason
    
    db.commit()
    
    return {"success": True, "message": f"Statut mis à jour: {status}"}

@router.get("/stats")
def get_staging_stats(
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Statistiques globales du staging"""
    
    total_dem = db.query(TopoStagingDemandeur).count()
    pending_dem = db.query(TopoStagingDemandeur).filter(
        TopoStagingDemandeur.status == 'PENDING'
    ).count()
    
    total_prop = db.query(TopoStagingPropriete).count()
    pending_prop = db.query(TopoStagingPropriete).filter(
        TopoStagingPropriete.status == 'PENDING'
    ).count()
    
    return {
        "total": total_dem + total_prop,
        "pending": pending_dem + pending_prop,
        "demandeurs": {
            "total": total_dem,
            "pending": pending_dem
        },
        "proprietes": {
            "total": total_prop,
            "pending": pending_prop
        }
    }