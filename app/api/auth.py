# auth.py
# Authentication endpoints: login, register, logout.
# Validates email format, phone format, and password strength on registration.
# Dynamically assigns users to the correct table (Driver, Analyst, Specialist, Technician) based on their selected role.

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
    role: str = "driver"  # Frontend'den gelen rol bilgisi eklendi

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

        # 3. Check OperationSpecialist table (admin)
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
    """Register a new user to the correct table based on their selected role."""
    with Session(engine) as session:
        
        # 1. Seçilen role göre hangi Modeli (Tabloyu) kullanacağımızı belirliyoruz
        model_class = EVDriver
        is_admin = False
        
        if request.role == "analyst":
            model_class = SystemAnalyst
            is_admin = True
        elif request.role == "specialist":
            model_class = OperationsSpecialist
            is_admin = True
        elif request.role == "technician":
            model_class = EVTechnician
            is_admin = False

        # 2. Belirlenen tabloda bu mail adresi zaten var mı kontrol et
        existing = session.exec(
            select(model_class).where(model_class.email == request.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="This email address is already registered.")

        hashed_pw = hash_password(request.password)

        # 3. İlgili modele ait kullanıcıyı oluştur
        new_user = model_class(
            name=request.name,
            email=request.email,
            phoneNumber=request.phoneNumber,
            passwordHash=hashed_pw,
            is_admin=is_admin
        )
        
        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        # 4. Doğru ID'yi dinamik olarak çek (Hangi tabloya kayıt edildiyse)
        user_id = getattr(new_user, 'driverID',
                  getattr(new_user, 'analystID',
                  getattr(new_user, 'specialistID',
                  getattr(new_user, 'technicianID', getattr(new_user, 'id', 0)))))

        return UserResponse(
            driverID=user_id,
            name=new_user.name,
            email=new_user.email,
            phoneNumber=new_user.phoneNumber,
            is_admin=is_admin
        )

@auth_router.post("/logout")
def logout():
    """Logout endpoint (client-side session cleared by frontend)."""
    return {"message": "Logged out successfully"}