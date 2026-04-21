from sqlmodel import create_engine, SQLModel, Session
from fastapi import Depends

# SQLite kullanarak dosya tabanlı bir veritabanı oluşturur (Geçici çözüm)
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Veritabanı motorunu (engine) oluşturur
engine = create_engine(sqlite_url, echo=True)

# Veritabanı tablolarını oluşturma fonksiyonu (R13 gereksinimi için)
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# FastAPI endpoint'lerinde session yönetimi için kullanılan yardımcı (Dependency)
def get_session():
    with Session(engine) as session:
        yield session