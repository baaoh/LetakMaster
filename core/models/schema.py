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
    master_excel_path: Mapped[str] = mapped_column(String(1024))
    network_root_path: Mapped[str] = mapped_column(String(1024))
    
    states: Mapped[List["ProjectState"]] = relationship(back_populates="project")

class ProjectState(Base):
    """
    Acts like a 'Commit'. Points to a parent state to allow diffing.
    """
    __tablename__ = "project_states"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    parent_state_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_states.id"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_by: Mapped[str] = mapped_column(String(100))
    
    # Summary of changes for this sync (e.g. "3 pages updated, 12 prices changed")
    summary: Mapped[Optional[str]] = mapped_column(String(512))
    
    # Path to the .xlsx archive on the NAS for this specific sync point
    archive_path: Mapped[str] = mapped_column(String(1024))
    
    project: Mapped["Project"] = relationship(back_populates="states")
    page_snapshots: Mapped[List["PageSnapshot"]] = relationship(back_populates="state")
    diffs: Mapped[List["DataDiff"]] = relationship(back_populates="state")

class PageSnapshot(Base):
    """
    The data for a single page at a specific point in time.
    """
    __tablename__ = "page_snapshots"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    
    # Content Hash: If the hash matches the previous state, we know nothing changed.
    content_hash: Mapped[str] = mapped_column(String(64))
    
    # The actual product data for this page only
    data_json: Mapped[Dict] = mapped_column(JSON)
    
    # Status flags
    is_dirty: Mapped[bool] = mapped_column(Boolean, default=False) # True if needs new build plan
    
    # Path to the Build Plan (JSON) on the NAS for THIS version of the page
    build_plan_path: Mapped[Optional[str]] = mapped_column(String(1024))
    
    state: Mapped["ProjectState"] = relationship(back_populates="page_snapshots")

class DataDiff(Base):
    """
    The 'Github Diff' - Stores specific field-level changes between states.
    """
    __tablename__ = "data_diffs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    
    product_name: Mapped[str] = mapped_column(String(255))
    field_name: Mapped[str] = mapped_column(String(100)) # e.g. "Price", "Hero"
    
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    
    # Severity: Info (text change), Critical (Price/Hero change)
    change_type: Mapped[str] = mapped_column(String(50)) 

    state: Mapped["ProjectState"] = relationship(back_populates="diffs")

class UserWorkspace(Base):
    """
    Tracks what each user is doing locally.
    """
    __tablename__ = "user_workspaces"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100))
    active_state_id: Mapped[int] = mapped_column(ForeignKey("project_states.id"))
    
    # The local scratchpad (.xlsm) on the Designer's PC
    local_excel_path: Mapped[str] = mapped_column(String(1024))
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
