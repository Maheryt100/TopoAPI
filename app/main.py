# app/main.py
"""
FastAPI TopoManager - Application principale
Version avec téléchargement de fichiers sécurisé
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.config import get_settings
from app.api.v1 import auth, demandeurs, proprietes, files, imports, download

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="API pour imports terrain TopoManager avec téléchargement sécurisé"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routes existantes
app.include_router(auth.router, prefix="/api/v1")
app.include_router(demandeurs.router, prefix="/api/v1")
app.include_router(proprietes.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/imports")

# Nouvelle route de téléchargement
app.include_router(download.router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "healthy",
        "features": [
            "Authentication JWT",
            "Import demandeurs/proprietes",
            "Upload fichiers",
            "Download fichiers sécurisé",
            "ZIP automatique"
        ]
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.fastapi_port)