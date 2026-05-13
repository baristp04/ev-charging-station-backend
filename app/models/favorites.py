from sqlmodel import SQLModel, Field
from typing import Optional

class FavoriteStation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    driver_id: int = Field(foreign_key="evdriver.driverID") # Senin driver tablonun adı neyse
    station_id: int = Field(foreign_key="chargingstation.stationID")