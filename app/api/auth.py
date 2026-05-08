# auth.py
# Authentication endpoints: login, register, logout.
# Validates email format, phone format, and password strength on registration.
# Only EVDriver self-registration is allowed — staff accounts are created by system administrators.

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models.driver import EVDriver
from app.models.SystemAnalyst import SystemAnalyst
from app.models.operationspecialist import OperationsSpecialist
from app.models.EVTechnician import EVTechnician
from pydantic import BaseModel, field_validator
import hashlib
import re

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# -- Helpers ------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plain-text password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# -- Request / Response Schemas -----------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    phoneNumber: str
    password: str
    role: str = "driver"  # Only "driver" is accepted for self-registration

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Full name is required.')
        return v.strip()

    @field_validator('email')
    @classmethod
    def email_valid(cls, v):
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(pattern, v):
            raise ValueError('Please enter a valid email address.')
        return v.lower().strip()

    @field_validator('phoneNumber')
    @classmethod
    def phone_valid(cls, v):
        digits = re.sub(r'\s', '', v)
        if not re.match(r'^\d{10,15}$', digits):
            raise ValueError('Phone number must contain 10-15 digits only.')
        return digits

    @field_validator('password')
    @classmethod
    def password_strong(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number.')
        return v

class UserResponse(BaseModel):
    # Return ID as driverID so frontend stays consistent regardless of user role
    driverID: int
    name: str
    email: str
    phoneNumber: str
    is_admin: bool

# -- Endpoints ----------------------------------------------------------------

@auth_router.post("/login", response_model=UserResponse)
def login(request: LoginRequest):
    """Search all role tables in order and authenticate the matching user."""
    with Session(engine) as session:
        user = None
        is_admin = False

        # 1. Check EVDriver table first (most common login type)
        user = session.exec(select(EVDriver).where(EVDriver.email == request.email.lower().strip())).first()
        if user:
            is_admin = getattr(user, 'is_admin', False)

        # 2. Check SystemAnalyst table (admin)
        if not user:
            user = session.exec(select(SystemAnalyst).where(SystemAnalyst.email == request.email.lower().strip())).first()
            if user:
                is_admin = True

        # 3. Check OperationsSpecialist table (admin)
        if not user:
            user = session.exec(select(OperationsSpecialist).where(OperationsSpecialist.email == request.email.lower().strip())).first()
            if user:
                is_admin = True

        # 4. Check EVTechnician table (field staff, not admin)
        if not user:
            user = session.exec(select(EVTechnician).where(EVTechnician.email == request.email.lower().strip())).first()
            if user:
                is_admin = False

        if not user or getattr(user, 'passwordHash', '') != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        # Use getattr to handle different ID field names across models
        user_id = getattr(user, 'driverID',
                  getattr(user, 'analystID',
                  getattr(user, 'specialistID',
                  getattr(user, 'technicianID', getattr(user, 'id', 0)))))

        return UserResponse(
            driverID=user_id,
            name=getattr(user, 'name', 'Unknown User'),
            email=user.email,
            phoneNumber=getattr(user, 'phoneNumber', ''),
            is_admin=is_admin
        )

@auth_router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """Register a new EVDriver account. Self-registration is restricted to drivers only.
    Staff and admin accounts (analyst, specialist, technician) must be created by system administrators."""

    # Block self-registration for admin/staff roles
    if request.role in ("analyst", "specialist", "technician"):
        raise HTTPException(
            status_code=403,
            detail="Self-registration is only available for drivers. Staff accounts are created by system administrators."
        )

    with Session(engine) as session:

        # Check if email is already registered in the EVDriver table
        existing = session.exec(
            select(EVDriver).where(EVDriver.email == request.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="This email address is already registered.")

        # Create new EVDriver — self-registered users are never admins
        new_user = EVDriver(
            name=request.name,
            email=request.email,
            phoneNumber=request.phoneNumber,
            passwordHash=hash_password(request.password),
            is_admin=False
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return UserResponse(
            driverID=new_user.driverID,
            name=new_user.name,
            email=new_user.email,
            phoneNumber=new_user.phoneNumber,
            is_admin=False
        )

@auth_router.post("/logout")
def logout():
    """Logout endpoint (client-side session cleared by frontend)."""
    return {"message": "Logged out successfully"}