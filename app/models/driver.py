from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.reservation import Reservation
    from app.models.notification import Notification

class EVDriver(SQLModel, table=True):
    __tablename__ = "evdriver"
    driverID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phoneNumber: str
    passwordHash: str
    
    # İlişkiler
    vehicles: List["Vehicle"] = Relationship(back_populates="driver")
    reservations: List["Reservation"] = Relationship(back_populates="driver")

    notifications: List["Notification"] = Relationship(back_populates="driver")  #added by Beyazt43