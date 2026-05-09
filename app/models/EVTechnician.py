from sqlmodel import Field
from typing import List, Optional, TYPE_CHECKING
from app.models.base_user import UserBase

class EVTechnician(UserBase, table=True):
    __tablename__ = "evtechnician"

    technicianID: Optional[int] = Field(default=None, primary_key=True)

