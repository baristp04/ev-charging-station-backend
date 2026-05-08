from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, TYPE_CHECKING

# We import MaintenanceRecord here for the relationship,
# assuming you will create it based on the Domain Model.
# if TYPE_CHECKING:                                                  UNCOMMENT AFTER THE CREATION OF MaintenanceRecord
   # from app.models.maintenancerecord import MaintenanceRecord


class EVTechnician(SQLModel, table=True):
    __tablename__ = "evtechnician"

    technicianID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phone: str
    passwordHash: str
    is_admin: bool = Field(default=False)

    # Relationship: An EV Technician performs many maintenance activities
 #   maintenance_records: List["MaintenanceRecord"] = Relationship(back_populates="technician")