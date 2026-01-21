from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, ForeignKey, String, Integer, DateTime, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./letak_master.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SourceFile(Base):
    __tablename__ = "source_files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    data_rows: Mapped[List["SourceData"]] = relationship(back_populates="source_file", cascade="all, delete-orphan")

class SourceData(Base):
    __tablename__ = "source_data"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"))
    row_index: Mapped[int] = mapped_column(Integer)
    column_name: Mapped[str] = mapped_column(String(255))
    value: Mapped[Optional[str]] = mapped_column(Text)
    formatting_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON string of cell formatting
    
    source_file: Mapped["SourceFile"] = relationship(back_populates="data_rows")
    layer_mappings: Mapped[List["LayerMapping"]] = relationship(back_populates="source_data")

class PSDFile(Base):
    __tablename__ = "psd_files"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    layer_mappings: Mapped[List["LayerMapping"]] = relationship(back_populates="psd_file")

class LayerMapping(Base):
    __tablename__ = "layer_mappings"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    source_data_id: Mapped[int] = mapped_column(ForeignKey("source_data.id"))
    psd_file_id: Mapped[int] = mapped_column(ForeignKey("psd_files.id"))
    layer_name: Mapped[str] = mapped_column(String(255))
    
    source_data: Mapped["SourceData"] = relationship(back_populates="layer_mappings")
    psd_file: Mapped["PSDFile"] = relationship(back_populates="layer_mappings")

class AppConfig(Base):
    __tablename__ = "app_config"
    
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(Text)

class ProjectState(Base):
    __tablename__ = "project_states"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(100)) # System user who triggered sync
    
    # Source Metadata
    source_path: Mapped[Optional[str]] = mapped_column(String(1024))
    source_sheet: Mapped[Optional[str]] = mapped_column(String(255))
    excel_last_modified_by: Mapped[Optional[str]] = mapped_column(String(255)) # Excel's "Last Author"
    
    excel_hash: Mapped[str] = mapped_column(String(64))
    data_snapshot_json: Mapped[str] = mapped_column(Text) # Large JSON blob

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100))
    active_project_state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
