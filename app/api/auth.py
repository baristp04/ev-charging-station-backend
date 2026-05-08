from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models.driver import EVDriver
from pydantic import BaseModel
import hashlib

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plain-text password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# ── Request / Response Schemas ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    phoneNumber: str
    password: str

class UserResponse(BaseModel):
    driverID: int
    name: str
    email: str
    phoneNumber: str
    is_admin: bool

# ── Endpoints ─────────────────────────────────────────────────────────────────

@auth_router.post("/login", response_model=UserResponse)
def login(request: LoginRequest):
    """Authenticate a driver by email and hashed password."""
    with Session(engine) as session:
        driver = session.exec(
            select(EVDriver).where(EVDriver.email == request.email)
        ).first()

        if not driver or driver.passwordHash != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return UserResponse(
            driverID=driver.driverID,
            name=driver.name,
            email=driver.email,
            phoneNumber=driver.phoneNumber,
            is_admin=driver.is_admin
        )

@auth_router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """Register a new EV driver account."""
    with Session(engine) as session:
        # Check if email is already in use
        existing = session.exec(
            select(EVDriver).where(EVDriver.email == request.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        driver = EVDriver(
            name=request.name,
            email=request.email,
            phoneNumber=request.phoneNumber,
            passwordHash=hash_password(request.password)
        )
        session.add(driver)
        session.commit()
        session.refresh(driver)

        return UserResponse(
            driverID=driver.driverID,
            name=driver.name,
            email=driver.email,
            phoneNumber=driver.phoneNumber,
            is_admin=driver.is_admin
        )

@auth_router.post("/logout")
def logout():
    """Logout endpoint (client-side session cleared by frontend)."""
    return {"message": "Logged out successfully"}