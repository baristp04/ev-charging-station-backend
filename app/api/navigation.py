from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.models.station import ChargingStation
from app.models.charger import Charger
from app.database import get_session

navigation_router = APIRouter(prefix="/api/navigation", tags=["Navigation"])


def compute_status(station_status: str, available: int, total: int) -> str:
    # Station seviyesinde özel durum varsa DB kazanır
    if station_status in ("offline", "maintenance"):
        return station_status
    # Diğer durumlarda charger'lardan hesapla
    if total == 0:
        return "offline"
    if available == 0:
        return "occupied"
    return "available"


def get_charger_summary(station_id: int, session: Session):
    chargers = session.exec(
        select(Charger).where(Charger.station_id == station_id)
    ).all()
    total = len(chargers)
    available = sum(1 for c in chargers if c.status == "available")
    return chargers, total, available


@navigation_router.get("/stations")
def get_stations_for_map(session: Session = Depends(get_session)):
    stations = session.exec(select(ChargingStation)).all()
    result = []
    for s in stations:
        _, total, available = get_charger_summary(s.stationID, session)
        result.append({
            "id": s.stationID,
            "name": s.name,
            "location": s.location,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "status": compute_status(s.status, available, total),
            "total_chargers": total,
            "available_chargers": available
        })
    return result


@navigation_router.get("/stations/{station_id}")
def get_station_detail(station_id: int, session: Session = Depends(get_session)):
    station = session.get(ChargingStation, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")
    chargers, total, available = get_charger_summary(station_id, session)
    return {
        "id": station.stationID,
        "name": station.name,
        "location": station.location,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "status": compute_status(station.status, available, total),
        "total_chargers": total,
        "available_chargers": available,
        "chargers": [
            {
                "id": c.chargerID,
                "type": c.type,
                "connectorType": c.connectorType,
                "powerOutput": c.powerOutput,
                "pricePerKwh": c.pricePerKwh,
                "status": c.status
            }
            for c in chargers
        ]
    }