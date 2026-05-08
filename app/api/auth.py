from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.database import engine
from pydantic import BaseModel
import hashlib

# ── Modellerin İçeri Aktarılması ──
from app.models.driver import EVDriver
from app.models.SystemAnalyst import SystemAnalyst
from app.models.operationspecialist import OperationSpecialist
from app.models.EVTechnician import EVTechnician

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
    # Frontend'in bozulmaması için ID'yi "driverID" adıyla döndürüyoruz.
    # (Giriş yapan bir analist olsa bile onun ID'si bu alana yazılacak)
    driverID: int 
    name: str
    email: str
    phoneNumber: str
    is_admin: bool

# ── Endpoints ─────────────────────────────────────────────────────────────────

@auth_router.post("/login", response_model=UserResponse)
def login(request: LoginRequest):
    """Gelen mail adresini sırayla tüm rol tablolarında arar ve yetkilendirir."""
    with Session(engine) as session:
        user = None
        is_admin = False

        # 1. Önce Sürücülerde Ara (En çok giriş yapacak olan kitle)
        user = session.exec(select(EVDriver).where(EVDriver.email == request.email)).first()
        if user:
            is_admin = getattr(user, 'is_admin', False)

        # 2. Sistem Analistlerinde Ara (Yönetici)
        if not user:
            user = session.exec(select(SystemAnalyst).where(SystemAnalyst.email == request.email)).first()
            if user:
                is_admin = True

        # 3. Operasyon Uzmanlarında Ara (Yönetici)
        if not user:
            user = session.exec(select(OperationSpecialist).where(OperationSpecialist.email == request.email)).first()
            if user:
                is_admin = True

        # 4. Teknisyenlerde Ara (Saha elemanı, yönetici değil)
        if not user:
            user = session.exec(select(EVTechnician).where(EVTechnician.email == request.email)).first()
            if user:
                is_admin = False

        # Eğer hiçbir tabloda bulunamadıysa veya şifre yanlışsa hata ver
        if not user or getattr(user, 'passwordHash', '') != hash_password(request.password):
            raise HTTPException(status_code=401, detail="Geçersiz e-posta veya şifre")

        # Modellerdeki ID kolonlarının ismi farklı olabilir (analystID, specialistID vb.)
        # Hata almamak için getattr ile dinamik olarak kullanıcının ID'sini çekiyoruz.
        user_id = getattr(user, 'driverID', 
                  getattr(user, 'analystID', 
                  getattr(user, 'specialistID', 
                  getattr(user, 'technicianID', getattr(user, 'id', 0)))))

        return UserResponse(
            driverID=user_id,
            name=getattr(user, 'name', 'İsimsiz Kullanıcı'),
            email=user.email,
            phoneNumber=getattr(user, 'phoneNumber', ''),
            is_admin=is_admin
        )

@auth_router.post("/register", response_model=UserResponse)
def register(request: RegisterRequest):
    """Yeni kayıt olan kişiyi varsayılan olarak Sürücü (EVDriver) tablosuna kaydeder.
       (Yöneticiler genelde sistem dışından / DB üzerinden manuel eklenir)
    """
    with Session(engine) as session:
        existing = session.exec(
            select(EVDriver).where(EVDriver.email == request.email)
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Bu email adresi zaten kullanımda.")

        driver = EVDriver(
            name=request.name,
            email=request.email,
            phoneNumber=request.phoneNumber,
            passwordHash=hash_password(request.password),
            is_admin=False  # Yeni kayıtlar asla varsayılan admin olamaz
        )
        session.add(driver)
        session.commit()
        session.refresh(driver)

        return UserResponse(
            driverID=driver.driverID,
            name=driver.name,
            email=driver.email,
            phoneNumber=driver.phoneNumber,
            is_admin=False
        )

@auth_router.post("/logout")
def logout():
    """Logout endpoint"""
    return {"message": "Başarıyla çıkış yapıldı"}