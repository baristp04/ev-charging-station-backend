from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.reservation import Reservation
    from app.models.payment import Payment

class ChargingSession(SQLModel, table=True):
    __tablename__ = "session"
    sessionID: Optional[int] = Field(default=None, primary_key=True)
    startTime: datetime = Field(default_factory=datetime.utcnow)
    endTime: Optional[datetime] = None
    energyConsumed: float = 0.0  # kWh
    totalCost: float = 0.0
    status: str = Field(default="active")
    
    reservation_id: int = Field(foreign_key="reservation.reservationID")

    reservation: "Reservation" = Relationship(back_populates="charging_session")
    payment: Optional["Payment"] = Relationship(back_populates="session")