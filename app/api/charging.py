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
        raise HTTPException(status_code=404, detail="Rezervasyon bulunamadı.")

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
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")

    # 1. Zaman Farkını Bul (Dakika cinsinden)
    now = datetime.now(timezone.utc)
    start_time = session_obj.startTime.replace(tzinfo=timezone.utc) if session_obj.startTime.tzinfo is None else session_obj.startTime
    elapsed_seconds = (now - start_time).total_seconds()
    elapsed_minutes = int(elapsed_seconds / 60)

    # 2. Otomatik Tüketim Simülasyonu (Örn: Dakikada 0.5 kWh harcandığını varsayalım)
    # Gerçek hayatta bu değer Charger'ın powerOutput değerine bağlıdır (Örn: 22kW / 60 dk)
    power_output = session_obj.reservation.charger.powerOutput if session_obj.reservation else 22.0
    kwh_per_minute = power_output / 60
    
    # Simüle edilen tüketim:
    simulated_energy = (elapsed_seconds / 3600) * power_output # Saatlik oran üzerinden net hesap
    
    # 3. Maliyet Hesaplama
    price_per_kwh = session_obj.reservation.charger.pricePerKwh if session_obj.reservation else 0.0
    current_cost = simulated_energy * price_per_kwh

    return {
        "sessionID": session_id,
        "status": session_obj.status,
        "simulation": "Active (Real-time calculation)",
        "energyConsumed": f"{simulated_energy:.4f} kWh",
        "currentCost": f"{current_cost:.2f} TL",
        "elapsedTime": f"{elapsed_minutes} dakika",
        "remainingTime": max(0, 120 - elapsed_minutes),
        "details": {
            "chargerPower": f"{power_output} kW",
            "unitPrice": f"{price_per_kwh} TL/kWh"
        }
    }

@router.post("/{session_id}/stop")
def stop_charging(session_id: int, reason: str = "completed", db: Session = Depends(get_session)):
    # 1. Oturumu ID ile biz bulalım, Swagger'dan obje istemeyelim
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")

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
        "message": f"Oturum durduruldu: {reason}",
        "summary": {
            "totalKwh": round(calculated_kwh, 2),
            "totalCost": round(calculated_cost, 2),
            "durationMinutes": int(elapsed_hours * 60)
        }
    }

@router.post("/{session_id}/emergency-fault")
def report_fault(session_id: int, db: Session = Depends(get_session)):
    """
    İstisna Durumu: Elektriksel arıza algılandığında şarjı anında keser 
    ve şarj ünitesini arıza moduna alır.
    """
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı.")

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
        raise HTTPException(status_code=500, detail="Acil durdurma sırasında veritabanı hatası oluştu.")