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
    
    # 1. HAYAT KURTARAN DÖNÜŞÜM: Gelen string verilerini Python datetime objesine çeviriyoruz.
    # Bu işlemin FONKSİYONUN EN BAŞINDA (hiçbir if kontrolünden önce) olması ŞARTTIR.
    if isinstance(reservation_data.startTime, str):
        reservation_data.startTime = datetime.fromisoformat(reservation_data.startTime)
    if isinstance(reservation_data.endTime, str):
        reservation_data.endTime = datetime.fromisoformat(reservation_data.endTime)

    # Modelinde 'date' alanı zorunlu olduğu için, ayrı bir date verisi gelmezse startTime'dan çekip dolduruyoruz:
    if not reservation_data.date:
        reservation_data.date = reservation_data.startTime

    # 2. Kural: Maksimum 24 saat önceden (ARTIK HATA VERMEYECEK)
    if reservation_data.startTime > datetime.utcnow() + timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Rezervasyon en fazla 24 saat önceden yapılabilir.")
    
    # 3. Kural: Maksimum şarj süresi (2 saat)
    if reservation_data.endTime > reservation_data.startTime + timedelta(hours=2):
         raise HTTPException(status_code=400, detail="Maksimum şarj süresi 2 saattir.")

    # -- ARAÇ VE CİHAZ KONTROLLERİ BAŞLIYOR --
    
    # Cihazı bul
    charger = session.get(Charger, reservation_data.charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Şarj ünitesi bulunamadı.")
        
    # Aracı bul
    vehicle = session.get(Vehicle, reservation_data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Araç bulunamadı.")
        
    # Soket Uyumluluğu
    if charger.connectorType != vehicle.connectorType:
        raise HTTPException(status_code=400, detail="Araç ve şarj ünitesi konnektörleri uyumsuz!")

    # Çakışma (Overlap) Kontrolü
    overlapping = session.exec(
        select(Reservation).where(
            Reservation.charger_id == reservation_data.charger_id,
            Reservation.status == "active",
            Reservation.startTime < reservation_data.endTime,
            Reservation.endTime > reservation_data.startTime
        )
    ).first()

    if overlapping:
        raise HTTPException(status_code=409, detail="Seçilen saat diliminde bu ünite zaten rezerve edilmiş.")

    # Tüm kurallar geçildiyse veritabanına kaydet
    session.add(reservation_data)
    session.commit()
    session.refresh(reservation_data)
    
    return {"message": "Rezervasyon başarıyla oluşturuldu.", "data": reservation_data}