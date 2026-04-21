from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.driver import EVDriver

class Vehicle(SQLModel, table=True):
    __tablename__ = "vehicle"
    vehicleID: Optional[int] = Field(default=None, primary_key=True)
    brand: str
    model: str
    plateNumber: str = Field(unique=True)
    batteryCapacity: float
    connectorType: str # Örn: 'Type 2'
    
    driver_id: int = Field(foreign_key="evdriver.driverID")
    driver: "EVDriver" = Relationship(back_populates="vehicles")