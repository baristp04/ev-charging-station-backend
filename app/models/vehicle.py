from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING 

if TYPE_CHECKING:
    from app.models.driver import EVDriver
    from app.models.reservation import Reservation 

class Vehicle(SQLModel, table=True):
    __tablename__ = "vehicle"
    vehicleID: Optional[int] = Field(default=None, primary_key=True)
    brand: str
    model: str
    plateNumber: str = Field(unique=True)
    batteryCapacity: float
    connectorType: str # e.g. 'Type 2'
    
    driver_id: int = Field(foreign_key="evdriver.driverID")
    
    driver: "EVDriver" = Relationship(back_populates="vehicles")
    # Added: allows viewing vehicle reservation history
    reservations: List["Reservation"] = Relationship(back_populates="vehicle")