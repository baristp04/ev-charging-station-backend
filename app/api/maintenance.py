from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime
from app.database import get_session
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession

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

    if active_session:
        # Main Action: If a session is active, the system delays maintenance.
        charger.status = "maintenance_delayed"
        charger.maintenanceNotes = f"LOG: Aktif seans (ID: {active_session.sessionID}) nedeniyle bakım bitime ertelendi."
    else:
        # Main Action: System updates the charger status to "Offline".
        charger.status = "offline"
        charger.maintenanceNotes = f"LOG: Bakım planlandığı gibi başlatıldı."

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