from sqlmodel import SQLModel, Field

class UserBase(SQLModel):
    name: str
    email: str = Field(unique=True, index=True)
    phoneNumber: str
    passwordHash: str
    role: str