from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from app.models.session import ChargingSession

class Payment(SQLModel, table=True):
    __tablename__ = "payment"
    paymentID: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    method: str
    status: str = Field(default="completed")
    transactionDate: datetime = Field(default_factory=datetime.utcnow)
    receiptURL: Optional[str] = None
    
    session_id: int = Field(foreign_key="chargingsession.sessionID")
    session: "ChargingSession" = Relationship(back_populates="payment")