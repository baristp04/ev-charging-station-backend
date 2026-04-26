from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING

# The linter needs this block to understand the string type hints!
if TYPE_CHECKING:
    from app.models.charger import Charger
    from app.models.operationspecialist import OperationsSpecialist


class ChargingStation(SQLModel, table=True):
    __tablename__ = "chargingstation"

    stationID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    location: str
    latitude: float
    longitude: float
    status: str = Field(default="available")

    # Existing relationship
    chargers: List["Charger"] = Relationship(back_populates="station")

    # New relationships for Operations Specialist
    operator_id: Optional[int] = Field(default=None, foreign_key="operationspecialist.operatorID")
    operator: Optional["OperationsSpecialist"] = Relationship(back_populates="managed_stations")