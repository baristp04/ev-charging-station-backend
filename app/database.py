import os
from sqlmodel import create_engine, SQLModel, Session
from fastapi import Depends
from dotenv import load_dotenv

# .env dosyasındaki gizli değişkenleri (DATABASE_URL vb.) sisteme yükler
load_dotenv()

# Veritabanı URL'sini ortam değişkenlerinden güvenli bir şekilde çeker
DATABASE_URL = os.getenv("DATABASE_URL")

# Eğer .env dosyası yoksa veya içi boşsa sistemi uyarır
if not DATABASE_URL:
    raise ValueError("DATABASE_URL bulunamadı! Lütfen proje kök dizininde .env dosyasının olduğundan emin olun.")

# SQLAlchemy bazen bulut sağlayıcıların verdiği "postgres://" önekiyle hata verebilir, 
# standart "postgresql://" olmasını garantiliyoruz
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Veritabanı motorunu (engine) oluşturur
# echo=True parametresi, terminalde SQL sorgularını görmeni sağlar (geliştirme aşamasında faydalıdır)
engine = create_engine(DATABASE_URL, echo=True)

# Veritabanı tablolarını oluşturma fonksiyonu (Uygulama başlarken çalışır)
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# FastAPI endpoint'lerinde session yönetimi için kullanılan yardımcı (Dependency)
def get_session():
    with Session(engine) as session:
        yield session