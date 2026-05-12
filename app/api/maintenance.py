from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from app.database import get_session
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from datetime import datetime, timezone
from datetime import timedelta

# Router Tanımı
maintenance_router = APIRouter(prefix="/api/maintenance", tags=["Station Maintenance"])

@maintenance_router.post("/schedule/{charger_id}")
def schedule_maintenance(charger_id: int, start_time: datetime, session: Session = Depends(get_session)):
    """
    Primary Actor: Station Operator
    Main Action: Schedules a maintenance window for a specific charger.
    """
    charger = session.get(Charger, charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Şarj ünitesi bulunamadı.")

    # Main Action: System checks for active charging sessions on that unit.
    # Reservation tablosu üzerinden cihazdaki aktif seansları buluyoruz.
    active_session_query = select(ChargingSession).join(Reservation).where(
        Reservation.charger_id == charger_id,
        ChargingSession.status == "active"
    )
    active_session = session.exec(active_session_query).first()

    # Bakım zamanını kaydet
    charger.maintenanceStartTime = start_time

    # Şimdiki zamanı al (UTC kullanıyorsanız utcnow, yerel ise now)
    current_time = datetime.now(timezone.utc)

    if active_session:
        # Durum 1: Şu an araç şarj oluyor -> Ertele
        charger.status = "maintenance_delayed"
        charger.maintenanceNotes = f"LOG: Aktif seans (ID: {active_session.sessionID}) nedeniyle bakım bitime ertelendi."
    elif start_time > current_time:
        # Durum 2: Bakım ileri bir tarihe planlandı -> Hemen kapatma!
        # Mesajı Türkiye saatine (UTC+3) çevirerek göster
        local_time = start_time + timedelta(hours=3)
        charger.status = "available"
        charger.maintenanceNotes = f"LOG: Bakım {local_time.strftime('%d/%m/%Y %H:%M')} tarihi için sisteme planlandı."
    else:
        # Durum 3: Bakım zamanı geldi ve aktif seans yok -> Çevrimdışı yap
        charger.status = "offline"
        charger.maintenanceNotes = "LOG: Bakım planlandığı gibi başlatıldı."

    session.add(charger)
    session.commit()
    session.refresh(charger)

    # Outputs: Updated station status and maintenance log entry.
    return {
        "message": "Bakım talebi işlendi.",
        "charger_status": charger.status,
        "maintenance_log_entry": charger.maintenanceNotes
    }


@maintenance_router.post("/cancel/{charger_id}")
def cancel_maintenance(charger_id: int, session: Session = Depends(get_session)):
    """
    Exceptions: Manual Override - Administrator cancels the maintenance (e.g., peak hours).
    """
    charger = session.get(Charger, charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Şarj ünitesi bulunamadı.")

    if charger.status not in ["offline", "maintenance_delayed"]:
        raise HTTPException(status_code=400, detail="Bu ünite şu an bakım durumunda değil.")

    # Override Action: Cihazı tekrar aktif hale getir.
    charger.status = "available"
    charger.maintenanceStartTime = None
    charger.maintenanceNotes = "LOG: Bakım, yoğun talep (peak hours) nedeniyle yönetici tarafından iptal edildi."

    session.add(charger)
    session.commit()
    session.refresh(charger)

    # Outputs: Updated station status.
    return {
        "message": "Manuel Override başarılı. Cihaz tekrar kullanıma açıldı.",
        "charger_status": charger.status,
        "maintenance_log_entry": charger.maintenanceNotes
    }