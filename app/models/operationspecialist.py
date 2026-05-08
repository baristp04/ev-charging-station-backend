from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.station import ChargingStation

#ismi OperationsSpecialist olamadigi icin ozur dilerim büyük harfle yapinca alakasiz bir yerde error veriyordu

class OperationsSpecialist(SQLModel, table=True):
    __tablename__ = "operationspecialist"

    operatorID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phone: str
    passwordHash: str
    is_admin: bool = Field(default=True)

    # Relationship: An Operations Specialist manages multiple Charging Stations
    managed_stations: List["ChargingStation"] = Relationship(back_populates="operator")