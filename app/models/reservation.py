from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.driver import EVDriver
    from app.models.charger import Charger
    from app.models.session import ChargingSession

class Reservation(SQLModel, table=True):
    __tablename__ = "reservation"
    reservationID: Optional[int] = Field(default=None, primary_key=True)
    date: datetime
    startTime: datetime
    endTime: datetime
    status: str = Field(default="active")
    
    driver_id: int = Field(foreign_key="evdriver.driverID")
    charger_id: int = Field(foreign_key="charger.chargerID")