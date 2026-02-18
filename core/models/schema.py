from datetime import datetime
from typing import List, Optional, Dict
from sqlalchemy import ForeignKey, String, Integer, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    
    # Path on the NAS relative to the root
    master_excel_path: Mapped[str] = mapped_column(String(1024))
    network_root_path: Mapped[str] = mapped_column(String(1024))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    states: Mapped[List["ProjectState"]] = relationship(back_populates="project")

class ProjectState(Base):
    """
    Acts like a 'Commit'. Points to a parent state to allow diffing.
    Now restored with 'Classic' metadata.
    """
    __tablename__ = "project_states"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    parent_state_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_states.id"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(100)) # The Computer Name/User ID
    
    # Restored 'Classic' Metadata
    sheet_name: Mapped[str] = mapped_column(String(255)) # The "Week" (e.g. 04.03 - 10.03)
    excel_author: Mapped[Optional[str]] = mapped_column(String(255)) # The person who saved the Excel
    
    # Summary of changes for this sync
    summary: Mapped[Optional[str]] = mapped_column(String(512))
    
    # Path to the .xlsx archive on the NAS
    archive_path: Mapped[str] = mapped_column(String(1024))
    
    # Full data snapshot stored as JSON
    data_snapshot: Mapped[Dict] = mapped_column(JSON)
    
    project: Mapped["Project"] = relationship(back_populates="states")
    page_snapshots: Mapped[List["PageSnapshot"]] = relationship(back_populates="state")
    diffs: Mapped[List["DataDiff"]] = relationship(back_populates="state")

class PageSnapshot(Base):
    __tablename__ = "page_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    data_json: Mapped[Dict] = mapped_column(JSON)
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    build_plan_path: Mapped[Optional[str]] = mapped_column(String(1024))
    state: Mapped["ProjectState"] = relationship(back_populates="page_snapshots")

class DataDiff(Base):
    __tablename__ = "data_diffs"
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(255))
    field_name: Mapped[str] = mapped_column(String(100))
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    change_type: Mapped[str] = mapped_column(String(50)) 
    state: Mapped["ProjectState"] = relationship(back_populates="diffs")

class UserWorkspace(Base):
    __tablename__ = "user_workspaces"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100))
    active_state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    local_excel_path: Mapped[str] = mapped_column(String(1024))
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
