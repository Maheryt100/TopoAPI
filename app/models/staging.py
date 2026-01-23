"""Modèles SQLAlchemy avec relations optimisées"""
# app/models/staging.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.core.database import Base

class TopoUser(Base):
    """Utilisateurs de l'application TopoManager"""
    __tablename__ = "topo_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default='operator')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    demandeurs_imports = relationship(
        "TopoStagingDemandeur", 
        back_populates="user",
        cascade="all, delete-orphan"
    )
    proprietes_imports = relationship(
        "TopoStagingPropriete", 
        back_populates="user",
        cascade="all, delete-orphan"
    )

class TopoStagingDemandeur(Base):
    """Staging pour les demandeurs importés depuis le terrain"""
    __tablename__ = "topo_staging_demandeurs"
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), default='topo')
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), index=True)
    checksum = Column(String(64))
    
    # Relations utilisateur
    topo_user_id = Column(Integer, ForeignKey('topo_users.id', ondelete='CASCADE'))
    topo_user_name = Column(String(100))
    
    # Données
    numero_ouverture = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    
    # Statut
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relation inverse
    user = relationship("TopoUser", back_populates="demandeurs_imports")

class TopoStagingPropriete(Base):
    """Staging pour les propriétés importées depuis le terrain"""
    __tablename__ = "topo_staging_proprietes"
    
    id = Column(BigInteger, primary_key=True)
    source = Column(String(50), default='topo')
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'), index=True)
    checksum = Column(String(64))
    
    # Relations utilisateur
    topo_user_id = Column(Integer, ForeignKey('topo_users.id', ondelete='CASCADE'))
    topo_user_name = Column(String(100))
    
    # Données
    numero_ouverture = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    
    # Statut
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relation inverse
    user = relationship("TopoUser", back_populates="proprietes_imports")

class TopoStagingFile(Base):
    """Fichiers uploadés depuis le terrain"""
    __tablename__ = "topo_staging_files"
    
    id = Column(Integer, primary_key=True)
    numero_ouverture = Column(String(50), nullable=False, index=True)
    category = Column(String(50), index=True)
    
    # Métadonnées fichier
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False, unique=True)
    file_size = Column(BigInteger, nullable=False)  # ✅ BigInteger pour fichiers > 2GB
    mime_type = Column(String(100))
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)