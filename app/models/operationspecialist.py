from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.station import ChargingStation

class OperationsSpecialist(SQLModel, table=True):
    __tablename__ = "operationspecialist"

    operatorID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phoneNumber: str
    passwordHash: str
    is_admin: bool = Field(default=True)  # Operations specialists are always admins

    # Relationship: An operations specialist manages multiple charging stations
    managed_stations: List["ChargingStation"] = Relationship(back_populates="operator")