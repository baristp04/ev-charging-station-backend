from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicle Registration"])

@router.post("/", response_model=Vehicle, status_code=status.HTTP_201_CREATED)
def register_vehicle(vehicle: Vehicle, db: Session = Depends(get_session)):
    """
    Sisteme yeni bir araç kaydeder. Plaka numarası (plateNumber) benzersiz olmalıdır.
    """
    # Plaka kontrolü
    statement = select(Vehicle).where(Vehicle.plateNumber == vehicle.plateNumber)
    existing_vehicle = db.exec(statement).first()
    
    if existing_vehicle:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="There is already a vehicle with this plate number."
        )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle

@router.get("/driver/{driver_id}", response_model=List[Vehicle])
def get_driver_vehicles(driver_id: int, db: Session = Depends(get_session)):
    """
    Belirli bir sürücüye (driver_id) ait kayıtlı tüm araçları getirir.
    """
    statement = select(Vehicle).where(Vehicle.driver_id == driver_id)
    vehicles = db.exec(statement).all()
    return vehicles

@router.get("/{vehicle_id}", response_model=Vehicle)
def get_vehicle_details(vehicle_id: int, db: Session = Depends(get_session)):
    """
    ID'ye göre araç detaylarını getirir.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle is not found.")
    return vehicle

@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_session)):
    """
    Aracı sistemden siler.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicles were found to delete.")
    
    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle is successfully deleted."}