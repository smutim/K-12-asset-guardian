from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import School
from ..schemas import SchoolCreate, SchoolOut


router = APIRouter(prefix="/schools", tags=["schools"])


@router.post("", response_model=SchoolOut)
def create_school(payload: SchoolCreate, db: Session = Depends(get_db)):
    school = School(name=payload.name)
    db.add(school)
    db.commit()
    db.refresh(school)
    return school


@router.get("", response_model=list[SchoolOut])
def list_schools(db: Session = Depends(get_db)):
    return db.query(School).all()
