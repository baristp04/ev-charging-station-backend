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
    role: str = "driver"  # Sadece "driver" dışarıdan kayda açık

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
    # Frontend'in bozulmaması için ID'yi "driverID" adıyla dönüyoruz
    driverID: int
    name: str
    email: str
    phoneNumber: str
    role: str  # YENİ: is_admin tamamen kaldırıldı, sadece rol dönüyoruz

# -- Endpoints ----------------------------------------------------------------

@auth_router.post("/login", response_model=UserResponse)
def login(request: LoginRequest):
    """Sırayla tüm tabloları tarar ve bulduğu kullanıcının veritabanındaki rolünü döndürür."""
    with Session(engine) as session:
        user = None

        # 1. EVDriver Tablosu (En sık giriş yapacak kitle)
        user = session.exec(select(EVDriver).where(EVDriver.email == request.email.lower().strip())).first()

        # 2. SystemAnalyst Tablosu
        if not user:
            user = session.exec(select(SystemAnalyst).where(SystemAnalyst.email == request.email.lower().strip())).first()

        # 3. OperationsSpecialist Tablosu
        if not user:
            user = session.exec(select(OperationsSpecialist).where(OperationsSpecialist.email == request.email.lower().strip())).first()

        # 4. EVTechnician Tablosu
        if not user:
            user = session.exec(select(EVTechnician).where(EVTechnician.email == request.email.lower().strip())).first()

        # Kullanıcı bulunamadıysa veya şifre eşleşmiyorsa
        if not user or getattr(user, 'passwordHash', '') != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        # Modellerdeki farklı ID isimlerini dinamik olarak yakalıyoruz
        user_id = getattr(user, 'driverID',
                  getattr(user, 'analystID',
                  getattr(user, 'operatorID',  # Dikkat: specialistID yerine senin modelindeki operatorID'yi kullandık
                  getattr(user, 'technicianID', getattr(user, 'id', 0)))))

        return UserResponse(
            driverID=user_id,
            name=user.name,
            email=user.email,
            phoneNumber=user.phoneNumber,
            role=user.role  # Rol doğrudan veritabanından okunarak Frontend'e gidiyor
        )

@auth_router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """
    Sadece EVDriver (Sürücü) kaydına izin verir.
    Personel hesapları sistem yöneticileri tarafından oluşturulur.
    """

    # Güvenlik: Dışarıdan personel rolüyle kayıt olmayı engelle
    if request.role in ("analyst", "specialist", "technician"):
        raise HTTPException(
            status_code=403,
            detail="Self-registration is only available for drivers. Staff accounts are created by system administrators."
        )

    with Session(engine) as session:
        existing = session.exec(
            select(EVDriver).where(EVDriver.email == request.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="This email address is already registered.")

        # Yeni sürücü, rolü 'driver' olarak oluşturuluyor
        new_user = EVDriver(
            name=request.name,
            email=request.email,
            phoneNumber=request.phoneNumber,
            passwordHash=hash_password(request.password),
            role="driver"  # YENİ: is_admin=False yerine rol ataması yapıyoruz
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return UserResponse(
            driverID=new_user.driverID,
            name=new_user.name,
            email=new_user.email,
            phoneNumber=new_user.phoneNumber,
            role=new_user.role
        )

@auth_router.post("/logout")
def logout():
    """Logout endpoint (client-side session cleared by frontend)."""
    return {"message": "Logged out successfully"}