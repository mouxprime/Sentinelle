"""Sources API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Source
from ..schemas import SourceResponse, SourceCreate

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=List[SourceResponse])
async def list_sources(db: Session = Depends(get_db)):
    """Get list of all sources."""
    sources = db.query(Source).all()
    return sources


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: int, db: Session = Depends(get_db)):
    """Get a specific source by ID."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(source_data: SourceCreate, db: Session = Depends(get_db)):
    """Create a new source."""
    source = Source(**source_data.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: int,
    source_data: SourceCreate,
    db: Session = Depends(get_db)
):
    """Update a source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    for key, value in source_data.model_dump().items():
        setattr(source, key, value)

    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Delete a source."""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.delete(source)
    db.commit()
    return None
