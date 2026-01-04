# """app/models/staging.py
"""
Modèles SQLAlchemy pour les tables STAGING
Tables séparées pour demandeurs et propriétés
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from app.core.database import Base

class TopoUser(Base):
    """Utilisateurs TopoManager (sync auto depuis GeODOC via JWT)"""
    __tablename__ = "topo_users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default='operator')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingDemandeur(Base):
    """Table STAGING pour les demandeurs venant du terrain"""
    __tablename__ = "topo_staging_demandeurs"
    
    id = Column(BigInteger, primary_key=True)
    
    # Métadonnées import
    source = Column(String(50), default='topo', nullable=False)
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    
    # Utilisateur terrain
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'), nullable=False)
    topo_user_name = Column(String(100))
    
    # Cible GeODOC
    target_dossier_id = Column(Integer, nullable=False)
    target_district_id = Column(Integer, nullable=False)
    
    # Données brutes JSON (tous champs optionnels)
    payload = Column(JSON, nullable=False)
    
    # Statut validation
    status = Column(String(20), default='PENDING')
    error_reason = Column(Text)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(BigInteger)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    files = relationship("TopoStagingFile", back_populates="demandeur", cascade="all, delete-orphan")

class TopoStagingPropriete(Base):
    """Table STAGING pour les propriétés venant du terrain"""
    __tablename__ = "topo_staging_proprietes"
    
    id = Column(BigInteger, primary_key=True)
    
    # Métadonnées import
    source = Column(String(50), default='topo', nullable=False)
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    
    # Utilisateur terrain
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'), nullable=False)
    topo_user_name = Column(String(100))
    
    # Cible GeODOC
    target_dossier_id = Column(Integer, nullable=False)
    target_district_id = Column(Integer, nullable=False)
    
    # Données brutes JSON (tous champs optionnels)
    payload = Column(JSON, nullable=False)
    
    # Statut validation
    status = Column(String(20), default='PENDING')
    error_reason = Column(Text)
    validated_at = Column(DateTime(timezone=True))
    validated_by = Column(BigInteger)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    files = relationship("TopoStagingFile", back_populates="propriete", cascade="all, delete-orphan")

class TopoStagingFile(Base):
    """Fichiers attachés aux imports STAGING"""
    __tablename__ = "topo_staging_files"
    
    id = Column(Integer, primary_key=True)
    
    # Relations polymorphiques
    demandeur_id = Column(BigInteger, ForeignKey('topo_staging_demandeurs.id', ondelete='CASCADE'))
    propriete_id = Column(BigInteger, ForeignKey('topo_staging_proprietes.id', ondelete='CASCADE'))
    
    # Informations fichier
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    demandeur = relationship("TopoStagingDemandeur", back_populates="files")
    propriete = relationship("TopoStagingPropriete", back_populates="files")