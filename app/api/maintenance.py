from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from datetime import datetime, timezone
from app.database import get_session
from app.models.charger import Charger
from app.models.reservation import Reservation
from app.models.session import ChargingSession
from app.models.driver import EVDriver
from app.models.notification import Notification

maintenance_router = APIRouter(prefix="/api/maintenance", tags=["Station Maintenance"])


def _cancel_future_reservations_and_refund(charger_id: int, session: Session):
    """
    Finds all future active reservations for the given charger,
    marks them as 'failed', refunds estimated_cost to the driver's wallet,
    and sends a notification to each affected driver.
    Called whenever a charger is taken offline or put into maintenance.
    """
    now = datetime.now(timezone.utc)

    # Find all active reservations for this charger that haven't started yet
    future_reservations = session.exec(
        select(Reservation).where(
            Reservation.charger_id == charger_id,
            Reservation.status == "active",
            Reservation.startTime > now
        )
    ).all()

    refunded_count = 0
    for reservation in future_reservations:
        # Mark reservation as failed
        reservation.status = "failed"

        # Refund estimated_cost back to driver's wallet
        driver = session.get(EVDriver, reservation.driver_id)
        if driver and reservation.estimated_cost:
            driver.balance += reservation.estimated_cost
            session.add(driver)

            # Send notification to driver
            notification = Notification(
                driver_id=reservation.driver_id,
                type="maintenance",
                message=(
                    f"Your reservation on {reservation.startTime.strftime('%d %b %Y %H:%M')} "
                    f"has been cancelled because the charger went offline for maintenance. "
                    f"{reservation.estimated_cost:.2f} ₺ has been refunded to your wallet."
                ),
                isRead=False,
                sentAt=now
            )
            session.add(notification)

        session.add(reservation)
        refunded_count += 1

    return refunded_count


@maintenance_router.post("/schedule/{charger_id}")
def schedule_maintenance(
    charger_id: int,
    start_time: datetime,
    session: Session = Depends(get_session)
):
    """
    Primary Actor: Station Operator
    Schedules a maintenance window for a specific charger.
    - If the charger has an active charging session right now → delay maintenance
    - If maintenance is in the future or immediate with no active session → take offline
    - In both offline cases, cancel future reservations and refund drivers
    """
    charger = session.get(Charger, charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found.")

    now = datetime.now(timezone.utc)

    # Normalize start_time to UTC if no timezone info
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # Check for an active charging session on this charger right now
    active_session = session.exec(
        select(ChargingSession).join(Reservation).where(
            Reservation.charger_id == charger_id,
            ChargingSession.status == "active"
        )
    ).first()

    charger.maintenanceStartTime = start_time

    if active_session:
        # A vehicle is currently charging — cannot interrupt, delay maintenance
        charger.status = "maintenance_delayed"
        charger.maintenanceNotes = (
            f"LOG: Maintenance delayed due to active session (ID: {active_session.sessionID}). "
            f"Will begin after session ends."
        )
        # Still cancel future (not-yet-started) reservations and refund
        refunded = _cancel_future_reservations_and_refund(charger_id, session)
        session.add(charger)
        session.commit()
        session.refresh(charger)
        return {
            "message": "Active session in progress. Maintenance scheduled after session ends.",
            "charger_status": charger.status,
            "reservations_cancelled": refunded,
            "maintenance_log": charger.maintenanceNotes
        }

    elif start_time > now:
        # Maintenance is scheduled for the future — keep charger available until then
        charger.status = "available"
        charger.maintenanceNotes = (
            f"LOG: Maintenance scheduled for {start_time.strftime('%d/%m/%Y %H:%M')} UTC."
        )
        # Cancel future reservations that fall within or after the maintenance window
        refunded = _cancel_future_reservations_and_refund(charger_id, session)
        session.add(charger)
        session.commit()
        session.refresh(charger)
        return {
            "message": "Maintenance scheduled. Affected reservations cancelled and refunded.",
            "charger_status": charger.status,
            "reservations_cancelled": refunded,
            "maintenance_log": charger.maintenanceNotes
        }

    else:
        # Maintenance starts now — take charger offline immediately
        charger.status = "offline"
        charger.maintenanceNotes = "LOG: Maintenance started immediately."
        refunded = _cancel_future_reservations_and_refund(charger_id, session)
        session.add(charger)
        session.commit()
        session.refresh(charger)
        return {
            "message": "Charger taken offline. Affected reservations cancelled and refunded.",
            "charger_status": charger.status,
            "reservations_cancelled": refunded,
            "maintenance_log": charger.maintenanceNotes
        }


@maintenance_router.post("/cancel/{charger_id}")
def cancel_maintenance(charger_id: int, session: Session = Depends(get_session)):
    """
    Administrator manually cancels a scheduled maintenance (e.g., during peak hours).
    Charger is set back to available.
    """
    charger = session.get(Charger, charger_id)
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found.")

    if charger.status not in ["offline", "maintenance_delayed"]:
        raise HTTPException(
            status_code=400,
            detail="This charger is not currently in a maintenance state."
        )

    charger.status = "available"
    charger.maintenanceStartTime = None
    charger.maintenanceNotes = (
        "LOG: Maintenance cancelled by administrator (manual override)."
    )

    session.add(charger)
    session.commit()
    session.refresh(charger)

    return {
        "message": "Maintenance cancelled. Charger is back online.",
        "charger_status": charger.status,
        "maintenance_log": charger.maintenanceNotes
    }