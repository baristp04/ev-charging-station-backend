from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from app.models.station import ChargingStation
from app.database import get_session
from app.models.reservation import Reservation
from app.models.vehicle import Vehicle
from app.models.charger import Charger

# UC-01: Charging Reservation Management
station_router = APIRouter(prefix="/api/stations", tags=["Stations"])


@station_router.get("/")
def get_stations(session: Session = Depends(get_session)):
    # Return all charging stations with their current state
    stations = session.exec(select(ChargingStation)).all()
    return stations


@station_router.get("/{station_id}/chargers")
def get_station_chargers(station_id: int, session: Session = Depends(get_session)):
    station = session.get(ChargingStation, station_id)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found.")
    # Return all chargers linked to this station
    return station.chargers


@station_router.post("/reserve")
def create_reservation(reservation_data: Reservation, session: Session = Depends(get_session)):

    # Convert incoming string values to Python datetime objects
    # This must happen before any validation checks
    if isinstance(reservation_data.startTime, str):
        reservation_data.startTime = datetime.fromisoformat(reservation_data.startTime)
    if isinstance(reservation_data.endTime, str):
        reservation_data.endTime = datetime.fromisoformat(reservation_data.endTime)

    # Fill date field from startTime if not provided separately
    if not reservation_data.date:
        reservation_data.date = reservation_data.startTime

    # Rule: Reservation cannot be made more than 24 hours in advance
    if reservation_data.startTime > datetime.now(timezone.utc) + timedelta(hours=24):
        raise HTTPException(status_code=400, detail="Reservations can only be made up to 24 hours in advance.")

    # Rule: Maximum charging session duration is 2 hours
    if reservation_data.endTime > reservation_data.startTime + timedelta(hours=2):
        raise HTTPException(status_code=400, detail="Maximum charging duration is 2 hours.")

    # Verify charger exists
    charger = session.get(Charger, reservation_data.charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found.")

    # Verify vehicle exists
    vehicle = session.get(Vehicle, reservation_data.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    # Check connector type compatibility between vehicle and charger
    if charger.connectorType != vehicle.connectorType:
        raise HTTPException(status_code=400, detail="Vehicle and charger connector types are incompatible.")

    # Check for overlapping active reservations on the same charger
    overlapping = session.exec(
        select(Reservation).where(
            Reservation.charger_id == reservation_data.charger_id,
            Reservation.status == "active",
            Reservation.startTime < reservation_data.endTime,
            Reservation.endTime > reservation_data.startTime
        )
    ).first()

    if overlapping:
        raise HTTPException(status_code=409, detail="This charger is already reserved for the selected time slot.")

    # All checks passed — save reservation to database
    session.add(reservation_data)
    session.commit()
    session.refresh(reservation_data)

    return {"message": "Reservation created successfully.", "data": reservation_data}


@station_router.get("/my-reservations/{driver_id}")
def get_my_reservations(driver_id: int, session: Session = Depends(get_session)):
    # Fetch all active reservations belonging to the given driver
    reservations = session.exec(
        select(Reservation).where(
            Reservation.driver_id == driver_id,
            Reservation.status == "active"
        )
    ).all()

    result = []
    for r in reservations:
        charger = session.get(Charger, r.charger_id)
        vehicle = session.get(Vehicle, r.vehicle_id)

        # Retrieve the station associated with this charger
        station = session.get(ChargingStation, charger.station_id) if charger else None

        result.append({
            "reservationID": r.reservationID,
            "date": r.date,
            "startTime": r.startTime,
            "endTime": r.endTime,
            "status": r.status,
            "charger_id": r.charger_id,
            "chargerType": charger.type if charger else None,
            "connectorType": charger.connectorType if charger else None,
            "stationName": station.name if station else None,
            "stationLocation": station.location if station else None,
            "vehiclePlate": vehicle.plateNumber if vehicle else None,
            "vehicleBrand": vehicle.brand if vehicle else None,
        })

    return result


@station_router.delete("/reservations/{reservation_id}")
def cancel_reservation(reservation_id: int, session: Session = Depends(get_session)):
    # Check if the reservation exists
    reservation = session.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found.")

    # Prevent cancelling an already cancelled reservation
    if reservation.status != "active":
        raise HTTPException(status_code=400, detail="This reservation is already cancelled.")

    # Soft delete — mark as cancelled instead of removing the record
    reservation.status = "cancelled"
    session.add(reservation)
    session.commit()
    session.refresh(reservation)

    return {"message": "Reservation successfully cancelled.", "reservationID": reservation_id}