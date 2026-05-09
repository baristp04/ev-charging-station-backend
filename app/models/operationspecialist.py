from sqlmodel import Field, Relationship
from typing import List, Optional, TYPE_CHECKING
from app.models.base_user import UserBase

if TYPE_CHECKING:
    from app.models.station import ChargingStation

class OperationsSpecialist(UserBase, table=True):
    __tablename__ = "operationspecialist"

    operatorID: Optional[int] = Field(default=None, primary_key=True)

    # Relationship: An operations specialist manages multiple charging stations
    managed_stations: List["ChargingStation"] = Relationship(back_populates="operator")