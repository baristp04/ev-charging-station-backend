from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.driver import EVDriver


class Notification(SQLModel, table=True):
    __tablename__ = "notification"

    notificationID: Optional[int] = Field(default=None, primary_key=True)
    # The UML specifies this as an Enum (reservation, session, alert) [cite: 545]
    # Storing it as a string is the most straightforward approach in SQLModel
    type: str
    message: str
    sentAt: datetime = Field(default_factory=datetime.utcnow)
    isRead: bool = Field(default=False)

    # Relationship: A notification is received by a specific EV Driver
    driver_id: int = Field(foreign_key="evdriver.driverID")
    driver: Optional["EVDriver"] = Relationship(back_populates="notifications")