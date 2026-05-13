from sqlmodel import Field, Relationship
from typing import List, Optional, TYPE_CHECKING
from app.models.base_user import UserBase

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle
    from app.models.reservation import Reservation
    from app.models.notification import Notification
    from app.models.card import Card

class EVDriver(UserBase, table=True):
    __tablename__ = "evdriver"

    driverID: Optional[int] = Field(default=None, primary_key=True)
    balance: float = Field(default=0.0)

    # Relationships
    vehicles: List["Vehicle"] = Relationship(back_populates="driver")
    reservations: List["Reservation"] = Relationship(back_populates="driver")
    notifications: List["Notification"] = Relationship(back_populates="driver")
    cards: List["Card"] = Relationship(back_populates="driver")