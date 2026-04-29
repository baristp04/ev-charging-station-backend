from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.driver import EVDriver
    from app.models.charger import Charger
    from app.models.session import ChargingSession
    from app.models.vehicle import Vehicle # Vehicle import edildi

class Reservation(SQLModel, table=True):
    __tablename__ = "reservation"
    
    reservationID: Optional[int] = Field(default=None, primary_key=True)
    date: datetime
    startTime: datetime
    endTime: datetime
    status: str = Field(default="active")
    
    # 1. Veritabanı Sütunları (Foreign Keys)
    driver_id: int = Field(foreign_key="evdriver.driverID")
    charger_id: int = Field(foreign_key="charger.chargerID")
    vehicle_id: int = Field(foreign_key="vehicle.vehicleID") # EKLENDİ: Hangi araç şarj edilecek?

    # 2. Python İlişkileri (Relationships)
    driver: Optional["EVDriver"] = Relationship(back_populates="reservations")
    charger: Optional["Charger"] = Relationship(back_populates="reservations")
    vehicle: Optional["Vehicle"] = Relationship(back_populates="reservations") # EKLENDİ
    
    # DÜZELTİLDİ: "session" yerine "charging_session" yapıldı (session.py ile uyumlu olması için)
    charging_session: Optional["ChargingSession"] = Relationship(back_populates="reservation")