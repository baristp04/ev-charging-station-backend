from sqlmodel import SQLModel, Field
from typing import Optional


class SystemAnalyst(SQLModel, table=True):
    __tablename__ = "systemanalyst"

    analystID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    phoneNumber: str
    passwordHash: str
    is_admin: bool = Field(default=True)

    #
    # If you look at the UML diagram, the System Analyst "monitors" the Charging Stations.
    # Unlike the Operations Specialist who "manages" specific stations (which requires a direct database link or foreign key so we know who manages what),
    # a System Analyst typically has global read-access to the entire network to generate revenue reports and view utilization stats .
    # Because of this, we don't need to add a specific relationship list or foreign key to this model or the ChargingStation model.
    # The analyst will just query the tables directly when those report endpoints are called.
    #
    #
    #
    #
    #
    #
    #