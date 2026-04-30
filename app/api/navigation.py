from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from app.models.station import ChargingStation
from app.database import get_session

navigation_router = APIRouter(prefix="/api/navigation", tags=["Navigation"])

@navigation_router.get("/stations")
def get_stations_for_map(session: Session = Depends(get_session)):
    stations = session.exec(select(ChargingStation)).all()
    return [
        {
            "id": s.stationID,
            "name": s.name,
            "location": s.location,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "status": s.status
        }
        for s in stations
    ]

@navigation_router.get("/stations/{station_id}")
def get_station_detail(station_id: int, session: Session = Depends(get_session)):
    station = session.get(ChargingStation, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="İstasyon bulunamadı")
    return {
        "id": station.stationID,
        "name": station.name,
        "location": station.location,
        "latitude": station.latitude,
        "longitude": station.longitude,
        "status": station.status
    }