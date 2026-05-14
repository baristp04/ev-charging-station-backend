from app.utils.notifications import create_system_notification
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from app.database import get_session
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.driver import EVDriver
from app.models.notification import Notification

router = APIRouter(prefix="/api/v1/charging", tags=["Charging"])


@router.post("/start")
def start_session(reservation_id: int, db: Session = Depends(get_session)):
    """
    Driver presses 'Start Charging' — creates a live session for the reservation.
    Rules:
      - Reservation must exist and belong to an active status
      - startTime must have been reached (cannot start early)
      - No duplicate active session allowed for the same reservation
    """
    reservation = db.get(Reservation, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found.")

    if reservation.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Reservation is not active (status: {reservation.status})."
        )

    now = datetime.now(timezone.utc)
    start_time = reservation.startTime
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # Prevent starting before the reserved time slot
    if now < start_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot start session before the reserved time."
        )

    # Prevent duplicate active session for the same reservation
    existing = db.exec(
        select(ChargingSession).where(
            ChargingSession.reservation_id == reservation_id,
            ChargingSession.status == "active"
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active session already exists for this reservation."
        )

    new_session = ChargingSession(
        reservation_id=reservation_id,
        startTime=now,
        status="active",
        energyConsumed=0.0,
        totalCost=0.0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    # Change UTC to local timezone for notification
    local_time = reservation.startTime + timedelta(hours=3)
    display_time = local_time.strftime("%d/%m/%Y %H:%M")

    create_system_notification(
        db, 
        driver_id= reservation.driver_id,  
        n_type="Active Session", 
        message=f"Your charging session at {display_time} started!"
    )
    return new_session


@router.get("/{session_id}/status")
def get_session_status(session_id: int, db: Session = Depends(get_session)):
    """
    Returns live simulation data for the active session.
    Energy and cost are calculated from elapsed time × charger power output.
    """
    session_obj = db.exec(
        select(ChargingSession).where(ChargingSession.sessionID == session_id)
    ).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    now = datetime.now(timezone.utc)
    start_time = session_obj.startTime
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    # Use actual endTime for completed sessions, current time for active
    reference_time = now
    if session_obj.status != "active" and session_obj.endTime:
        end_time = session_obj.endTime
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
        reference_time = end_time

    elapsed_seconds = (reference_time - start_time).total_seconds()

    reservation = session_obj.reservation
    power_output = reservation.charger.powerOutput if reservation else 22.0
    price_per_kwh = reservation.charger.pricePerKwh if reservation else 0.0

    # Calculate total session duration from reservation
    total_seconds = 3600.0  # fallback: 1 hour
    if reservation:
        end_time_res = reservation.endTime
        if end_time_res.tzinfo is None:
            end_time_res = end_time_res.replace(tzinfo=timezone.utc)
        start_time_res = reservation.startTime
        if start_time_res.tzinfo is None:
            start_time_res = start_time_res.replace(tzinfo=timezone.utc)
        total_seconds = (end_time_res - start_time_res).total_seconds()

    simulated_kwh = (elapsed_seconds / 3600) * power_output
    current_cost = simulated_kwh * price_per_kwh
    progress = min(100, int((elapsed_seconds / total_seconds) * 100))
    remaining_minutes = max(0, int((total_seconds - elapsed_seconds) / 60))

    return {
        "sessionID": session_id,
        "status": session_obj.status,
        "progress": progress,
        "energyConsumed": round(simulated_kwh, 2),
        "currentCost": round(current_cost, 2),
        "elapsedMinutes": int(elapsed_seconds / 60),
        "remainingMinutes": remaining_minutes,
        "chargerPower": power_output,
        "totalCost": round(session_obj.totalCost, 2) if session_obj.status != "active" else None
    }


@router.post("/{session_id}/stop")
def stop_charging(session_id: int, db: Session = Depends(get_session)):
    """
    Ends the charging session at endTime (called when session duration is complete).
    - Calculates actual kWh consumed and cost based on elapsed time
    - Updates session: totalCost, endTime, status → completed
    - Updates reservation status → completed
    - Creates a payment record
    Note: Payment was already deducted from wallet at reservation time (estimated_cost).
    No additional deduction here — cost tracking only.
    """
    session_obj = db.get(ChargingSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session_obj.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Session is not active (status: {session_obj.status})."
        )

    now = datetime.now(timezone.utc)
    start_time = session_obj.startTime
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    elapsed_hours = (now - start_time).total_seconds() / 3600
    reservation = session_obj.reservation
    power = reservation.charger.powerOutput if reservation else 22.0
    price = reservation.charger.pricePerKwh if reservation else 0.0

    calculated_kwh = elapsed_hours * power
    calculated_cost = calculated_kwh * price

    # Update session
    session_obj.status = "completed"
    session_obj.endTime = now
    session_obj.energyConsumed = round(calculated_kwh, 2)
    session_obj.totalCost = round(calculated_cost, 2)

    # Mark reservation as completed
    if reservation:
        reservation.status = "completed"
        db.add(reservation)

    # Create payment record for bookkeeping (wallet was already charged at reservation)
    payment = Payment(
        session_id=session_id,
        amount=round(calculated_cost, 2),
        status="completed",
        method="wallet",
        transactionDate=now
    )

    db.add(session_obj)
    db.add(payment)
    db.commit()

    # Change UTC to local timezone for notification
    local_time = reservation.startTime + timedelta(hours=3)
    display_time = local_time.strftime("%d/%m/%Y %H:%M")

    create_system_notification(
        db, 
        driver_id= reservation.driver_id,  
        n_type="Active Session", 
        message=f"Your charging session at {display_time} stopped!"
    )

    return {
        "message": "Charging session completed.",
        "summary": {
            "totalKwh": round(calculated_kwh, 2),
            "totalCost": round(calculated_cost, 2),
            "durationMinutes": int(elapsed_hours * 60)
        }
    }


@router.get("/active-session-for-driver/{driver_id}")
def get_active_session_for_driver(driver_id: int, db: Session = Depends(get_session)):
    """
    Returns the active session ID for a driver, if any.
    Used by the frontend to redirect to the live session page on load.
    """
    result = db.exec(
        select(ChargingSession).join(Reservation).where(
            Reservation.driver_id == driver_id,
            ChargingSession.status == "active"
        )
    ).first()
    return {"sessionID": result.sessionID if result else None}