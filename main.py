from fastapi import FastAPI
from app.database import create_db_and_tables
from app.api.reservation import station_router 

from app.models.driver import EVDriver
from app.models.vehicle import Vehicle
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.payment import Payment

# 1. FastAPI uygulamasını başlatıyoruz
app = FastAPI(title="EV Charging Station Management System")

# 2. Veritabanı tablolarını uygulama başlarken oluşturuyoruz
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(station_router)

@app.get("/")
def root():
    return {"message": "EV Charging System API is running"}