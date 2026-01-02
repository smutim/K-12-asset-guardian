from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, get_db

# Import models so SQLAlchemy creates tables
from . import models  # noqa: F401
from . import models_ext  # noqa: F401

from .models import User
from .schemas import UserCreate, UserOut, TokenOut
from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
)
from .alerts import offline_sweep

from .routers import schools, devices, alerts, ingest, goguardian
from .connectors.google_chrome import sync_chromebooks_for_customer


app = FastAPI(title=settings.app_name)
@app.get("/")
def root():
    return {"status": "ok", "service": "k-12-asset-guardian"}

# Create tables (MVP). For production use Alembic migrations.
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(schools.router)
app.include_router(devices.router)
app.include_router(alerts.router)
app.include_router(ingest.router)
app.include_router(goguardian.router)


# -------------------------
# Auth endpoints
# -------------------------
@app.post("/auth/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        school_id=payload.school_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenOut)
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenOut(access_token=create_access_token(user.id))


# -------------------------
# Ops / Admin endpoints
# -------------------------
@app.post("/ops/offline-sweep")
def run_offline_sweep(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    changed = offline_sweep(db, school_id=admin.school_id)
    return {"ok": True, "devices_marked_offline": changed}


@app.post("/connectors/google/chromebooks/sync")
def google_chromebook_sync(
    customer_id: str = Query(default="my_customer"),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """
    Sync Chromebooks for the admin's school using Google Admin SDK.
    Requires env vars:
      GOOGLE_SA_JSON_PATH
      GOOGLE_DELEGATED_ADMIN
    """
    return sync_chromebooks_for_customer(
        db=db,
        school_id=admin.school_id,
        customer_id=customer_id,
    )


@app.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user
