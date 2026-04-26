from sqlmodel import SQLModel, Field
from typing import Optional


class SystemAnalyst(SQLModel, table=True):
    __tablename__ = "systemanalyst"

    analystID: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    passwordHash: str