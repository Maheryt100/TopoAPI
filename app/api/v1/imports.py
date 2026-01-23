"""Routes liste imports avec requêtes optimisées"""
# app/api/v1/imports.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.core.database import get_db
from app.models.staging import TopoUser, TopoStagingDemandeur, TopoStagingPropriete, TopoStagingFile
from app.api.v1.auth import get_current_user

router = APIRouter(tags=["Imports"])

@router.get("/")
async def list_imports(
    status: Optional[str] = "pending",
    entity_type: Optional[str] = None,
    numero_ouverture: Optional[str] = None,
    user: TopoUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Liste tous les imports avec comptage optimisé des fichiers
    
    Utilise des jointures pour éviter les requêtes N+1
    """
    status_upper = status.upper() if status else None
    valid_statuses = ['PENDING', 'ARCHIVED', 'REJECTED']
    
    if status_upper and status_upper not in valid_statuses:
        raise HTTPException(
            400, 
            f"Statut invalide. Valeurs acceptées: {', '.join(valid_statuses)}"
        )
    
    results = []
    
    # =====================================================
    # DEMANDEURS avec comptage optimisé
    # =====================================================
    if not entity_type or entity_type == 'demandeur':
        query = db.query(
            TopoStagingDemandeur,
            func.count(TopoStagingFile.id).label('files_count')
        ).outerjoin(
            TopoStagingFile,
            TopoStagingFile.numero_ouverture == TopoStagingDemandeur.numero_ouverture
        ).group_by(TopoStagingDemandeur.id)
        
        if status_upper:
            query = query.filter(TopoStagingDemandeur.status == status_upper)
        if numero_ouverture:
            query = query.filter(TopoStagingDemandeur.numero_ouverture == numero_ouverture)
        
        for d, fc in query.order_by(TopoStagingDemandeur.created_at.desc()).all():
            results.append({
                "id": d.id,
                "entity_type": "demandeur",
                "batch_id": str(d.batch_id),
                "status": d.status.lower(),
                "numero_ouverture": d.numero_ouverture,
                "topo_user_name": d.topo_user_name,
                "import_date": d.created_at.isoformat(),
                "files_count": fc,
                "raw_data": d.payload
            })
    
    # =====================================================
    # PROPRIETES avec comptage optimisé
    # =====================================================
    if not entity_type or entity_type == 'propriete':
        query = db.query(
            TopoStagingPropriete,
            func.count(TopoStagingFile.id).label('files_count')
        ).outerjoin(
            TopoStagingFile,
            TopoStagingFile.numero_ouverture == TopoStagingPropriete.numero_ouverture
        ).group_by(TopoStagingPropriete.id)
        
        if status_upper:
            query = query.filter(TopoStagingPropriete.status == status_upper)
        if numero_ouverture:
            query = query.filter(TopoStagingPropriete.numero_ouverture == numero_ouverture)
        
        for p, fc in query.order_by(TopoStagingPropriete.created_at.desc()).all():
            results.append({
                "id": p.id,
                "entity_type": "propriete",
                "batch_id": str(p.batch_id),
                "status": p.status.lower(),
                "numero_ouverture": p.numero_ouverture,
                "topo_user_name": p.topo_user_name,
                "import_date": p.created_at.isoformat(),
                "files_count": fc,
                "raw_data": p.payload
            })
    
    # =====================================================
    # FICHIERS groupés par numero_ouverture
    # =====================================================
    if not entity_type or entity_type == 'fichier':
        query = db.query(TopoStagingFile).filter(
            TopoStagingFile.numero_ouverture.isnot(None)
        )
        if numero_ouverture:
            query = query.filter(TopoStagingFile.numero_ouverture == numero_ouverture)
        
        grouped = {}
        for f in query.order_by(TopoStagingFile.uploaded_at.desc()).all():
            key = f.numero_ouverture
            if key not in grouped:
                grouped[key] = {"files": [], "first_upload": f.uploaded_at}
            grouped[key]["files"].append({
                "id": f.id,
                "name": f.original_name,
                "size": f.file_size,
                "category": f.category
            })
        
        for num, data in grouped.items():
            results.append({
                "id": f"files_{num}",
                "entity_type": "fichier",
                "batch_id": f"files_{num}",
                "status": "pending",
                "numero_ouverture": num,
                "topo_user_name": "Import fichiers",
                "import_date": data["first_upload"].isoformat(),
                "files_count": len(data["files"]),
                "raw_data": {},
                "preview": {"files": data["files"]}
            })
    
    # Tri final par date
    results.sort(key=lambda x: x['import_date'], reverse=True)
    
    # Calcul des statistiques
    stats = {
        "total": len(results),
        "pending": len([r for r in results if r['status'] == 'pending']),
        "archived": len([r for r in results if r.get('status') == 'archived']),
        "rejected": len([r for r in results if r.get('status') == 'rejected'])
    }
    
    return {
        "data": results,
        "stats": stats,
        "filters": {
            "status": status,
            "entity_type": entity_type,
            "numero_ouverture": numero_ouverture
        }
    }