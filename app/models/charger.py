from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime

if TYPE_CHECKING:
    from app.models.station import ChargingStation
    from app.models.reservation import Reservation

class Charger(SQLModel, table=True):
    __tablename__ = "charger"
    chargerID: Optional[int] = Field(default=None, primary_key=True)
    type: str  # AC or DC
    powerOutput: float
    connectorType: str
    pricePerKwh: float
    status: str = Field(default="available")

    # EKLENEN ALANLAR:
    maintenanceStartTime: Optional[datetime] = None
    maintenanceNotes: Optional[str] = None
    
    station_id: int = Field(foreign_key="chargingstation.stationID")
    station: "ChargingStation" = Relationship(back_populates="chargers")
    reservations: List["Reservation"] = Relationship(back_populates="charger")