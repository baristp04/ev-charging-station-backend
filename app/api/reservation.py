from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.models.station import ChargingStation
from app.database import get_session # Veritabanı bağlantısı
from app.models.reservation import Reservation
from app.models.vehicle import Vehicle
from app.models.charger import Charger

#UC-01: Create a Charging Reservation
station_router = APIRouter(prefix="/api/stations", tags=["Stations"])

@station_router.get("/")
def get_stations(session: Session = Depends(get_session)):
    # Tüm istasyonları ve anlık durumlarını getirir
    stations = session.exec(select(ChargingStation)).all()
    return stations

@station_router.get("/{station_id}/chargers")
def get_station_chargers(station_id: int, session: Session = Depends(get_session)):
    station = session.get(ChargingStation, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")
    return station.chargers # İlişkili şarj ünitelerini döner

@station_router.post("/reserve")
def create_reservation(reservation_data: Reservation, session: Session = Depends(get_session)):
    # 1. Kural: 24 saatten fazla süre öncesine rezervasyon yapılamaz
    if reservation_data.startTime > datetime.utcnow() + timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Rezervasyon en fazla 24 saat önceden yapılabilir.")

    # 2. Kural: Rezervasyon süresi 2 saati geçemez
    duration = reservation_data.endTime - reservation_data.startTime
    if duration > timedelta(hours=2):
        raise HTTPException(status_code=400, detail="Maksimum şarj süresi 2 saattir.")

    # 3. Uyumluluk Kontrolü: Araç ve Şarj Ünitesi konnektörleri eşleşmeli
    charger = session.get(Charger, reservation_data.charger_id)
    vehicle = session.get(Vehicle, reservation_data.vehicle_id)
    if charger.connectorType != vehicle.connectorType:
        raise HTTPException(status_code=400, detail="Araç ve şarj ünitesi konnektörleri uyumsuz!")

    # 4. Çakışma Kontrolü (Double-booking): Aynı ünite o saatte dolu mu?
    # (Burada veritabanında tarih çakışması kontrol eden bir sorgu olmalı)
    overlap_query = select(Reservation).where(
    Reservation.charger_id == reservation_data.charger_id,
    Reservation.status == "active",
    Reservation.startTime < reservation_data.endTime, # Mevcut başlangıç, yeni bitişten önceyse
    Reservation.endTime > reservation_data.startTime  # Mevcut bitiş, yeni başlangıçtan sonraysa
    )
    existing_conflict = session.exec(overlap_query).first()

    if existing_conflict:
        raise HTTPException(status_code=409, detail="Seçilen saat diliminde bu ünite zaten rezerve edilmiş.")
    session.add(reservation_data)
    session.commit()
    session.refresh(reservation_data)
    return {"message": "Rezervasyon başarıyla oluşturuldu", "data": reservation_data}