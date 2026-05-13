from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models.favorite import Favorite
from app.models.station import ChargingStation
from pydantic import BaseModel

router = APIRouter()


class FavoriteCreate(BaseModel):
    driver_id: int
    station_id: int


@router.post("/")
def add_favorite(payload: FavoriteCreate):
    """Add a station to driver's favorites. Prevents duplicates."""
    with Session(engine) as session:
        # Check for existing favorite
        existing = session.exec(
            select(Favorite).where(
                Favorite.driver_id == payload.driver_id,
                Favorite.station_id == payload.station_id
            )
        ).first()

        if existing:
            raise HTTPException(status_code=409, detail="Already in favorites")

        favorite = Favorite(driver_id=payload.driver_id, station_id=payload.station_id)
        session.add(favorite)
        session.commit()
        session.refresh(favorite)
        return {"message": "Added to favorites", "id": favorite.id}


@router.delete("/{driver_id}/{station_id}")
def remove_favorite(driver_id: int, station_id: int):
    """Remove a station from driver's favorites."""
    with Session(engine) as session:
        favorite = session.exec(
            select(Favorite).where(
                Favorite.driver_id == driver_id,
                Favorite.station_id == station_id
            )
        ).first()

        if not favorite:
            raise HTTPException(status_code=404, detail="Favorite not found")

        session.delete(favorite)
        session.commit()
        return {"message": "Removed from favorites"}


@router.get("/{driver_id}")
def get_favorites(driver_id: int):
    """Return all favorite stations for a driver with full station details."""
    with Session(engine) as session:
        favorites = session.exec(
            select(Favorite).where(Favorite.driver_id == driver_id)
        ).all()

        station_ids = [f.station_id for f in favorites]

        if not station_ids:
            return []

        stations = session.exec(
            select(ChargingStation).where(ChargingStation.stationID.in_(station_ids))
        ).all()

        return stations