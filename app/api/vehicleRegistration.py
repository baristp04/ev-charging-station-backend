from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.vehicle import Vehicle

router = APIRouter(prefix="/api/v1/vehicles", tags=["Vehicle Registration"])

@router.post("/", response_model=Vehicle, status_code=status.HTTP_201_CREATED)
def register_vehicle(vehicle: Vehicle, db: Session = Depends(get_session)):
    """
    Sisteme yeni bir ara├ğ kaydeder. Plaka numaras─▒ (plateNumber) benzersiz olmal─▒d─▒r.
    """
    # Plaka kontrol├╝
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
    Belirli bir s├╝r├╝c├╝ye (driver_id) ait kay─▒tl─▒ t├╝m ara├ğlar─▒ getirir.
    """
    statement = select(Vehicle).where(Vehicle.driver_id == driver_id)
    vehicles = db.exec(statement).all()
    return vehicles

@router.get("/{vehicle_id}", response_model=Vehicle)
def get_vehicle_details(vehicle_id: int, db: Session = Depends(get_session)):
    """
    ID'ye g├Âre ara├ğ detaylar─▒n─▒ getirir.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle is not found.")
    return vehicle

@router.put("/{vehicle_id}", response_model=Vehicle)
def update_vehicle(vehicle_id: int, updated_data: Vehicle, db: Session = Depends(get_session)):
    """
    Mevcut bir arac─▒n bilgilerini g├╝nceller. 
    Plaka numaras─▒ de─şi┼ştirilirse, yeni plakan─▒n sistemde benzersiz oldu─şu kontrol edilir.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Vehicle not found."
        )

    if updated_data.plateNumber != vehicle.plateNumber:
        statement = select(Vehicle).where(Vehicle.plateNumber == updated_data.plateNumber)
        existing_with_same_plate = db.exec(statement).first()
        if existing_with_same_plate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="This plate number is already registered to another vehicle."
            )

    update_dict = updated_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(vehicle, key, value)

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle

@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_session)):
    """
    Arac─▒ sistemden siler.
    """
    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="No vehicles were found to delete.")
    
    db.delete(vehicle)
    db.commit()
    return {"message": "Vehicle is successfully deleted."}
