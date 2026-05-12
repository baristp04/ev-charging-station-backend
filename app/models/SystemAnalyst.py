from sqlmodel import  Field
from typing import Optional
from app.models.base_user import UserBase

class SystemAnalyst(UserBase, table=True):
    __tablename__ = "systemanalyst"

    analystID: Optional[int] = Field(default=None, primary_key=True)

