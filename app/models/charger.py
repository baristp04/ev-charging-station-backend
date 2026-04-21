from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.models.station import ChargingStation
    from app.models.reservation import Reservation

class Charger(SQLModel, table=True):
    __tablename__ = "charger"
    chargerID: Optional[int] = Field(default=None, primary_key=True)
    type: str  # AC veya DC
    powerOutput: float
    connectorType: str
    pricePerKwh: float
    status: str = Field(default="available")
    
    station_id: int = Field(foreign_key="chargingstation.stationID")
    station: "ChargingStation" = Relationship(back_populates="chargers")
    reservations: List["Reservation"] = Relationship(back_populates="charger")