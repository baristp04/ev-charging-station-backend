from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

class Report(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="evdriver.driverID") # Senin driver tablonun adı neyse ona göre düzelt
    message: str
    status: str = Field(default="pending") # pending, investigating, resolved
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))