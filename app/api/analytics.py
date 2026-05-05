"""
app/api/analytics.py — UC-04: Generate Administrative Revenue Reports
Add to main.py:
    from app.api.analytics import analytics_router
    app.include_router(analytics_router)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func, col
from datetime import datetime, date, timedelta
from typing import Optional

from app.database import get_session
from app.models.session import ChargingSession
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.charger import Charger
from app.models.station import ChargingStation

analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ── Helper: parse date strings ───────────────────────────────────────────────
def _parse_date(d: str, label: str) -> datetime:
    try:
        return datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {label} format. Use YYYY-MM-DD.")


# ── UC-04 Main Endpoint ───────────────────────────────────────────────────────
@analytics_router.get("/revenue")
def get_revenue_report(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date:   str = Query(..., description="End date   (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
):
    """
    UC-04: Generate Administrative Revenue Reports.
    Returns:
      - summary: total revenue, total sessions, total energy consumed
      - revenue_by_station: per-station breakdown
      - peak_hour_analysis: session count and revenue grouped by hour of day
      - recent_transactions: last 50 completed payments in the range
    """
    start_dt = _parse_date(start_date, "start_date")
    end_dt   = _parse_date(end_date,   "end_date") + timedelta(days=1)  # inclusive end

    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="start_date must be before end_date.")

    # ── All sessions in range ─────────────────────────────────────────────────
    sessions_in_range = session.exec(
        select(ChargingSession).where(
            ChargingSession.startTime >= start_dt,
            ChargingSession.startTime <  end_dt,
            ChargingSession.status == "completed"
        )
    ).all()

    # ── EXCEPTION: no data ────────────────────────────────────────────────────
    if not sessions_in_range:
        return {
            "period": {"start": start_date, "end": end_date},
            "summary": {
                "total_revenue_tl": 0,
                "total_sessions": 0,
                "total_energy_kwh": 0,
                "average_session_cost_tl": 0
            },
            "revenue_by_station": [],
            "peak_hour_analysis": [],
            "recent_transactions": [],
            "message": "No completed sessions found for the selected period."
        }

    session_ids = [cs.sessionID for cs in sessions_in_range]

    # ── Summary ───────────────────────────────────────────────────────────────
    total_revenue = round(sum(cs.totalCost       for cs in sessions_in_range), 2)
    total_energy  = round(sum(cs.energyConsumed  for cs in sessions_in_range), 2)
    total_count   = len(sessions_in_range)
    avg_cost      = round(total_revenue / total_count, 2) if total_count else 0

    # ── Revenue by station ────────────────────────────────────────────────────
    # ChargingSession → Reservation → Charger → ChargingStation
    reservation_ids = [cs.reservation_id for cs in sessions_in_range]

    reservations = session.exec(
        select(Reservation).where(col(Reservation.reservationID).in_(reservation_ids))
    ).all()

    charger_ids = list({r.charger_id for r in reservations})
    chargers    = session.exec(
        select(Charger).where(col(Charger.chargerID).in_(charger_ids))
    ).all()
    charger_map = {c.chargerID: c for c in chargers}

    station_ids = list({c.station_id for c in chargers})
    stations    = session.exec(
        select(ChargingStation).where(col(ChargingStation.stationID).in_(station_ids))
    ).all()
    station_map = {s.stationID: s for s in stations}

    # Build a lookup: session_id → station
    res_by_id = {r.reservationID: r for r in reservations}
    station_stats: dict[int, dict] = {}

    for cs in sessions_in_range:
        res      = res_by_id.get(cs.reservation_id)
        if not res:
            continue
        charger  = charger_map.get(res.charger_id)
        if not charger:
            continue
        st_id    = charger.station_id
        st_name  = station_map.get(st_id, ChargingStation(name="Unknown", location="", latitude=0, longitude=0)).name

        if st_id not in station_stats:
            station_stats[st_id] = {
                "station_id":   st_id,
                "station_name": st_name,
                "session_count": 0,
                "total_revenue_tl": 0.0,
                "total_energy_kwh": 0.0
            }
        station_stats[st_id]["session_count"]    += 1
        station_stats[st_id]["total_revenue_tl"] += cs.totalCost
        station_stats[st_id]["total_energy_kwh"] += cs.energyConsumed

    revenue_by_station = []
    for stats in station_stats.values():
        stats["total_revenue_tl"] = round(stats["total_revenue_tl"], 2)
        stats["total_energy_kwh"] = round(stats["total_energy_kwh"], 2)
        revenue_by_station.append(stats)
    revenue_by_station.sort(key=lambda x: x["total_revenue_tl"], reverse=True)

    # ── Peak hour analysis (0–23) ─────────────────────────────────────────────
    hour_stats: dict[int, dict] = {h: {"hour": h, "session_count": 0, "total_revenue_tl": 0.0} for h in range(24)}

    for cs in sessions_in_range:
        h = cs.startTime.hour
        hour_stats[h]["session_count"]    += 1
        hour_stats[h]["total_revenue_tl"] += cs.totalCost

    peak_hour_analysis = []
    for h in range(24):
        stats = hour_stats[h]
        peak_hour_analysis.append({
            "hour":             f"{h:02d}:00",
            "hour_int":         h,
            "session_count":    stats["session_count"],
            "total_revenue_tl": round(stats["total_revenue_tl"], 2)
        })

    # ── Recent transactions (last 50) ────────────────────────────────────────
    payments = session.exec(
        select(Payment).where(
            col(Payment.session_id).in_(session_ids),
            Payment.status == "completed"
        ).order_by(col(Payment.transactionDate).desc()).limit(50)
    ).all()

    recent_transactions = []
    session_map = {cs.sessionID: cs for cs in sessions_in_range}
    for pay in payments:
        cs  = session_map.get(pay.session_id)
        res = res_by_id.get(cs.reservation_id) if cs else None
        c   = charger_map.get(res.charger_id) if res else None
        st  = station_map.get(c.station_id) if c else None

        recent_transactions.append({
            "payment_id":       pay.paymentID,
            "amount_tl":        pay.amount,
            "method":           pay.method,
            "transaction_date": pay.transactionDate.isoformat(),
            "station_name":     st.name if st else "N/A",
            "energy_kwh":       cs.energyConsumed if cs else 0,
            "receipt_url":      pay.receiptURL
        })

    return {
        "period": {"start": start_date, "end": end_date},
        "summary": {
            "total_revenue_tl":      total_revenue,
            "total_sessions":        total_count,
            "total_energy_kwh":      total_energy,
            "average_session_cost_tl": avg_cost
        },
        "revenue_by_station": revenue_by_station,
        "peak_hour_analysis":  peak_hour_analysis,
        "recent_transactions": recent_transactions
    }
