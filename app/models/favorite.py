from sqlmodel import SQLModel, Field
from typing import Optional


class Favorite(SQLModel, table=True):
    """Stores a driver's favorite charging stations."""
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="evdriver.driverID")
    station_id: int = Field(foreign_key="chargingstation.stationID")