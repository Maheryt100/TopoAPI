"""app/models/staging.py
Modeles SQLAlchemy pour les tables STAGING 
Fichiers associes au dossier uniquement
Statuts: PENDING, ARCHIVED, REJECTED
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
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
    
    source = Column(String(50), default='topo', nullable=False)
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'), nullable=False)
    topo_user_name = Column(String(100))
    
    numero_ouverture = Column(String(50), nullable=False, index=True)
    
    payload = Column(JSON, nullable=False)
    
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingPropriete(Base):
    """Table STAGING pour les proprietes venant du terrain"""
    __tablename__ = "topo_staging_proprietes"
    
    id = Column(BigInteger, primary_key=True)
    
    source = Column(String(50), default='topo', nullable=False)
    batch_id = Column(UUID(as_uuid=True), server_default=text('gen_random_uuid()'))
    checksum = Column(String(64))
    
    topo_user_id = Column(Integer, ForeignKey('topo_users.id'), nullable=False)
    topo_user_name = Column(String(100))
    
    numero_ouverture = Column(String(50), nullable=False, index=True)
    
    payload = Column(JSON, nullable=False)
    
    status = Column(String(20), default='PENDING', index=True)
    error_reason = Column(Text)
    
    archived_at = Column(DateTime(timezone=True))
    archived_by_email = Column(String(100))
    archived_note = Column(Text)
    
    rejected_at = Column(DateTime(timezone=True))
    rejected_by_email = Column(String(100))
    rejection_reason = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TopoStagingFile(Base):
    """
    Fichiers attaches aux dossiers
    Associes au dossier uniquement via numero_ouverture
    """
    __tablename__ = "topo_staging_files"
    
    id = Column(Integer, primary_key=True)
    
    numero_ouverture = Column(String(50), nullable=False, index=True)
    
    original_name = Column(String(255), nullable=False)
    stored_name = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100))
    
    category = Column(String(50), index=True)
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())