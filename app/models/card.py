from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from app.models.driver import EVDriver

class Card(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cardName: str  # Örn: "Ziraat Banka Kartım"
    cardHolderName: str
    cardNumber: str # Veritabanında maskelenmiş veya şifreli tutulabilir
    expiryDate: str # MM/YY
    cvv: str # Ödeme anında doğrulanacak bilgi
    driver_id: int = Field(foreign_key="evdriver.driverID")

    # Sürücü ile ilişki (Opsiyonel ama temiz kod için iyi)
    driver: "EVDriver" = Relationship(back_populates="cards")