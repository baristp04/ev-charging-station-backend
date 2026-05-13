from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime, timedelta
from typing import List
from app.database import get_session
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.reservation import Reservation

router = APIRouter(prefix="/api/v1/charging", tags=["Charging"])

UNIT_PRICE = 0.50  # 1 kWh başına birim fiyat

@router.post("/start", response_model=ChargingSession)
def start_session(reservation_id: int, db: Session = Depends(get_session)):
    """
    Fiziksel bağlantı sinyali alındığında rezervasyona bağlı şarj oturumunu başlatır.
    """
    # Rezervasyon kontrolü
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation is not found")

    new_session = ChargingSession(
        reservation_id=reservation_id,
        startTime=datetime.utcnow(),
        status="active",
        energyConsumed=0.0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

from datetime import datetime, timezone, timedelta

@router.get("/{session_id}/status")
def get_session_status(session_id: int, db: Session = Depends(get_session)):
   
    session_obj = db.exec(
    select(ChargingSession).where(ChargingSession.sessionID == session_id)
).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session is not found")

    now = datetime.now(timezone.utc)
    start_time = session_obj.startTime.replace(tzinfo=timezone.utc) if session_obj.startTime.tzinfo is None else session_obj.startTime
    elapsed_seconds = (now - start_time).total_seconds()
    
    # Simülasyon Verileri
    power_output = session_obj.reservation.charger.powerOutput if session_obj.reservation else 22.0
    simulated_energy = (elapsed_seconds / 3600) * power_output
    price_per_kwh = session_obj.reservation.charger.pricePerKwh if session_obj.reservation else 0.0
    current_cost = simulated_energy * price_per_kwh

    # YÜZDE HESABI: Arabanın 0'dan 100'e 2 saatte dolduğunu varsayalım (120 dk)
    # Veya arabanın batarya kapasitesine göre oranlayabilirsin.
    total_estimated_time = 120 # 2 saatlik simülasyon
    progress_percentage = min(100, int((elapsed_seconds / (total_estimated_time * 60)) * 100))

    return {
        "sessionID": session_id,
        "status": session_obj.status,
        "percentage": progress_percentage, # EKLENDİ
        "energyConsumed": round(simulated_energy, 2),
        "currentCost": round(current_cost, 2),
        "elapsedTime": int(elapsed_seconds / 60),
        "remainingTime": max(0, total_estimated_time - int(elapsed_seconds / 60)),
        "chargerPower": power_output
    }

@router.post("/{session_id}/stop")
def stop_charging(session_id: int, reason: str = "completed", db: Session = Depends(get_session)):
    # 1. Oturumu ID ile biz bulalım, Swagger'dan obje istemeyelim
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session is not found")

    # 2. Zamanı ve tüketimi otomatiğe bağlayalım
    now = datetime.now(timezone.utc)
    start_time = session_obj.startTime.replace(tzinfo=timezone.utc) if session_obj.startTime.tzinfo is None else session_obj.startTime
    
    # Geçen süreyi saate çevir
    elapsed_hours = (now - start_time).total_seconds() / 3600
    # İstasyon gücünü al (yoksa 22kW kabul et)
    power = session_obj.reservation.charger.powerOutput if session_obj.reservation else 22.0
    
    calculated_kwh = elapsed_hours * power
    price = session_obj.reservation.charger.pricePerKwh if session_obj.reservation else 0.0
    calculated_cost = calculated_kwh * price

    # 3. Veritabanı güncellemeleri
    session_obj.status = reason
    session_obj.endTime = now
    session_obj.energyConsumed = calculated_kwh
    
    # Ödeme kaydı
    new_payment = Payment(
        session_id=session_id,
        amount=calculated_cost,
        status="pending",
        method="credit_card",  # Buraya veritabanının kabul edeceği bir değer ekle
        transactionDate=datetime.now(timezone.utc)
    )
    
    db.add(session_obj)
    db.add(new_payment)
    db.commit()
    db.refresh(new_payment)

    return {
        "message": f"Session is stopped: {reason}",
        "summary": {
            "totalKwh": round(calculated_kwh, 2),
            "totalCost": round(calculated_cost, 2),
            "durationMinutes": int(elapsed_hours * 60)
        }
    }

# app/api/charging.py içine ekle
@router.get("/active-session-for-driver/{driver_id}")
def get_active_session_id(driver_id: int, db: Session = Depends(get_session)):
    statement = select(ChargingSession).join(Reservation).where(
        Reservation.driver_id == driver_id,
        ChargingSession.status == "active"
    )
    result = db.exec(statement).first()
    if not result:
        return {"sessionID": None}
    return {"sessionID": result.sessionID}

@router.post("/{session_id}/emergency-fault")
def report_fault(session_id: int, db: Session = Depends(get_session)):
    """
    İstisna Durumu: Elektriksel arıza algılandığında şarjı anında keser 
    ve şarj ünitesini arıza moduna alır.
    """
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session is not found.")

    try:
        # 1. Oturum durumunu hemen güncelle
        session_obj.status = "emergency_stopped"
        session_obj.endTime = datetime.now(timezone.utc)
        
        # 2. Şarj ünitesini (Charger) devre dışı bırak
        # Reservation üzerinden Charger'a ulaşıyoruz
        if session_obj.reservation and session_obj.reservation.charger:
            session_obj.reservation.charger.status = "faulted"
            session_obj.reservation.charger.maintenanceNotes = "Electrical fault reported."

        db.add(session_obj)
        db.commit()
        
        # 3. Ödeme ve diğer detaylar için stop_charging'i arkadan çağırabiliriz
        # Veya stop_charging fonksiyonunu 'emergency' parametresini alacak şekilde esnetebilirsin.
        return stop_charging(session_id, reason="electrical_fault", db = db)

    except Exception as e:
        db.rollback()
        # Kritik hata: Loglama yapılması şart
        print(f"CRITICAL: Emergency stop failed for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Database error happened during emergency fault.")